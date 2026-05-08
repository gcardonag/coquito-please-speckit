"""update_batch — PUT /api/v1/batches/{id}

Partial update of an OPEN or CLOSED batch. COMPLETED batches are read-only.
Enforces name uniqueness, variety-removal guard (FR-012), and active-variety check.
Chef role required.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from typing import Any

from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef
from src.models.batch import Batch
from src.services.dynamodb import (
    ItemNotFoundError,
    batches_table_name,
    get_item,
    requests_table_name,
    scan_table,
    update_item,
    varieties_table_name,
)


logger = Logger(service="coquito-update-batch")


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def _error(code: str, message: str, status: int = 400) -> dict[str, Any]:
    return _response(status, {"code": code, "message": message})


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for PUT /api/v1/batches/{id}."""
    denied = require_chef(event)
    if denied:
        return denied

    batch_id = (event.get("pathParameters") or {}).get("id", "")
    if not batch_id:
        return _error("VALIDATION_ERROR", "Batch ID is required.")

    try:
        item = get_item(batches_table_name(), {"batchId": batch_id})
    except ItemNotFoundError:
        return _error("BATCH_NOT_FOUND", f"Batch '{batch_id}' not found.", 404)

    if item.get("status") == "COMPLETED":
        return _error("BATCH_COMPLETED", "Completed batches cannot be edited.", 409)

    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _error("VALIDATION_ERROR", "Request body is not valid JSON.")

    updates: dict[str, Any] = {}

    if "batchName" in payload:
        name = (payload["batchName"] or "").strip()
        if not name:
            return _error("VALIDATION_ERROR", "batchName must not be empty.")
        if Batch.name_exists(name, exclude_batch_id=batch_id):
            return _error("BATCH_NAME_CONFLICT", f"A batch named '{name}' already exists.")
        updates["batchName"] = name

    if "cutoffDate" in payload:
        cutoff_str = (payload["cutoffDate"] or "").strip()
        try:
            cutoff = date.fromisoformat(cutoff_str)
        except ValueError:
            return _error("VALIDATION_ERROR", "cutoffDate must be a valid YYYY-MM-DD date.")
        if cutoff < date.today():
            return _error("CUTOFF_DATE_IN_PAST", "cutoffDate must be today or a future date.")
        updates["cutoffDate"] = cutoff_str

    if "maxBottleVolumeMl" in payload:
        try:
            vol = int(payload["maxBottleVolumeMl"])
            if vol <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return _error("VALIDATION_ERROR", "maxBottleVolumeMl must be a positive integer.")
        updates["maxBottleVolumeMl"] = vol

    if "availableVarietyIds" in payload:
        new_ids: list[str] = payload["availableVarietyIds"] or []
        if not new_ids:
            return _error("VALIDATION_ERROR", "availableVarietyIds must contain at least one variety.")

        # Variety-removal guard (FR-012): block removal of varieties with non-CANCELLED requests
        current_ids = set(item.get("availableVarietyIds", []))
        removing = current_ids - set(new_ids)
        if removing:
            requests = scan_table(requests_table_name())
            # Count non-CANCELLED requests per variety for this batch
            variety_counts: dict[str, int] = defaultdict(int)
            for req in requests:
                if req.get("batchId") == batch_id and req.get("status") != "CANCELLED":
                    vid = req.get("varietyId", "")
                    if vid:
                        variety_counts[vid] += 1
            for vid in removing:
                if variety_counts[vid] > 0:
                    return _error(
                        "VARIETY_HAS_REQUESTS",
                        f"Variety '{vid}' cannot be removed — confirmed requests exist for it.",
                    )

        # All remaining varieties must be active
        active_ids = {
            i["varietyId"]
            for i in scan_table(varieties_table_name())
            if i.get("active") is True
        }
        for vid in new_ids:
            if vid not in active_ids:
                return _error("VARIETY_NOT_ACTIVE", f"Variety '{vid}' is not active and cannot be added to a batch.")
        updates["availableVarietyIds"] = new_ids

    if not updates:
        # Nothing to update — return current state
        active_request_count = _count_active_requests(batch_id)
        return _response(200, _format_batch(item, active_request_count))

    # Build update expression
    set_parts = []
    expr_values: dict[str, Any] = {}
    expr_names: dict[str, str] = {}
    for i, (key, val) in enumerate(updates.items()):
        safe_key = f"#f{i}"
        val_key = f":v{i}"
        set_parts.append(f"{safe_key} = {val_key}")
        expr_names[safe_key] = key
        expr_values[val_key] = val

    expr_names["#st"] = "status"
    expr_values[":completed"] = "COMPLETED"

    updated = update_item(
        batches_table_name(),
        key={"batchId": batch_id},
        update_expression=f"SET {', '.join(set_parts)}",
        expression_attribute_values=expr_values,
        expression_attribute_names=expr_names,
        condition_expression="#st <> :completed",
    )
    # Merge to ensure all fields present (update_item returns ALL_NEW)
    merged = {**item, **updated}
    active_request_count = _count_active_requests(batch_id)
    logger.info("update_batch", extra={"batchId": batch_id, "fields": list(updates.keys())})
    return _response(200, _format_batch(merged, active_request_count))


def _count_active_requests(batch_id: str) -> int:
    requests = scan_table(requests_table_name())
    return sum(1 for r in requests if r.get("batchId") == batch_id and r.get("status") != "CANCELLED")


def _format_batch(item: dict[str, Any], active_request_count: int) -> dict[str, Any]:
    return {
        "batchId": item.get("batchId", ""),
        "batchName": item.get("batchName", ""),
        "cutoffDate": item.get("cutoffDate", ""),
        "maxBottleVolumeMl": int(item.get("maxBottleVolumeMl", 0)),
        "status": item.get("status", ""),
        "availableVarietyIds": list(item.get("availableVarietyIds", [])),
        "activeRequestCount": active_request_count,
        "createdAt": item.get("createdAt", ""),
    }

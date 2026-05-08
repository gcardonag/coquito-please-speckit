"""update_batch_status — PUT /api/v1/batches/{id}/status

Transitions batch status forward: OPEN→CLOSED or CLOSED→COMPLETED only.
Chef role required.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef
from src.services.dynamodb import (
    ConflictError,
    ItemNotFoundError,
    batches_table_name,
    get_item,
    requests_table_name,
    scan_table,
    update_item,
)


logger = Logger(service="coquito-update-batch-status")

_ALLOWED_TRANSITIONS: dict[str, str] = {
    "OPEN": "CLOSED",
    "CLOSED": "COMPLETED",
}


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def _error(code: str, message: str, status: int = 400) -> dict[str, Any]:
    return _response(status, {"code": code, "message": message})


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for PUT /api/v1/batches/{id}/status."""
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

    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _error("VALIDATION_ERROR", "Request body is not valid JSON.")

    target_status = (payload.get("status") or "").strip().upper()
    current_status = item.get("status", "")

    allowed_target = _ALLOWED_TRANSITIONS.get(current_status)
    if target_status != allowed_target:
        return _error(
            "INVALID_STATUS_TRANSITION",
            f"Cannot transition from {current_status} to {target_status}.",
        )

    updated = update_item(
        batches_table_name(),
        key={"batchId": batch_id},
        update_expression="SET #st = :new_status",
        expression_attribute_values={":new_status": target_status, ":current": current_status},
        expression_attribute_names={"#st": "status"},
        condition_expression="#st = :current",
    )
    merged = {**item, **updated}

    # Compute activeRequestCount
    requests = scan_table(requests_table_name())
    active_count = sum(
        1 for r in requests
        if r.get("batchId") == batch_id and r.get("status") != "CANCELLED"
    )

    logger.info("update_batch_status", extra={
        "batchId": batch_id,
        "from": current_status,
        "to": target_status,
    })

    return _response(200, {
        "batchId": merged.get("batchId", ""),
        "batchName": merged.get("batchName", ""),
        "cutoffDate": merged.get("cutoffDate", ""),
        "maxBottleVolumeMl": int(merged.get("maxBottleVolumeMl", 0)),
        "status": merged.get("status", ""),
        "availableVarietyIds": list(merged.get("availableVarietyIds", [])),
        "activeRequestCount": active_count,
        "createdAt": merged.get("createdAt", ""),
    })

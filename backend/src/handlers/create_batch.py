"""create_batch — POST /api/v1/batches

Creates a new batch. Validates all inputs, enforces name uniqueness,
and persists with status=OPEN. Chef role required.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from typing import Any

from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef
from src.models.batch import Batch
from src.services.dynamodb import (
    batches_table_name,
    put_item,
    scan_table,
    varieties_table_name,
)


logger = Logger(service="coquito-create-batch")


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def _error(code: str, message: str, status: int = 400) -> dict[str, Any]:
    return _response(status, {"code": code, "message": message})


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for POST /api/v1/batches."""
    denied = require_chef(event)
    if denied:
        return denied

    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _error("VALIDATION_ERROR", "Request body is not valid JSON.")

    batch_name: str = (payload.get("batchName") or "").strip()
    cutoff_date: str = (payload.get("cutoffDate") or "").strip()
    max_volume = payload.get("maxBottleVolumeMl")
    variety_ids: list[str] = payload.get("availableVarietyIds") or []

    # Required fields
    missing = [f for f, v in [("batchName", batch_name), ("cutoffDate", cutoff_date),
                                ("maxBottleVolumeMl", max_volume), ("availableVarietyIds", variety_ids)] if not v]
    if missing:
        return _error("VALIDATION_ERROR", f"Missing required fields: {', '.join(missing)}.")

    # Volume must be positive integer
    try:
        max_volume_int = int(max_volume)
        if max_volume_int <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return _error("VALIDATION_ERROR", "maxBottleVolumeMl must be a positive integer.")

    # Varieties must be non-empty list
    if not variety_ids:
        return _error("VALIDATION_ERROR", "availableVarietyIds must contain at least one variety.")

    # Cutoff date must be valid and >= today
    try:
        cutoff = date.fromisoformat(cutoff_date)
    except ValueError:
        return _error("VALIDATION_ERROR", "cutoffDate must be a valid date in YYYY-MM-DD format.")
    if cutoff < date.today():
        return _error("CUTOFF_DATE_IN_PAST", "cutoffDate must be today or a future date.")

    # Name uniqueness (case-insensitive)
    if Batch.name_exists(batch_name):
        return _error("BATCH_NAME_CONFLICT", f"A batch named '{batch_name}' already exists.")

    # Variety validation — each must exist and be active
    active_ids = {
        item["varietyId"]
        for item in scan_table(varieties_table_name())
        if item.get("active") is True
    }
    for vid in variety_ids:
        if vid not in active_ids:
            return _error("VARIETY_NOT_ACTIVE", f"Variety '{vid}' is not active and cannot be added to a batch.")

    batch_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    item = {
        "batchId": batch_id,
        "batchName": batch_name,
        "cutoffDate": cutoff_date,
        "maxBottleVolumeMl": max_volume_int,
        "availableVarietyIds": variety_ids,
        "status": "OPEN",
        "createdAt": created_at,
    }
    put_item(batches_table_name(), item)
    logger.info("create_batch", extra={"batchId": batch_id, "batchName": batch_name})

    return _response(201, {**item, "activeRequestCount": 0})

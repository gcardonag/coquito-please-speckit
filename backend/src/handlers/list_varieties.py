"""list_varieties — GET /api/v1/varieties

Returns all active coquito varieties, optionally filtered to those
available in a specific batch.
"""
from __future__ import annotations

import os
from typing import Any
import json

from aws_lambda_powertools import Logger

from src.models.variety import Variety
from src.services.dynamodb import (
    ItemNotFoundError,
    get_item,
    scan_table,
    batches_table_name,
    varieties_table_name,
)


logger = Logger(service="coquito-list-varieties")


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for GET /api/v1/varieties."""
    qs = event.get("queryStringParameters") or {}
    batch_id: str | None = qs.get("batchId")

    cloudfront_base = os.environ.get("CLOUDFRONT_ASSETS_BASE_URL", "")

    # If batchId provided, validate batch exists and get its available variety IDs
    allowed_ids: set[str] | None = None
    if batch_id:
        try:
            batch_item = get_item(batches_table_name(), {"batchId": batch_id})
        except ItemNotFoundError:
            return _response(404, {"code": "BATCH_NOT_FOUND", "message": f"Batch '{batch_id}' not found"})
        allowed_ids = set(batch_item.get("availableVarietyIds", []))

    # Fetch all varieties from DynamoDB
    raw_items = scan_table(varieties_table_name())
    varieties = [Variety.from_dict(item) for item in raw_items]

    # Filter: active only + optionally filtered to batch allowed IDs
    result = []
    for v in varieties:
        if not v.active:
            continue
        if allowed_ids is not None and v.variety_id not in allowed_ids:
            continue
        result.append({
            "varietyId": v.variety_id,
            "name": v.name,
            "description": v.description,
            "imageUrl": v.image_url(cloudfront_base),
        })

    return _response(200, {"varieties": result})

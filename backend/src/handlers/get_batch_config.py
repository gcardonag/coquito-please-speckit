"""get_batch_config — GET /api/v1/batches/{batchId}

Returns batch configuration including resolved variety summaries.
"""
from __future__ import annotations

import os
from typing import Any

from src.models.batch import Batch
from src.models.variety import Variety
from src.services.dynamodb import (
    ItemNotFoundError,
    get_item,
    batches_table_name,
    varieties_table_name,
)


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": body}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for GET /api/v1/batches/{batchId}."""
    role = (event.get("requestContext") or {}).get("authorizer", {}).get("lambda", {}).get("role", "")
    if role != "chef":
        return _response(403, {"code": "FORBIDDEN", "message": "Chef access required"})

    batch_id: str = (event.get("pathParameters") or {}).get("batchId", "")
    cloudfront_base = os.environ.get("CLOUDFRONT_ASSETS_BASE_URL", "")

    try:
        batch_item = get_item(batches_table_name(), {"batchId": batch_id})
    except ItemNotFoundError:
        return _response(404, {"code": "BATCH_NOT_FOUND", "message": f"Batch '{batch_id}' not found"})

    batch = Batch.from_dict(batch_item)

    # Resolve variety summaries for available IDs
    available_varieties = []
    for variety_id in batch.available_variety_ids:
        try:
            variety_item = get_item(varieties_table_name(), {"varietyId": variety_id})
            variety = Variety.from_dict(variety_item)
            if variety.active:
                available_varieties.append({
                    "varietyId": variety.variety_id,
                    "name": variety.name,
                    "description": variety.description,
                    "imageUrl": variety.image_url(cloudfront_base),
                })
        except ItemNotFoundError:
            # Variety referenced by batch no longer exists — skip gracefully
            continue

    return _response(200, {
        "batchId": batch.batch_id,
        "batchName": batch.batch_name,
        "cutoffDate": batch.cutoff_date,
        "maxBottleVolumeMl": batch.max_bottle_volume_ml,
        "status": batch.status,
        "availableVarieties": available_varieties,
    })

"""mark_ingredient_acquired — PATCH /api/v1/batches/{batchId}/ingredients/{ingredientId}/acquired

Chef-only endpoint (role enforced by Lambda authorizer context).
Updates the acquired state of an ingredient on the batch item.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from src.models.batch import Batch
from src.models.variety import Variety
from src.services.dynamodb import (
    ItemNotFoundError,
    get_item,
    put_item,
    batches_table_name,
    varieties_table_name,
)


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": body}


def _ingredient_exists(batch: Batch, ingredient_id: str) -> bool:
    """Check if ingredient_id is known in any of the batch's variety recipes."""
    for variety_id in batch.available_variety_ids:
        try:
            v_item = get_item(varieties_table_name(), {"varietyId": variety_id})
            variety = Variety.from_dict(v_item)
            if any(i.ingredient_id == ingredient_id for i in variety.ingredients):
                return True
        except ItemNotFoundError:
            pass
    return False


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    role = (event.get("requestContext") or {}).get("authorizer", {}).get("lambda", {}).get("role", "")
    if role != "chef":
        return _response(403, {"code": "FORBIDDEN", "message": "Chef access required"})

    path_params = event.get("pathParameters") or {}
    batch_id: str = path_params.get("batchId", "")
    ingredient_id: str = path_params.get("ingredientId", "")

    try:
        body: dict[str, Any] = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"code": "VALIDATION_ERROR", "message": "Invalid JSON body"})

    acquired: bool = bool(body.get("acquired", False))

    try:
        batch_item = get_item(batches_table_name(), {"batchId": batch_id})
        batch = Batch.from_dict(batch_item)
    except ItemNotFoundError:
        return _response(404, {"code": "BATCH_NOT_FOUND", "message": f"Batch '{batch_id}' not found"})

    if not _ingredient_exists(batch, ingredient_id):
        return _response(404, {"code": "INGREDIENT_NOT_FOUND", "message": f"Ingredient '{ingredient_id}' not found"})

    # Update acquired state on batch item
    batch.acquired_ingredients[ingredient_id] = acquired
    updated_item = batch.to_dict()
    updated_item["createdAt"] = batch_item.get("createdAt", "")
    put_item(batches_table_name(), updated_item)

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return _response(200, {
        "ingredientId": ingredient_id,
        "acquired": acquired,
        "updatedAt": now,
    })

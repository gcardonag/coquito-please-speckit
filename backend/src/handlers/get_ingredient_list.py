"""get_ingredient_list — GET /api/v1/batches/{batchId}/ingredients

Chef-only endpoint (role enforced by Lambda authorizer context).
Aggregates ingredient quantities across all CONFIRMED requests in the batch.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from src.models.batch import Batch
from src.models.variety import Variety
from src.services.dynamodb import (
    ItemNotFoundError,
    get_item,
    scan_table,
    batches_table_name,
    varieties_table_name,
    requests_table_name,
)


def _today() -> date:
    return date.today()


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": body}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    role = (event.get("requestContext") or {}).get("authorizer", {}).get("lambda", {}).get("role", "")
    if role != "chef":
        return _response(403, {"code": "FORBIDDEN", "message": "Chef access required"})

    batch_id: str = (event.get("pathParameters") or {}).get("batchId", "")

    try:
        batch_item = get_item(batches_table_name(), {"batchId": batch_id})
        batch = Batch.from_dict(batch_item)
    except ItemNotFoundError:
        return _response(404, {"code": "BATCH_NOT_FOUND", "message": f"Batch '{batch_id}' not found"})

    is_finalized = batch.is_cutoff_passed(_today())

    # Load all varieties for this batch
    variety_map: dict[str, Variety] = {}
    for variety_id in batch.available_variety_ids:
        try:
            v_item = get_item(varieties_table_name(), {"varietyId": variety_id})
            variety_map[variety_id] = Variety.from_dict(v_item)
        except ItemNotFoundError:
            pass

    # Scan requests and filter by batchId + CONFIRMED status
    all_requests = scan_table(requests_table_name())
    confirmed = [r for r in all_requests if r.get("batchId") == batch_id and r.get("status") == "CONFIRMED"]

    # Count confirmed per variety
    variety_count: dict[str, int] = defaultdict(int)
    for req in confirmed:
        variety_count[req["varietyId"]] += 1

    # Build byVariety list
    by_variety = []
    for variety_id, count in variety_count.items():
        variety = variety_map.get(variety_id)
        if variety is None:
            continue
        ingredients = []
        for ing in variety.ingredients:
            total_qty = round(ing.quantity_per_bottle * count, 4)
            acquired = batch.acquired_ingredients.get(ing.ingredient_id, False)
            ingredients.append({
                "ingredientId": ing.ingredient_id,
                "name": ing.name,
                "totalQuantity": total_qty,
                "unit": ing.unit,
                "category": ing.category,
                "acquired": acquired,
            })
        by_variety.append({
            "varietyId": variety_id,
            "varietyName": variety.name,
            "confirmedCount": count,
            "ingredients": ingredients,
        })

    # Compute totals — aggregate by (ingredientId, name, unit, category) across all varieties
    totals_map: dict[str, dict[str, Any]] = {}
    for variety_entry in by_variety:
        for ing in variety_entry["ingredients"]:
            key = ing["ingredientId"]
            if key not in totals_map:
                totals_map[key] = {
                    "name": ing["name"],
                    "totalQuantity": 0.0,
                    "unit": ing["unit"],
                    "category": ing["category"],
                }
            totals_map[key]["totalQuantity"] = round(
                totals_map[key]["totalQuantity"] + ing["totalQuantity"], 4
            )

    totals = list(totals_map.values())

    return _response(200, {
        "batchId": batch.batch_id,
        "batchName": batch.batch_name,
        "isFinalized": is_finalized,
        "totalConfirmedRequests": len(confirmed),
        "byVariety": by_variety,
        "totals": totals,
    })

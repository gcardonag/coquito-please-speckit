"""chef_create_variety — POST /api/v1/chef/varieties

Creates a new variety with system-assigned UUIDs for varietyId and each
ingredientId. Chef role is required; non-chefs receive 403.
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any

from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef
from src.services.dynamodb import put_item, varieties_table_name


logger = Logger(service="coquito-chef-create-variety")


class _DecimalEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body, cls=_DecimalEncoder)}


def _validation_error(message: str, field: str) -> dict[str, Any]:
    return _response(400, {"code": "VALIDATION_ERROR", "message": message, "field": field})


def _validate_ingredient(ingredient: Any, idx: int) -> dict[str, Any] | None:
    if not isinstance(ingredient, dict):
        return _validation_error(f"ingredients[{idx}] must be an object", f"ingredients[{idx}]")
    if not str(ingredient.get("name", "")).strip():
        return _validation_error(
            f"ingredients[{idx}].name is required", f"ingredients[{idx}].name"
        )
    qty = ingredient.get("quantityPerBottle")
    try:
        qty = float(qty)
    except (TypeError, ValueError):
        return _validation_error(
            f"ingredients[{idx}].quantityPerBottle must be a positive number",
            f"ingredients[{idx}].quantityPerBottle",
        )
    if qty <= 0:
        return _validation_error(
            f"ingredients[{idx}].quantityPerBottle must be positive",
            f"ingredients[{idx}].quantityPerBottle",
        )
    if not str(ingredient.get("unit", "")).strip():
        return _validation_error(
            f"ingredients[{idx}].unit is required", f"ingredients[{idx}].unit"
        )
    if not str(ingredient.get("category", "")).strip():
        return _validation_error(
            f"ingredients[{idx}].category is required", f"ingredients[{idx}].category"
        )
    return None


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for POST /api/v1/chef/varieties."""
    denied = require_chef(event)
    if denied:
        return denied

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _validation_error("Request body must be valid JSON", "body")

    name = str(body.get("name", "")).strip()
    if not name:
        return _validation_error("name is required", "name")

    bottle_yield_ml = body.get("bottleYieldMl")
    if bottle_yield_ml is None:
        return _validation_error("bottleYieldMl is required", "bottleYieldMl")
    try:
        bottle_yield_ml = int(bottle_yield_ml)
    except (TypeError, ValueError):
        return _validation_error("bottleYieldMl must be a positive integer", "bottleYieldMl")
    if bottle_yield_ml <= 0:
        return _validation_error("bottleYieldMl must be a positive integer", "bottleYieldMl")

    raw_ingredients = body.get("ingredients", [])
    if not isinstance(raw_ingredients, list):
        return _validation_error("ingredients must be a list", "ingredients")

    processed_ingredients = []
    for idx, raw in enumerate(raw_ingredients):
        err = _validate_ingredient(raw, idx)
        if err:
            return err
        processed_ingredients.append({
            "ingredientId": str(uuid.uuid4()).replace("-", ""),
            "name": str(raw["name"]).strip(),
            "quantityPerBottle": Decimal(str(float(raw["quantityPerBottle"]))),
            "unit": str(raw["unit"]).strip(),
            "category": str(raw["category"]).strip(),
        })

    item = {
        "varietyId": str(uuid.uuid4()).replace("-", ""),
        "name": name,
        "description": str(body.get("description", "")).strip(),
        "imageKey": str(body.get("imageKey", "")).strip(),
        "bottleYieldMl": bottle_yield_ml,
        "active": bool(body.get("active", True)),
        "ingredients": processed_ingredients,
    }

    put_item(varieties_table_name(), item)
    return _response(201, {"variety": item})

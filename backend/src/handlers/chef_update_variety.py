"""chef_update_variety — PUT /api/v1/chef/varieties/{id}

Updates an existing variety. All top-level fields are optional (only provided
fields are merged). When `ingredients` is provided, the full list is replaced;
ingredients without an `ingredientId` receive a system-assigned UUID.
Chef role is required; non-chefs receive 403.
"""
from __future__ import annotations

import json
import uuid
from decimal import Decimal
from typing import Any

from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef
from src.services.dynamodb import (
    ItemNotFoundError,
    get_item,
    put_item,
    varieties_table_name,
)


logger = Logger(service="coquito-chef-update-variety")


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
    """Lambda handler for PUT /api/v1/chef/varieties/{id}."""
    denied = require_chef(event)
    if denied:
        return denied

    variety_id = (event.get("pathParameters") or {}).get("id", "")
    if not variety_id:
        return _validation_error("id is required", "id")

    try:
        existing = get_item(varieties_table_name(), {"varietyId": variety_id})
    except ItemNotFoundError:
        return _response(404, {
            "code": "VARIETY_NOT_FOUND",
            "message": f"Variety '{variety_id}' not found.",
        })

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _validation_error("Request body must be valid JSON", "body")

    if "name" in body:
        name = str(body["name"]).strip()
        if not name:
            return _validation_error("name must not be empty", "name")
        existing["name"] = name

    if "description" in body:
        existing["description"] = str(body["description"])

    if "imageKey" in body:
        existing["imageKey"] = str(body["imageKey"])

    if "bottleYieldMl" in body:
        try:
            bym = int(body["bottleYieldMl"])
        except (TypeError, ValueError):
            return _validation_error("bottleYieldMl must be a positive integer", "bottleYieldMl")
        if bym <= 0:
            return _validation_error("bottleYieldMl must be a positive integer", "bottleYieldMl")
        existing["bottleYieldMl"] = bym

    if "active" in body:
        existing["active"] = bool(body["active"])

    if "ingredients" in body:
        raw_ingredients = body["ingredients"]
        if not isinstance(raw_ingredients, list):
            return _validation_error("ingredients must be a list", "ingredients")
        processed = []
        for idx, raw in enumerate(raw_ingredients):
            err = _validate_ingredient(raw, idx)
            if err:
                return err
            ingredient_id = raw.get("ingredientId") or str(uuid.uuid4()).replace("-", "")
            processed.append({
                "ingredientId": ingredient_id,
                "name": str(raw["name"]).strip(),
                "quantityPerBottle": Decimal(str(float(raw["quantityPerBottle"]))),
                "unit": str(raw["unit"]).strip(),
                "category": str(raw["category"]).strip(),
            })
        existing["ingredients"] = processed

    put_item(varieties_table_name(), existing)
    return _response(200, {"variety": existing})

"""chef_list_varieties — GET /api/v1/chef/varieties

Returns ALL varieties (active and inactive) with full ingredient lists.
Chef role is required; non-chefs receive 403.
"""
from __future__ import annotations

import json
from typing import Any

from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef
from src.models.variety import Variety
from src.services.dynamodb import scan_table, varieties_table_name


logger = Logger(service="coquito-chef-list-varieties")


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for GET /api/v1/chef/varieties."""
    denied = require_chef(event)
    if denied:
        return denied

    raw_items = scan_table(varieties_table_name())
    varieties = [Variety.from_dict(item) for item in raw_items]

    return _response(200, {"varieties": [v.to_dict() for v in varieties]})

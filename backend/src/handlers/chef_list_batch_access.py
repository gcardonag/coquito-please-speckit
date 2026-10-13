"""chef_list_batch_access — GET /api/v1/chef/batches/{id}/access

Returns all users currently granted access to a batch. Chef-only.
"""
from __future__ import annotations

import json
from typing import Any

from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef
from src.models.batch_access import BatchAccessGrant
from src.services.dynamodb import (
    ItemNotFoundError,
    batch_access_table_name,
    batches_table_name,
    get_item,
    query_by_partition_key,
)

logger = Logger(service="coquito-chef-list-batch-access")


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for GET /api/v1/chef/batches/{id}/access."""
    denied = require_chef(event)
    if denied:
        return denied

    params = event.get("pathParameters") or {}
    batch_id = params.get("id", "")

    try:
        get_item(batches_table_name(), {"batchId": batch_id})
    except ItemNotFoundError:
        return _response(404, {"code": "NOT_FOUND", "message": "Batch not found"})

    raw_items = query_by_partition_key(batch_access_table_name(), "batchId", batch_id)
    grants = [BatchAccessGrant.from_dict(item) for item in raw_items]

    users = []
    for g in grants:
        entry: dict[str, Any] = {
            "userId": g.user_id,
            "email": g.email,
            "firstName": g.first_name,
            "grantedAt": g.granted_at,
        }
        if g.last_name:
            entry["lastName"] = g.last_name
        users.append(entry)

    return _response(200, {"batchId": batch_id, "users": users})

"""chef_revoke_batch_access — DELETE /api/v1/chef/batches/{id}/access/{userId}

Revokes a user's access to an open batch. Returns 204 on success. Chef-only.
"""
from __future__ import annotations

import json
from typing import Any

from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef
from src.services.dynamodb import (
    ItemNotFoundError,
    batch_access_table_name,
    batches_table_name,
    get_item,
    delete_item,
)

logger = Logger(service="coquito-chef-revoke-batch-access")


def _response(status_code: int, body: Any = "") -> dict[str, Any]:
    if status_code == 204:
        return {"statusCode": 204, "body": ""}
    return {"statusCode": status_code, "body": json.dumps(body)}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for DELETE /api/v1/chef/batches/{id}/access/{userId}."""
    denied = require_chef(event)
    if denied:
        return denied

    params = event.get("pathParameters") or {}
    batch_id = params.get("id", "")
    user_id = params.get("userId", "")

    try:
        batch = get_item(batches_table_name(), {"batchId": batch_id})
    except ItemNotFoundError:
        return _response(404, {"code": "NOT_FOUND", "message": "Batch not found"})

    if batch.get("status") != "OPEN":
        return _response(403, {
            "code": "FORBIDDEN",
            "message": "Access revocation is only permitted on open batches",
        })

    try:
        get_item(batch_access_table_name(), {"batchId": batch_id, "userId": user_id})
    except ItemNotFoundError:
        return _response(404, {"code": "NOT_FOUND", "message": "Access grant not found"})

    delete_item(batch_access_table_name(), {"batchId": batch_id, "userId": user_id})

    logger.info("Batch access revoked", extra={"event": "ACCESS_REVOKED", "batchId": batch_id})
    return _response(204)

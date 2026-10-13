"""chef_grant_batch_access — PUT /api/v1/chef/batches/{id}/access/{userId}

Grants a Cognito user access to an open batch. Idempotency is enforced via a
conditional DynamoDB write (409 if the grant already exists). Chef-only.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef
from src.models.batch_access import BatchAccessGrant
from src.services.dynamodb import (
    ItemNotFoundError,
    ConflictError,
    batches_table_name,
    batch_access_table_name,
    get_item,
    put_item_if_not_exists,
)

logger = Logger(service="coquito-chef-grant-batch-access")


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def _extract_attr(attrs: list[dict], name: str) -> str:
    return next((a["Value"] for a in attrs if a["Name"] == name), "")


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for PUT /api/v1/chef/batches/{id}/access/{userId}."""
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
            "message": "Access grants are only permitted on open batches",
        })

    user_pool_id = os.environ["COGNITO_USER_POOL_ID"]
    cognito = boto3.client("cognito-idp")

    try:
        user_response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=user_id,
        )
        attrs = user_response.get("UserAttributes", [])
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code in ("UserNotFoundException", "ResourceNotFoundException"):
            return _response(404, {"code": "NOT_FOUND", "message": "User not found"})
        logger.error("Cognito error", extra={"reason": str(exc)})
        return _response(503, {"code": "COGNITO_ERROR", "message": "Failed to look up user in Cognito. Please try again or contact support."})

    email = _extract_attr(attrs, "email")
    first_name = _extract_attr(attrs, "given_name")
    last_name = _extract_attr(attrs, "family_name")
    granted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    grant = BatchAccessGrant(
        batch_id=batch_id,
        user_id=user_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        granted_at=granted_at,
    )

    try:
        put_item_if_not_exists(batch_access_table_name(), grant.to_dict(), "userId")
    except ConflictError:
        return _response(409, {
            "code": "ALREADY_GRANTED",
            "message": "This user already has access to the batch",
        })

    logger.info("Batch access granted", extra={"event": "ACCESS_GRANTED", "batchId": batch_id})
    return _response(200, {
        "batchId": batch_id,
        "userId": user_id,
        "grantedAt": granted_at,
    })

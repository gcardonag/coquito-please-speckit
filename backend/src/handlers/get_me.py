"""get_me — GET /api/v1/me

Returns the identity and role of the currently authenticated user.
Reads from the Lambda authorizer context — no DynamoDB access.
Available to any authenticated role (no require_chef check).
"""
from __future__ import annotations

import json
from typing import Any

from aws_lambda_powertools import Logger


logger = Logger(service="coquito-get-me")


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for GET /api/v1/me."""
    authorizer = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("lambda")
    )
    if not authorizer:
        return _response(401, {"code": "UNAUTHORIZED", "message": "Session expired or missing."})

    user_id = authorizer.get("userId", "")
    role = authorizer.get("role", "")
    email = authorizer.get("email", "")

    logger.info("get_me", extra={"userId": user_id, "role": role})

    return _response(200, {"userId": user_id, "role": role, "email": email})

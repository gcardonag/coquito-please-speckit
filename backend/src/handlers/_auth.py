"""Shared authorization helper for chef-only Lambda handlers."""
from __future__ import annotations

import json
from typing import Any


def require_chef(event: dict[str, Any]) -> dict[str, Any] | None:
    """Return a 403 response dict if the caller is not a chef, else None."""
    role = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("lambda", {})
        .get("role", "")
    )
    if role != "chef":
        return {
            "statusCode": 403,
            "body": json.dumps({
                "code": "CHEF_ROLE_REQUIRED",
                "message": "This endpoint is restricted to chefs.",
            }),
        }
    return None

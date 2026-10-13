"""chef_search_users — GET /api/v1/chef/users?query={q}

Searches Cognito users by email prefix and by given_name prefix, merges the
results (deduplicating by sub), and returns up to 20 matches. Chef-only.
"""
from __future__ import annotations

import json
import os
from typing import Any

import boto3
from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef

logger = Logger(service="coquito-chef-search-users")


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def _extract_attr(attrs: list[dict], name: str) -> str:
    return next((a["Value"] for a in attrs if a["Name"] == name), "")


def _cognito_users_to_summaries(users: list[dict]) -> dict[str, dict]:
    """Return a dict keyed by sub, value is the UserSummary dict."""
    summaries: dict[str, dict] = {}
    for u in users:
        attrs = u.get("Attributes", [])
        sub = _extract_attr(attrs, "sub")
        if not sub:
            continue
        summaries[sub] = {
            "userId": sub,
            "email": _extract_attr(attrs, "email"),
            "firstName": _extract_attr(attrs, "given_name"),
            "lastName": _extract_attr(attrs, "family_name") or None,
        }
    return summaries


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for GET /api/v1/chef/users."""
    denied = require_chef(event)
    if denied:
        return denied

    params = event.get("queryStringParameters") or {}
    query = (params.get("query") or "").strip()
    if not query:
        return _response(400, {"code": "VALIDATION_ERROR", "message": "query parameter is required"})

    user_pool_id = os.environ["COGNITO_USER_POOL_ID"]
    cognito = boto3.client("cognito-idp")

    email_users = cognito.list_users(
        UserPoolId=user_pool_id,
        Filter=f'email ^= "{query}"',
        Limit=20,
    ).get("Users", [])

    name_users = cognito.list_users(
        UserPoolId=user_pool_id,
        Filter=f'given_name ^= "{query}"',
        Limit=20,
    ).get("Users", [])

    merged = _cognito_users_to_summaries(email_users)
    merged.update(_cognito_users_to_summaries(name_users))  # deduplicates by sub

    results = list(merged.values())[:20]
    # Remove None lastName to keep response clean (omit key if absent)
    for r in results:
        if r["lastName"] is None:
            del r["lastName"]

    logger.info("User search completed", extra={"query_len": len(query), "result_count": len(results)})
    return _response(200, {"users": results})

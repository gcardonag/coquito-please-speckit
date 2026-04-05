"""Token refresh handler: POST /auth/refresh.

Reads the refresh_token cookie, calls cognito.refresh_tokens(), and sets
new id_token and access_token cookies. Returns 401 REFRESH_EXPIRED if the
refresh token is missing or Cognito rejects it.
"""
import json
from typing import Any

from aws_lambda_powertools import Logger

from src.services import cognito

logger = Logger(service="coquito-refresh")


def _extract_cookie(cookie_header: str | None, name: str) -> str | None:
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        n, _, v = part.strip().partition("=")
        if n.strip() == name:
            return v.strip()
    return None


def _set_cookie(name: str, value: str, max_age: int, path: str = "/") -> str:
    return f"{name}={value}; HttpOnly; Secure; SameSite=Strict; Max-Age={max_age}; Path={path}"


def handler(event: dict, context: Any) -> dict:  # noqa: ANN401
    cookie_header = (event.get("headers") or {}).get("cookie")
    refresh_token = _extract_cookie(cookie_header, "refresh_token")

    if not refresh_token:
        logger.warning("Refresh denied: missing refresh_token cookie", extra={"reason": "MISSING_REFRESH_TOKEN"})
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"code": "REFRESH_EXPIRED", "message": "Session has expired. Please log in again."}),
        }

    try:
        tokens = cognito.refresh_tokens(refresh_token)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Refresh failed", extra={"reason": "REFRESH_EXPIRED", "error": str(exc)})
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"code": "REFRESH_EXPIRED", "message": "Session has expired. Please log in again."}),
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "cookies": [
            _set_cookie("id_token", tokens["id_token"], max_age=3600),
            _set_cookie("access_token", tokens["access_token"], max_age=3600),
        ],
        "body": json.dumps({"ok": True}),
    }

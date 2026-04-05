"""Logout handler: POST /auth/logout.

Clears all three session cookies (Max-Age=0) and revokes the refresh token.
Token revocation is best-effort — a failure does not prevent logout.
"""
import json
from typing import Any

from aws_lambda_powertools import Logger

from src.services import cognito

logger = Logger(service="coquito-logout")


def _extract_cookie(cookie_header: str | None, name: str) -> str | None:
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        n, _, v = part.strip().partition("=")
        if n.strip() == name:
            return v.strip()
    return None


def _clear_cookie(name: str, path: str = "/") -> str:
    return f"{name}=; HttpOnly; Secure; SameSite=Strict; Max-Age=0; Path={path}"


def handler(event: dict, context: Any) -> dict:  # noqa: ANN401
    cookie_header = (event.get("headers") or {}).get("cookie")
    refresh_token = _extract_cookie(cookie_header, "refresh_token")

    if refresh_token:
        try:
            cognito.revoke_token(refresh_token)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Refresh token revocation failed (best-effort)", extra={"reason": "REVOKE_FAILED", "error": str(exc)})

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "cookies": [
            _clear_cookie("id_token"),
            _clear_cookie("access_token"),
            _clear_cookie("refresh_token", path="/auth/refresh"),
        ],
        "body": json.dumps({"ok": True}),
    }

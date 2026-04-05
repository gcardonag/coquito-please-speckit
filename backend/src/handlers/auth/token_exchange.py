"""Token exchange handler: POST /auth/callback.

Exchanges the Cognito authorization code for tokens and sets three httpOnly
cookies: id_token, access_token, refresh_token.

The SPA echoes code_verifier and state as query params alongside the auth code
redirect. state is echoed back in the Location header so the SPA can verify
CSRF in sessionStorage — no server-side state storage required.
"""
import json
import os
from typing import Any
from urllib.parse import urlencode

from aws_lambda_powertools import Logger

from src.services import cognito

logger = Logger(service="coquito-token-exchange")

_REDIRECT_URI = None  # cached at cold-start


def _redirect_uri() -> str:
    global _REDIRECT_URI  # noqa: PLW0603
    if _REDIRECT_URI is None:
        _REDIRECT_URI = os.environ["REDIRECT_URI"]
    return _REDIRECT_URI


def _set_cookie(name: str, value: str, max_age: int, path: str = "/") -> str:
    return f"{name}={value}; HttpOnly; Secure; SameSite=Strict; Max-Age={max_age}; Path={path}"


def handler(event: dict, context: Any) -> dict:  # noqa: ANN401
    params = event.get("queryStringParameters") or {}
    code = params.get("code")
    state = params.get("state", "")
    code_verifier = params.get("code_verifier", "")

    if not code:
        logger.warning("Token exchange denied: missing code", extra={"reason": "INVALID_CODE"})
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"code": "INVALID_CODE", "message": "Authorization code is required"}),
        }

    try:
        tokens = cognito.exchange_code(
            code=code,
            redirect_uri=_redirect_uri(),
            code_verifier=code_verifier,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Token exchange failed", extra={"reason": "COGNITO_ERROR", "error": str(exc)})
        return {
            "statusCode": 503,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"code": "COGNITO_UNAVAILABLE", "message": "Authentication service error"}),
        }

    base_url = "https://" + (event.get("headers") or {}).get("host", "coquito.gcardona.me")
    location = f"{base_url}/?state={state}" if state else f"{base_url}/"

    return {
        "statusCode": 302,
        "headers": {
            "location": location,
            "Content-Type": "application/json",
        },
        "cookies": [
            _set_cookie("id_token", tokens["id_token"], max_age=3600),
            _set_cookie("access_token", tokens["access_token"], max_age=3600),
            _set_cookie("refresh_token", tokens["refresh_token"], max_age=2592000, path="/auth/refresh"),
        ],
        "body": "",
    }

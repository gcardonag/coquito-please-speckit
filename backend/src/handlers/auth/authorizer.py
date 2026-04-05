"""Lambda authorizer: validates id_token JWT from the Cookie header.

Flow:
  1. Parse Cookie header to extract id_token.
  2. Fetch and cache Cognito JWKS (15-minute in-memory cache).
  3. Validate JWT: signature, expiry, aud = COGNITO_CLIENT_ID.
  4. Extract cognito:groups claim and apply chef-first precedence:
       chef > authorized-user > deny
  5. Return simple response: {isAuthorized, context: {userId, role, email}}

Logging: WARN via Lambda Powertools on any validation failure (no PII).
"""
import json
import os
import time
import urllib.request
from typing import Any

import jwt
from aws_lambda_powertools import Logger

logger = Logger(service="coquito-authorizer")

# ---------------------------------------------------------------------------
# Module-level JWKS cache (shared across warm invocations)
# ---------------------------------------------------------------------------
_jwks_cache: dict[str, Any] = {}  # keys: "keys" list, "fetched_at" timestamp
_CACHE_TTL_SECONDS = 900  # 15 minutes


def _fetch_jwks(jwks_uri: str) -> list[dict]:
    """Fetch JWKS keys from Cognito. Used as a seam for testing."""
    with urllib.request.urlopen(jwks_uri, timeout=5) as resp:  # noqa: S310
        data = json.loads(resp.read())
    return data["keys"]


def _get_jwks(jwks_uri: str) -> list[dict]:
    """Return cached JWKS keys, refreshing if stale (>15 min)."""
    now = time.monotonic()
    if _jwks_cache.get("keys") and now - _jwks_cache.get("fetched_at", 0) < _CACHE_TTL_SECONDS:
        return _jwks_cache["keys"]

    keys = _fetch_jwks(jwks_uri)
    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    return keys


def _extract_id_token(cookie_header: str | None) -> str | None:
    """Parse Cookie header and return the id_token value, or None."""
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        name, _, value = part.strip().partition("=")
        if name.strip() == "id_token":
            return value.strip()
    return None


def _determine_role(groups: list[str]) -> str | None:
    """Apply chef-first precedence rule.

    Returns 'chef', 'authorized-user', or None if neither group is present.
    This precedence is intentional: a user in both groups is treated as a chef.
    """
    if "chef" in groups:
        return "chef"
    if "authorized-user" in groups:
        return "authorized-user"
    return None


def handler(event: dict, context: Any) -> dict:  # noqa: ANN401
    """Lambda authorizer entry point.

    Returns HTTP API v2 simple-response format:
      {"isAuthorized": bool, "context": {...}}
    """
    client_id = os.environ["COGNITO_CLIENT_ID"]
    jwks_uri = os.environ["JWKS_URI"]

    cookie_header = (event.get("headers") or {}).get("cookie") or (event.get("headers") or {}).get("Cookie")
    id_token = _extract_id_token(cookie_header)

    if not id_token:
        logger.warning("Authorization denied: missing id_token cookie", extra={"reason": "MISSING_COOKIE"})
        return {"isAuthorized": False}

    try:
        jwks_keys = _get_jwks(jwks_uri)
        unverified_header = jwt.get_unverified_header(id_token)
        matching_key = next(
            (k for k in jwks_keys if k.get("kid") == unverified_header.get("kid")),
            None,
        )
        if matching_key is None:
            logger.warning("Authorization denied: no matching JWKS key", extra={"reason": "NO_MATCHING_KEY"})
            return {"isAuthorized": False}

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(matching_key))
        payload = jwt.decode(
            id_token,
            key=public_key,
            algorithms=["RS256"],
            audience=client_id,
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Authorization denied: token expired", extra={"reason": "EXPIRED_TOKEN"})
        return {"isAuthorized": False}
    except jwt.InvalidTokenError as exc:
        logger.warning("Authorization denied: invalid token", extra={"reason": "INVALID_TOKEN", "error": str(exc)})
        return {"isAuthorized": False}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Authorization denied: unexpected error", extra={"reason": "UNEXPECTED_ERROR", "error": str(exc)})
        return {"isAuthorized": False}

    groups: list[str] = payload.get("cognito:groups") or []
    role = _determine_role(groups)

    if role is None:
        logger.warning("Authorization denied: user has no recognized role", extra={"reason": "UNAUTHORIZED_ROLE"})
        return {"isAuthorized": False}

    return {
        "isAuthorized": True,
        "context": {
            "userId": payload["sub"],
            "role": role,
            "email": payload.get("email", ""),
        },
    }

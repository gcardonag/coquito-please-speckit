"""Contract test: POST /auth/refresh.

Tests:
  (a) valid refresh_token cookie → 200, new id_token + access_token cookies set
  (b) missing/expired refresh_token → 401 REFRESH_EXPIRED

cognito.refresh_tokens is mocked.
RED step: must FAIL before refresh.py is implemented.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


def _make_event(cookies: str | None = "refresh_token=valid-refresh-tok") -> dict:
    return {
        "version": "2.0",
        "requestContext": {"http": {"method": "POST", "path": "/auth/refresh"}},
        "headers": {"cookie": cookies} if cookies else {},
    }


class TestAuthRefresh:
    def _invoke(self, event, token_response=None, raise_exc=None):
        import src.handlers.auth.refresh as re  # noqa: PLC0415

        mock_refresh = MagicMock()
        if raise_exc:
            mock_refresh.side_effect = raise_exc
        else:
            mock_refresh.return_value = token_response or {
                "id_token": "new.id.tok",
                "access_token": "new.access.tok",
                "expires_in": 3600,
            }

        with patch("src.handlers.auth.refresh.cognito.refresh_tokens", mock_refresh):
            return re.handler(event, MagicMock())

    def _get_cookies(self, result: dict) -> list[str]:
        return result.get("cookies", []) or []

    def test_valid_refresh_token_returns_200_with_new_cookies(self):
        """Valid refresh_token → 200 with new id_token and access_token cookies."""
        result = self._invoke(_make_event())

        assert result["statusCode"] == 200
        cookies = self._get_cookies(result)
        cookie_names = [c.split("=")[0].strip() for c in cookies]
        assert "id_token" in cookie_names
        assert "access_token" in cookie_names

    def test_missing_refresh_token_returns_401(self):
        """Missing refresh_token cookie → 401 REFRESH_EXPIRED."""
        result = self._invoke(_make_event(cookies=None))

        assert result["statusCode"] == 401
        body = json.loads(result["body"])
        assert body["code"] == "REFRESH_EXPIRED"

    def test_expired_refresh_token_returns_401(self):
        """Expired/invalid refresh_token (Cognito error) → 401 REFRESH_EXPIRED."""
        result = self._invoke(
            _make_event(),
            raise_exc=RuntimeError("invalid_grant: Refresh Token has expired"),
        )

        assert result["statusCode"] == 401
        body = json.loads(result["body"])
        assert body["code"] == "REFRESH_EXPIRED"

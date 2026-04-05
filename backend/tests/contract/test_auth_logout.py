"""Contract test: POST /auth/logout.

Tests:
  (a) valid session → 200, three cookies cleared (Max-Age=0)
  (b) no session → 200 (idempotent)

cognito.revoke_token is mocked.
RED step: must FAIL before logout.py is implemented.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


def _make_event(cookies: str | None = "refresh_token=tok") -> dict:
    return {
        "version": "2.0",
        "requestContext": {"http": {"method": "POST", "path": "/auth/logout"}},
        "headers": {"cookie": cookies} if cookies else {},
    }


class TestAuthLogout:
    def _invoke(self, event, revoke_side_effect=None):
        import src.handlers.auth.logout as lo  # noqa: PLC0415

        mock_revoke = MagicMock()
        if revoke_side_effect:
            mock_revoke.side_effect = revoke_side_effect

        with patch("src.handlers.auth.logout.cognito.revoke_token", mock_revoke):
            return lo.handler(event, MagicMock())

    def _get_cookies(self, result: dict) -> list[str]:
        return result.get("cookies", []) or []

    def test_valid_session_returns_200_with_cleared_cookies(self):
        """Valid session → 200 with all three cookies cleared (Max-Age=0)."""
        result = self._invoke(_make_event())

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body.get("ok") is True

        cookies = self._get_cookies(result)
        assert len(cookies) == 3
        for cookie in cookies:
            assert "Max-Age=0" in cookie

    def test_no_session_returns_200_idempotent(self):
        """No session cookies → still 200 (idempotent)."""
        result = self._invoke(_make_event(cookies=None))
        assert result["statusCode"] == 200

    def test_revoke_failure_does_not_break_logout(self):
        """revoke_token failure (best-effort) → still 200."""
        result = self._invoke(_make_event(), revoke_side_effect=RuntimeError("Cognito down"))
        assert result["statusCode"] == 200

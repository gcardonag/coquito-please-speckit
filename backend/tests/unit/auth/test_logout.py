"""Unit tests for the logout handler.

Tests:
  (a) valid session → 200, three cookies cleared (Max-Age=0)
  (b) revoke failure (best-effort) → still 200
  (c) no session cookies → 200 (idempotent)
"""
import json
from unittest.mock import MagicMock, patch


def _make_event(cookies: str | None = "refresh_token=tok") -> dict:
    return {
        "version": "2.0",
        "requestContext": {"http": {"method": "POST", "path": "/auth/logout"}},
        "headers": {"cookie": cookies} if cookies else {},
    }


class TestLogout:
    def _invoke(self, event, revoke_side_effect=None):
        import src.handlers.auth.logout as lo  # noqa: PLC0415

        mock_revoke = MagicMock()
        if revoke_side_effect:
            mock_revoke.side_effect = revoke_side_effect

        with patch("src.handlers.auth.logout.cognito.revoke_token", mock_revoke):
            return lo.handler(event, MagicMock())

    def test_logout_clears_three_cookies(self):
        result = self._invoke(_make_event())
        assert result["statusCode"] == 200
        cookies = result.get("cookies", [])
        assert len(cookies) == 3
        for cookie in cookies:
            assert "Max-Age=0" in cookie

    def test_logout_returns_ok_true(self):
        result = self._invoke(_make_event())
        body = json.loads(result["body"])
        assert body["ok"] is True

    def test_revoke_failure_still_returns_200(self):
        result = self._invoke(_make_event(), revoke_side_effect=RuntimeError("Cognito error"))
        assert result["statusCode"] == 200

    def test_no_session_returns_200(self):
        result = self._invoke(_make_event(cookies=None))
        assert result["statusCode"] == 200

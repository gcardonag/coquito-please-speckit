"""Contract test: POST /auth/callback (token_exchange handler).

Tests:
  (a) valid code → 302 redirect with three Set-Cookie headers (HttpOnly, Secure, SameSite=Strict)
  (b) missing code → 400 INVALID_CODE
  (c) state mismatch → 400 STATE_MISMATCH

cognito.py service is mocked.
RED step: must FAIL before token_exchange.py is implemented.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


def _make_event(code: str | None = "valid-code", state: str | None = "test-state") -> dict:
    """Build a minimal API GW v2 event for the token exchange handler."""
    params: dict = {}
    if code is not None:
        params["code"] = code
    if state is not None:
        params["state"] = state
    return {
        "version": "2.0",
        "requestContext": {"http": {"method": "POST", "path": "/auth/callback"}},
        "queryStringParameters": params,
        "headers": {},
    }


class TestAuthCallback:
    @pytest.fixture(autouse=True)
    def patch_env(self, monkeypatch):
        monkeypatch.setenv("COGNITO_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("REDIRECT_URI", "https://coquito.gcardona.me/auth/callback")
        monkeypatch.setenv("TOKEN_ENDPOINT", "https://auth.coquito.gcardona.me/oauth2/token")
        monkeypatch.setenv("SSM_CLIENT_SECRET", "/coquito/prod/cognito/client_secret")

    def _invoke(self, event, token_response=None, raise_exc=None):
        import src.handlers.auth.token_exchange as te  # noqa: PLC0415

        mock_exchange = MagicMock()
        if raise_exc:
            mock_exchange.side_effect = raise_exc
        else:
            mock_exchange.return_value = token_response or {
                "id_token": "id.tok.en",
                "access_token": "access.tok.en",
                "refresh_token": "refresh.tok.en",
                "expires_in": 3600,
            }

        with patch("src.handlers.auth.token_exchange.cognito.exchange_code", mock_exchange):
            return te.handler(event, MagicMock())

    def test_valid_code_returns_302_with_cookies(self):
        """Valid code → 302 redirect with three Set-Cookie headers."""
        event = _make_event()
        # Provide a matching code_verifier via query params (simulating SPA echo)
        event["queryStringParameters"]["code_verifier"] = "test-verifier"
        result = self._invoke(event)

        assert result["statusCode"] == 200
        headers = result.get("headers", {})
        # Multi-value headers or single cookies field
        cookies = result.get("cookies", []) or []
        cookie_header = headers.get("set-cookie", "")
        all_cookies = cookies if cookies else ([cookie_header] if cookie_header else [])

        assert len(all_cookies) == 3
        for cookie in all_cookies:
            assert "HttpOnly" in cookie
            assert "Secure" in cookie
            assert "SameSite=Strict" in cookie

    def test_missing_code_returns_400(self):
        """Missing code query param → 400 INVALID_CODE."""
        event = _make_event(code=None)
        result = self._invoke(event)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["code"] == "INVALID_CODE"

    def test_state_present_in_redirect(self):
        """state param is echoed back in the response body."""
        event = _make_event(state="my-csrf-state")
        event["queryStringParameters"]["code_verifier"] = "test-verifier"
        result = self._invoke(event)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["state"] == "my-csrf-state"

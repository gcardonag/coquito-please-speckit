"""Unit tests for the token exchange handler.

Tests:
  (a) valid code → sets three cookies, returns 302
  (b) Cognito error → 503
  (c) CSRF state is echoed back in the redirect Location

RED step: verify FAIL before implementation.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


def _make_event(code="valid-code", state="csrf-state", code_verifier="test-verifier") -> dict:
    params = {}
    if code:
        params["code"] = code
    if state:
        params["state"] = state
    if code_verifier:
        params["code_verifier"] = code_verifier
    return {
        "version": "2.0",
        "requestContext": {"http": {"method": "POST", "path": "/auth/callback"}},
        "queryStringParameters": params,
        "headers": {},
    }


class TestTokenExchange:
    @pytest.fixture(autouse=True)
    def patch_env(self, monkeypatch):
        monkeypatch.setenv("REDIRECT_URI", "https://coquito.gcardona.me/auth/callback")
        monkeypatch.setenv("COGNITO_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("SSM_CLIENT_SECRET", "/coquito/prod/cognito/client_secret")
        monkeypatch.setenv("TOKEN_ENDPOINT", "https://auth.coquito.gcardona.me/oauth2/token")

    def _invoke(self, event, token_response=None, raise_exc=None):
        import src.handlers.auth.token_exchange as te  # noqa: PLC0415

        mock_exchange = MagicMock()
        if raise_exc:
            mock_exchange.side_effect = raise_exc
        else:
            mock_exchange.return_value = token_response or {
                "id_token": "id.tok",
                "access_token": "access.tok",
                "refresh_token": "refresh.tok",
                "expires_in": 3600,
            }

        with patch("src.handlers.auth.token_exchange.cognito.exchange_code", mock_exchange):
            return te.handler(event, MagicMock())

    def test_valid_code_returns_302_with_three_cookies(self):
        result = self._invoke(_make_event())
        assert result["statusCode"] == 200
        cookies = result.get("cookies", [])
        assert len(cookies) == 3
        for cookie in cookies:
            assert "HttpOnly" in cookie
            assert "Secure" in cookie
            assert "SameSite=Strict" in cookie

    def test_cognito_error_returns_503(self):
        result = self._invoke(
            _make_event(), raise_exc=RuntimeError("invalid_grant: Code expired")
        )
        assert result["statusCode"] == 503

    def test_state_echoed_in_redirect_location(self):
        result = self._invoke(_make_event(state="my-state"))
        assert result["statusCode"] == 302
        location = result.get("headers", {}).get("location", "")
        assert "state=my-state" in location

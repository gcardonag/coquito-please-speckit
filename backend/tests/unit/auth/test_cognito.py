"""Unit tests for the Cognito service.

Mocks urllib.request so no real HTTP calls are made.
RED step: these tests must FAIL before cognito.py is implemented.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


class TestCognitoService:
    @pytest.fixture(autouse=True)
    def patch_env(self, monkeypatch):
        monkeypatch.setenv("COGNITO_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("SSM_CLIENT_SECRET", "/coquito/prod/cognito/client_secret")
        monkeypatch.setenv("TOKEN_ENDPOINT", "https://auth.coquito.gcardona.me/oauth2/token")

    @pytest.fixture(autouse=True)
    def patch_ssm(self):
        """Patch SSM to return a fake client secret at cold-start."""
        import boto3
        with patch("boto3.client") as mock_boto:
            ssm_mock = MagicMock()
            ssm_mock.get_parameter.return_value = {
                "Parameter": {"Value": "test-client-secret"}
            }
            mock_boto.return_value = ssm_mock
            yield

    def _mock_token_response(self, data: dict):
        """Return a mock urllib.response-like object."""
        encoded = json.dumps(data).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = encoded
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_exchange_code_returns_token_dict(self):
        """exchange_code with valid code → returns dict with token fields."""
        from src.services import cognito  # noqa: PLC0415

        # Reset cached client_secret so SSM is re-read
        cognito._client_secret = None  # type: ignore[attr-defined]

        token_response = {
            "id_token": "id.tok.en",
            "access_token": "access.tok.en",
            "refresh_token": "refresh.tok.en",
            "expires_in": 3600,
        }
        mock_resp = self._mock_token_response(token_response)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = cognito.exchange_code(
                code="auth-code-123",
                redirect_uri="https://coquito.gcardona.me/auth/callback",
                code_verifier="verifier-abc",
            )

        assert result["id_token"] == "id.tok.en"
        assert result["access_token"] == "access.tok.en"
        assert result["refresh_token"] == "refresh.tok.en"

    def test_exchange_code_raises_on_cognito_error(self):
        """exchange_code when Cognito returns error → raises RuntimeError."""
        from src.services import cognito  # noqa: PLC0415

        cognito._client_secret = None  # type: ignore[attr-defined]
        error_response = {"error": "invalid_grant", "error_description": "Code expired"}
        mock_resp = self._mock_token_response(error_response)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="invalid_grant"):
                cognito.exchange_code(
                    code="bad-code",
                    redirect_uri="https://coquito.gcardona.me/auth/callback",
                    code_verifier="verifier-abc",
                )

    def test_revoke_token_calls_correct_endpoint(self):
        """revoke_token → calls /oauth2/revoke with the refresh token."""
        from src.services import cognito  # noqa: PLC0415

        cognito._client_secret = None  # type: ignore[attr-defined]
        mock_resp = MagicMock()
        mock_resp.read.return_value = b""
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            cognito.revoke_token("my-refresh-token")

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        body = request_obj.data.decode()
        assert "token=my-refresh-token" in body
        assert "/oauth2/revoke" in request_obj.full_url

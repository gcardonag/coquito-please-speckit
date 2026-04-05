"""Unit tests for the Lambda JWT authorizer.

Test RSA key pair fixture is used to sign JWTs locally without hitting Cognito.
JWKS fetch is mocked so tests are fully offline.

RED step: these tests must FAIL before authorizer.py is implemented.
"""
import json
import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def rsa_key_pair():
    """Generate a throw-away RSA-2048 key pair for test JWTs."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return private_pem, public_key


@pytest.fixture(scope="session")
def jwks_mock(rsa_key_pair):
    """Minimal JWKS response built from the test public key."""
    import base64

    _, public_key = rsa_key_pair
    pub_numbers = public_key.public_numbers()

    def _int_to_base64url(n: int) -> str:
        length = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()

    return {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-key-id",
                "use": "sig",
                "alg": "RS256",
                "n": _int_to_base64url(pub_numbers.n),
                "e": _int_to_base64url(pub_numbers.e),
            }
        ]
    }


def _make_token(
    private_pem: bytes,
    sub: str = "user-123",
    groups: list[str] | None = None,
    email: str = "user@example.com",
    client_id: str = "test-client-id",
    expired: bool = False,
    tampered: bool = False,
) -> str:
    """Create a signed JWT for testing."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TESTPOOL",
        "aud": client_id,
        "iat": now - 10,
        "exp": (now - 3600) if expired else (now + 3600),
        "email": email,
        "cognito:groups": groups or [],
        "token_use": "id",
    }
    token = jwt.encode(
        payload,
        private_pem,
        algorithm="RS256",
        headers={"kid": "test-key-id"},
    )
    if tampered:
        # Flip a character in the signature section
        parts = token.split(".")
        sig = list(parts[2])
        sig[0] = "X" if sig[0] != "X" else "Y"
        token = ".".join([parts[0], parts[1], "".join(sig)])
    return token


def _make_event(token: str | None = None) -> dict:
    """Build a minimal HTTP API v2 Lambda authorizer event."""
    cookie = f"id_token={token}" if token else ""
    return {
        "version": "2.0",
        "type": "REQUEST",
        "headers": {"cookie": cookie},
        "requestContext": {
            "http": {"method": "GET", "path": "/api/v1/varieties"}
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestAuthorizer:
    @pytest.fixture(autouse=True)
    def patch_env(self, monkeypatch):
        monkeypatch.setenv("COGNITO_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("JWKS_URI", "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TESTPOOL/.well-known/jwks.json")
        monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TESTPOOL")

    def _invoke(self, event, jwks_mock):
        from src.handlers.auth import authorizer  # noqa: PLC0415

        # Reset the module-level JWKS cache between test runs
        authorizer._jwks_cache.clear()  # type: ignore[attr-defined]

        with patch.object(authorizer, "_fetch_jwks", return_value=jwks_mock["keys"]):
            return authorizer.handler(event, MagicMock())

    def test_valid_token_returns_authorized(self, rsa_key_pair, jwks_mock):
        """Valid id_token cookie → isAuthorized=true with correct context."""
        private_pem, _ = rsa_key_pair
        token = _make_token(private_pem, sub="user-abc", groups=["authorized-user"], email="u@example.com")
        result = self._invoke(_make_event(token), jwks_mock)

        assert result["isAuthorized"] is True
        assert result["context"]["userId"] == "user-abc"
        assert result["context"]["role"] == "authorized-user"
        assert result["context"]["email"] == "u@example.com"

    def test_missing_cookie_returns_denied(self, rsa_key_pair, jwks_mock):
        """Missing id_token cookie → isAuthorized=false."""
        result = self._invoke(_make_event(None), jwks_mock)
        assert result["isAuthorized"] is False

    def test_expired_jwt_returns_denied(self, rsa_key_pair, jwks_mock):
        """Expired JWT → isAuthorized=false."""
        private_pem, _ = rsa_key_pair
        token = _make_token(private_pem, expired=True)
        result = self._invoke(_make_event(token), jwks_mock)
        assert result["isAuthorized"] is False

    def test_chef_group_returns_chef_role(self, rsa_key_pair, jwks_mock):
        """Valid JWT with chef group → role='chef'."""
        private_pem, _ = rsa_key_pair
        token = _make_token(private_pem, groups=["chef"])
        result = self._invoke(_make_event(token), jwks_mock)
        assert result["isAuthorized"] is True
        assert result["context"]["role"] == "chef"

    def test_authorized_user_group_returns_authorized_user_role(self, rsa_key_pair, jwks_mock):
        """Valid JWT with authorized-user group → role='authorized-user'."""
        private_pem, _ = rsa_key_pair
        token = _make_token(private_pem, groups=["authorized-user"])
        result = self._invoke(_make_event(token), jwks_mock)
        assert result["isAuthorized"] is True
        assert result["context"]["role"] == "authorized-user"

    def test_both_groups_chef_takes_precedence(self, rsa_key_pair, jwks_mock):
        """If user has both chef and authorized-user, chef takes precedence."""
        private_pem, _ = rsa_key_pair
        token = _make_token(private_pem, groups=["authorized-user", "chef"])
        result = self._invoke(_make_event(token), jwks_mock)
        assert result["isAuthorized"] is True
        assert result["context"]["role"] == "chef"

    def test_tampered_signature_returns_denied(self, rsa_key_pair, jwks_mock):
        """Tampered JWT signature → isAuthorized=false."""
        private_pem, _ = rsa_key_pair
        token = _make_token(private_pem, tampered=True)
        result = self._invoke(_make_event(token), jwks_mock)
        assert result["isAuthorized"] is False

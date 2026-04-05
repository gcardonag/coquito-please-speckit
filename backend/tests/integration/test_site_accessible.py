"""Integration test: unauthenticated GET /api/v1/varieties → 401.

Mocks the Lambda authorizer returning isAuthorized=false and verifies that
protected routes return 401 to unauthenticated callers.
"""
from unittest.mock import MagicMock, patch


class TestUnauthenticatedAccess:
    def _make_unauthorized_event(self) -> dict:
        """Simulate an API Gateway event after the authorizer returns isAuthorized=false.

        When the authorizer denies access, API Gateway returns 401 directly
        without invoking the handler. We test the authorizer denial path here.
        """
        return {
            "version": "2.0",
            "requestContext": {
                "http": {"method": "GET", "path": "/api/v1/varieties"},
            },
            "headers": {},  # no cookie
        }

    def test_authorizer_denies_unauthenticated_request(self):
        """Authorizer returns isAuthorized=false when no cookie is present."""
        import os

        os.environ.setdefault("COGNITO_CLIENT_ID", "test-client-id")
        os.environ.setdefault("JWKS_URI", "https://example.com/.well-known/jwks.json")
        os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_TEST")

        from src.handlers.auth import authorizer  # noqa: PLC0415

        authorizer._jwks_cache.clear()

        event = self._make_unauthorized_event()
        result = authorizer.handler(event, MagicMock())

        assert result["isAuthorized"] is False

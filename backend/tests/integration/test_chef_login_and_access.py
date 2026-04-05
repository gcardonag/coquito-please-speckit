"""Integration test: Chef login and role-based access.

Tests:
  (a) Chef session (role='chef') → Chef-only handler returns 200
  (b) No session → 401 (authorizer denies)
  (c) authorized-user session on Chef-only endpoint → 403

Uses JWT fixtures and mocks the authorizer context injection.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


def _make_protected_event(role: str | None = None, user_id: str = "user-123") -> dict:
    """Build an event as API Gateway would inject after authorizer approval."""
    event: dict = {
        "version": "2.0",
        "requestContext": {
            "http": {"method": "GET", "path": "/api/v1/batches/batch-001/config"},
        },
        "pathParameters": {"id": "batch-001"},
        "headers": {},
    }
    if role is not None:
        event["requestContext"]["authorizer"] = {
            "lambda": {"userId": user_id, "role": role, "email": "u@example.com"}
        }
    return event


class TestChefLoginAndAccess:
    @pytest.fixture(autouse=True)
    def patch_env(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
        monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
        monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    def _invoke_batch_config(self, event: dict) -> dict:
        """Invoke get_batch_config handler directly."""
        from src.handlers.get_batch_config import handler  # noqa: PLC0415
        from src.models.batch import Batch  # noqa: PLC0415

        mock_batch_item = {
            "batchId": "batch-001",
            "batchName": "Test Batch",
            "cutoffDate": "2027-12-31",
            "maxBottleVolumeMl": 750,
            "status": "OPEN",
            "availableVarietyIds": [],
            "acquiredIngredients": {},
            "createdAt": "2026-01-01T00:00:00Z",
        }

        with patch("src.handlers.get_batch_config.get_item", return_value=mock_batch_item):
            return handler(event, MagicMock())

    def test_chef_session_returns_200(self):
        """Chef role → batch config handler returns 200."""
        event = _make_protected_event(role="chef")
        result = self._invoke_batch_config(event)
        assert result["statusCode"] == 200

    def test_authorized_user_on_chef_only_endpoint_returns_403(self):
        """authorized-user role on Chef-only endpoint → 403."""
        event = _make_protected_event(role="authorized-user")
        result = self._invoke_batch_config(event)
        assert result["statusCode"] == 403
        # Handler returns body as dict (not JSON string)
        body = result["body"] if isinstance(result["body"], dict) else json.loads(result["body"])
        assert body["code"] == "FORBIDDEN"

    def test_no_session_authorizer_denies(self):
        """No cookie → authorizer returns isAuthorized=false."""
        import os  # noqa: PLC0415

        os.environ.setdefault("COGNITO_CLIENT_ID", "test-client-id")
        os.environ.setdefault("JWKS_URI", "https://example.com/.well-known/jwks.json")

        from src.handlers.auth import authorizer  # noqa: PLC0415

        authorizer._jwks_cache.clear()
        event = {
            "version": "2.0",
            "requestContext": {"http": {"method": "GET", "path": "/api/v1/batches/b1/config"}},
            "headers": {},
        }
        result = authorizer.handler(event, MagicMock())
        assert result["isAuthorized"] is False

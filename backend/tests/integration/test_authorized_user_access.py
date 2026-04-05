"""Integration tests for authorized-user access and user isolation.

T049: authorized-user access patterns
T050: user isolation (can't access another user's request)
T051a: cancel_request ownership check

Uses JWT fixtures and mocks authorizer context injection.
"""
import json
from unittest.mock import MagicMock, patch

import pytest


def _auth_event(role: str, user_id: str = "user-abc", path_params: dict | None = None, body: str | None = None, method: str = "GET", path: str = "/api/v1/requests") -> dict:
    """Build an API GW v2 event with authorizer context injected."""
    event: dict = {
        "version": "2.0",
        "requestContext": {
            "http": {"method": method, "path": path},
            "authorizer": {
                "lambda": {"userId": user_id, "role": role, "email": f"{user_id}@example.com"}
            },
        },
        "headers": {},
    }
    if path_params:
        event["pathParameters"] = path_params
    if body is not None:
        event["body"] = body
    return event


class TestAuthorizedUserAccess:
    """T049: Authorized user access patterns."""

    @pytest.fixture(autouse=True)
    def patch_env(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
        monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
        monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")

    def test_authorized_user_can_create_request(self):
        """authorized-user → POST /api/v1/requests returns 201."""
        from src.handlers.create_request import handler  # noqa: PLC0415

        body = json.dumps({
            "requesterName": "Test User",
            "requesterEmail": "user@example.com",
            "batchId": "batch-001",
            "varietyId": "variety-001",
            "pickupDate": "2028-02-15",
            "pickupTime": "10:00",
            "exchangeLocation": "Main St",
            "bottleProvided": False,
            "costContribution": False,
        })

        mock_batch = {
            "batchId": "batch-001", "batchName": "Test", "cutoffDate": "2027-12-31",
            "maxBottleVolumeMl": 750, "status": "OPEN", "availableVarietyIds": ["variety-001"],
            "acquiredIngredients": {}, "createdAt": "2026-01-01T00:00:00Z",
        }
        mock_variety = {
            "varietyId": "variety-001", "name": "Classic", "description": "Traditional",
            "imageKey": "img.jpg", "active": True, "bottleYieldMl": 750, "ingredients": [],
        }

        event = _auth_event("authorized-user", user_id="user-abc", method="POST", path="/api/v1/requests", body=body)

        with patch("src.handlers.create_request.get_item") as mock_get, \
             patch("src.handlers.create_request.put_item"), \
             patch("src.handlers.create_request.scan_table", return_value=[]), \
             patch("src.handlers.create_request.requests_table_name", return_value="coquito-requests"), \
             patch("src.handlers.create_request.batches_table_name", return_value="coquito-batches"), \
             patch("src.handlers.create_request.varieties_table_name", return_value="coquito-varieties"), \
             patch("src.handlers.create_request._schedule_reminders", return_value=[]):
            mock_get.side_effect = [mock_batch, mock_variety]
            result = handler(event, MagicMock())

        assert result["statusCode"] == 201

    def test_authorized_user_on_chef_endpoint_returns_403(self):
        """authorized-user → GET /api/v1/batches/{id}/config returns 403."""
        from src.handlers.get_batch_config import handler  # noqa: PLC0415

        event = _auth_event("authorized-user", path_params={"batchId": "batch-001"})
        result = handler(event, MagicMock())

        assert result["statusCode"] == 403
        body = result["body"] if isinstance(result["body"], dict) else json.loads(result["body"])
        assert body["code"] == "FORBIDDEN"

    def test_no_session_on_create_request_denied_by_authorizer(self):
        """No session → authorizer returns isAuthorized=false (simulated)."""
        import os  # noqa: PLC0415

        os.environ.setdefault("COGNITO_CLIENT_ID", "test-client-id")
        os.environ.setdefault("JWKS_URI", "https://example.com/.well-known/jwks.json")

        from src.handlers.auth import authorizer  # noqa: PLC0415

        authorizer._jwks_cache.clear()
        event = {
            "version": "2.0",
            "requestContext": {"http": {"method": "POST", "path": "/api/v1/requests"}},
            "headers": {},
        }
        result = authorizer.handler(event, MagicMock())
        assert result["isAuthorized"] is False


class TestUserIsolation:
    """T050: Users cannot access each other's requests."""

    @pytest.fixture(autouse=True)
    def patch_env(self, monkeypatch):
        monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
        monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
        monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")

    def test_authorized_user_cannot_get_other_users_request(self):
        """authorized-user A tries to GET request owned by user B → 403."""
        from src.handlers.get_request import handler  # noqa: PLC0415

        # Request owned by user-xyz
        mock_request = {
            "requestId": "req-001",
            "requesterId": "user-xyz",
            "requesterName": "User XYZ",
            "requesterEmail": "xyz@example.com",
            "batchId": "b1", "varietyId": "v1",
            "pickupDate": "2027-12-20", "pickupTime": "10:00",
            "exchangeLocation": "A", "bottleProvided": False,
            "bottleVolumeMl": None, "costContribution": False,
            "status": "CONFIRMED", "reminders": [],
            "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z",
        }

        # user-abc (not user-xyz) tries to access req-001
        event = _auth_event("authorized-user", user_id="user-abc", path_params={"requestId": "req-001"})

        with patch("src.handlers.get_request.get_item", return_value=mock_request), \
             patch("src.handlers.get_request.requests_table_name", return_value="coquito-requests"):
            result = handler(event, MagicMock())

        assert result["statusCode"] == 403
        body = result["body"] if isinstance(result["body"], dict) else json.loads(result["body"])
        assert body["code"] == "FORBIDDEN"

    def test_authorized_user_can_get_own_request(self):
        """authorized-user A can GET their own request."""
        from src.handlers.get_request import handler  # noqa: PLC0415
        from src.services.dynamodb import ItemNotFoundError  # noqa: PLC0415

        mock_request = {
            "requestId": "req-002",
            "requesterId": "user-abc",
            "requesterName": "User ABC",
            "requesterEmail": "abc@example.com",
            "batchId": "b1", "varietyId": "v1",
            "pickupDate": "2027-12-20", "pickupTime": "10:00",
            "exchangeLocation": "A", "bottleProvided": False,
            "bottleVolumeMl": None, "costContribution": False,
            "status": "CONFIRMED", "reminders": [],
            "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z",
        }

        event = _auth_event("authorized-user", user_id="user-abc", path_params={"requestId": "req-002"})

        # get_item is called 3 times: request, batch, variety — batch and variety raise NotFound
        with patch("src.handlers.get_request.get_item") as mock_get, \
             patch("src.handlers.get_request.requests_table_name", return_value="coquito-requests"), \
             patch("src.handlers.get_request.batches_table_name", return_value="coquito-batches"), \
             patch("src.handlers.get_request.varieties_table_name", return_value="coquito-varieties"):
            mock_get.side_effect = [mock_request, ItemNotFoundError("b1"), ItemNotFoundError("v1")]
            result = handler(event, MagicMock())

        # Should not be 403 (may be 200 or error loading batch, but not access denied)
        assert result["statusCode"] != 403

    def test_authorized_user_cannot_cancel_other_users_request(self):
        """T051a: authorized-user cannot cancel another user's request → 403."""
        from src.handlers.cancel_request import handler  # noqa: PLC0415

        mock_request = {
            "requestId": "req-cancel-001",
            "requesterId": "user-xyz",
            "requesterName": "User XYZ",
            "requesterEmail": "xyz@example.com",
            "batchId": "b1", "varietyId": "v1",
            "pickupDate": "2027-12-20", "pickupTime": "10:00",
            "exchangeLocation": "A", "bottleProvided": False,
            "bottleVolumeMl": None, "costContribution": False,
            "status": "CONFIRMED", "reminders": [],
            "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z",
        }

        # user-abc tries to cancel user-xyz's request
        event = _auth_event(
            "authorized-user", user_id="user-abc",
            path_params={"requestId": "req-cancel-001"},
            method="POST", path="/api/v1/requests/req-cancel-001/cancel",
        )

        with patch("src.handlers.cancel_request.get_item", return_value=mock_request), \
             patch("src.handlers.cancel_request.requests_table_name", return_value="coquito-requests"), \
             patch("src.handlers.cancel_request.batches_table_name", return_value="coquito-batches"):
            result = handler(event, MagicMock())

        assert result["statusCode"] == 403
        body = result["body"] if isinstance(result["body"], dict) else json.loads(result["body"])
        assert body["code"] == "FORBIDDEN"

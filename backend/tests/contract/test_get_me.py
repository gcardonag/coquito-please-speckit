"""T004: Contract test (RED) for GET /api/v1/me."""
import json
from unittest.mock import MagicMock


def _invoke(role: str = "chef", user_id: str = "u-001", email: str = "chef@example.com") -> dict:
    from src.handlers.get_me import handler  # noqa: PLC0415

    event = {
        "version": "2.0",
        "requestContext": {
            "http": {"method": "GET", "path": "/api/v1/me"},
            "authorizer": {
                "lambda": {"userId": user_id, "role": role, "email": email}
            },
        },
        "headers": {},
    }
    return handler(event, MagicMock())


class TestGetMeContract:
    def test_returns_200_for_chef(self):
        response = _invoke(role="chef")
        assert response["statusCode"] == 200

    def test_returns_200_for_authorized_user(self):
        response = _invoke(role="authorized-user")
        assert response["statusCode"] == 200

    def test_response_has_user_id(self):
        response = _invoke(user_id="u-abc")
        body = json.loads(response["body"])
        assert body["userId"] == "u-abc"

    def test_response_has_role(self):
        response = _invoke(role="chef")
        body = json.loads(response["body"])
        assert body["role"] == "chef"

    def test_response_has_email(self):
        response = _invoke(email="chef@example.com")
        body = json.loads(response["body"])
        assert body["email"] == "chef@example.com"

    def test_response_shape_exact(self):
        response = _invoke(role="authorized-user", user_id="u-xyz", email="user@example.com")
        body = json.loads(response["body"])
        assert set(body.keys()) == {"userId", "role", "email"}

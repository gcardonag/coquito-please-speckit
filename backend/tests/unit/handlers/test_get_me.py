"""T005: Unit tests (RED) for get_me Lambda handler."""
import json
from unittest.mock import MagicMock


def _make_event(role: str = "chef", user_id: str = "u-001", email: str = "chef@example.com") -> dict:
    return {
        "version": "2.0",
        "requestContext": {
            "http": {"method": "GET", "path": "/api/v1/me"},
            "authorizer": {
                "lambda": {"userId": user_id, "role": role, "email": email}
            },
        },
        "headers": {},
    }


class TestGetMeHandler:
    def test_chef_returns_200_with_chef_role(self):
        from src.handlers.get_me import handler  # noqa: PLC0415
        response = handler(_make_event(role="chef"), MagicMock())
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["role"] == "chef"

    def test_authorized_user_returns_200(self):
        from src.handlers.get_me import handler  # noqa: PLC0415
        response = handler(_make_event(role="authorized-user"), MagicMock())
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["role"] == "authorized-user"

    def test_returns_correct_user_id_and_email(self):
        from src.handlers.get_me import handler  # noqa: PLC0415
        response = handler(_make_event(user_id="u-xyz", email="test@example.com"), MagicMock())
        body = json.loads(response["body"])
        assert body["userId"] == "u-xyz"
        assert body["email"] == "test@example.com"

    def test_missing_authorizer_context_returns_401(self):
        from src.handlers.get_me import handler  # noqa: PLC0415
        event = {
            "version": "2.0",
            "requestContext": {"http": {"method": "GET", "path": "/api/v1/me"}},
            "headers": {},
        }
        response = handler(event, MagicMock())
        assert response["statusCode"] == 401

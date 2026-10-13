"""Contract tests (RED) for POST /api/v1/users — extended for firstName/lastName.

Tests added per T020:
  - firstName present → 201 with Cognito given_name set
  - firstName missing → 400 VALIDATION_ERROR
  - lastName optional → 201 without family_name
  - duplicate email → 409 USER_EXISTS
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TestPool")


def _chef_event(body: dict) -> dict:
    return {
        "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
        "body": json.dumps(body),
    }


def _non_chef_event(body: dict) -> dict:
    return {
        "requestContext": {"authorizer": {"lambda": {"role": "authorized-user"}}},
        "body": json.dumps(body),
    }


_MOCK_CREATE_RESPONSE = {
    "User": {
        "Attributes": [
            {"Name": "sub", "Value": "new-user-sub-001"},
            {"Name": "email", "Value": "jane@example.com"},
        ]
    }
}


class TestCreateUserContract:
    def test_201_with_first_name_and_last_name(self):
        from src.handlers.create_user import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.admin_create_user.return_value = _MOCK_CREATE_RESPONSE
            mock_cognito.admin_add_user_to_group.return_value = {}
            result = handler(
                _chef_event({"email": "jane@example.com", "firstName": "Jane", "lastName": "Doe"}),
                MagicMock(),
            )
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["userId"] == "new-user-sub-001"
        assert body["email"] == "jane@example.com"
        # Verify given_name was passed to Cognito
        call_kwargs = mock_cognito.admin_create_user.call_args[1]
        attrs = {a["Name"]: a["Value"] for a in call_kwargs["UserAttributes"]}
        assert attrs.get("given_name") == "Jane"
        assert attrs.get("family_name") == "Doe"

    def test_201_without_last_name(self):
        from src.handlers.create_user import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.admin_create_user.return_value = _MOCK_CREATE_RESPONSE
            mock_cognito.admin_add_user_to_group.return_value = {}
            result = handler(
                _chef_event({"email": "jane@example.com", "firstName": "Jane"}),
                MagicMock(),
            )
        assert result["statusCode"] == 201
        # Verify family_name was NOT passed when lastName omitted
        call_kwargs = mock_cognito.admin_create_user.call_args[1]
        attr_names = [a["Name"] for a in call_kwargs["UserAttributes"]]
        assert "family_name" not in attr_names

    def test_400_missing_first_name(self):
        from src.handlers.create_user import handler  # noqa: PLC0415
        with patch("boto3.client"):
            result = handler(
                _chef_event({"email": "jane@example.com"}),
                MagicMock(),
            )
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["code"] == "VALIDATION_ERROR"
        assert "first name" in body["message"].lower()

    def test_400_empty_first_name_after_trim(self):
        from src.handlers.create_user import handler  # noqa: PLC0415
        with patch("boto3.client"):
            result = handler(
                _chef_event({"email": "jane@example.com", "firstName": "   "}),
                MagicMock(),
            )
        assert result["statusCode"] == 400
        assert json.loads(result["body"])["code"] == "VALIDATION_ERROR"

    def test_409_duplicate_email(self):
        from src.handlers.create_user import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            exc = ClientError(
                {"Error": {"Code": "UsernameExistsException", "Message": "User already exists."}},
                "AdminCreateUser",
            )
            mock_cognito.admin_create_user.side_effect = exc
            result = handler(
                _chef_event({"email": "dup@example.com", "firstName": "Jane"}),
                MagicMock(),
            )
        assert result["statusCode"] == 409
        assert json.loads(result["body"])["code"] == "USER_EXISTS"

    def test_403_non_chef_is_rejected(self):
        from src.handlers.create_user import handler  # noqa: PLC0415
        with patch("boto3.client"):
            result = handler(
                _non_chef_event({"email": "jane@example.com", "firstName": "Jane"}),
                MagicMock(),
            )
        assert result["statusCode"] == 403

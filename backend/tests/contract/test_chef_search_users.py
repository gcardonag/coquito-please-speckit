"""Contract tests (RED) for GET /api/v1/chef/users."""
import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TestPool")
    monkeypatch.setenv("DYNAMODB_BATCH_ACCESS_TABLE", "coquito-batch-access")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")


_CHEF_EVENT = {
    "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
    "queryStringParameters": {"query": "jane"},
}

_NON_CHEF_EVENT = {
    "requestContext": {"authorizer": {"lambda": {"role": "authorized-user"}}},
    "queryStringParameters": {"query": "jane"},
}

_COGNITO_USER_EMAIL = {
    "Username": "jane@example.com",
    "Attributes": [
        {"Name": "sub", "Value": "sub-email-match"},
        {"Name": "email", "Value": "jane@example.com"},
        {"Name": "given_name", "Value": "Jane"},
        {"Name": "family_name", "Value": "Doe"},
    ],
}

_COGNITO_USER_NAME = {
    "Username": "alice@example.com",
    "Attributes": [
        {"Name": "sub", "Value": "sub-name-match"},
        {"Name": "email", "Value": "alice@example.com"},
        {"Name": "given_name", "Value": "Janet"},
        {"Name": "family_name", "Value": "Smith"},
    ],
}

_COGNITO_USER_BOTH = {
    "Username": "jane.smith@example.com",
    "Attributes": [
        {"Name": "sub", "Value": "sub-both-match"},
        {"Name": "email", "Value": "jane.smith@example.com"},
        {"Name": "given_name", "Value": "Jane"},
        {"Name": "family_name", "Value": "Smith"},
    ],
}


class TestSearchUsersContract:
    def test_200_email_match_returns_users(self):
        from src.handlers.chef_search_users import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.list_users.side_effect = [
                {"Users": [_COGNITO_USER_EMAIL]},  # email filter call
                {"Users": []},                      # given_name filter call
            ]
            result = handler(_CHEF_EVENT, MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "users" in body
        assert isinstance(body["users"], list)
        assert len(body["users"]) == 1
        u = body["users"][0]
        assert u["userId"] == "sub-email-match"
        assert u["email"] == "jane@example.com"
        assert u["firstName"] == "Jane"
        assert u["lastName"] == "Doe"

    def test_200_name_match_returns_users(self):
        from src.handlers.chef_search_users import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.list_users.side_effect = [
                {"Users": []},                       # email filter call
                {"Users": [_COGNITO_USER_NAME]},     # given_name filter call
            ]
            result = handler(_CHEF_EVENT, MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body["users"]) == 1
        assert body["users"][0]["userId"] == "sub-name-match"

    def test_200_deduplicates_user_appearing_in_both_results(self):
        from src.handlers.chef_search_users import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.list_users.side_effect = [
                {"Users": [_COGNITO_USER_BOTH]},   # email filter
                {"Users": [_COGNITO_USER_BOTH]},   # given_name filter (same user)
            ]
            result = handler(_CHEF_EVENT, MagicMock())
        body = json.loads(result["body"])
        assert result["statusCode"] == 200
        assert len(body["users"]) == 1  # deduplicated

    def test_200_empty_results_when_no_match(self):
        from src.handlers.chef_search_users import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.list_users.side_effect = [
                {"Users": []},
                {"Users": []},
            ]
            result = handler(_CHEF_EVENT, MagicMock())
        assert result["statusCode"] == 200
        assert json.loads(result["body"]) == {"users": []}

    def test_400_missing_query_param(self):
        from src.handlers.chef_search_users import handler  # noqa: PLC0415
        event = {**_CHEF_EVENT, "queryStringParameters": {}}
        result = handler(event, MagicMock())
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["code"] == "VALIDATION_ERROR"
        assert "message" in body

    def test_400_null_query_string_parameters(self):
        from src.handlers.chef_search_users import handler  # noqa: PLC0415
        event = {**_CHEF_EVENT, "queryStringParameters": None}
        result = handler(event, MagicMock())
        assert result["statusCode"] == 400

    def test_403_non_chef_is_rejected(self):
        from src.handlers.chef_search_users import handler  # noqa: PLC0415
        result = handler(_NON_CHEF_EVENT, MagicMock())
        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert body["code"] == "CHEF_ROLE_REQUIRED"

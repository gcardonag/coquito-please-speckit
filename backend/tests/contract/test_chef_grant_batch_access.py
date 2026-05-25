"""Contract tests (RED) for PUT /api/v1/chef/batches/{id}/access/{userId}."""
import json
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws


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


def _chef_event(batch_id: str, user_id: str) -> dict:
    return {
        "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
        "pathParameters": {"id": batch_id, "userId": user_id},
    }


def _non_chef_event(batch_id: str, user_id: str) -> dict:
    return {
        "requestContext": {"authorizer": {"lambda": {"role": "authorized-user"}}},
        "pathParameters": {"id": batch_id, "userId": user_id},
    }


@pytest.fixture
def tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        batches = ddb.create_table(
            TableName="coquito-batches",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        batches.put_item(Item={
            "batchId": "b-001",
            "batchName": "Holiday 2026",
            "status": "OPEN",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": [],
            "createdAt": "2026-01-01T00:00:00Z",
        })
        batches.put_item(Item={
            "batchId": "b-closed",
            "batchName": "Old Batch",
            "status": "CLOSED",
            "cutoffDate": "2025-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": [],
            "createdAt": "2025-01-01T00:00:00Z",
        })
        ddb.create_table(
            TableName="coquito-batch-access",
            KeySchema=[
                {"AttributeName": "batchId", "KeyType": "HASH"},
                {"AttributeName": "userId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "batchId", "AttributeType": "S"},
                {"AttributeName": "userId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield


_COGNITO_USER_ATTRS = [
    {"Name": "sub", "Value": "user-sub-001"},
    {"Name": "email", "Value": "jane@example.com"},
    {"Name": "given_name", "Value": "Jane"},
    {"Name": "family_name", "Value": "Doe"},
]


class TestGrantBatchAccessContract:
    def test_200_grants_access_and_returns_grant_record(self, tables):
        from unittest.mock import patch  # noqa: PLC0415
        from src.handlers.chef_grant_batch_access import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.admin_get_user.return_value = {"UserAttributes": _COGNITO_USER_ATTRS}
            result = handler(_chef_event("b-001", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["batchId"] == "b-001"
        assert body["userId"] == "user-sub-001"
        assert "grantedAt" in body

    def test_403_non_chef_is_rejected(self, tables):
        from src.handlers.chef_grant_batch_access import handler  # noqa: PLC0415
        result = handler(_non_chef_event("b-001", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "CHEF_ROLE_REQUIRED"

    def test_403_closed_batch_returns_forbidden(self, tables):
        from unittest.mock import patch  # noqa: PLC0415
        from src.handlers.chef_grant_batch_access import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_client.return_value = MagicMock()
            result = handler(_chef_event("b-closed", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert "open" in body["message"].lower() or "OPEN" in body["message"]

    def test_404_batch_not_found(self, tables):
        from unittest.mock import patch  # noqa: PLC0415
        from src.handlers.chef_grant_batch_access import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_client.return_value = MagicMock()
            result = handler(_chef_event("no-such-batch", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert body["code"] == "NOT_FOUND"

    def test_404_user_not_found_in_cognito(self, tables):
        from unittest.mock import patch  # noqa: PLC0415
        from src.handlers.chef_grant_batch_access import handler  # noqa: PLC0415
        from botocore.exceptions import ClientError  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            error = ClientError(
                {"Error": {"Code": "UserNotFoundException", "Message": "User does not exist."}},
                "AdminGetUser",
            )
            mock_cognito.admin_get_user.side_effect = error
            result = handler(_chef_event("b-001", "no-such-user"), MagicMock())
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert body["code"] == "NOT_FOUND"

    def test_409_duplicate_grant_returns_conflict(self, tables):
        from unittest.mock import patch  # noqa: PLC0415
        from src.handlers.chef_grant_batch_access import handler  # noqa: PLC0415
        # First grant
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.admin_get_user.return_value = {"UserAttributes": _COGNITO_USER_ATTRS}
            handler(_chef_event("b-001", "user-sub-001"), MagicMock())
        # Second grant (duplicate)
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.admin_get_user.return_value = {"UserAttributes": _COGNITO_USER_ATTRS}
            result = handler(_chef_event("b-001", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 409
        body = json.loads(result["body"])
        assert body["code"] == "ALREADY_GRANTED"

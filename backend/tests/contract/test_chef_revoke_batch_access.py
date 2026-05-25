"""Contract tests (RED) for DELETE /api/v1/chef/batches/{id}/access/{userId}."""
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
        access_table = ddb.create_table(
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
        access_table.put_item(Item={
            "batchId": "b-001",
            "userId": "user-sub-001",
            "email": "jane@example.com",
            "firstName": "Jane",
            "lastName": "Doe",
            "grantedAt": "2026-05-23T18:00:00Z",
        })
        yield


class TestRevokeBatchAccessContract:
    def test_204_revoke_existing_grant(self, tables):
        from src.handlers.chef_revoke_batch_access import handler  # noqa: PLC0415
        result = handler(_chef_event("b-001", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 204
        assert result["body"] == ""

    def test_403_non_chef_is_rejected(self, tables):
        from src.handlers.chef_revoke_batch_access import handler  # noqa: PLC0415
        result = handler(_non_chef_event("b-001", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "CHEF_ROLE_REQUIRED"

    def test_403_closed_batch_returns_forbidden(self, tables):
        from src.handlers.chef_revoke_batch_access import handler  # noqa: PLC0415
        result = handler(_chef_event("b-closed", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert body["code"] == "FORBIDDEN"
        assert "open" in body["message"].lower() or "OPEN" in body["message"]

    def test_404_batch_not_found(self, tables):
        from src.handlers.chef_revoke_batch_access import handler  # noqa: PLC0415
        result = handler(_chef_event("no-such-batch", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 404
        assert json.loads(result["body"])["code"] == "NOT_FOUND"

    def test_404_access_grant_not_found(self, tables):
        from src.handlers.chef_revoke_batch_access import handler  # noqa: PLC0415
        result = handler(_chef_event("b-001", "no-such-user"), MagicMock())
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert body["code"] == "NOT_FOUND"
        assert "grant" in body["message"].lower() or "access" in body["message"].lower()

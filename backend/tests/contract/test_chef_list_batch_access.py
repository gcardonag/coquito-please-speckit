"""Contract tests (RED) for GET /api/v1/chef/batches/{id}/access."""
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


def _chef_event(batch_id: str) -> dict:
    return {
        "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
        "pathParameters": {"id": batch_id},
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


class TestListBatchAccessContract:
    def test_200_returns_batch_id_and_users_list(self, tables):
        from src.handlers.chef_list_batch_access import handler  # noqa: PLC0415
        result = handler(_chef_event("b-001"), MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["batchId"] == "b-001"
        assert isinstance(body["users"], list)

    def test_200_returns_user_fields(self, tables):
        from src.handlers.chef_list_batch_access import handler  # noqa: PLC0415
        result = handler(_chef_event("b-001"), MagicMock())
        body = json.loads(result["body"])
        assert len(body["users"]) == 1
        u = body["users"][0]
        assert u["userId"] == "user-sub-001"
        assert u["email"] == "jane@example.com"
        assert u["firstName"] == "Jane"
        assert u["lastName"] == "Doe"
        assert "grantedAt" in u

    def test_200_empty_users_list_when_no_grants(self, tables):
        from src.handlers.chef_list_batch_access import handler  # noqa: PLC0415
        # Add a second batch with no access grants into the existing mocked tables
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.Table("coquito-batches").put_item(Item={
            "batchId": "b-empty",
            "batchName": "Empty Batch",
            "status": "OPEN",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": [],
            "createdAt": "2026-01-01T00:00:00Z",
        })
        result = handler(_chef_event("b-empty"), MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["users"] == []

    def test_404_batch_not_found(self, tables):
        from src.handlers.chef_list_batch_access import handler  # noqa: PLC0415
        result = handler(_chef_event("no-such-batch"), MagicMock())
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert body["code"] == "NOT_FOUND"

    def test_403_non_chef_is_rejected(self, tables):
        from src.handlers.chef_list_batch_access import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "authorized-user"}}},
            "pathParameters": {"id": "b-001"},
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "CHEF_ROLE_REQUIRED"

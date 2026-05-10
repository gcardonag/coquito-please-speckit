"""T011: Contract test (RED) for GET /api/v1/batches."""
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
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")


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
        requests = ddb.create_table(
            TableName="coquito-requests",
            KeySchema=[{"AttributeName": "requestId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "requestId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        batches.put_item(Item={
            "batchId": "b-001",
            "batchName": "Holiday 2026",
            "cutoffDate": "2026-11-15",
            "maxBottleVolumeMl": 1000,
            "availableVarietyIds": ["classic", "chocolate"],
            "status": "OPEN",
            "createdAt": "2026-05-01T12:00:00Z",
        })
        requests.put_item(Item={
            "requestId": "r-001",
            "batchId": "b-001",
            "status": "PENDING",
        })
        requests.put_item(Item={
            "requestId": "r-002",
            "batchId": "b-001",
            "status": "CANCELLED",
        })
        yield {"batches": batches, "requests": requests}


def _chef_event() -> dict:
    return {
        "version": "2.0",
        "requestContext": {
            "http": {"method": "GET", "path": "/api/v1/batches"},
            "authorizer": {"lambda": {"userId": "u-chef", "role": "chef", "email": "chef@example.com"}},
        },
        "headers": {},
    }


def _non_chef_event() -> dict:
    return {
        "version": "2.0",
        "requestContext": {
            "http": {"method": "GET", "path": "/api/v1/batches"},
            "authorizer": {"lambda": {"userId": "u-user", "role": "authorized-user", "email": "user@example.com"}},
        },
        "headers": {},
    }


class TestListBatchesContract:
    def test_chef_receives_200(self, tables):
        from src.handlers.list_batches import handler  # noqa: PLC0415
        response = handler(_chef_event(), MagicMock())
        assert response["statusCode"] == 200

    def test_non_chef_receives_403(self, tables):
        from src.handlers.list_batches import handler  # noqa: PLC0415
        response = handler(_non_chef_event(), MagicMock())
        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["code"] == "CHEF_ROLE_REQUIRED"

    def test_response_has_batches_array(self, tables):
        from src.handlers.list_batches import handler  # noqa: PLC0415
        response = handler(_chef_event(), MagicMock())
        body = json.loads(response["body"])
        assert "batches" in body
        assert isinstance(body["batches"], list)

    def test_batch_item_has_required_fields(self, tables):
        from src.handlers.list_batches import handler  # noqa: PLC0415
        response = handler(_chef_event(), MagicMock())
        body = json.loads(response["body"])
        batch = body["batches"][0]
        for field in ("batchId", "batchName", "cutoffDate", "maxBottleVolumeMl",
                       "status", "availableVarietyIds", "activeRequestCount", "createdAt"):
            assert field in batch, f"missing field: {field}"

    def test_active_request_count_excludes_cancelled(self, tables):
        from src.handlers.list_batches import handler  # noqa: PLC0415
        response = handler(_chef_event(), MagicMock())
        body = json.loads(response["body"])
        batch = next(b for b in body["batches"] if b["batchId"] == "b-001")
        # r-001 is PENDING (counted), r-002 is CANCELLED (not counted)
        assert batch["activeRequestCount"] == 1

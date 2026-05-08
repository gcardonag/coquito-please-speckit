"""T012: Unit tests (RED) for list_batches Lambda handler."""
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
        # Batch A — newer
        batches.put_item(Item={
            "batchId": "b-002",
            "batchName": "Summer 2026",
            "cutoffDate": "2026-08-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["classic"],
            "status": "OPEN",
            "createdAt": "2026-04-01T00:00:00Z",
        })
        # Batch B — older
        batches.put_item(Item={
            "batchId": "b-001",
            "batchName": "Holiday 2025",
            "cutoffDate": "2025-11-15",
            "maxBottleVolumeMl": 1000,
            "availableVarietyIds": ["classic", "chocolate"],
            "status": "CLOSED",
            "createdAt": "2025-10-01T00:00:00Z",
        })
        # Two requests on b-002: one PENDING, one CANCELLED
        requests.put_item(Item={"requestId": "r-001", "batchId": "b-002", "status": "PENDING"})
        requests.put_item(Item={"requestId": "r-002", "batchId": "b-002", "status": "CANCELLED"})
        # One CONFIRMED on b-001
        requests.put_item(Item={"requestId": "r-003", "batchId": "b-001", "status": "CONFIRMED"})
        yield {"batches": batches, "requests": requests}


def _make_event(role: str = "chef") -> dict:
    return {
        "version": "2.0",
        "requestContext": {
            "http": {"method": "GET", "path": "/api/v1/batches"},
            "authorizer": {"lambda": {"userId": "u-001", "role": role, "email": "chef@example.com"}},
        },
        "headers": {},
    }


class TestListBatchesHandler:
    def test_returns_all_batches(self, tables):
        from src.handlers.list_batches import handler  # noqa: PLC0415
        response = handler(_make_event(), MagicMock())
        body = json.loads(response["body"])
        assert len(body["batches"]) == 2

    def test_batches_sorted_by_created_at_descending(self, tables):
        from src.handlers.list_batches import handler  # noqa: PLC0415
        response = handler(_make_event(), MagicMock())
        body = json.loads(response["body"])
        dates = [b["createdAt"] for b in body["batches"]]
        assert dates == sorted(dates, reverse=True)

    def test_active_request_count_excludes_cancelled(self, tables):
        from src.handlers.list_batches import handler  # noqa: PLC0415
        response = handler(_make_event(), MagicMock())
        body = json.loads(response["body"])
        b002 = next(b for b in body["batches"] if b["batchId"] == "b-002")
        assert b002["activeRequestCount"] == 1

    def test_confirmed_requests_counted(self, tables):
        from src.handlers.list_batches import handler  # noqa: PLC0415
        response = handler(_make_event(), MagicMock())
        body = json.loads(response["body"])
        b001 = next(b for b in body["batches"] if b["batchId"] == "b-001")
        assert b001["activeRequestCount"] == 1

    def test_empty_table_returns_empty_list(self, monkeypatch):
        with mock_aws():
            ddb = boto3.resource("dynamodb", region_name="us-east-1")
            ddb.create_table(
                TableName="coquito-batches",
                KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            ddb.create_table(
                TableName="coquito-requests",
                KeySchema=[{"AttributeName": "requestId", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "requestId", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            from src.handlers.list_batches import handler  # noqa: PLC0415
            response = handler(_make_event(), MagicMock())
            body = json.loads(response["body"])
            assert body["batches"] == []

    def test_non_chef_gets_403(self, tables):
        from src.handlers.list_batches import handler  # noqa: PLC0415
        response = handler(_make_event(role="authorized-user"), MagicMock())
        assert response["statusCode"] == 403

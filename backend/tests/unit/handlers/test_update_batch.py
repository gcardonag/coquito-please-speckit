"""T036: Unit tests (RED) for update_batch Lambda handler."""
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
        varieties = ddb.create_table(
            TableName="coquito-varieties",
            KeySchema=[{"AttributeName": "varietyId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "varietyId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        varieties.put_item(Item={"varietyId": "classic", "name": "Classic", "active": True})
        varieties.put_item(Item={"varietyId": "chocolate", "name": "Chocolate", "active": True})
        batches.put_item(Item={
            "batchId": "b-001",
            "batchName": "Holiday 2026",
            "cutoffDate": "2030-11-15",
            "maxBottleVolumeMl": 1000,
            "availableVarietyIds": ["classic", "chocolate"],
            "status": "OPEN",
            "createdAt": "2026-05-01T00:00:00Z",
        })
        batches.put_item(Item={
            "batchId": "b-completed",
            "batchName": "Old Batch",
            "cutoffDate": "2025-01-01",
            "maxBottleVolumeMl": 500,
            "availableVarietyIds": ["classic"],
            "status": "COMPLETED",
            "createdAt": "2024-01-01T00:00:00Z",
        })
        requests.put_item(Item={
            "requestId": "r-001",
            "batchId": "b-001",
            "varietyId": "classic",
            "status": "CONFIRMED",
        })
        yield {"batches": batches, "requests": requests, "varieties": varieties}


def _event(batch_id: str, body: dict, role: str = "chef") -> dict:
    return {
        "version": "2.0",
        "pathParameters": {"id": batch_id},
        "requestContext": {
            "http": {"method": "PUT"},
            "authorizer": {"lambda": {"userId": "u-001", "role": role, "email": "c@example.com"}},
        },
        "body": json.dumps(body),
        "headers": {},
    }


class TestUpdateBatchHandler:
    def test_partial_update_only_changes_provided_fields(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        response = handler(_event("b-001", {"maxBottleVolumeMl": 500}), MagicMock())
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["maxBottleVolumeMl"] == 500
        assert body["batchName"] == "Holiday 2026"  # unchanged

    def test_completed_batch_rejected_with_409(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        response = handler(_event("b-completed", {"batchName": "New Name"}), MagicMock())
        assert response["statusCode"] == 409
        assert json.loads(response["body"])["code"] == "BATCH_COMPLETED"

    def test_name_uniqueness_excludes_self(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        # Updating b-001 with its own name should not conflict
        response = handler(_event("b-001", {"batchName": "Holiday 2026"}), MagicMock())
        assert response["statusCode"] == 200

    def test_missing_batch_returns_404(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        response = handler(_event("b-unknown", {"batchName": "X"}), MagicMock())
        assert response["statusCode"] == 404
        assert json.loads(response["body"])["code"] == "BATCH_NOT_FOUND"

    def test_removing_variety_with_confirmed_request_returns_400(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        # r-001 is CONFIRMED for "classic" in b-001; removing classic should be blocked
        response = handler(_event("b-001", {"availableVarietyIds": ["chocolate"]}), MagicMock())
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["code"] == "VARIETY_HAS_REQUESTS"
        assert "classic" in body["message"]

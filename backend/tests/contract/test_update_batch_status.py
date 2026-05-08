"""T035: Contract test (RED) for PUT /api/v1/batches/{id}/status."""
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
        ddb.create_table(
            TableName="coquito-requests",
            KeySchema=[{"AttributeName": "requestId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "requestId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        batches.put_item(Item={
            "batchId": "b-open",
            "batchName": "Open Batch",
            "cutoffDate": "2030-11-15",
            "maxBottleVolumeMl": 1000,
            "availableVarietyIds": ["classic"],
            "status": "OPEN",
            "createdAt": "2026-05-01T00:00:00Z",
        })
        batches.put_item(Item={
            "batchId": "b-closed",
            "batchName": "Closed Batch",
            "cutoffDate": "2026-01-01",
            "maxBottleVolumeMl": 1000,
            "availableVarietyIds": ["classic"],
            "status": "CLOSED",
            "createdAt": "2025-10-01T00:00:00Z",
        })
        batches.put_item(Item={
            "batchId": "b-completed",
            "batchName": "Completed Batch",
            "cutoffDate": "2025-01-01",
            "maxBottleVolumeMl": 500,
            "availableVarietyIds": ["classic"],
            "status": "COMPLETED",
            "createdAt": "2024-01-01T00:00:00Z",
        })
        yield {"batches": batches}


def _event(batch_id: str, status: str, role: str = "chef") -> dict:
    return {
        "version": "2.0",
        "pathParameters": {"id": batch_id},
        "requestContext": {
            "http": {"method": "PUT"},
            "authorizer": {"lambda": {"userId": "u-001", "role": role, "email": "c@example.com"}},
        },
        "body": json.dumps({"status": status}),
        "headers": {},
    }


class TestUpdateBatchStatusContract:
    def test_open_to_closed_returns_200(self, tables):
        from src.handlers.update_batch_status import handler  # noqa: PLC0415
        response = handler(_event("b-open", "CLOSED"), MagicMock())
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "CLOSED"

    def test_closed_to_completed_returns_200(self, tables):
        from src.handlers.update_batch_status import handler  # noqa: PLC0415
        response = handler(_event("b-closed", "COMPLETED"), MagicMock())
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "COMPLETED"

    def test_completed_to_open_returns_400(self, tables):
        from src.handlers.update_batch_status import handler  # noqa: PLC0415
        response = handler(_event("b-completed", "OPEN"), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "INVALID_STATUS_TRANSITION"

    def test_open_to_completed_returns_400(self, tables):
        from src.handlers.update_batch_status import handler  # noqa: PLC0415
        response = handler(_event("b-open", "COMPLETED"), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "INVALID_STATUS_TRANSITION"

    def test_unknown_batch_returns_404(self, tables):
        from src.handlers.update_batch_status import handler  # noqa: PLC0415
        response = handler(_event("b-unknown", "CLOSED"), MagicMock())
        assert response["statusCode"] == 404

    def test_non_chef_returns_403(self, tables):
        from src.handlers.update_batch_status import handler  # noqa: PLC0415
        response = handler(_event("b-open", "CLOSED", role="authorized-user"), MagicMock())
        assert response["statusCode"] == 403

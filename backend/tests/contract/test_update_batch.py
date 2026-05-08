"""T034: Contract test (RED) for PUT /api/v1/batches/{id}."""
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
        # Confirmed request for b-001 using classic variety
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


class TestUpdateBatchContract:
    def test_valid_update_returns_200(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        response = handler(_event("b-001", {"batchName": "Updated Name"}), MagicMock())
        assert response["statusCode"] == 200

    def test_response_has_full_batch_shape(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        response = handler(_event("b-001", {"maxBottleVolumeMl": 750}), MagicMock())
        body = json.loads(response["body"])
        for f in ("batchId", "batchName", "cutoffDate", "maxBottleVolumeMl",
                   "status", "availableVarietyIds", "activeRequestCount", "createdAt"):
            assert f in body

    def test_unknown_batch_returns_404(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        response = handler(_event("b-unknown", {"batchName": "X"}), MagicMock())
        assert response["statusCode"] == 404
        assert json.loads(response["body"])["code"] == "BATCH_NOT_FOUND"

    def test_completed_batch_returns_409(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        response = handler(_event("b-completed", {"batchName": "X"}), MagicMock())
        assert response["statusCode"] == 409
        assert json.loads(response["body"])["code"] == "BATCH_COMPLETED"

    def test_duplicate_name_returns_400(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        tables["batches"].put_item(Item={
            "batchId": "b-002",
            "batchName": "Other Batch",
            "cutoffDate": "2030-01-01",
            "maxBottleVolumeMl": 500,
            "availableVarietyIds": ["classic"],
            "status": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
        })
        response = handler(_event("b-001", {"batchName": "Other Batch"}), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "BATCH_NAME_CONFLICT"

    def test_removing_variety_with_confirmed_requests_returns_400(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        # Remove "classic" which has a confirmed request
        response = handler(_event("b-001", {"availableVarietyIds": ["chocolate"]}), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "VARIETY_HAS_REQUESTS"

    def test_non_chef_returns_403(self, tables):
        from src.handlers.update_batch import handler  # noqa: PLC0415
        response = handler(_event("b-001", {"batchName": "X"}, role="authorized-user"), MagicMock())
        assert response["statusCode"] == 403

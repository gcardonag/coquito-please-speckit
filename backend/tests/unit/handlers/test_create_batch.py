"""T024: Unit tests (RED) for create_batch Lambda handler."""
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
        varieties = ddb.create_table(
            TableName="coquito-varieties",
            KeySchema=[{"AttributeName": "varietyId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "varietyId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        varieties.put_item(Item={"varietyId": "classic", "name": "Classic", "active": True})
        varieties.put_item(Item={"varietyId": "inactive-v", "name": "Discontinued", "active": False})
        yield {"batches": batches, "varieties": varieties}


def _event(role: str = "chef", body: dict | None = None) -> dict:
    return {
        "version": "2.0",
        "requestContext": {
            "http": {"method": "POST"},
            "authorizer": {"lambda": {"userId": "u-001", "role": role, "email": "c@example.com"}},
        },
        "body": json.dumps(body or {
            "batchName": "Holiday 2026",
            "cutoffDate": "2030-11-15",
            "maxBottleVolumeMl": 1000,
            "availableVarietyIds": ["classic"],
        }),
        "headers": {},
    }


class TestCreateBatchHandler:
    def test_valid_create_assigns_uuid_and_open_status(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_event(), MagicMock())
        assert response["statusCode"] == 201
        body = json.loads(response["body"])
        assert body["status"] == "OPEN"
        assert len(body["batchId"]) == 36  # UUID v4

    def test_valid_create_sets_created_at(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_event(), MagicMock())
        body = json.loads(response["body"])
        assert body["createdAt"] != ""

    def test_duplicate_name_rejected(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        handler(_event(), MagicMock())
        response = handler(_event(), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "BATCH_NAME_CONFLICT"

    def test_past_date_rejected(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_event(body={
            "batchName": "Past Batch",
            "cutoffDate": "2020-01-01",
            "maxBottleVolumeMl": 500,
            "availableVarietyIds": ["classic"],
        }), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "CUTOFF_DATE_IN_PAST"

    def test_inactive_variety_rejected(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_event(body={
            "batchName": "Test Batch",
            "cutoffDate": "2030-11-15",
            "maxBottleVolumeMl": 500,
            "availableVarietyIds": ["inactive-v"],
        }), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "VARIETY_NOT_ACTIVE"

    def test_empty_variety_list_rejected(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_event(body={
            "batchName": "Test Batch",
            "cutoffDate": "2030-11-15",
            "maxBottleVolumeMl": 500,
            "availableVarietyIds": [],
        }), MagicMock())
        assert response["statusCode"] == 400

    def test_negative_volume_rejected(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_event(body={
            "batchName": "Test Batch",
            "cutoffDate": "2030-11-15",
            "maxBottleVolumeMl": -100,
            "availableVarietyIds": ["classic"],
        }), MagicMock())
        assert response["statusCode"] == 400

    def test_non_chef_gets_403(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_event(role="authorized-user"), MagicMock())
        assert response["statusCode"] == 403

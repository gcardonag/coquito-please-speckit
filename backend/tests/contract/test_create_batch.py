"""T023: Contract test (RED) for POST /api/v1/batches."""
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
        varieties.put_item(Item={"varietyId": "chocolate", "name": "Chocolate", "active": True})
        varieties.put_item(Item={"varietyId": "inactive-v", "name": "Discontinued", "active": False})
        yield {"batches": batches, "varieties": varieties}


def _chef_event(body: dict) -> dict:
    return {
        "version": "2.0",
        "requestContext": {
            "http": {"method": "POST", "path": "/api/v1/batches"},
            "authorizer": {"lambda": {"userId": "u-chef", "role": "chef", "email": "chef@example.com"}},
        },
        "body": json.dumps(body),
        "headers": {},
    }


_valid_body = {
    "batchName": "Holiday 2026",
    "cutoffDate": "2030-11-15",
    "maxBottleVolumeMl": 1000,
    "availableVarietyIds": ["classic", "chocolate"],
}


class TestCreateBatchContract:
    def test_chef_creates_batch_returns_201(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_chef_event(_valid_body), MagicMock())
        assert response["statusCode"] == 201

    def test_response_has_all_required_fields(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_chef_event(_valid_body), MagicMock())
        body = json.loads(response["body"])
        for f in ("batchId", "batchName", "cutoffDate", "maxBottleVolumeMl",
                   "status", "availableVarietyIds", "activeRequestCount", "createdAt"):
            assert f in body, f"missing field: {f}"

    def test_status_is_open(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_chef_event(_valid_body), MagicMock())
        body = json.loads(response["body"])
        assert body["status"] == "OPEN"

    def test_active_request_count_is_zero(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_chef_event(_valid_body), MagicMock())
        body = json.loads(response["body"])
        assert body["activeRequestCount"] == 0

    def test_duplicate_name_returns_400_batch_name_conflict(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        handler(_chef_event(_valid_body), MagicMock())
        response = handler(_chef_event(_valid_body), MagicMock())
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["code"] == "BATCH_NAME_CONFLICT"

    def test_past_cutoff_date_returns_400_cutoff_date_in_past(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        body = {**_valid_body, "cutoffDate": "2020-01-01"}
        response = handler(_chef_event(body), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "CUTOFF_DATE_IN_PAST"

    def test_inactive_variety_returns_400_variety_not_active(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        body = {**_valid_body, "availableVarietyIds": ["inactive-v"]}
        response = handler(_chef_event(body), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "VARIETY_NOT_ACTIVE"

    def test_missing_fields_returns_400_validation_error(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        response = handler(_chef_event({}), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "VALIDATION_ERROR"

    def test_non_chef_returns_403(self, tables):
        from src.handlers.create_batch import handler  # noqa: PLC0415
        event = {
            "version": "2.0",
            "requestContext": {
                "http": {"method": "POST"},
                "authorizer": {"lambda": {"userId": "u-user", "role": "authorized-user", "email": "u@example.com"}},
            },
            "body": json.dumps(_valid_body),
            "headers": {},
        }
        response = handler(event, MagicMock())
        assert response["statusCode"] == 403
        assert json.loads(response["body"])["code"] == "CHEF_ROLE_REQUIRED"

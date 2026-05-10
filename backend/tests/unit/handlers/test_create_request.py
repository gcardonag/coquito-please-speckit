"""T023: Unit tests for create_request Lambda handler."""
import json
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch

from src.handlers.create_request import handler


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("SES_FROM_ADDRESS", "coquito@example.com")
    monkeypatch.setenv("SCHEDULER_ROLE_ARN", "arn:aws:iam::123:role/test")
    monkeypatch.setenv("SEND_REMINDER_LAMBDA_ARN", "arn:aws:lambda:us-east-1:123:function:send-reminder")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:5173")


VALID_PAYLOAD = {
    "idempotencyKey": "idem-001",
    "requesterName": "María Rivera",
    "requesterEmail": "maria@example.com",
    "batchId": "b-001",
    "varietyId": "v-classic",
    "pickupDate": "2026-12-20",
    "pickupTime": "14:00",
    "exchangeLocation": "123 Palmas St",
    "bottleProvided": False,
    "bottleVolumeMl": None,
    "costContribution": True,
}


@pytest.fixture
def ddb_tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        requests_table = ddb.create_table(
            TableName="coquito-requests",
            KeySchema=[{"AttributeName": "requestId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "requestId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        batches_table = ddb.create_table(
            TableName="coquito-batches",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        varieties_table = ddb.create_table(
            TableName="coquito-varieties",
            KeySchema=[{"AttributeName": "varietyId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "varietyId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        batches_table.put_item(Item={
            "batchId": "b-001",
            "batchName": "Christmas 2026",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["v-classic"],
            "status": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
        })
        varieties_table.put_item(Item={
            "varietyId": "v-classic",
            "name": "Classic",
            "description": "Original recipe",
            "imageKey": "images/varieties/v-classic.jpg",
            "active": True,
            "bottleYieldMl": 750,
            "ingredients": [],
        })
        yield {"requests": requests_table, "batches": batches_table}


def make_event(payload=None):
    body = payload if payload is not None else VALID_PAYLOAD
    return {"body": json.dumps(body)}


class TestCreateRequest:
    def test_happy_path_returns_201_with_request_id(self, ddb_tables):
        with patch("src.services.scheduler.create_one_time_schedule", return_value="arn:schedule:1"):
            result = handler(make_event(), {})
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert "requestId" in body
        assert body["status"] == "CONFIRMED"
        assert body["variety"]["name"] == "Classic"

    def test_idempotency_returns_existing_request(self, ddb_tables):
        with patch("src.services.scheduler.create_one_time_schedule", return_value="arn:schedule:1"):
            result1 = handler(make_event(), {})
            result2 = handler(make_event(), {})
        assert json.loads(result1["body"])["requestId"] == json.loads(result2["body"])["requestId"]

    def test_bottle_volume_exceeded_returns_400(self, ddb_tables):
        payload = {**VALID_PAYLOAD, "bottleProvided": True, "bottleVolumeMl": 9999}
        result = handler(make_event(payload), {})
        assert result["statusCode"] == 400
        assert json.loads(result["body"])["code"] == "BOTTLE_VOLUME_EXCEEDED"

    def test_batch_closed_for_past_cutoff_date(self, ddb_tables):
        payload = {**VALID_PAYLOAD, "pickupDate": "2025-01-01"}
        result = handler(make_event(payload), {})
        assert result["statusCode"] == 400
        assert json.loads(result["body"])["code"] == "BATCH_CLOSED"

    def test_validation_error_for_missing_field(self, ddb_tables):
        payload = {**VALID_PAYLOAD, "requesterName": ""}
        result = handler(make_event(payload), {})
        assert result["statusCode"] == 400
        assert json.loads(result["body"])["code"] == "VALIDATION_ERROR"

    def test_variety_not_found_for_inactive_variety(self, ddb_tables):
        payload = {**VALID_PAYLOAD, "varietyId": "v-inactive"}
        result = handler(make_event(payload), {})
        assert result["statusCode"] in (404, 400)
        assert json.loads(result["body"])["code"] in ("VARIETY_NOT_FOUND", "VALIDATION_ERROR")

    def test_batch_not_found_returns_404(self, ddb_tables):
        payload = {**VALID_PAYLOAD, "batchId": "nonexistent"}
        result = handler(make_event(payload), {})
        assert result["statusCode"] == 404
        assert json.loads(result["body"])["code"] == "BATCH_NOT_FOUND"

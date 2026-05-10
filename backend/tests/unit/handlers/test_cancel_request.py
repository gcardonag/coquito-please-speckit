"""T036: Unit tests for cancel_request Lambda handler."""
import json
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch
from datetime import date

from src.handlers.cancel_request import handler


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")


CONFIRMED_REQUEST = {
    "requestId": "req-cancel-001",
    "requesterName": "Carmen López",
    "requesterEmail": "carmen@example.com",
    "batchId": "b-001",
    "varietyId": "v-classic",
    "pickupDate": "2026-12-20",
    "pickupTime": "14:00",
    "exchangeLocation": "456 Coconut Ave",
    "bottleProvided": False,
    "costContribution": False,
    "status": "CONFIRMED",
    "reminders": [
        {
            "reminderId": "rem-c-001",
            "scheduledFor": "2026-12-13T10:00:00Z",
            "schedulerArn": "arn:scheduler:c-1",
            "status": "SCHEDULED",
        },
    ],
    "createdAt": "2026-03-29T00:00:00Z",
    "updatedAt": "2026-03-29T00:00:00Z",
    "idempotencyKey": "idem-cancel-001",
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
        batches_table.put_item(Item={
            "batchId": "b-001",
            "batchName": "Christmas 2026",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": [],
            "status": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
        })
        requests_table.put_item(Item=CONFIRMED_REQUEST)
        yield {"requests": requests_table}


class TestCancelRequest:
    def test_cancels_request_and_returns_200(self, ddb_tables):
        with patch("src.handlers.cancel_request._today", return_value=date(2026, 11, 1)):
            with patch("src.services.scheduler.delete_schedule"):
                result = handler({"pathParameters": {"id": "req-cancel-001"}}, {})
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "CANCELLED"
        assert "cancelledAt" in body

    def test_idempotent_already_cancelled_returns_200(self, ddb_tables):
        with patch("src.handlers.cancel_request._today", return_value=date(2026, 11, 1)):
            with patch("src.services.scheduler.delete_schedule"):
                handler({"pathParameters": {"id": "req-cancel-001"}}, {})
                result = handler({"pathParameters": {"id": "req-cancel-001"}}, {})
        assert result["statusCode"] == 200

    def test_returns_403_after_cutoff(self, ddb_tables):
        with patch("src.handlers.cancel_request._today", return_value=date(2026, 12, 15)):
            result = handler({"pathParameters": {"id": "req-cancel-001"}}, {})
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "CUTOFF_PASSED"

    def test_cancels_all_scheduled_reminders_in_eventbridge(self, ddb_tables):
        deleted = []
        with patch("src.handlers.cancel_request._today", return_value=date(2026, 11, 1)):
            with patch("src.services.scheduler.delete_schedule", side_effect=lambda name: deleted.append(name)):
                handler({"pathParameters": {"id": "req-cancel-001"}}, {})
        # One SCHEDULED reminder → two schedule names deleted (7d and 1d)
        assert len(deleted) == 2

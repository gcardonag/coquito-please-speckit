"""T034: Unit tests for get_request Lambda handler."""
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch
from datetime import date

from src.handlers.get_request import handler


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")


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
        requests_table.put_item(Item={
            "requestId": "req-001",
            "requesterName": "José Colón",
            "requesterEmail": "jose@example.com",
            "batchId": "b-001",
            "varietyId": "v-classic",
            "pickupDate": "2026-12-20",
            "pickupTime": "14:00",
            "exchangeLocation": "123 Palmas St",
            "bottleProvided": False,
            "costContribution": True,
            "status": "CONFIRMED",
            "reminders": [],
            "createdAt": "2026-03-29T00:00:00Z",
            "updatedAt": "2026-03-29T00:00:00Z",
            "idempotencyKey": "idem-001",
        })
        yield {"requests": requests_table, "batches": batches_table}


class TestGetRequest:
    def test_returns_full_request_with_editable_true_before_cutoff(self, ddb_tables):
        with patch("src.handlers.get_request._today", return_value=date(2026, 11, 1)):
            result = handler({"pathParameters": {"requestId": "req-001"}}, {})
        assert result["statusCode"] == 200
        body = result["body"]
        assert body["requestId"] == "req-001"
        assert body["editable"] is True
        assert body["batch"]["batchId"] == "b-001"
        assert body["variety"]["name"] == "Classic"

    def test_returns_editable_false_after_cutoff(self, ddb_tables):
        with patch("src.handlers.get_request._today", return_value=date(2026, 12, 15)):
            result = handler({"pathParameters": {"requestId": "req-001"}}, {})
        assert result["statusCode"] == 200
        assert result["body"]["editable"] is False

    def test_returns_404_for_unknown_request(self, ddb_tables):
        result = handler({"pathParameters": {"requestId": "nonexistent"}}, {})
        assert result["statusCode"] == 404
        assert result["body"]["code"] == "REQUEST_NOT_FOUND"

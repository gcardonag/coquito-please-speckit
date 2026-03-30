"""T037: Integration tests for request update and cancel flows."""
import json
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch
from datetime import date

from src.handlers.update_request import handler as update_handler
from src.handlers.cancel_request import handler as cancel_handler


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("SCHEDULER_ROLE_ARN", "arn:aws:iam::123:role/test")
    monkeypatch.setenv("SEND_REMINDER_LAMBDA_ARN", "arn:aws:lambda:us-east-1:123:function:send-reminder")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:5173")


@pytest.fixture
def seeded_tables():
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
            "batchId": "b-int-mgmt",
            "batchName": "Management Test Batch",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["v-int-classic"],
            "status": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
        })
        varieties_table.put_item(Item={
            "varietyId": "v-int-classic", "name": "Classic", "description": "Test variety",
            "imageKey": "images/test.jpg", "active": True, "bottleYieldMl": 750, "ingredients": [],
        })
        requests_table.put_item(Item={
            "requestId": "req-int-mgmt-001",
            "requesterName": "Integration Manager",
            "requesterEmail": "int-mgmt@example.com",
            "batchId": "b-int-mgmt",
            "varietyId": "v-int-classic",
            "pickupDate": "2026-12-20",
            "pickupTime": "10:00",
            "exchangeLocation": "Original St",
            "bottleProvided": False,
            "costContribution": False,
            "status": "CONFIRMED",
            "reminders": [
                {"reminderId": "rem-int-1", "scheduledFor": "2026-12-13T10:00:00Z",
                 "schedulerArn": "arn:scheduler:int-old-1", "status": "SCHEDULED"},
                {"reminderId": "rem-int-2", "scheduledFor": "2026-12-19T10:00:00Z",
                 "schedulerArn": "arn:scheduler:int-old-2", "status": "SCHEDULED"},
            ],
            "createdAt": "2026-03-29T00:00:00Z",
            "updatedAt": "2026-03-29T00:00:00Z",
            "idempotencyKey": "idem-int-mgmt",
        })
        yield {"requests": requests_table}


class TestRequestManagementIntegration:
    def test_update_changes_date_and_reschedules_reminders(self, seeded_tables):
        deleted = []
        created = []

        with patch("src.handlers.update_request._today", return_value=date(2026, 11, 1)):
            with patch("src.services.scheduler.delete_schedule",
                       side_effect=lambda name: deleted.append(name)):
                with patch("src.services.scheduler.create_one_time_schedule",
                           side_effect=lambda **kwargs: created.append(kwargs) or "arn:new"):
                    result = update_handler({
                        "pathParameters": {"requestId": "req-int-mgmt-001"},
                        "body": json.dumps({"pickupDate": "2026-12-22"}),
                    }, {})

        assert result["statusCode"] == 200
        assert result["body"]["pickupDate"] == "2026-12-22"

        # Old reminders deleted, new ones created
        assert len(deleted) == 2
        assert len(created) == 2

        # Verify DynamoDB item updated
        item = seeded_tables["requests"].get_item(Key={"requestId": "req-int-mgmt-001"})["Item"]
        assert item["pickupDate"] == "2026-12-22"
        reminder_statuses = [r["status"] for r in item["reminders"]]
        assert all(s == "SCHEDULED" for s in reminder_statuses)

    def test_cancel_sets_status_and_cancels_reminders(self, seeded_tables):
        with patch("src.handlers.cancel_request._today", return_value=date(2026, 11, 1)):
            with patch("src.services.scheduler.delete_schedule"):
                result = cancel_handler({
                    "pathParameters": {"requestId": "req-int-mgmt-001"},
                }, {})

        assert result["statusCode"] == 200
        assert result["body"]["status"] == "CANCELLED"

        # Verify status in DynamoDB
        item = seeded_tables["requests"].get_item(Key={"requestId": "req-int-mgmt-001"})["Item"]
        assert item["status"] == "CANCELLED"
        reminder_statuses = [r["status"] for r in item.get("reminders", [])]
        assert all(s == "CANCELLED" for s in reminder_statuses)

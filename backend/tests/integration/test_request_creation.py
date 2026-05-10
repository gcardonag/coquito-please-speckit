"""T024: Integration test for request creation end-to-end."""
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
            "batchId": "b-int-001",
            "batchName": "Integration Batch",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["v-int-classic"],
            "status": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
        })
        varieties_table.put_item(Item={
            "varietyId": "v-int-classic",
            "name": "Classic",
            "description": "Integration test variety",
            "imageKey": "images/varieties/v-int-classic.jpg",
            "active": True,
            "bottleYieldMl": 750,
            "ingredients": [
                {
                    "ingredientId": "ing-001",
                    "name": "Cream of coconut",
                    "quantityPerBottle": 400,
                    "unit": "ml",
                    "category": "Dairy",
                }
            ],
        })
        yield {"requests": requests_table, "batches": batches_table, "varieties": varieties_table}


class TestRequestCreationIntegration:
    def test_creates_item_in_dynamodb_with_confirmed_status(self, seeded_tables):
        payload = {
            "idempotencyKey": "int-idem-001",
            "requesterName": "Integration User",
            "requesterEmail": "int@example.com",
            "batchId": "b-int-001",
            "varietyId": "v-int-classic",
            "pickupDate": "2026-12-20",
            "pickupTime": "10:00",
            "exchangeLocation": "Integration Ave",
            "bottleProvided": False,
            "bottleVolumeMl": None,
            "costContribution": False,
        }
        with patch("src.services.scheduler.create_one_time_schedule", return_value="arn:schedule:int"):
            result = handler({"body": json.dumps(payload)}, {})

        assert result["statusCode"] == 201
        request_id = json.loads(result["body"])["requestId"]

        # Verify DynamoDB item was written
        item = seeded_tables["requests"].get_item(Key={"requestId": request_id})["Item"]
        assert item["status"] == "CONFIRMED"
        assert item["requesterEmail"] == "int@example.com"
        assert item["batchId"] == "b-int-001"

    def test_creates_two_scheduled_reminders(self, seeded_tables):
        payload = {
            "idempotencyKey": "int-idem-002",
            "requesterName": "Reminder User",
            "requesterEmail": "reminder@example.com",
            "batchId": "b-int-001",
            "varietyId": "v-int-classic",
            "pickupDate": "2026-12-20",
            "pickupTime": "10:00",
            "exchangeLocation": "Reminder St",
            "bottleProvided": False,
            "bottleVolumeMl": None,
            "costContribution": False,
        }
        schedule_calls = []

        def record_schedule(name, schedule_at, target_arn, input_payload):
            schedule_calls.append(name)
            return f"arn:schedule:{name}"

        with patch("src.services.scheduler.create_one_time_schedule", side_effect=record_schedule):
            result = handler({"body": json.dumps(payload)}, {})

        assert result["statusCode"] == 201
        assert len(schedule_calls) == 2

        # Verify reminders stored in DynamoDB
        request_id = json.loads(result["body"])["requestId"]
        item = seeded_tables["requests"].get_item(Key={"requestId": request_id})["Item"]
        assert len(item["reminders"]) == 2
        statuses = [r["status"] for r in item["reminders"]]
        assert all(s == "SCHEDULED" for s in statuses)

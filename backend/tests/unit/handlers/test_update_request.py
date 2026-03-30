"""T035: Unit tests for update_request Lambda handler."""
import json
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch
from datetime import date

from src.handlers.update_request import handler


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


EXISTING_REQUEST = {
    "requestId": "req-upd-001",
    "requesterName": "Ana García",
    "requesterEmail": "ana@example.com",
    "batchId": "b-001",
    "varietyId": "v-classic",
    "pickupDate": "2026-12-20",
    "pickupTime": "14:00",
    "exchangeLocation": "Original Location",
    "bottleProvided": False,
    "costContribution": True,
    "status": "CONFIRMED",
    "reminders": [
        {
            "reminderId": "rem-001",
            "scheduledFor": "2026-12-13T10:00:00Z",
            "schedulerArn": "arn:scheduler:old-1",
            "status": "SCHEDULED",
        },
        {
            "reminderId": "rem-002",
            "scheduledFor": "2026-12-19T10:00:00Z",
            "schedulerArn": "arn:scheduler:old-2",
            "status": "SCHEDULED",
        },
    ],
    "createdAt": "2026-03-29T00:00:00Z",
    "updatedAt": "2026-03-29T00:00:00Z",
    "idempotencyKey": "idem-upd-001",
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
            "availableVarietyIds": ["v-classic", "v-chocolate"],
            "status": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
        })
        varieties_table.put_item(Item={
            "varietyId": "v-classic", "name": "Classic", "description": "Original",
            "imageKey": "images/varieties/v-classic.jpg", "active": True,
            "bottleYieldMl": 750, "ingredients": [],
        })
        varieties_table.put_item(Item={
            "varietyId": "v-chocolate", "name": "Chocolate", "description": "Chocolate twist",
            "imageKey": "images/varieties/v-chocolate.jpg", "active": True,
            "bottleYieldMl": 750, "ingredients": [],
        })
        requests_table.put_item(Item=EXISTING_REQUEST)
        yield {"requests": requests_table}


class TestUpdateRequest:
    def test_updates_location_and_returns_200(self, ddb_tables):
        with patch("src.handlers.update_request._today", return_value=date(2026, 11, 1)):
            with patch("src.services.scheduler.create_one_time_schedule", return_value="arn:new"):
                result = handler({
                    "pathParameters": {"requestId": "req-upd-001"},
                    "body": json.dumps({"exchangeLocation": "New Location"}),
                }, {})
        assert result["statusCode"] == 200
        assert result["body"]["exchangeLocation"] == "New Location"

    def test_reschedules_reminders_when_pickup_date_changes(self, ddb_tables):
        delete_calls = []
        create_calls = []

        with patch("src.handlers.update_request._today", return_value=date(2026, 11, 1)):
            with patch("src.services.scheduler.delete_schedule", side_effect=lambda name: delete_calls.append(name)):
                with patch("src.services.scheduler.create_one_time_schedule",
                           side_effect=lambda **kwargs: create_calls.append(kwargs) or "arn:new"):
                    result = handler({
                        "pathParameters": {"requestId": "req-upd-001"},
                        "body": json.dumps({"pickupDate": "2026-12-21"}),
                    }, {})

        assert result["statusCode"] == 200
        assert len(create_calls) == 2

    def test_returns_403_cutoff_passed(self, ddb_tables):
        with patch("src.handlers.update_request._today", return_value=date(2026, 12, 15)):
            result = handler({
                "pathParameters": {"requestId": "req-upd-001"},
                "body": json.dumps({"exchangeLocation": "New"}),
            }, {})
        assert result["statusCode"] == 403
        assert result["body"]["code"] == "CUTOFF_PASSED"

    def test_returns_400_bottle_volume_exceeded(self, ddb_tables):
        with patch("src.handlers.update_request._today", return_value=date(2026, 11, 1)):
            result = handler({
                "pathParameters": {"requestId": "req-upd-001"},
                "body": json.dumps({"bottleProvided": True, "bottleVolumeMl": 9999}),
            }, {})
        assert result["statusCode"] == 400
        assert result["body"]["code"] == "BOTTLE_VOLUME_EXCEEDED"

    def test_returns_409_for_cancelled_request(self, ddb_tables):
        ddb_tables["requests"].update_item(
            Key={"requestId": "req-upd-001"},
            UpdateExpression="SET #s = :s",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":s": "CANCELLED"},
        )
        with patch("src.handlers.update_request._today", return_value=date(2026, 11, 1)):
            result = handler({
                "pathParameters": {"requestId": "req-upd-001"},
                "body": json.dumps({"exchangeLocation": "New"}),
            }, {})
        assert result["statusCode"] == 409
        assert result["body"]["code"] == "REQUEST_CANCELLED"

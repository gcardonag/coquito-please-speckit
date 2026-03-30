"""T045: Unit tests for send_reminder Lambda handler."""
import json
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch, MagicMock

from src.handlers.send_reminder import handler


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    monkeypatch.setenv("SES_FROM_ADDRESS", "no-reply@coquito.example.com")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:5173")


CONFIRMED_REQUEST = {
    "requestId": "req-reminder-001",
    "requesterName": "Ana Rivera",
    "requesterEmail": "ana@example.com",
    "batchId": "b-001",
    "varietyId": "v-classic",
    "pickupDate": "2026-12-20",
    "pickupTime": "14:00",
    "exchangeLocation": "123 Palmas St",
    "bottleProvided": False,
    "costContribution": True,
    "status": "CONFIRMED",
    "reminders": [
        {
            "reminderId": "rem-r-001",
            "scheduledFor": "2026-12-13T10:00:00Z",
            "schedulerArn": "arn:scheduler:r-1",
            "status": "SCHEDULED",
        },
    ],
    "createdAt": "2026-01-01T00:00:00Z",
    "updatedAt": "2026-01-01T00:00:00Z",
    "idempotencyKey": "idem-r-001",
}

CANCELLED_REQUEST = {
    **CONFIRMED_REQUEST,
    "requestId": "req-reminder-002",
    "status": "CANCELLED",
}

EVENT = {
    "requestId": "req-reminder-001",
    "reminderId": "rem-r-001",
    "daysUntil": 7,
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
        requests_table.put_item(Item=CONFIRMED_REQUEST)
        requests_table.put_item(Item=CANCELLED_REQUEST)
        yield {"requests": requests_table}


class TestSendReminder:
    def test_sends_ses_email_with_correct_fields(self, ddb_tables):
        with patch("src.services.ses.send_email") as mock_send:
            handler(EVENT, {})

        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args if mock_send.call_args.kwargs else (None, {})
        call_kwargs = mock_send.call_args.kwargs or {}
        # Positional call: to, subject, body_html, body_text
        call_args = mock_send.call_args.args if mock_send.call_args.args else ()

        to = call_args[0] if call_args else call_kwargs.get("to")
        subject = call_args[1] if len(call_args) > 1 else call_kwargs.get("subject")
        body_html = call_args[2] if len(call_args) > 2 else call_kwargs.get("body_html")

        assert to == "ana@example.com"
        assert "Classic" in subject or "coquito" in subject.lower()
        assert "Ana Rivera" in body_html
        assert "req-reminder-001" in body_html  # manage link contains requestId

    def test_marks_reminder_status_sent_in_dynamodb(self, ddb_tables):
        with patch("src.services.ses.send_email"):
            handler(EVENT, {})

        item = ddb_tables["requests"].get_item(Key={"requestId": "req-reminder-001"})["Item"]
        reminder = next(r for r in item["reminders"] if r["reminderId"] == "rem-r-001")
        assert reminder["status"] == "SENT"

    def test_skips_cancelled_request_without_sending_email(self, ddb_tables):
        event = {**EVENT, "requestId": "req-reminder-002", "reminderId": "rem-r-001"}
        with patch("src.services.ses.send_email") as mock_send:
            result = handler(event, {})

        mock_send.assert_not_called()
        assert result is None or result.get("skipped") or result == {}

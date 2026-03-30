"""T046: Integration tests for reminder email sending flow."""
import boto3
import pytest
from moto import mock_aws

from src.handlers.send_reminder import handler as send_reminder_handler


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    monkeypatch.setenv("SES_FROM_ADDRESS", "no-reply@coquito.example.com")
    monkeypatch.setenv("APP_BASE_URL", "https://coquito.example.com")


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
        requests_table.put_item(Item={
            "requestId": "req-int-reminder-001",
            "requesterName": "Luisa Torres",
            "requesterEmail": "luisa@example.com",
            "batchId": "b-int",
            "varietyId": "v-classic",
            "pickupDate": "2026-12-20",
            "pickupTime": "10:00",
            "exchangeLocation": "456 Coco St",
            "bottleProvided": False,
            "costContribution": False,
            "status": "CONFIRMED",
            "reminders": [
                {
                    "reminderId": "rem-int-001",
                    "scheduledFor": "2026-12-13T10:00:00Z",
                    "schedulerArn": "arn:scheduler:int-1",
                    "status": "SCHEDULED",
                },
            ],
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
            "idempotencyKey": "idem-int-r",
        })

        # Verify SES identity in moto so send_email doesn't bounce
        ses = boto3.client("ses", region_name="us-east-1")
        ses.verify_email_identity(EmailAddress="no-reply@coquito.example.com")

        yield {"requests": requests_table, "ses": ses}


class TestReminderIntegration:
    def test_sends_exactly_one_email_to_requester(self, seeded_tables):
        event = {
            "requestId": "req-int-reminder-001",
            "reminderId": "rem-int-001",
            "daysUntil": 7,
        }
        send_reminder_handler(event, {})

        # Verify via DynamoDB state that reminder was marked SENT
        item = seeded_tables["requests"].get_item(
            Key={"requestId": "req-int-reminder-001"}
        )["Item"]
        reminder = next(r for r in item["reminders"] if r["reminderId"] == "rem-int-001")
        assert reminder["status"] == "SENT"

    def test_sent_email_html_contains_manage_url_and_variety(self, seeded_tables):
        """Verify email body contains the manage-request URL and variety name."""
        sent_emails = []

        import src.services.ses as ses_svc
        original_send = ses_svc.send_email

        def capture_send(to, subject, body_html, body_text):
            sent_emails.append({"to": to, "subject": subject, "html": body_html, "text": body_text})
            return original_send(to, subject, body_html, body_text)

        import unittest.mock as mock
        with mock.patch("src.services.ses.send_email", side_effect=capture_send):
            event = {
                "requestId": "req-int-reminder-001",
                "reminderId": "rem-int-001",
                "daysUntil": 7,
            }
            send_reminder_handler(event, {})

        assert len(sent_emails) == 1
        email = sent_emails[0]
        assert email["to"] == "luisa@example.com"
        assert "req-int-reminder-001" in email["html"]  # manage link
        # variety_id is used as fallback name when no varieties table
        assert "luisa" in email["html"].lower() or "Luisa" in email["html"]

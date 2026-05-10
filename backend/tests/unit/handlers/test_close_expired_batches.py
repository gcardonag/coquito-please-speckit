"""T008: Unit tests (RED) for close_expired_batches Lambda handler."""
import json
from datetime import date
from unittest.mock import MagicMock, patch

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
def batches_table():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        table = ddb.create_table(
            TableName="coquito-batches",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        # Expired OPEN batch — cutoff in the past
        table.put_item(Item={
            "batchId": "b-expired",
            "batchName": "Past Batch",
            "cutoffDate": "2026-01-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["classic"],
            "status": "OPEN",
            "createdAt": "2025-12-01T00:00:00Z",
        })
        # Current OPEN batch — cutoff in the future
        table.put_item(Item={
            "batchId": "b-current",
            "batchName": "Future Batch",
            "cutoffDate": "2030-12-31",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["classic"],
            "status": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
        })
        # Already CLOSED batch — should stay CLOSED
        table.put_item(Item={
            "batchId": "b-closed",
            "batchName": "Closed Batch",
            "cutoffDate": "2026-01-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["classic"],
            "status": "CLOSED",
            "createdAt": "2025-11-01T00:00:00Z",
        })
        yield table


class TestCloseExpiredBatches:
    def test_expired_open_batch_transitions_to_closed(self, batches_table):
        from src.handlers.close_expired_batches import handler  # noqa: PLC0415

        handler({}, MagicMock())

        item = batches_table.get_item(Key={"batchId": "b-expired"})["Item"]
        assert item["status"] == "CLOSED"

    def test_future_open_batch_remains_open(self, batches_table):
        from src.handlers.close_expired_batches import handler  # noqa: PLC0415

        handler({}, MagicMock())

        item = batches_table.get_item(Key={"batchId": "b-current"})["Item"]
        assert item["status"] == "OPEN"

    def test_already_closed_batch_unchanged(self, batches_table):
        from src.handlers.close_expired_batches import handler  # noqa: PLC0415

        handler({}, MagicMock())

        item = batches_table.get_item(Key={"batchId": "b-closed"})["Item"]
        assert item["status"] == "CLOSED"

    def test_empty_table_runs_without_error(self, monkeypatch):
        with mock_aws():
            ddb = boto3.resource("dynamodb", region_name="us-east-1")
            ddb.create_table(
                TableName="coquito-batches",
                KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            from src.handlers.close_expired_batches import handler  # noqa: PLC0415
            result = handler({}, MagicMock())
            # Should complete without raising
            assert result is not None

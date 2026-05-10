"""T001: Unit tests (RED) for Batch.name_exists classmethod."""
import os

import boto3
import pytest
from moto import mock_aws

from src.models.batch import Batch


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")


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
        table.put_item(Item={
            "batchId": "b-001",
            "batchName": "Holiday 2026",
            "cutoffDate": "2026-11-15",
            "maxBottleVolumeMl": 1000,
            "availableVarietyIds": ["classic"],
            "status": "OPEN",
            "createdAt": "2026-05-01T00:00:00Z",
        })
        table.put_item(Item={
            "batchId": "b-002",
            "batchName": "Summer 2026",
            "cutoffDate": "2026-08-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["classic"],
            "status": "CLOSED",
            "createdAt": "2026-04-01T00:00:00Z",
        })
        yield table


class TestBatchNameExists:
    def test_returns_true_when_name_matches(self, batches_table):
        assert Batch.name_exists("Holiday 2026") is True

    def test_match_is_case_insensitive(self, batches_table):
        assert Batch.name_exists("holiday 2026") is True
        assert Batch.name_exists("HOLIDAY 2026") is True

    def test_returns_false_when_name_not_found(self, batches_table):
        assert Batch.name_exists("Nonexistent Batch") is False

    def test_exclude_self_returns_false(self, batches_table):
        # Editing b-001 — its own name should not be a conflict
        assert Batch.name_exists("Holiday 2026", exclude_batch_id="b-001") is False

    def test_exclude_self_case_insensitive(self, batches_table):
        assert Batch.name_exists("holiday 2026", exclude_batch_id="b-001") is False

    def test_exclude_self_still_catches_other_batch(self, batches_table):
        # b-001 excludes itself but "Summer 2026" is still another batch
        assert Batch.name_exists("Summer 2026", exclude_batch_id="b-001") is True

    def test_returns_false_for_empty_table(self, monkeypatch):
        with mock_aws():
            ddb = boto3.resource("dynamodb", region_name="us-east-1")
            ddb.create_table(
                TableName="coquito-batches",
                KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            assert Batch.name_exists("Any Name") is False

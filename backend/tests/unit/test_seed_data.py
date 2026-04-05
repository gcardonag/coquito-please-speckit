"""T011: Unit test for seed_data.py idempotency (US3).

Calls the seed functions twice against moto-mocked DynamoDB.
Asserts no ConflictError on second call and exactly 2 variety records
and 1 batch record exist after both runs.
"""
import os
import pytest
import boto3
from moto import mock_aws

from scripts.seed_data import seed_varieties, seed_batch
from src.services.dynamodb import ConflictError


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties-test")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches-test")


@pytest.fixture
def mocked_tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        varieties_table = ddb.create_table(
            TableName="coquito-varieties-test",
            KeySchema=[{"AttributeName": "varietyId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "varietyId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        batches_table = ddb.create_table(
            TableName="coquito-batches-test",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield {"varieties": varieties_table, "batches": batches_table}


class TestSeedDataIdempotency:
    def test_seed_runs_twice_without_conflict_error(self, mocked_tables):
        # First run
        seed_varieties()
        seed_batch()

        # Second run — must not raise ConflictError
        seed_varieties()
        seed_batch()

    def test_seed_writes_exactly_two_varieties(self, mocked_tables):
        seed_varieties()

        response = mocked_tables["varieties"].scan()
        assert response["Count"] == 2, f"Expected 2 varieties, got {response['Count']}"

        variety_ids = {item["varietyId"] for item in response["Items"]}
        assert "classic" in variety_ids
        assert "chocolate" in variety_ids

    def test_seed_writes_exactly_one_batch(self, mocked_tables):
        seed_batch()

        response = mocked_tables["batches"].scan()
        assert response["Count"] == 1, f"Expected 1 batch, got {response['Count']}"
        assert response["Items"][0]["batchId"] == "batch-test-2026"

    def test_second_seed_does_not_duplicate_varieties(self, mocked_tables):
        seed_varieties()
        seed_varieties()  # idempotent — no error, no duplicates

        response = mocked_tables["varieties"].scan()
        assert response["Count"] == 2, f"Expected 2 varieties after double seed, got {response['Count']}"

    def test_second_seed_does_not_duplicate_batch(self, mocked_tables):
        seed_batch()
        seed_batch()  # idempotent — no error, no duplicates

        response = mocked_tables["batches"].scan()
        assert response["Count"] == 1, f"Expected 1 batch after double seed, got {response['Count']}"

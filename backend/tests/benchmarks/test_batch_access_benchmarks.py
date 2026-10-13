"""Performance benchmarks for batch access handlers (constitution §IV).

Asserts wall-clock p95 latency under moto:
  - chef_search_users: ≤ 1 000 ms
  - chef_grant_batch_access: ≤ 200 ms
"""
import json
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TestPool")
    monkeypatch.setenv("DYNAMODB_BATCH_ACCESS_TABLE", "coquito-batch-access")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")


@pytest.fixture
def tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        batches = ddb.create_table(
            TableName="coquito-batches",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        batches.put_item(Item={
            "batchId": "b-bench",
            "batchName": "Benchmark Batch",
            "status": "OPEN",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": [],
            "createdAt": "2026-01-01T00:00:00Z",
        })
        ddb.create_table(
            TableName="coquito-batch-access",
            KeySchema=[
                {"AttributeName": "batchId", "KeyType": "HASH"},
                {"AttributeName": "userId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "batchId", "AttributeType": "S"},
                {"AttributeName": "userId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield


_SEARCH_EVENT = {
    "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
    "queryStringParameters": {"query": "jane"},
}

_COGNITO_USER = {
    "Username": "jane@example.com",
    "Attributes": [
        {"Name": "sub", "Value": "user-sub-bench"},
        {"Name": "email", "Value": "jane@example.com"},
        {"Name": "given_name", "Value": "Jane"},
        {"Name": "family_name", "Value": "Doe"},
    ],
}

_USER_ATTRS = [
    {"Name": "sub", "Value": "user-sub-bench"},
    {"Name": "email", "Value": "jane@example.com"},
    {"Name": "given_name", "Value": "Jane"},
    {"Name": "family_name", "Value": "Doe"},
]


def test_chef_search_users_p95_under_1000ms(benchmark, tables):
    """p95 wall-clock for chef_search_users must be ≤ 1 000 ms under moto."""
    from src.handlers.chef_search_users import handler  # noqa: PLC0415

    def run():
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.list_users.side_effect = [
                {"Users": [_COGNITO_USER]},
                {"Users": []},
            ]
            return handler(_SEARCH_EVENT, MagicMock())

    result = benchmark.pedantic(run, iterations=5, rounds=10)
    assert result["statusCode"] == 200

    p95 = benchmark.stats.get("q95") or benchmark.stats["mean"] * 2
    assert p95 < 1.0, f"p95 latency {p95:.3f}s exceeds 1 000 ms budget"


def test_chef_grant_batch_access_p95_under_200ms(benchmark, tables):
    """p95 wall-clock for chef_grant_batch_access must be ≤ 200 ms under moto."""
    from src.handlers.chef_grant_batch_access import handler  # noqa: PLC0415

    grant_event = {
        "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
        "pathParameters": {"id": "b-bench", "userId": f"user-bench-{{i}}"},
    }

    counter = {"n": 0}

    def run():
        counter["n"] += 1
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "pathParameters": {"id": "b-bench", "userId": f"user-bench-{counter['n']}"},
        }
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.admin_get_user.return_value = {"UserAttributes": _USER_ATTRS}
            return handler(event, MagicMock())

    result = benchmark.pedantic(run, iterations=5, rounds=10)
    assert result["statusCode"] == 200

    p95 = benchmark.stats.get("q95") or benchmark.stats["mean"] * 2
    assert p95 < 0.2, f"p95 latency {p95:.3f}s exceeds 200 ms budget"

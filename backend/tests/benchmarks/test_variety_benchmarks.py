"""Performance benchmarks for variety handlers (constitution §IV).

Asserts wall-clock p95 latency under moto:
  - chef_list_varieties (22 varieties, 5 ingredients each): ≤ 200 ms
"""
import math
from decimal import Decimal
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")


@pytest.fixture
def varieties_table():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        table = ddb.create_table(
            TableName="coquito-varieties",
            KeySchema=[{"AttributeName": "varietyId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "varietyId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        for i in range(1, 23):
            table.put_item(Item={
                "varietyId": f"v-{i:03d}",
                "name": f"Variety {i}",
                "description": "Test variety",
                "imageKey": "",
                "active": i % 2 == 0,
                "bottleYieldMl": 750,
                "ingredients": [
                    {
                        "ingredientId": f"ing-{i}-{j}",
                        "name": f"Ingredient {j}",
                        "quantityPerBottle": Decimal(str(j * 10)),
                        "unit": "ml",
                        "category": "dairy",
                    }
                    for j in range(1, 6)
                ],
            })
        yield table


_CHEF_EVENT = {"requestContext": {"authorizer": {"lambda": {"role": "chef"}}}}


def test_chef_list_varieties_p95_under_200ms(benchmark, varieties_table):
    """p95 wall-clock for chef_list_varieties must be ≤ 200 ms under moto."""
    from src.handlers.chef_list_varieties import handler  # noqa: PLC0415

    def run():
        return handler(_CHEF_EVENT, MagicMock())

    result = benchmark.pedantic(run, iterations=5, rounds=10, warmup_rounds=1)
    assert result["statusCode"] == 200

    # pytest-benchmark has no q95 stat; derive it from the per-round timings.
    rounds = sorted(benchmark.stats.stats.data)
    p95 = rounds[math.ceil(0.95 * len(rounds)) - 1]
    assert p95 < 0.2, f"p95 latency {p95:.3f}s exceeds 200 ms budget"

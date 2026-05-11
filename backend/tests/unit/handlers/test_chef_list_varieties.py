"""Unit tests for chef_list_varieties Lambda handler (US1 + performance benchmark)."""
import json
import time
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
        table.put_item(Item={
            "varietyId": "classic",
            "name": "Classic",
            "description": "Original recipe",
            "imageKey": "images/classic.jpg",
            "active": True,
            "bottleYieldMl": 750,
            "ingredients": [
                {
                    "ingredientId": "i-001",
                    "name": "Coconut cream",
                    "quantityPerBottle": Decimal("400.0"),
                    "unit": "ml",
                    "category": "dairy",
                }
            ],
        })
        table.put_item(Item={
            "varietyId": "discontinued",
            "name": "Discontinued",
            "description": "No longer made",
            "imageKey": "",
            "active": False,
            "bottleYieldMl": 750,
            "ingredients": [],
        })
        yield table


def _chef_event():
    return {
        "requestContext": {
            "authorizer": {"lambda": {"role": "chef"}},
        },
    }


def _user_event():
    return {
        "requestContext": {
            "authorizer": {"lambda": {"role": "authorized-user"}},
        },
    }


class TestChefListVarieties:
    def test_chef_returns_200_with_all_varieties(self, varieties_table):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_chef_event(), MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body["varieties"]) == 2

    def test_includes_inactive_varieties(self, varieties_table):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_chef_event(), MagicMock())
        body = json.loads(result["body"])
        names = [v["name"] for v in body["varieties"]]
        assert "Classic" in names
        assert "Discontinued" in names

    def test_each_item_has_required_fields(self, varieties_table):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_chef_event(), MagicMock())
        body = json.loads(result["body"])
        for v in body["varieties"]:
            for field in ("varietyId", "name", "description", "imageKey", "bottleYieldMl", "active", "ingredients"):
                assert field in v, f"missing field: {field}"

    def test_ingredients_included_with_details(self, varieties_table):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_chef_event(), MagicMock())
        body = json.loads(result["body"])
        classic = next(v for v in body["varieties"] if v["varietyId"] == "classic")
        assert len(classic["ingredients"]) == 1
        ing = classic["ingredients"][0]
        for field in ("ingredientId", "name", "quantityPerBottle", "unit", "category"):
            assert field in ing, f"ingredient missing field: {field}"

    def test_active_filter_not_applied(self, varieties_table):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_chef_event(), MagicMock())
        body = json.loads(result["body"])
        active_flags = {v["active"] for v in body["varieties"]}
        assert True in active_flags
        assert False in active_flags

    def test_non_chef_returns_403(self, varieties_table):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_user_event(), MagicMock())
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "CHEF_ROLE_REQUIRED"

    def test_empty_table_returns_empty_list(self, varieties_table):
        varieties_table.delete_item(Key={"varietyId": "classic"})
        varieties_table.delete_item(Key={"varietyId": "discontinued"})
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_chef_event(), MagicMock())
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["varieties"] == []

    def test_performance_under_200ms_with_20_varieties(self, varieties_table):
        """Constitution Principle IV: handler must complete ≤200ms with 20 varieties (5 ingredients each)."""
        for i in range(3, 23):
            varieties_table.put_item(Item={
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
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        start = time.perf_counter()
        result = handler(_chef_event(), MagicMock())
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert result["statusCode"] == 200
        assert elapsed_ms < 200, f"handler took {elapsed_ms:.1f}ms — must be <200ms"

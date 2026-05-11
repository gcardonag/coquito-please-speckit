"""Unit tests for chef_create_variety Lambda handler (US4)."""
import json
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
        yield table


def _event(role: str = "chef", body: dict | None = None) -> dict:
    default_body = {
        "name": "Chocolate Coquito",
        "description": "Rich and chocolatey.",
        "imageKey": "assets/chocolate.jpg",
        "bottleYieldMl": 750,
        "active": True,
        "ingredients": [],
    }
    return {
        "requestContext": {"authorizer": {"lambda": {"role": role}}},
        "body": json.dumps(body if body is not None else default_body),
    }


class TestChefCreateVariety:
    def test_valid_request_returns_201_with_32char_variety_id(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        result = handler(_event(), MagicMock())
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert "variety" in body
        assert len(body["variety"]["varietyId"]) == 32

    def test_ingredients_each_get_32char_uuid(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        result = handler(_event(body={
            "name": "Classic",
            "bottleYieldMl": 750,
            "ingredients": [
                {"name": "Coconut cream", "quantityPerBottle": 400.0, "unit": "ml", "category": "dairy"},
                {"name": "Rum", "quantityPerBottle": 200.0, "unit": "ml", "category": "spirit"},
            ],
        }), MagicMock())
        body = json.loads(result["body"])
        assert result["statusCode"] == 201
        for ing in body["variety"]["ingredients"]:
            assert "ingredientId" in ing
            assert len(ing["ingredientId"]) == 32

    def test_non_chef_returns_403(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        result = handler(_event(role="authorized-user"), MagicMock())
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "CHEF_ROLE_REQUIRED"

    def test_blank_name_returns_400_with_field(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"name": "  ", "bottleYieldMl": 750}), MagicMock())
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["code"] == "VALIDATION_ERROR"
        assert body["field"] == "name"

    def test_missing_name_returns_400(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"bottleYieldMl": 750}), MagicMock())
        assert result["statusCode"] == 400
        assert json.loads(result["body"])["field"] == "name"

    def test_bottle_yield_zero_returns_400(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"name": "Test", "bottleYieldMl": 0}), MagicMock())
        assert result["statusCode"] == 400
        assert json.loads(result["body"])["field"] == "bottleYieldMl"

    def test_active_defaults_to_true_when_omitted(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"name": "Test", "bottleYieldMl": 750}), MagicMock())
        assert json.loads(result["body"])["variety"]["active"] is True

    def test_ingredients_default_to_empty_list(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"name": "Test", "bottleYieldMl": 750}), MagicMock())
        assert json.loads(result["body"])["variety"]["ingredients"] == []

    def test_ingredient_missing_name_returns_400(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        result = handler(_event(body={
            "name": "Test",
            "bottleYieldMl": 750,
            "ingredients": [{"quantityPerBottle": 100.0, "unit": "ml", "category": "dairy"}],
        }), MagicMock())
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "name" in body["field"]

    def test_ingredient_negative_quantity_returns_400(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        result = handler(_event(body={
            "name": "Test",
            "bottleYieldMl": 750,
            "ingredients": [{"name": "X", "quantityPerBottle": -1.0, "unit": "ml", "category": "dairy"}],
        }), MagicMock())
        assert result["statusCode"] == 400

"""Contract tests for GET /api/v1/chef/varieties, POST /api/v1/chef/varieties,
and PUT /api/v1/chef/varieties/{id}."""
import json
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


_VARIETY_ITEM = {
    "varietyId": "classic",
    "name": "Classic Coquito",
    "description": "Traditional recipe",
    "imageKey": "assets/classic.jpg",
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
}

_CHEF_EVENT_BASE = {
    "requestContext": {
        "authorizer": {"lambda": {"role": "chef"}},
    },
}

_VARIETY_DETAIL_FIELDS = ("varietyId", "name", "description", "imageKey", "bottleYieldMl", "active", "ingredients")
_INGREDIENT_FIELDS = ("ingredientId", "name", "quantityPerBottle", "unit", "category")


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
        table.put_item(Item=_VARIETY_ITEM)
        yield table


class TestGetChefVarietiesContract:
    def test_200_response_has_varieties_list(self, varieties_table):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_CHEF_EVENT_BASE, MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "varieties" in body
        assert isinstance(body["varieties"], list)

    def test_each_variety_matches_chef_variety_detail_shape(self, varieties_table):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_CHEF_EVENT_BASE, MagicMock())
        body = json.loads(result["body"])
        for v in body["varieties"]:
            for f in _VARIETY_DETAIL_FIELDS:
                assert f in v, f"variety missing field: {f}"
            assert isinstance(v["ingredients"], list)
            for ing in v["ingredients"]:
                for f in _INGREDIENT_FIELDS:
                    assert f in ing, f"ingredient missing field: {f}"

    def test_403_has_chef_role_required_code(self, varieties_table):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        event = {"requestContext": {"authorizer": {"lambda": {"role": "authorized-user"}}}}
        result = handler(event, MagicMock())
        assert result["statusCode"] == 403
        body = json.loads(result["body"])
        assert body["code"] == "CHEF_ROLE_REQUIRED"
        assert "message" in body


class TestPostChefVarietiesContract:
    def test_201_response_has_variety_with_all_fields(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        event = {
            **_CHEF_EVENT_BASE,
            "body": json.dumps({
                "name": "Chocolate Coquito",
                "bottleYieldMl": 750,
                "ingredients": [
                    {"name": "Cocoa powder", "quantityPerBottle": 50.0, "unit": "g", "category": "flavoring"},
                ],
            }),
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert "variety" in body
        v = body["variety"]
        for f in _VARIETY_DETAIL_FIELDS:
            assert f in v, f"variety missing field: {f}"
        assert len(v["varietyId"]) == 32
        for ing in v["ingredients"]:
            for f in _INGREDIENT_FIELDS:
                assert f in ing, f"ingredient missing field: {f}"
            assert len(ing["ingredientId"]) == 32

    def test_400_has_validation_error_code_and_field(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        event = {**_CHEF_EVENT_BASE, "body": json.dumps({})}
        result = handler(event, MagicMock())
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["code"] == "VALIDATION_ERROR"
        assert "field" in body
        assert "message" in body

    def test_403_has_chef_role_required_code(self, varieties_table):
        from src.handlers.chef_create_variety import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "authorized-user"}}},
            "body": json.dumps({"name": "Test", "bottleYieldMl": 750}),
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "CHEF_ROLE_REQUIRED"


class TestPutChefVarietyContract:
    def test_200_response_has_variety_with_all_fields(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        event = {
            **_CHEF_EVENT_BASE,
            "pathParameters": {"id": "classic"},
            "body": json.dumps({"name": "Classic Coquito Updated"}),
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "variety" in body
        for f in _VARIETY_DETAIL_FIELDS:
            assert f in body["variety"], f"variety missing field: {f}"

    def test_404_has_variety_not_found_code_and_message(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        event = {
            **_CHEF_EVENT_BASE,
            "pathParameters": {"id": "no-such-variety"},
            "body": json.dumps({}),
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert body["code"] == "VARIETY_NOT_FOUND"
        assert "message" in body

    def test_400_has_validation_error_code_and_field(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        event = {
            **_CHEF_EVENT_BASE,
            "pathParameters": {"id": "classic"},
            "body": json.dumps({"bottleYieldMl": 0}),
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["code"] == "VALIDATION_ERROR"
        assert "field" in body
        assert "message" in body

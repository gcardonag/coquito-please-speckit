"""Unit tests for chef_update_variety Lambda handler (US2 top-level fields + US3 ingredients)."""
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


_EXISTING_VARIETY = {
    "varietyId": "classic",
    "name": "Classic",
    "description": "Original recipe",
    "imageKey": "images/classic.jpg",
    "active": True,
    "bottleYieldMl": 750,
    "ingredients": [
        {
            "ingredientId": "i-coconut",
            "name": "Coconut cream",
            "quantityPerBottle": Decimal("400.0"),
            "unit": "ml",
            "category": "dairy",
        }
    ],
}


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
        table.put_item(Item=_EXISTING_VARIETY)
        yield table


def _event(role: str = "chef", variety_id: str = "classic", body: dict | None = None) -> dict:
    return {
        "requestContext": {"authorizer": {"lambda": {"role": role}}},
        "pathParameters": {"id": variety_id},
        "body": json.dumps(body or {}),
    }


# ---------------------------------------------------------------------------
# US2: Top-level field updates
# ---------------------------------------------------------------------------
class TestChefUpdateVarietyTopLevelFields:
    def test_chef_updates_name_returns_200(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"name": "Classic Coquito"}), MagicMock())
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["variety"]["name"] == "Classic Coquito"

    def test_chef_sets_active_false(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"active": False}), MagicMock())
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["variety"]["active"] is False

    def test_chef_updates_bottle_yield(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"bottleYieldMl": 1000}), MagicMock())
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["variety"]["bottleYieldMl"] == 1000

    def test_non_chef_returns_403(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(role="authorized-user"), MagicMock())
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "CHEF_ROLE_REQUIRED"

    def test_variety_not_found_returns_404(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(variety_id="nonexistent"), MagicMock())
        assert result["statusCode"] == 404
        assert json.loads(result["body"])["code"] == "VARIETY_NOT_FOUND"

    def test_blank_name_returns_400_with_field(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"name": "   "}), MagicMock())
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["code"] == "VALIDATION_ERROR"
        assert body["field"] == "name"

    def test_bottle_yield_zero_returns_400(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"bottleYieldMl": 0}), MagicMock())
        assert result["statusCode"] == 400
        assert json.loads(result["body"])["field"] == "bottleYieldMl"

    def test_bottle_yield_negative_returns_400(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"bottleYieldMl": -5}), MagicMock())
        assert result["statusCode"] == 400

    def test_omitting_ingredients_preserves_existing(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"name": "Updated Name"}), MagicMock())
        body = json.loads(result["body"])
        assert len(body["variety"]["ingredients"]) == 1
        assert body["variety"]["ingredients"][0]["ingredientId"] == "i-coconut"


# ---------------------------------------------------------------------------
# US3: Ingredient management
# ---------------------------------------------------------------------------
class TestChefUpdateVarietyIngredients:
    def test_ingredient_without_id_gets_new_uuid(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"ingredients": [
            {"name": "Rum", "quantityPerBottle": 200.0, "unit": "ml", "category": "spirit"},
        ]}), MagicMock())
        body = json.loads(result["body"])
        assert result["statusCode"] == 200
        ing = body["variety"]["ingredients"][0]
        assert "ingredientId" in ing
        assert len(ing["ingredientId"]) == 32

    def test_ingredient_with_existing_id_preserves_it(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"ingredients": [
            {"ingredientId": "i-coconut", "name": "Coconut cream", "quantityPerBottle": 420.0, "unit": "ml", "category": "dairy"},
        ]}), MagicMock())
        body = json.loads(result["body"])
        assert body["variety"]["ingredients"][0]["ingredientId"] == "i-coconut"

    def test_empty_ingredients_list_clears_all(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"ingredients": []}), MagicMock())
        assert json.loads(result["body"])["variety"]["ingredients"] == []

    def test_ingredient_missing_name_returns_400_with_field(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"ingredients": [
            {"quantityPerBottle": 100.0, "unit": "ml", "category": "dairy"},
        ]}), MagicMock())
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "ingredients[0].name" in body["field"]

    def test_ingredient_zero_quantity_returns_400(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"ingredients": [
            {"name": "X", "quantityPerBottle": 0, "unit": "ml", "category": "dairy"},
        ]}), MagicMock())
        assert result["statusCode"] == 400

    def test_ingredient_missing_unit_returns_400_with_field(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"ingredients": [
            {"name": "X", "quantityPerBottle": 100.0, "category": "dairy"},
        ]}), MagicMock())
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "unit" in body["field"]

    def test_ingredient_missing_category_returns_400_with_field(self, varieties_table):
        from src.handlers.chef_update_variety import handler  # noqa: PLC0415
        result = handler(_event(body={"ingredients": [
            {"name": "X", "quantityPerBottle": 100.0, "unit": "ml"},
        ]}), MagicMock())
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "category" in body["field"]

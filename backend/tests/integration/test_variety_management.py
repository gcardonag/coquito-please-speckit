"""Integration tests for chef variety management (US1–US4).

These tests call real handler functions with moto-backed DynamoDB.
They verify cross-handler behaviour (e.g. chef edit → public listing reflects change).
"""
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
    monkeypatch.setenv("CLOUDFRONT_ASSETS_BASE_URL", "https://assets.example.com")


@pytest.fixture
def tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        varieties = ddb.create_table(
            TableName="coquito-varieties",
            KeySchema=[{"AttributeName": "varietyId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "varietyId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        ddb.create_table(
            TableName="coquito-batches",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        ddb.create_table(
            TableName="coquito-requests",
            KeySchema=[{"AttributeName": "requestId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "requestId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        varieties.put_item(Item={
            "varietyId": "v-active",
            "name": "Active Variety",
            "description": "A current offering",
            "imageKey": "images/active.jpg",
            "active": True,
            "bottleYieldMl": 750,
            "ingredients": [],
        })
        varieties.put_item(Item={
            "varietyId": "v-inactive",
            "name": "Inactive Variety",
            "description": "Old recipe",
            "imageKey": "",
            "active": False,
            "bottleYieldMl": 500,
            "ingredients": [],
        })
        yield {"varieties": varieties}


def _chef_event(path_params=None, body=None):
    return {
        "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
        "pathParameters": path_params,
        "body": json.dumps(body) if body is not None else None,
        "queryStringParameters": None,
    }


# ---------------------------------------------------------------------------
# US1: Chef views all varieties including inactive
# ---------------------------------------------------------------------------
class TestUS1ChefViewsAllVarieties:
    def test_chef_sees_both_active_and_inactive(self, tables):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_chef_event(), MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        names = {v["name"] for v in body["varieties"]}
        assert "Active Variety" in names
        assert "Inactive Variety" in names

    def test_active_only_filter_not_applied(self, tables):
        from src.handlers.chef_list_varieties import handler  # noqa: PLC0415
        result = handler(_chef_event(), MagicMock())
        body = json.loads(result["body"])
        flags = {v["active"] for v in body["varieties"]}
        assert True in flags
        assert False in flags


# ---------------------------------------------------------------------------
# US2: Chef edits variety — deactivation reflects in public listing
# ---------------------------------------------------------------------------
class TestUS2ChefEditsVariety:
    def test_deactivating_removes_from_public_listing(self, tables):
        from src.handlers.chef_update_variety import handler as update  # noqa: PLC0415
        from src.handlers.list_varieties import handler as list_public  # noqa: PLC0415

        update(_chef_event({"id": "v-active"}, {"active": False}), MagicMock())

        public_result = list_public({"queryStringParameters": None}, MagicMock())
        public_names = {v["name"] for v in json.loads(public_result["body"])["varieties"]}
        assert "Active Variety" not in public_names

    def test_reactivating_adds_back_to_public_listing(self, tables):
        from src.handlers.chef_update_variety import handler as update  # noqa: PLC0415
        from src.handlers.list_varieties import handler as list_public  # noqa: PLC0415

        update(_chef_event({"id": "v-inactive"}, {"active": True}), MagicMock())

        public_result = list_public({"queryStringParameters": None}, MagicMock())
        public_names = {v["name"] for v in json.loads(public_result["body"])["varieties"]}
        assert "Inactive Variety" in public_names


# ---------------------------------------------------------------------------
# US3: Chef manages ingredients — stable IDs across edits
# ---------------------------------------------------------------------------
class TestUS3ChefManagesIngredients:
    def test_add_ingredient_appears_with_stable_uuid(self, tables):
        from src.handlers.chef_update_variety import handler as update  # noqa: PLC0415
        from src.handlers.chef_list_varieties import handler as list_all  # noqa: PLC0415

        update(_chef_event({"id": "v-active"}, {"ingredients": [
            {"name": "Coconut cream", "quantityPerBottle": 400.0, "unit": "ml", "category": "dairy"},
        ]}), MagicMock())

        varieties = json.loads(list_all(_chef_event(), MagicMock())["body"])["varieties"]
        active = next(v for v in varieties if v["varietyId"] == "v-active")
        assert len(active["ingredients"]) == 1
        ing = active["ingredients"][0]
        assert ing["name"] == "Coconut cream"
        assert len(ing["ingredientId"]) == 32

    def test_update_ingredient_preserves_id(self, tables):
        from src.handlers.chef_update_variety import handler as update  # noqa: PLC0415

        r1 = update(_chef_event({"id": "v-active"}, {"ingredients": [
            {"name": "Coconut cream", "quantityPerBottle": 400.0, "unit": "ml", "category": "dairy"},
        ]}), MagicMock())
        ing_id = json.loads(r1["body"])["variety"]["ingredients"][0]["ingredientId"]

        r2 = update(_chef_event({"id": "v-active"}, {"ingredients": [
            {"ingredientId": ing_id, "name": "Coconut cream", "quantityPerBottle": 500.0, "unit": "ml", "category": "dairy"},
        ]}), MagicMock())
        body = json.loads(r2["body"])
        assert body["variety"]["ingredients"][0]["quantityPerBottle"] == 500.0
        assert body["variety"]["ingredients"][0]["ingredientId"] == ing_id

    def test_remove_ingredient_by_omission(self, tables):
        from src.handlers.chef_update_variety import handler as update  # noqa: PLC0415

        update(_chef_event({"id": "v-active"}, {"ingredients": [
            {"name": "Coconut cream", "quantityPerBottle": 400.0, "unit": "ml", "category": "dairy"},
            {"name": "Rum", "quantityPerBottle": 200.0, "unit": "ml", "category": "spirit"},
        ]}), MagicMock())

        r = update(_chef_event({"id": "v-active"}, {"ingredients": [
            {"name": "Rum", "quantityPerBottle": 200.0, "unit": "ml", "category": "spirit"},
        ]}), MagicMock())
        body = json.loads(r["body"])
        assert len(body["variety"]["ingredients"]) == 1
        assert body["variety"]["ingredients"][0]["name"] == "Rum"


# ---------------------------------------------------------------------------
# US4: Chef creates new variety — appears in chef list
# ---------------------------------------------------------------------------
class TestUS4ChefCreatesVariety:
    def test_created_variety_appears_in_chef_list(self, tables):
        from src.handlers.chef_create_variety import handler as create  # noqa: PLC0415
        from src.handlers.chef_list_varieties import handler as list_all  # noqa: PLC0415

        r = create(_chef_event(body={
            "name": "Spiced Rum Coquito",
            "bottleYieldMl": 750,
            "ingredients": [
                {"name": "White rum", "quantityPerBottle": 300.0, "unit": "ml", "category": "spirit"},
            ],
        }), MagicMock())
        assert r["statusCode"] == 201
        new_id = json.loads(r["body"])["variety"]["varietyId"]
        assert len(new_id) == 32

        varieties = json.loads(list_all(_chef_event(), MagicMock())["body"])["varieties"]
        assert any(v["varietyId"] == new_id for v in varieties)

    def test_new_variety_ingredient_has_stable_uuid(self, tables):
        from src.handlers.chef_create_variety import handler as create  # noqa: PLC0415

        r = create(_chef_event(body={
            "name": "Spiced",
            "bottleYieldMl": 750,
            "ingredients": [
                {"name": "Rum", "quantityPerBottle": 200.0, "unit": "ml", "category": "spirit"},
            ],
        }), MagicMock())
        ing = json.loads(r["body"])["variety"]["ingredients"][0]
        assert len(ing["ingredientId"]) == 32

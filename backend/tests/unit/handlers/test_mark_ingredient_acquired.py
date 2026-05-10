"""T054: Unit tests for mark_ingredient_acquired handler."""
import json
from decimal import Decimal
import boto3
import pytest
from moto import mock_aws

from src.handlers.mark_ingredient_acquired import handler


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("COOK_SECRET", "secret-sauce")


BATCH_ITEM = {
    "batchId": "b-acq-001",
    "batchName": "Acquired Test",
    "cutoffDate": "2026-12-01",
    "maxBottleVolumeMl": 750,
    "availableVarietyIds": ["v-classic"],
    "status": "OPEN",
    "createdAt": "2026-01-01T00:00:00Z",
    "acquiredIngredients": {},
}

CLASSIC_VARIETY = {
    "varietyId": "v-classic",
    "name": "Classic",
    "description": "Traditional",
    "imageKey": "images/classic.jpg",
    "active": True,
    "bottleYieldMl": 750,
    "ingredients": [
        {"ingredientId": "i-rum", "name": "Rum", "quantityPerBottle": Decimal("1.0"), "unit": "bottle", "category": "alcohol"},
    ],
}


@pytest.fixture
def ddb_tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        batches_table = ddb.create_table(
            TableName="coquito-batches",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        varieties_table = ddb.create_table(
            TableName="coquito-varieties",
            KeySchema=[{"AttributeName": "varietyId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "varietyId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        batches_table.put_item(Item=BATCH_ITEM)
        varieties_table.put_item(Item=CLASSIC_VARIETY)
        yield {"batches": batches_table}


def _event(batch_id="b-acq-001", ingredient_id="i-rum", acquired=True, cook_secret="secret-sauce"):
    import json
    return {
        "pathParameters": {"id": batch_id, "ingredId": ingredient_id},
        "headers": {"X-Cook-Secret": cook_secret},
        "body": json.dumps({"acquired": acquired}),
        "requestContext": {"authorizer": {"lambda": {"role": "chef", "userId": "chef-001", "email": "chef@example.com"}}},
    }


class TestMarkIngredientAcquired:
    def test_sets_acquired_true_and_returns_200(self, ddb_tables):
        result = handler(_event(acquired=True), {})
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["acquired"] is True
        assert body["ingredientId"] == "i-rum"

        item = ddb_tables["batches"].get_item(Key={"batchId": "b-acq-001"})["Item"]
        assert item["acquiredIngredients"]["i-rum"] is True

    def test_idempotent_already_acquired_returns_200(self, ddb_tables):
        handler(_event(acquired=True), {})
        result = handler(_event(acquired=True), {})
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["acquired"] is True

    def test_sets_acquired_false_to_toggle_off(self, ddb_tables):
        handler(_event(acquired=True), {})
        result = handler(_event(acquired=False), {})
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["acquired"] is False

    def test_returns_403_for_non_chef_role(self, ddb_tables):
        import json as _json  # noqa: PLC0415
        event = {
            "pathParameters": {"id": "b-acq-001", "ingredId": "i-rum"},
            "headers": {},
            "body": _json.dumps({"acquired": True}),
            "requestContext": {"authorizer": {"lambda": {"role": "authorized-user", "userId": "u-001", "email": "u@example.com"}}},
        }
        result = handler(event, {})
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "FORBIDDEN"

    def test_returns_404_for_unknown_ingredient(self, ddb_tables):
        result = handler(_event(ingredient_id="i-unknown"), {})
        assert result["statusCode"] == 404
        assert json.loads(result["body"])["code"] == "INGREDIENT_NOT_FOUND"

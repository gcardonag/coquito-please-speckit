"""T053: Unit tests for get_ingredient_list handler."""
from decimal import Decimal
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch
from datetime import date

from src.handlers.get_ingredient_list import handler


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("COOK_SECRET", "secret-sauce")


BATCH_ITEM = {
    "batchId": "b-cook-001",
    "batchName": "Cook Test Batch",
    "cutoffDate": "2026-12-01",
    "maxBottleVolumeMl": 750,
    "availableVarietyIds": ["v-classic", "v-choco"],
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
        {"ingredientId": "i-coconut", "name": "Coconut cream", "quantityPerBottle": Decimal("2.0"), "unit": "can", "category": "dairy"},
    ],
}

CHOCO_VARIETY = {
    "varietyId": "v-choco",
    "name": "Chocolate",
    "description": "Chocolate",
    "imageKey": "images/choco.jpg",
    "active": True,
    "bottleYieldMl": 750,
    "ingredients": [
        {"ingredientId": "i-cacao", "name": "Cacao powder", "quantityPerBottle": Decimal("0.5"), "unit": "cup", "category": "baking"},
        {"ingredientId": "i-coconut", "name": "Coconut cream", "quantityPerBottle": Decimal("2.0"), "unit": "can", "category": "dairy"},
    ],
}

REQUEST_CLASSIC = {
    "requestId": "req-cook-001",
    "batchId": "b-cook-001",
    "varietyId": "v-classic",
    "status": "CONFIRMED",
    "requesterName": "A", "requesterEmail": "a@a.com",
    "pickupDate": "2026-12-20", "pickupTime": "10:00",
    "exchangeLocation": "A St", "bottleProvided": False,
    "costContribution": False, "reminders": [],
    "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z",
    "idempotencyKey": "ik1",
}
REQUEST_CLASSIC_2 = {**REQUEST_CLASSIC, "requestId": "req-cook-002", "idempotencyKey": "ik2"}
REQUEST_CHOCO = {
    **REQUEST_CLASSIC, "requestId": "req-cook-003", "varietyId": "v-choco", "idempotencyKey": "ik3",
}
REQUEST_CANCELLED = {
    **REQUEST_CLASSIC, "requestId": "req-cook-004", "status": "CANCELLED", "idempotencyKey": "ik4",
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
        requests_table = ddb.create_table(
            TableName="coquito-requests",
            KeySchema=[{"AttributeName": "requestId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "requestId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        batches_table.put_item(Item=BATCH_ITEM)
        varieties_table.put_item(Item=CLASSIC_VARIETY)
        varieties_table.put_item(Item=CHOCO_VARIETY)
        requests_table.put_item(Item=REQUEST_CLASSIC)
        requests_table.put_item(Item=REQUEST_CLASSIC_2)
        requests_table.put_item(Item=REQUEST_CHOCO)
        requests_table.put_item(Item=REQUEST_CANCELLED)
        yield {"batches": batches_table, "varieties": varieties_table, "requests": requests_table}


def _event(batch_id="b-cook-001", cook_secret="secret-sauce"):
    return {
        "pathParameters": {"batchId": batch_id},
        "headers": {"X-Cook-Secret": cook_secret},
    }


class TestGetIngredientList:
    def test_aggregates_quantities_for_confirmed_requests(self, ddb_tables):
        with patch("src.handlers.get_ingredient_list._today", return_value=date(2026, 11, 1)):
            result = handler(_event(), {})

        assert result["statusCode"] == 200
        body = result["body"]
        assert body["totalConfirmedRequests"] == 3  # 2 classic + 1 choco

        variety_ids = {v["varietyId"] for v in body["byVariety"]}
        assert "v-classic" in variety_ids
        assert "v-choco" in variety_ids

        classic = next(v for v in body["byVariety"] if v["varietyId"] == "v-classic")
        rum = next(i for i in classic["ingredients"] if i["ingredientId"] == "i-rum")
        assert rum["totalQuantity"] == 2.0  # 1.0 * 2 confirmed classic requests

    def test_ignores_cancelled_requests(self, ddb_tables):
        with patch("src.handlers.get_ingredient_list._today", return_value=date(2026, 11, 1)):
            result = handler(_event(), {})

        body = result["body"]
        assert body["totalConfirmedRequests"] == 3  # CANCELLED not counted

    def test_is_finalized_false_before_cutoff(self, ddb_tables):
        with patch("src.handlers.get_ingredient_list._today", return_value=date(2026, 11, 1)):
            result = handler(_event(), {})
        assert result["body"]["isFinalized"] is False

    def test_is_finalized_true_after_cutoff(self, ddb_tables):
        with patch("src.handlers.get_ingredient_list._today", return_value=date(2026, 12, 15)):
            result = handler(_event(), {})
        assert result["body"]["isFinalized"] is True

    def test_returns_401_for_wrong_cook_secret(self, ddb_tables):
        with patch("src.handlers.get_ingredient_list._today", return_value=date(2026, 11, 1)):
            result = handler(_event(cook_secret="wrong"), {})
        assert result["statusCode"] == 401
        assert result["body"]["code"] == "UNAUTHORIZED"

    def test_returns_401_for_missing_cook_secret(self, ddb_tables):
        with patch("src.handlers.get_ingredient_list._today", return_value=date(2026, 11, 1)):
            event = {"pathParameters": {"batchId": "b-cook-001"}, "headers": {}}
            result = handler(event, {})
        assert result["statusCode"] == 401

    def test_returns_404_for_unknown_batch(self, ddb_tables):
        with patch("src.handlers.get_ingredient_list._today", return_value=date(2026, 11, 1)):
            result = handler(_event(batch_id="b-unknown"), {})
        assert result["statusCode"] == 404
        assert result["body"]["code"] == "BATCH_NOT_FOUND"

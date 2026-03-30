"""T055: Integration tests for ingredient list aggregation and acquired flow."""
from decimal import Decimal
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch
from datetime import date

from src.handlers.get_ingredient_list import handler as get_ingredients
from src.handlers.mark_ingredient_acquired import handler as mark_acquired


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("COOK_SECRET", "int-secret")


@pytest.fixture
def seeded_tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        batches = ddb.create_table(
            TableName="coquito-batches",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        varieties = ddb.create_table(
            TableName="coquito-varieties",
            KeySchema=[{"AttributeName": "varietyId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "varietyId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        requests = ddb.create_table(
            TableName="coquito-requests",
            KeySchema=[{"AttributeName": "requestId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "requestId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        batches.put_item(Item={
            "batchId": "b-int-cook",
            "batchName": "Int Cook Batch",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["v-classic", "v-choco"],
            "status": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
            "acquiredIngredients": {},
        })
        varieties.put_item(Item={
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
        })
        varieties.put_item(Item={
            "varietyId": "v-choco",
            "name": "Chocolate",
            "description": "Choco",
            "imageKey": "images/choco.jpg",
            "active": True,
            "bottleYieldMl": 750,
            "ingredients": [
                {"ingredientId": "i-cacao", "name": "Cacao powder", "quantityPerBottle": Decimal("0.5"), "unit": "cup", "category": "baking"},
                {"ingredientId": "i-coconut", "name": "Coconut cream", "quantityPerBottle": Decimal("2.0"), "unit": "can", "category": "dairy"},
            ],
        })

        base = {
            "pickupDate": "2026-12-20", "pickupTime": "10:00", "exchangeLocation": "A",
            "bottleProvided": False, "costContribution": False, "reminders": [],
            "requesterName": "T", "requesterEmail": "t@t.com",
            "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z",
            "batchId": "b-int-cook",
        }
        # 2 classic + 1 choco confirmed
        requests.put_item(Item={**base, "requestId": "r1", "varietyId": "v-classic", "status": "CONFIRMED", "idempotencyKey": "k1"})
        requests.put_item(Item={**base, "requestId": "r2", "varietyId": "v-classic", "status": "CONFIRMED", "idempotencyKey": "k2"})
        requests.put_item(Item={**base, "requestId": "r3", "varietyId": "v-choco", "status": "CONFIRMED", "idempotencyKey": "k3"})

        yield {"batches": batches}


class TestIngredientListIntegration:
    def test_quantities_multiplied_per_variety(self, seeded_tables):
        with patch("src.handlers.get_ingredient_list._today", return_value=date(2026, 11, 1)):
            result = get_ingredients({
                "pathParameters": {"batchId": "b-int-cook"},
                "headers": {"X-Cook-Secret": "int-secret"},
            }, {})

        assert result["statusCode"] == 200
        body = result["body"]
        assert body["totalConfirmedRequests"] == 3

        classic = next(v for v in body["byVariety"] if v["varietyId"] == "v-classic")
        rum = next(i for i in classic["ingredients"] if i["ingredientId"] == "i-rum")
        assert rum["totalQuantity"] == 2.0  # 1.0 * 2

        coconut_classic = next(i for i in classic["ingredients"] if i["ingredientId"] == "i-coconut")
        assert coconut_classic["totalQuantity"] == 4.0  # 2.0 * 2

        choco = next(v for v in body["byVariety"] if v["varietyId"] == "v-choco")
        cacao = next(i for i in choco["ingredients"] if i["ingredientId"] == "i-cacao")
        assert cacao["totalQuantity"] == 0.5  # 0.5 * 1

    def test_mark_acquired_persists_to_dynamodb(self, seeded_tables):
        import json
        result = mark_acquired({
            "pathParameters": {"batchId": "b-int-cook", "ingredientId": "i-rum"},
            "headers": {"X-Cook-Secret": "int-secret"},
            "body": json.dumps({"acquired": True}),
        }, {})

        assert result["statusCode"] == 200
        item = seeded_tables["batches"].get_item(Key={"batchId": "b-int-cook"})["Item"]
        assert item["acquiredIngredients"]["i-rum"] is True

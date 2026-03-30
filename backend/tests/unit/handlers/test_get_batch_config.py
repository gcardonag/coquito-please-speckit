"""T022: Unit tests for get_batch_config Lambda handler."""
import boto3
import pytest
from moto import mock_aws

from src.handlers.get_batch_config import handler


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("CLOUDFRONT_ASSETS_BASE_URL", "https://assets.example.com")


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
        batches_table.put_item(Item={
            "batchId": "b-001",
            "batchName": "Christmas 2026",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["v-classic"],
            "status": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
        })
        varieties_table.put_item(Item={
            "varietyId": "v-classic",
            "name": "Classic",
            "description": "Original recipe",
            "imageKey": "images/varieties/v-classic.jpg",
            "active": True,
            "bottleYieldMl": 750,
            "ingredients": [],
        })
        yield {"batches": batches_table, "varieties": varieties_table}


class TestGetBatchConfig:
    def test_returns_batch_with_resolved_varieties(self, ddb_tables):
        event = {"pathParameters": {"batchId": "b-001"}}
        result = handler(event, {})
        assert result["statusCode"] == 200
        body = result["body"]
        assert body["batchId"] == "b-001"
        assert body["batchName"] == "Christmas 2026"
        assert body["maxBottleVolumeMl"] == 750
        assert len(body["availableVarieties"]) == 1
        assert body["availableVarieties"][0]["name"] == "Classic"

    def test_variety_image_url_is_resolved(self, ddb_tables):
        event = {"pathParameters": {"batchId": "b-001"}}
        result = handler(event, {})
        variety = result["body"]["availableVarieties"][0]
        assert variety["imageUrl"].startswith("https://assets.example.com")

    def test_returns_404_for_unknown_batch(self, ddb_tables):
        event = {"pathParameters": {"batchId": "nonexistent"}}
        result = handler(event, {})
        assert result["statusCode"] == 404
        assert result["body"]["code"] == "BATCH_NOT_FOUND"

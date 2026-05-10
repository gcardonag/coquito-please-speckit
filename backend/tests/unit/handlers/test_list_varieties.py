"""T021: Unit tests for list_varieties Lambda handler."""
import json
import os

import boto3
import pytest
from moto import mock_aws

from src.handlers.list_varieties import handler


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("CLOUDFRONT_ASSETS_BASE_URL", "https://assets.example.com")


@pytest.fixture
def ddb_tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")

        varieties_table = ddb.create_table(
            TableName="coquito-varieties",
            KeySchema=[{"AttributeName": "varietyId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "varietyId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        batches_table = ddb.create_table(
            TableName="coquito-batches",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        varieties_table.put_item(Item={
            "varietyId": "v-classic",
            "name": "Classic",
            "description": "Original recipe",
            "imageKey": "images/varieties/v-classic.jpg",
            "active": True,
            "bottleYieldMl": 750,
            "ingredients": [],
        })
        varieties_table.put_item(Item={
            "varietyId": "v-chocolate",
            "name": "Chocolate",
            "description": "Chocolate twist",
            "imageKey": "images/varieties/v-chocolate.jpg",
            "active": True,
            "bottleYieldMl": 750,
            "ingredients": [],
        })
        varieties_table.put_item(Item={
            "varietyId": "v-inactive",
            "name": "Discontinued",
            "description": "No longer available",
            "imageKey": "images/varieties/v-inactive.jpg",
            "active": False,
            "bottleYieldMl": 750,
            "ingredients": [],
        })
        batches_table.put_item(Item={
            "batchId": "b-001",
            "batchName": "Christmas 2026",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["v-classic"],
            "status": "OPEN",
            "createdAt": "2026-01-01T00:00:00Z",
        })

        yield {"varieties": varieties_table, "batches": batches_table}


class TestListVarieties:
    def test_returns_only_active_varieties(self, ddb_tables):
        event = {"queryStringParameters": None}
        result = handler(event, {})
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        names = [v["name"] for v in body["varieties"]]
        assert "Classic" in names
        assert "Chocolate" in names
        assert "Discontinued" not in names

    def test_filters_to_batch_varieties_when_batch_id_provided(self, ddb_tables):
        event = {"queryStringParameters": {"batchId": "b-001"}}
        result = handler(event, {})
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body["varieties"]) == 1
        assert body["varieties"][0]["name"] == "Classic"

    def test_returns_404_for_unknown_batch_id(self, ddb_tables):
        event = {"queryStringParameters": {"batchId": "nonexistent"}}
        result = handler(event, {})
        assert result["statusCode"] == 404
        assert json.loads(result["body"])["code"] == "BATCH_NOT_FOUND"

    def test_image_urls_use_cloudfront_base(self, ddb_tables):
        event = {"queryStringParameters": None}
        result = handler(event, {})
        for variety in json.loads(result["body"])["varieties"]:
            assert variety["imageUrl"].startswith("https://assets.example.com")

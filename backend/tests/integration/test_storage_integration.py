"""T006b / T006c / T011b: Real-AWS integration tests for storage layer (US2, US3).

Tests run against a real deployed AWS environment. All tests are guarded
behind the AWS_INTEGRATION env var and will skip if it is not set.

Requires:
  AWS_INTEGRATION=1
  AWS_REGION (default: us-east-1)
  DYNAMODB_VARIETIES_TABLE
  DYNAMODB_BATCHES_TABLE
  DYNAMODB_REQUESTS_TABLE
  CLOUDFRONT_ASSETS_BASE_URL (for US3 test)
"""
import os
import uuid
import pytest
import boto3

from src.handlers.list_varieties import handler as list_varieties_handler
from src.handlers.create_request import handler as create_request_handler
from src.handlers.get_request import handler as get_request_handler


def _skip_if_no_integration():
    if not os.environ.get("AWS_INTEGRATION"):
        pytest.skip("AWS_INTEGRATION env var not set — skipping real AWS test")


@pytest.fixture(scope="module", autouse=True)
def require_integration():
    _skip_if_no_integration()


@pytest.fixture(scope="module")
def region():
    return os.environ.get("AWS_REGION", "us-east-1")


@pytest.fixture(scope="module")
def dynamodb(region):
    return boto3.resource("dynamodb", region_name=region)


@pytest.fixture(scope="module")
def varieties_table(dynamodb):
    return dynamodb.Table(os.environ["DYNAMODB_VARIETIES_TABLE"])


@pytest.fixture(scope="module")
def batches_table(dynamodb):
    return dynamodb.Table(os.environ["DYNAMODB_BATCHES_TABLE"])


@pytest.fixture(scope="module")
def requests_table(dynamodb):
    return dynamodb.Table(os.environ["DYNAMODB_REQUESTS_TABLE"])


# ---------------------------------------------------------------------------
# T006b: US2 — varieties read path
# ---------------------------------------------------------------------------

class TestVarietiesReadPath:
    """T006b: Seed one Variety and one Batch, call list_varieties handler, verify imageUrl."""

    def test_list_varieties_returns_200_with_image_url(self, varieties_table, batches_table):
        variety_id = f"integration-test-{uuid.uuid4().hex[:8]}"
        batch_id = f"integration-batch-{uuid.uuid4().hex[:8]}"
        try:
            varieties_table.put_item(Item={
                "varietyId": variety_id,
                "name": "Integration Test Variety",
                "description": "A variety seeded by integration tests",
                "imageKey": "assets/integration-test.jpg",
                "bottleYieldMl": 750,
                "active": True,
                "ingredients": [],
            })
            batches_table.put_item(Item={
                "batchId": batch_id,
                "batchName": "Integration Batch",
                "cutoffDate": "2026-01-01",
                "maxBottleVolumeMl": 1000,
                "availableVarietyIds": [variety_id],
                "status": "OPEN",
                "createdAt": "2026-04-05T00:00:00Z",
                "acquiredIngredients": {},
            })

            result = list_varieties_handler({"queryStringParameters": None}, {})

            assert result["statusCode"] == 200
            varieties = result["body"]["varieties"]
            assert len(varieties) >= 1, "Expected at least one variety in response"

            # Find our seeded variety
            seeded = next((v for v in varieties if v["varietyId"] == variety_id), None)
            assert seeded is not None, f"Seeded variety {variety_id} not found in response"
            assert seeded["imageUrl"], "Expected non-empty imageUrl"
        finally:
            varieties_table.delete_item(Key={"varietyId": variety_id})
            batches_table.delete_item(Key={"batchId": batch_id})


# ---------------------------------------------------------------------------
# T006c: US2 — requests write→read path
# ---------------------------------------------------------------------------

class TestRequestsWriteReadPath:
    """T006c: Write a request via create_request handler, read it back via get_request handler."""

    def test_create_and_retrieve_request(self, varieties_table, batches_table, requests_table):
        variety_id = f"integration-variety-{uuid.uuid4().hex[:8]}"
        batch_id = f"integration-batch-{uuid.uuid4().hex[:8]}"
        idempotency_key = str(uuid.uuid4())
        created_request_id = None
        try:
            varieties_table.put_item(Item={
                "varietyId": variety_id,
                "name": "Integration Classic",
                "description": "Integration test variety for request flow",
                "imageKey": "assets/integration-classic.jpg",
                "bottleYieldMl": 750,
                "active": True,
                "ingredients": [],
            })
            batches_table.put_item(Item={
                "batchId": batch_id,
                "batchName": "Integration Request Batch",
                "cutoffDate": "2026-01-01",
                "maxBottleVolumeMl": 1000,
                "availableVarietyIds": [variety_id],
                "status": "OPEN",
                "createdAt": "2026-04-05T00:00:00Z",
                "acquiredIngredients": {},
            })

            import json
            payload = {
                "idempotencyKey": idempotency_key,
                "batchId": batch_id,
                "varietyId": variety_id,
                "requesterName": "Integration Tester",
                "requesterEmail": "integration@example.com",
                "pickupDate": "2026-12-20",
                "pickupTime": "14:00",
                "exchangeLocation": "Test Location",
                "bottleProvided": False,
                "costContribution": True,
            }
            create_event = {"body": json.dumps(payload)}
            create_result = create_request_handler(create_event, {})

            assert create_result["statusCode"] == 201, f"Expected 201, got {create_result}"
            created_request_id = create_result["body"]["requestId"]
            assert created_request_id, "Expected requestId in create response"

            # Read it back
            get_event = {"pathParameters": {"requestId": created_request_id}}
            get_result = get_request_handler(get_event, {})

            assert get_result["statusCode"] == 200, f"Expected 200, got {get_result}"
            body = get_result["body"]
            assert body["requestId"] == created_request_id
            assert body["requesterName"] == "Integration Tester"
            assert body["pickupDate"] == "2026-12-20"

        finally:
            varieties_table.delete_item(Key={"varietyId": variety_id})
            batches_table.delete_item(Key={"batchId": batch_id})
            if created_request_id:
                requests_table.delete_item(Key={"requestId": created_request_id})


# ---------------------------------------------------------------------------
# T011b: US3 — media asset URL resolution
# ---------------------------------------------------------------------------

class TestMediaAssetUrlResolution:
    """T011b: Verify list_varieties constructs imageUrl from CLOUDFRONT_ASSETS_BASE_URL."""

    def test_image_url_composed_correctly(self, varieties_table, monkeypatch):
        test_domain = "https://test-cdn.example.com"
        monkeypatch.setenv("CLOUDFRONT_ASSETS_BASE_URL", test_domain)

        variety_id = f"integration-asset-{uuid.uuid4().hex[:8]}"
        image_key = "assets/classic.jpg"
        try:
            varieties_table.put_item(Item={
                "varietyId": variety_id,
                "name": "Asset Test Variety",
                "description": "Tests imageUrl construction",
                "imageKey": image_key,
                "bottleYieldMl": 750,
                "active": True,
                "ingredients": [],
            })

            result = list_varieties_handler({"queryStringParameters": None}, {})

            assert result["statusCode"] == 200
            varieties = result["body"]["varieties"]
            seeded = next((v for v in varieties if v["varietyId"] == variety_id), None)
            assert seeded is not None, f"Seeded variety {variety_id} not found in response"
            expected_url = f"{test_domain}/{image_key}"
            assert seeded["imageUrl"] == expected_url, (
                f"Expected imageUrl {expected_url!r}, got {seeded['imageUrl']!r}"
            )
        finally:
            varieties_table.delete_item(Key={"varietyId": variety_id})

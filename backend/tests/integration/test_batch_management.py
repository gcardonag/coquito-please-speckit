"""T022 / T033 / T046 / T047: Integration tests for chef batch management.

Tests:
  US1: Chef lists batches with correct activeRequestCount; non-chef gets 403
  US2: Chef creates batch → appears in list as OPEN with correct fields; duplicate name → 400
  T046: Full flow — create → list → update → OPEN→CLOSED → CLOSED→COMPLETED → read-only
  T047: authorized-user gets 403 on all five chef-only endpoints; /me returns correct role
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
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")


@pytest.fixture
def tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        batches = ddb.create_table(
            TableName="coquito-batches",
            KeySchema=[{"AttributeName": "batchId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "batchId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        requests = ddb.create_table(
            TableName="coquito-requests",
            KeySchema=[{"AttributeName": "requestId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "requestId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        varieties = ddb.create_table(
            TableName="coquito-varieties",
            KeySchema=[{"AttributeName": "varietyId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "varietyId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        varieties.put_item(Item={"varietyId": "classic", "name": "Classic", "active": True})
        varieties.put_item(Item={"varietyId": "chocolate", "name": "Chocolate", "active": True})
        yield {"batches": batches, "requests": requests, "varieties": varieties}


def _chef_event(method: str = "GET", path: str = "/api/v1/batches",
                body: dict | None = None, path_params: dict | None = None) -> dict:
    return {
        "version": "2.0",
        "pathParameters": path_params or {},
        "requestContext": {
            "http": {"method": method, "path": path},
            "authorizer": {"lambda": {"userId": "u-chef", "role": "chef", "email": "chef@example.com"}},
        },
        "body": json.dumps(body) if body else None,
        "headers": {},
    }


def _user_event(method: str = "GET", path: str = "/api/v1/batches",
                body: dict | None = None, path_params: dict | None = None) -> dict:
    return {
        "version": "2.0",
        "pathParameters": path_params or {},
        "requestContext": {
            "http": {"method": method, "path": path},
            "authorizer": {"lambda": {"userId": "u-user", "role": "authorized-user", "email": "user@example.com"}},
        },
        "body": json.dumps(body) if body else None,
        "headers": {},
    }


# ---------------------------------------------------------------------------
# US1: View all batches (T022)
# ---------------------------------------------------------------------------
class TestUS1ViewBatches:
    def test_chef_receives_batch_list_with_correct_active_count(self, tables):
        from src.handlers.list_batches import handler as list_handler  # noqa: PLC0415

        tables["batches"].put_item(Item={
            "batchId": "b-001",
            "batchName": "Holiday 2026",
            "cutoffDate": "2030-11-15",
            "maxBottleVolumeMl": 1000,
            "availableVarietyIds": ["classic"],
            "status": "OPEN",
            "createdAt": "2026-05-01T00:00:00Z",
        })
        tables["requests"].put_item(Item={"requestId": "r-1", "batchId": "b-001", "status": "PENDING"})
        tables["requests"].put_item(Item={"requestId": "r-2", "batchId": "b-001", "status": "CANCELLED"})

        response = list_handler(_chef_event(), MagicMock())
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        batch = next(b for b in body["batches"] if b["batchId"] == "b-001")
        assert batch["activeRequestCount"] == 1

    def test_non_chef_receives_403_on_list(self, tables):
        from src.handlers.list_batches import handler as list_handler  # noqa: PLC0415
        response = list_handler(_user_event(), MagicMock())
        assert response["statusCode"] == 403


# ---------------------------------------------------------------------------
# US2: Create batch (T033)
# ---------------------------------------------------------------------------
class TestUS2CreateBatch:
    def test_chef_creates_batch_appears_in_list(self, tables):
        from src.handlers.create_batch import handler as create_handler  # noqa: PLC0415
        from src.handlers.list_batches import handler as list_handler  # noqa: PLC0415

        create_resp = create_handler(_chef_event("POST", "/api/v1/batches", {
            "batchName": "Test Batch",
            "cutoffDate": "2030-06-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["classic"],
        }), MagicMock())
        assert create_resp["statusCode"] == 201
        created = json.loads(create_resp["body"])
        assert created["status"] == "OPEN"

        list_resp = list_handler(_chef_event(), MagicMock())
        batches = json.loads(list_resp["body"])["batches"]
        assert any(b["batchId"] == created["batchId"] for b in batches)

    def test_duplicate_name_returns_400(self, tables):
        from src.handlers.create_batch import handler as create_handler  # noqa: PLC0415

        payload = {
            "batchName": "Duplicate Batch",
            "cutoffDate": "2030-06-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["classic"],
        }
        create_handler(_chef_event("POST", "/api/v1/batches", payload), MagicMock())
        response = create_handler(_chef_event("POST", "/api/v1/batches", payload), MagicMock())
        assert response["statusCode"] == 400
        assert json.loads(response["body"])["code"] == "BATCH_NAME_CONFLICT"

    def test_non_chef_returns_403_on_create(self, tables):
        from src.handlers.create_batch import handler as create_handler  # noqa: PLC0415
        response = create_handler(_user_event("POST", "/api/v1/batches", {
            "batchName": "X",
            "cutoffDate": "2030-06-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": ["classic"],
        }), MagicMock())
        assert response["statusCode"] == 403


# ---------------------------------------------------------------------------
# T046: Full flow
# ---------------------------------------------------------------------------
class TestFullFlow:
    def test_full_batch_lifecycle(self, tables):
        from src.handlers.create_batch import handler as create_handler  # noqa: PLC0415
        from src.handlers.list_batches import handler as list_handler  # noqa: PLC0415
        from src.handlers.update_batch import handler as update_handler  # noqa: PLC0415
        from src.handlers.update_batch_status import handler as status_handler  # noqa: PLC0415

        # Step 1: Create batch
        create_resp = create_handler(_chef_event("POST", body={
            "batchName": "Full Flow Batch",
            "cutoffDate": "2030-12-01",
            "maxBottleVolumeMl": 1000,
            "availableVarietyIds": ["classic", "chocolate"],
        }), MagicMock())
        assert create_resp["statusCode"] == 201
        batch = json.loads(create_resp["body"])
        batch_id = batch["batchId"]
        assert batch["status"] == "OPEN"

        # Step 2: Appears in list
        list_resp = list_handler(_chef_event(), MagicMock())
        assert any(b["batchId"] == batch_id for b in json.loads(list_resp["body"])["batches"])

        # Step 3: Update properties
        update_resp = update_handler(_chef_event("PUT", path_params={"id": batch_id}, body={
            "maxBottleVolumeMl": 750,
        }), MagicMock())
        assert update_resp["statusCode"] == 200
        assert json.loads(update_resp["body"])["maxBottleVolumeMl"] == 750

        # Step 4: OPEN → CLOSED
        close_resp = status_handler(_chef_event("PUT", path_params={"id": batch_id}, body={"status": "CLOSED"}), MagicMock())
        assert close_resp["statusCode"] == 200
        assert json.loads(close_resp["body"])["status"] == "CLOSED"

        # Step 5: CLOSED → COMPLETED
        complete_resp = status_handler(_chef_event("PUT", path_params={"id": batch_id}, body={"status": "COMPLETED"}), MagicMock())
        assert complete_resp["statusCode"] == 200
        assert json.loads(complete_resp["body"])["status"] == "COMPLETED"

        # Step 6: COMPLETED batch is read-only
        edit_resp = update_handler(_chef_event("PUT", path_params={"id": batch_id}, body={"batchName": "Changed"}), MagicMock())
        assert edit_resp["statusCode"] == 409
        assert json.loads(edit_resp["body"])["code"] == "BATCH_COMPLETED"


# ---------------------------------------------------------------------------
# T047: Non-chef blocked on all endpoints; /me returns correct role
# ---------------------------------------------------------------------------
class TestNonChefBlocked:
    def test_authorized_user_blocked_on_all_chef_endpoints(self, tables):
        from src.handlers.create_batch import handler as create_handler  # noqa: PLC0415
        from src.handlers.list_batches import handler as list_handler  # noqa: PLC0415
        from src.handlers.update_batch import handler as update_handler  # noqa: PLC0415
        from src.handlers.update_batch_status import handler as status_handler  # noqa: PLC0415
        from src.handlers.get_me import handler as me_handler  # noqa: PLC0415

        assert list_handler(_user_event(), MagicMock())["statusCode"] == 403
        assert create_handler(_user_event("POST", body={}), MagicMock())["statusCode"] == 403
        assert update_handler(_user_event("PUT", path_params={"id": "x"}, body={}), MagicMock())["statusCode"] == 403
        assert status_handler(_user_event("PUT", path_params={"id": "x"}, body={"status": "CLOSED"}), MagicMock())["statusCode"] == 403

    def test_get_me_returns_authorized_user_role(self, tables):
        from src.handlers.get_me import handler as me_handler  # noqa: PLC0415
        response = me_handler(_user_event(), MagicMock())
        assert response["statusCode"] == 200
        assert json.loads(response["body"])["role"] == "authorized-user"

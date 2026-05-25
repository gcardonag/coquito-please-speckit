"""Integration tests for batch user access management (feature 006).

Covers US1–US4 acceptance scenarios end-to-end using moto-mocked AWS services.
"""
import json
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_TestPool")
    monkeypatch.setenv("DYNAMODB_BATCH_ACCESS_TABLE", "coquito-batch-access")
    monkeypatch.setenv("DYNAMODB_BATCHES_TABLE", "coquito-batches")
    monkeypatch.setenv("DYNAMODB_VARIETIES_TABLE", "coquito-varieties")
    monkeypatch.setenv("DYNAMODB_REQUESTS_TABLE", "coquito-requests")


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
        batches.put_item(Item={
            "batchId": "b-open",
            "batchName": "Holiday 2026",
            "status": "OPEN",
            "cutoffDate": "2026-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": [],
            "createdAt": "2026-01-01T00:00:00Z",
        })
        batches.put_item(Item={
            "batchId": "b-closed",
            "batchName": "Old Batch",
            "status": "CLOSED",
            "cutoffDate": "2025-12-01",
            "maxBottleVolumeMl": 750,
            "availableVarietyIds": [],
            "createdAt": "2025-01-01T00:00:00Z",
        })
        access_table = ddb.create_table(
            TableName="coquito-batch-access",
            KeySchema=[
                {"AttributeName": "batchId", "KeyType": "HASH"},
                {"AttributeName": "userId", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "batchId", "AttributeType": "S"},
                {"AttributeName": "userId", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield {"batches": batches, "access": access_table}


def _chef_event(batch_id="b-open", user_id="user-sub-001"):
    return {
        "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
        "pathParameters": {"id": batch_id, "userId": user_id},
        "queryStringParameters": None,
    }


_COGNITO_USER_ATTRS = [
    {"Name": "sub", "Value": "user-sub-001"},
    {"Name": "email", "Value": "jane@example.com"},
    {"Name": "given_name", "Value": "Jane"},
    {"Name": "family_name", "Value": "Doe"},
]


# ---------------------------------------------------------------------------
# US1: Search for existing user, grant access, verify in list
# ---------------------------------------------------------------------------
class TestUS1GrantExistingUserAccess:
    def test_search_returns_matching_user(self, tables):
        """Chef searches by email prefix and gets results."""
        from src.handlers.chef_search_users import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "queryStringParameters": {"query": "jane"},
        }
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.list_users.side_effect = [
                {"Users": [{
                    "Username": "jane@example.com",
                    "Attributes": _COGNITO_USER_ATTRS,
                }]},
                {"Users": []},
            ]
            result = handler(event, MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body["users"]) == 1
        assert body["users"][0]["userId"] == "user-sub-001"
        assert body["users"][0]["email"] == "jane@example.com"

    def test_grant_access_to_open_batch(self, tables):
        """Chef grants access; handler returns 200 with grant record."""
        from src.handlers.chef_grant_batch_access import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.admin_get_user.return_value = {"UserAttributes": _COGNITO_USER_ATTRS}
            result = handler(_chef_event("b-open", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["batchId"] == "b-open"
        assert body["userId"] == "user-sub-001"
        assert "grantedAt" in body

    def test_granted_user_appears_in_access_list(self, tables):
        """After granting access, the user appears in the list endpoint."""
        from src.handlers.chef_grant_batch_access import handler as grant  # noqa: PLC0415
        from src.handlers.chef_list_batch_access import handler as list_access  # noqa: PLC0415

        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.admin_get_user.return_value = {"UserAttributes": _COGNITO_USER_ATTRS}
            grant(_chef_event("b-open", "user-sub-001"), MagicMock())

        list_event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "pathParameters": {"id": "b-open"},
        }
        result = list_access(list_event, MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["batchId"] == "b-open"
        assert len(body["users"]) == 1
        u = body["users"][0]
        assert u["userId"] == "user-sub-001"
        assert u["email"] == "jane@example.com"
        assert u["firstName"] == "Jane"
        assert u["lastName"] == "Doe"

    def test_grant_to_closed_batch_returns_403(self, tables):
        """Granting to a CLOSED batch is forbidden."""
        from src.handlers.chef_grant_batch_access import handler  # noqa: PLC0415
        with patch("boto3.client") as mock_client:
            mock_client.return_value = MagicMock()
            result = handler(_chef_event("b-closed", "user-sub-001"), MagicMock())
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "FORBIDDEN"

    def test_list_access_empty_for_batch_with_no_grants(self, tables):
        """Access list is empty for a batch with no grants."""
        from src.handlers.chef_list_batch_access import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "pathParameters": {"id": "b-open"},
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 200
        assert json.loads(result["body"])["users"] == []


# ---------------------------------------------------------------------------
# US2: Create a new user and auto-grant access
# ---------------------------------------------------------------------------
class TestUS2CreateUserAndGrantAccess:
    def test_create_user_with_first_name_succeeds(self, tables):
        """Chef creates a user with firstName; returns 201."""
        from src.handlers.create_user import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "body": json.dumps({"email": "new@example.com", "firstName": "Alice", "lastName": "Smith"}),
        }
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.admin_create_user.return_value = {
                "User": {"Attributes": [
                    {"Name": "sub", "Value": "new-sub-001"},
                    {"Name": "email", "Value": "new@example.com"},
                ]}
            }
            mock_cognito.admin_add_user_to_group.return_value = {}
            result = handler(event, MagicMock())
        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["userId"] == "new-sub-001"
        assert body["email"] == "new@example.com"

    def test_create_user_without_first_name_returns_400(self, tables):
        """Missing firstName returns 400 VALIDATION_ERROR."""
        from src.handlers.create_user import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "body": json.dumps({"email": "noname@example.com"}),
        }
        with patch("boto3.client"):
            result = handler(event, MagicMock())
        assert result["statusCode"] == 400
        assert json.loads(result["body"])["code"] == "VALIDATION_ERROR"

    def test_duplicate_email_returns_409(self, tables):
        """Duplicate email returns 409 USER_EXISTS."""
        from src.handlers.create_user import handler  # noqa: PLC0415
        from botocore.exceptions import ClientError  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "body": json.dumps({"email": "dup@example.com", "firstName": "Bob"}),
        }
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            exc = ClientError(
                {"Error": {"Code": "UsernameExistsException", "Message": "User already exists."}},
                "AdminCreateUser",
            )
            mock_cognito.admin_create_user.side_effect = exc
            result = handler(event, MagicMock())
        assert result["statusCode"] == 409
        assert json.loads(result["body"])["code"] == "USER_EXISTS"

    def test_last_name_is_optional(self, tables):
        """Creating a user without lastName succeeds."""
        from src.handlers.create_user import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "body": json.dumps({"email": "nolast@example.com", "firstName": "Charlie"}),
        }
        with patch("boto3.client") as mock_client:
            mock_cognito = MagicMock()
            mock_client.return_value = mock_cognito
            mock_cognito.admin_create_user.return_value = {
                "User": {"Attributes": [
                    {"Name": "sub", "Value": "sub-no-last"},
                    {"Name": "email", "Value": "nolast@example.com"},
                ]}
            }
            mock_cognito.admin_add_user_to_group.return_value = {}
            result = handler(event, MagicMock())
        assert result["statusCode"] == 201


# ---------------------------------------------------------------------------
# US3: View all users with batch access (including empty state)
# ---------------------------------------------------------------------------
class TestUS3ViewBatchAccessList:
    def test_list_returns_all_granted_users(self, tables):
        """List endpoint returns all users granted access to a batch."""
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        access_table = ddb.Table("coquito-batch-access")
        access_table.put_item(Item={
            "batchId": "b-open", "userId": "u-001", "email": "a@example.com",
            "firstName": "Alice", "lastName": "A", "grantedAt": "2026-05-01T00:00:00Z",
        })
        access_table.put_item(Item={
            "batchId": "b-open", "userId": "u-002", "email": "b@example.com",
            "firstName": "Bob", "lastName": "", "grantedAt": "2026-05-02T00:00:00Z",
        })

        from src.handlers.chef_list_batch_access import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "pathParameters": {"id": "b-open"},
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert len(body["users"]) == 2
        user_ids = {u["userId"] for u in body["users"]}
        assert "u-001" in user_ids
        assert "u-002" in user_ids

    def test_list_empty_for_batch_with_no_grants(self, tables):
        """Empty array is returned when no access grants exist."""
        from src.handlers.chef_list_batch_access import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "pathParameters": {"id": "b-open"},
        }
        result = handler(event, MagicMock())
        body = json.loads(result["body"])
        assert result["statusCode"] == 200
        assert body["users"] == []

    def test_list_access_works_for_closed_batch(self, tables):
        """GET access list is allowed on CLOSED batches (read-only, no state change)."""
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.Table("coquito-batch-access").put_item(Item={
            "batchId": "b-closed", "userId": "u-001", "email": "a@example.com",
            "firstName": "Alice", "lastName": "", "grantedAt": "2025-12-01T00:00:00Z",
        })
        from src.handlers.chef_list_batch_access import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "pathParameters": {"id": "b-closed"},
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 200
        assert len(json.loads(result["body"])["users"]) == 1


# ---------------------------------------------------------------------------
# US4: Revoke a user's batch access
# ---------------------------------------------------------------------------
class TestUS4RevokeAccess:
    @pytest.fixture(autouse=True)
    def pre_grant(self, tables):
        """Seed an access grant for revoke tests."""
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.Table("coquito-batch-access").put_item(Item={
            "batchId": "b-open", "userId": "user-sub-001", "email": "jane@example.com",
            "firstName": "Jane", "lastName": "Doe", "grantedAt": "2026-05-23T18:00:00Z",
        })

    def test_revoke_removes_user_from_list(self, tables):
        """Revoking access removes the user from the batch access list."""
        from src.handlers.chef_revoke_batch_access import handler as revoke  # noqa: PLC0415
        from src.handlers.chef_list_batch_access import handler as list_access  # noqa: PLC0415

        revoke_event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "pathParameters": {"id": "b-open", "userId": "user-sub-001"},
        }
        result = revoke(revoke_event, MagicMock())
        assert result["statusCode"] == 204

        list_event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "pathParameters": {"id": "b-open"},
        }
        list_result = list_access(list_event, MagicMock())
        body = json.loads(list_result["body"])
        assert len(body["users"]) == 0

    def test_revoke_on_closed_batch_returns_403(self, tables):
        """Revoking on a CLOSED batch returns 403."""
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.Table("coquito-batch-access").put_item(Item={
            "batchId": "b-closed", "userId": "user-sub-001", "email": "jane@example.com",
            "firstName": "Jane", "lastName": "Doe", "grantedAt": "2025-12-01T00:00:00Z",
        })
        from src.handlers.chef_revoke_batch_access import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "pathParameters": {"id": "b-closed", "userId": "user-sub-001"},
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 403
        assert json.loads(result["body"])["code"] == "FORBIDDEN"

    def test_revoke_nonexistent_grant_returns_404(self, tables):
        """Revoking an access grant that does not exist returns 404."""
        from src.handlers.chef_revoke_batch_access import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "chef"}}},
            "pathParameters": {"id": "b-open", "userId": "no-such-user"},
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 404
        assert json.loads(result["body"])["code"] == "NOT_FOUND"

    def test_non_chef_revoke_returns_403(self, tables):
        """Non-chef caller is rejected with 403."""
        from src.handlers.chef_revoke_batch_access import handler  # noqa: PLC0415
        event = {
            "requestContext": {"authorizer": {"lambda": {"role": "authorized-user"}}},
            "pathParameters": {"id": "b-open", "userId": "user-sub-001"},
        }
        result = handler(event, MagicMock())
        assert result["statusCode"] == 403

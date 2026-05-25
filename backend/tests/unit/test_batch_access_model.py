"""Unit tests (RED → GREEN) for BatchAccessGrant.to_dict and from_dict."""
from src.models.batch_access import BatchAccessGrant


class TestBatchAccessGrantRoundTrip:
    def test_to_dict_contains_all_fields(self):
        grant = BatchAccessGrant(
            batch_id="b-001",
            user_id="user-sub-uuid",
            email="jane@example.com",
            first_name="Jane",
            last_name="Doe",
            granted_at="2026-05-23T18:00:00Z",
        )
        d = grant.to_dict()
        assert d["batchId"] == "b-001"
        assert d["userId"] == "user-sub-uuid"
        assert d["email"] == "jane@example.com"
        assert d["firstName"] == "Jane"
        assert d["lastName"] == "Doe"
        assert d["grantedAt"] == "2026-05-23T18:00:00Z"

    def test_from_dict_restores_all_fields(self):
        data = {
            "batchId": "b-001",
            "userId": "user-sub-uuid",
            "email": "jane@example.com",
            "firstName": "Jane",
            "lastName": "Doe",
            "grantedAt": "2026-05-23T18:00:00Z",
        }
        grant = BatchAccessGrant.from_dict(data)
        assert grant.batch_id == "b-001"
        assert grant.user_id == "user-sub-uuid"
        assert grant.email == "jane@example.com"
        assert grant.first_name == "Jane"
        assert grant.last_name == "Doe"
        assert grant.granted_at == "2026-05-23T18:00:00Z"

    def test_round_trip_preserves_optional_empty_last_name(self):
        grant = BatchAccessGrant(
            batch_id="b-002",
            user_id="u-002",
            email="bob@example.com",
            first_name="Bob",
            last_name="",
            granted_at="2026-05-23T00:00:00Z",
        )
        assert BatchAccessGrant.from_dict(grant.to_dict()).last_name == ""

    def test_to_dict_keys_are_camel_case(self):
        grant = BatchAccessGrant("b", "u", "e@e.com", "F", "L", "2026-01-01T00:00:00Z")
        keys = set(grant.to_dict().keys())
        assert keys == {"batchId", "userId", "email", "firstName", "lastName", "grantedAt"}

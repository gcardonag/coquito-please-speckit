"""Contract test: GET /health → 200 {"status":"ok","service":"coquito-api"}.

Invokes the Lambda handler directly (no network required).
RED step: must FAIL before health.py is implemented.
"""
import json
from unittest.mock import MagicMock


class TestHealthContract:
    def _invoke(self) -> dict:
        from src.handlers.health import handler  # noqa: PLC0415

        event = {
            "version": "2.0",
            "requestContext": {"http": {"method": "GET", "path": "/health"}},
            "headers": {},
        }
        return handler(event, MagicMock())

    def test_health_returns_200(self):
        response = self._invoke()
        assert response["statusCode"] == 200

    def test_health_body_has_status_ok(self):
        response = self._invoke()
        body = json.loads(response["body"])
        assert body["status"] == "ok"

    def test_health_body_has_service_name(self):
        response = self._invoke()
        body = json.loads(response["body"])
        assert body["service"] == "coquito-api"

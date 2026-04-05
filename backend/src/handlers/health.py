"""Health check handler: GET /health → {"status":"ok","service":"coquito-api"}."""
import json
from typing import Any

from aws_lambda_powertools import Logger

logger = Logger(service="coquito-health")


@logger.inject_lambda_context(log_event=False)
def handler(event: dict, context: Any) -> dict:  # noqa: ANN401
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok", "service": "coquito-api"}),
    }

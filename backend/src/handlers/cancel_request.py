"""cancel_request — DELETE /api/v1/requests/{requestId}"""
from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
import json

from aws_lambda_powertools import Logger

from src.models.batch import Batch
from src.models.request import Request
from src.services.dynamodb import (
    ItemNotFoundError,
    get_item,
    put_item,
    batches_table_name,
    requests_table_name,
)
from src.services import scheduler as scheduler_svc


logger = Logger(service="coquito-cancel-request")


def _today() -> date:
    return date.today()


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    authorizer_ctx = (event.get("requestContext") or {}).get("authorizer", {}).get("lambda", {})
    role = authorizer_ctx.get("role", "")
    caller_id = authorizer_ctx.get("userId", "")
    endpoint = (event.get("requestContext") or {}).get("http", {}).get("path", "POST /api/v1/requests/{id}/cancel")

    request_id: str = (event.get("pathParameters") or {}).get("id", "")

    try:
        req_item = get_item(requests_table_name(), {"requestId": request_id})
    except ItemNotFoundError:
        return _response(404, {"code": "REQUEST_NOT_FOUND", "message": f"Request '{request_id}' not found"})

    req = Request.from_dict(req_item)

    # Ownership check: authorized-user may only cancel their own requests; chef has full access
    if role == "authorized-user" and req.requester_id and req.requester_id != caller_id:
        logger.warning("UNAUTHORIZED_ROLE", extra={"error": "UNAUTHORIZED_ROLE", "endpoint": endpoint})
        return _response(403, {"code": "FORBIDDEN", "message": "Access denied"})

    # Idempotent — already cancelled
    if req.status == "CANCELLED":
        cancelled_at = req.updated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return _response(200, {"requestId": req.request_id, "status": "CANCELLED", "cancelledAt": cancelled_at})

    # Load batch for cutoff check
    try:
        batch_item = get_item(batches_table_name(), {"batchId": req.batch_id})
        batch = Batch.from_dict(batch_item)
    except ItemNotFoundError:
        return _response(404, {"code": "BATCH_NOT_FOUND", "message": "Batch not found"})

    if batch.is_cutoff_passed(_today()):
        return _response(403, {
            "code": "CUTOFF_PASSED",
            "message": "The order cut-off date has passed. Cancellations are no longer permitted.",
        })

    # Cancel EventBridge schedules for SCHEDULED reminders
    for reminder in req.reminders:
        if reminder.status == "SCHEDULED":
            # Derive schedule name from request ID and approximate days
            for days in ("7d", "1d"):
                try:
                    scheduler_svc.delete_schedule(f"coquito-reminder-{request_id}-{days}")
                except Exception:
                    pass
            reminder.status = "CANCELLED"

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    req.status = "CANCELLED"
    req.updated_at = now

    item = req.to_dict()
    item["idempotencyKey"] = req_item.get("idempotencyKey", "")
    put_item(requests_table_name(), item)

    return _response(200, {"requestId": req.request_id, "status": "CANCELLED", "cancelledAt": now})

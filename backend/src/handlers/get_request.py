"""get_request — GET /api/v1/requests/{requestId}"""
from __future__ import annotations

from datetime import date
from typing import Any

from aws_lambda_powertools import Logger

from src.models.batch import Batch
from src.models.request import Request
from src.models.variety import Variety
from src.services.dynamodb import (
    ItemNotFoundError,
    get_item,
    batches_table_name,
    requests_table_name,
    varieties_table_name,
)


logger = Logger(service="coquito-get-request")


def _today() -> date:
    return date.today()


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": body}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    authorizer_ctx = (event.get("requestContext") or {}).get("authorizer", {}).get("lambda", {})
    role = authorizer_ctx.get("role", "")
    caller_id = authorizer_ctx.get("userId", "")
    endpoint = (event.get("requestContext") or {}).get("http", {}).get("path", "GET /api/v1/requests/{id}")

    request_id: str = (event.get("pathParameters") or {}).get("requestId", "")

    try:
        req_item = get_item(requests_table_name(), {"requestId": request_id})
    except ItemNotFoundError:
        return _response(404, {"code": "REQUEST_NOT_FOUND", "message": f"Request '{request_id}' not found"})

    req = Request.from_dict(req_item)

    # Ownership check: authorized-user may only view their own requests; chef has full access
    if role == "authorized-user" and req.requester_id and req.requester_id != caller_id:
        logger.warning("UNAUTHORIZED_ROLE", extra={"error": "UNAUTHORIZED_ROLE", "endpoint": endpoint})
        return _response(403, {"code": "FORBIDDEN", "message": "Access denied"})

    try:
        batch_item = get_item(batches_table_name(), {"batchId": req.batch_id})
        batch = Batch.from_dict(batch_item)
    except ItemNotFoundError:
        batch = None

    editable = (batch is not None) and (not batch.is_cutoff_passed(_today()))

    # Resolve variety name
    variety_name = req.variety_id
    try:
        variety_item = get_item(varieties_table_name(), {"varietyId": req.variety_id})
        variety = Variety.from_dict(variety_item)
        variety_name = variety.name
    except ItemNotFoundError:
        pass

    body: dict[str, Any] = {
        **req.to_dict(),
        "variety": {"varietyId": req.variety_id, "name": variety_name},
        "editable": editable,
    }
    if batch:
        body["batch"] = {
            "batchId": batch.batch_id,
            "batchName": batch.batch_name,
            "cutoffDate": batch.cutoff_date,
            "maxBottleVolumeMl": batch.max_bottle_volume_ml,
        }

    return _response(200, body)

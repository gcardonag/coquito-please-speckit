"""create_request — POST /api/v1/requests

Creates a new coquito request. Idempotent on idempotencyKey.
Schedules two EventBridge reminders (7 days and 1 day before pickup).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, date, timedelta
from typing import Any

from src.models.batch import Batch
from src.models.request import Request, Reminder
from src.models.variety import Variety
from src.services.dynamodb import (
    ConflictError,
    ItemNotFoundError,
    get_item,
    put_item,
    scan_table,
    batches_table_name,
    varieties_table_name,
    requests_table_name,
)
from src.services import scheduler as scheduler_svc


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": body}


def _schedule_reminders(
    request_id: str,
    pickup_date_str: str,
    variety_name: str,
) -> list[Reminder]:
    """Create two EventBridge schedules and return Reminder objects."""
    target_arn = os.environ.get("SEND_REMINDER_LAMBDA_ARN", "")
    pickup = date.fromisoformat(pickup_date_str)
    reminders: list[Reminder] = []

    for days_before in (7, 1):
        fire_date = pickup - timedelta(days=days_before)
        fire_dt = datetime(fire_date.year, fire_date.month, fire_date.day, 10, 0, 0)
        reminder_id = str(uuid.uuid4())
        schedule_name = f"coquito-reminder-{request_id}-{days_before}d"
        payload = {"requestId": request_id, "reminderId": reminder_id, "daysUntil": days_before}
        try:
            arn = scheduler_svc.create_one_time_schedule(
                name=schedule_name,
                schedule_at=fire_dt,
                target_arn=target_arn,
                input_payload=payload,
            )
        except Exception:
            arn = ""  # best-effort — do not fail the request creation
        reminders.append(Reminder(
            reminder_id=reminder_id,
            scheduled_for=fire_dt.isoformat() + "Z",
            scheduler_arn=arn,
            status="SCHEDULED",
        ))
    return reminders


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for POST /api/v1/requests."""
    try:
        body: dict[str, Any] = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"code": "VALIDATION_ERROR", "message": "Invalid JSON body"})

    idempotency_key = body.get("idempotencyKey", "")
    batch_id = body.get("batchId", "")
    variety_id = body.get("varietyId", "")

    # Look up batch
    try:
        batch_item = get_item(batches_table_name(), {"batchId": batch_id})
    except ItemNotFoundError:
        return _response(404, {"code": "BATCH_NOT_FOUND", "message": f"Batch '{batch_id}' not found"})

    batch = Batch.from_dict(batch_item)

    # Validate input against batch constraints
    errors = Request.validate(
        data=body,
        max_bottle_volume_ml=batch.max_bottle_volume_ml,
        cutoff_date=batch.cutoff_date,
    )

    # Provide specific error codes for known violation types
    pickup_date = body.get("pickupDate", "")
    if pickup_date and pickup_date <= batch.cutoff_date:
        return _response(400, {
            "code": "BATCH_CLOSED",
            "message": f"Ordering is closed. Pickup date must be after {batch.cutoff_date}.",
        })

    bottle_provided = body.get("bottleProvided", False)
    bottle_volume = body.get("bottleVolumeMl")
    if bottle_provided and bottle_volume is not None:
        if int(bottle_volume) > batch.max_bottle_volume_ml:
            return _response(400, {
                "code": "BOTTLE_VOLUME_EXCEEDED",
                "message": f"Bottle volume {bottle_volume}ml exceeds maximum {batch.max_bottle_volume_ml}ml.",
            })

    if errors:
        return _response(400, {"code": "VALIDATION_ERROR", "message": "; ".join(errors)})

    # Validate variety exists and is active
    try:
        variety_item = get_item(varieties_table_name(), {"varietyId": variety_id})
        variety = Variety.from_dict(variety_item)
        if not variety.active:
            return _response(404, {"code": "VARIETY_NOT_FOUND", "message": f"Variety '{variety_id}' is not available"})
    except ItemNotFoundError:
        return _response(404, {"code": "VARIETY_NOT_FOUND", "message": f"Variety '{variety_id}' not found"})

    # Idempotency: check if a request with this key already exists
    # We store idempotency key as an attribute; scan is acceptable at this scale
    existing = scan_table(
        requests_table_name(),
        filter_expression="idempotencyKey = :key" if False else None,  # handled below
    )
    for item in existing:
        if item.get("idempotencyKey") == idempotency_key:
            # Return the existing request
            req = Request.from_dict(item)
            return _response(201, _build_response_body(req, variety, batch))

    # Create new request
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    request_id = str(uuid.uuid4())

    reminders = _schedule_reminders(request_id, body["pickupDate"], variety.name)

    req = Request(
        request_id=request_id,
        requester_name=body["requesterName"],
        requester_email=body["requesterEmail"],
        batch_id=batch_id,
        variety_id=variety_id,
        pickup_date=body["pickupDate"],
        pickup_time=body["pickupTime"],
        exchange_location=body["exchangeLocation"],
        bottle_provided=bool(body.get("bottleProvided", False)),
        bottle_volume_ml=int(body["bottleVolumeMl"]) if body.get("bottleVolumeMl") else None,
        cost_contribution=bool(body.get("costContribution", False)),
        status="CONFIRMED",
        reminders=reminders,
        created_at=now,
        updated_at=now,
    )

    item = req.to_dict()
    item["idempotencyKey"] = idempotency_key
    put_item(requests_table_name(), item)

    return _response(201, _build_response_body(req, variety, batch))


def _build_response_body(
    req: Request,
    variety: Variety,
    batch: Batch,
) -> dict[str, Any]:
    return {
        "requestId": req.request_id,
        "status": req.status,
        "requesterName": req.requester_name,
        "variety": {"varietyId": variety.variety_id, "name": variety.name},
        "pickupDate": req.pickup_date,
        "pickupTime": req.pickup_time,
        "exchangeLocation": req.exchange_location,
        "bottleProvided": req.bottle_provided,
        "bottleVolumeMl": req.bottle_volume_ml,
        "costContribution": req.cost_contribution,
        "reminders": [r.to_dict() for r in req.reminders],
        "createdAt": req.created_at,
    }

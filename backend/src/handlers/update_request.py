"""update_request — PUT /api/v1/requests/{requestId}"""
from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import Any

from src.models.batch import Batch
from src.models.request import Request, Reminder
from src.models.variety import Variety
from src.services.dynamodb import (
    ItemNotFoundError,
    get_item,
    put_item,
    batches_table_name,
    requests_table_name,
    varieties_table_name,
)
from src.services import scheduler as scheduler_svc
from src.handlers.create_request import _schedule_reminders


def _today() -> date:
    return date.today()


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": body}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    role = (event.get("requestContext") or {}).get("authorizer", {}).get("lambda", {}).get("role", "")
    if role != "chef":
        return _response(403, {"code": "FORBIDDEN", "message": "Chef access required"})

    request_id: str = (event.get("pathParameters") or {}).get("requestId", "")

    try:
        body: dict[str, Any] = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"code": "VALIDATION_ERROR", "message": "Invalid JSON body"})

    # Load request
    try:
        req_item = get_item(requests_table_name(), {"requestId": request_id})
    except ItemNotFoundError:
        return _response(404, {"code": "REQUEST_NOT_FOUND", "message": f"Request '{request_id}' not found"})

    req = Request.from_dict(req_item)

    if req.status == "CANCELLED":
        return _response(409, {"code": "REQUEST_CANCELLED", "message": "Cannot update a cancelled request"})

    # Load batch for cutoff check
    try:
        batch_item = get_item(batches_table_name(), {"batchId": req.batch_id})
        batch = Batch.from_dict(batch_item)
    except ItemNotFoundError:
        return _response(404, {"code": "BATCH_NOT_FOUND", "message": "Batch not found"})

    if batch.is_cutoff_passed(_today()):
        return _response(403, {"code": "CUTOFF_PASSED", "message": "The order cut-off date has passed. Changes are no longer permitted."})

    # Apply updates
    new_bottle_provided = body.get("bottleProvided", req.bottle_provided)
    new_bottle_volume = body.get("bottleVolumeMl", req.bottle_volume_ml)

    if new_bottle_provided and new_bottle_volume is not None:
        if int(new_bottle_volume) > batch.max_bottle_volume_ml:
            return _response(400, {
                "code": "BOTTLE_VOLUME_EXCEEDED",
                "message": f"Bottle volume {new_bottle_volume}ml exceeds maximum {batch.max_bottle_volume_ml}ml.",
            })

    pickup_date_changed = "pickupDate" in body and body["pickupDate"] != req.pickup_date

    # Cancel old reminders if date changed
    if pickup_date_changed:
        for reminder in req.reminders:
            if reminder.status == "SCHEDULED":
                schedule_name = f"coquito-reminder-{req.request_id}-7d"  # derive name pattern
                try:
                    # Delete by name pattern (we stored ARNs; delete by derived name)
                    scheduler_svc.delete_schedule(f"coquito-reminder-{request_id}-7d")
                    scheduler_svc.delete_schedule(f"coquito-reminder-{request_id}-1d")
                except Exception:
                    pass
                break

    # Build updated request
    updated_variety_id = body.get("varietyId", req.variety_id)
    new_pickup_date = body.get("pickupDate", req.pickup_date)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Get variety name
    variety_name = updated_variety_id
    try:
        variety_item = get_item(varieties_table_name(), {"varietyId": updated_variety_id})
        variety = Variety.from_dict(variety_item)
        variety_name = variety.name
    except ItemNotFoundError:
        pass

    # Schedule new reminders if date changed
    new_reminders = req.reminders
    if pickup_date_changed:
        new_reminders = _schedule_reminders(request_id, new_pickup_date, variety_name)

    updated = Request(
        request_id=req.request_id,
        requester_name=body.get("requesterName", req.requester_name),
        requester_email=req.requester_email,
        batch_id=req.batch_id,
        variety_id=updated_variety_id,
        pickup_date=new_pickup_date,
        pickup_time=body.get("pickupTime", req.pickup_time),
        exchange_location=body.get("exchangeLocation", req.exchange_location),
        bottle_provided=new_bottle_provided,
        bottle_volume_ml=int(new_bottle_volume) if new_bottle_volume else None,
        cost_contribution=body.get("costContribution", req.cost_contribution),
        status=req.status,
        reminders=new_reminders,
        created_at=req.created_at,
        updated_at=now,
    )

    item = updated.to_dict()
    item["idempotencyKey"] = req_item.get("idempotencyKey", "")
    put_item(requests_table_name(), item)

    return _response(200, {
        **updated.to_dict(),
        "variety": {"varietyId": updated_variety_id, "name": variety_name},
        "editable": True,
        "batch": {
            "batchId": batch.batch_id,
            "batchName": batch.batch_name,
            "cutoffDate": batch.cutoff_date,
            "maxBottleVolumeMl": batch.max_bottle_volume_ml,
        },
    })

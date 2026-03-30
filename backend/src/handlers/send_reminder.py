"""send_reminder — invoked by EventBridge Scheduler

Payload: {"requestId": "...", "reminderId": "...", "daysUntil": 7}
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from src.models.request import Request
from src.services.dynamodb import ItemNotFoundError, get_item, put_item, requests_table_name
from src.services import ses as ses_svc

logger = logging.getLogger(__name__)


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    # EventBridge Scheduler delivers the payload as a dict directly
    if isinstance(event, str):
        event = json.loads(event)

    request_id: str = event.get("requestId", "")
    reminder_id: str = event.get("reminderId", "")
    days_until: int = int(event.get("daysUntil", 7))

    try:
        req_item = get_item(requests_table_name(), {"requestId": request_id})
    except ItemNotFoundError:
        logger.warning("send_reminder: request %s not found — skipping", request_id)
        return {}

    req = Request.from_dict(req_item)

    if req.status == "CANCELLED":
        logger.info("send_reminder: request %s is CANCELLED — skipping reminder", request_id)
        return {}

    # Build manage URL
    app_base_url = os.environ.get("APP_BASE_URL", "").rstrip("/")
    manage_url = f"{app_base_url}/#/manage/{request_id}"

    # Resolve variety name (use varietyId as fallback)
    variety_name = req.variety_id
    try:
        from src.services.dynamodb import get_item as _get, varieties_table_name
        from src.models.variety import Variety
        variety_item = _get(varieties_table_name(), {"varietyId": req.variety_id})
        variety_name = Variety.from_dict(variety_item).name
    except Exception:
        pass

    subject = ses_svc.reminder_subject(days_until, variety_name)
    body_html = ses_svc.reminder_body_html(
        requester_name=req.requester_name,
        variety_name=variety_name,
        pickup_date=req.pickup_date,
        pickup_time=req.pickup_time,
        exchange_location=req.exchange_location,
        manage_url=manage_url,
        days_until=days_until,
    )
    body_text = ses_svc.reminder_body_text(
        requester_name=req.requester_name,
        variety_name=variety_name,
        pickup_date=req.pickup_date,
        pickup_time=req.pickup_time,
        exchange_location=req.exchange_location,
        manage_url=manage_url,
        days_until=days_until,
    )

    ses_svc.send_email(
        to=req.requester_email,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
    )
    logger.info("send_reminder: sent reminder to %s for request %s", req.requester_email, request_id)

    # Mark this reminder as SENT
    for reminder in req.reminders:
        if reminder.reminder_id == reminder_id:
            reminder.status = "SENT"
            break

    put_item(requests_table_name(), req_item | {"reminders": [r.to_dict() for r in req.reminders]})
    return {}

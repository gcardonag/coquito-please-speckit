"""Request model — represents a single coquito order."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

RequestStatus = Literal["PENDING", "CONFIRMED", "CANCELLED"]
ReminderStatus = Literal["SCHEDULED", "SENT", "CANCELLED"]


@dataclass
class Reminder:
    reminder_id: str
    scheduled_for: str  # ISO 8601 datetime
    scheduler_arn: str
    status: ReminderStatus

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reminder":
        return cls(
            reminder_id=data["reminderId"],
            scheduled_for=data["scheduledFor"],
            scheduler_arn=data.get("schedulerArn", ""),
            status=data["status"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reminderId": self.reminder_id,
            "scheduledFor": self.scheduled_for,
            "schedulerArn": self.scheduler_arn,
            "status": self.status,
        }


@dataclass
class Request:
    request_id: str
    requester_name: str
    requester_email: str
    batch_id: str
    variety_id: str
    pickup_date: str           # YYYY-MM-DD
    pickup_time: str           # HH:MM
    exchange_location: str
    bottle_provided: bool
    cost_contribution: bool
    status: RequestStatus
    reminders: list[Reminder] = field(default_factory=list)
    bottle_volume_ml: int | None = None
    created_at: str = ""
    updated_at: str = ""
    requester_id: str = ""  # Cognito sub of the user who created this request

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Request":
        reminders = [Reminder.from_dict(r) for r in data.get("reminders", [])]
        volume = data.get("bottleVolumeMl")
        return cls(
            request_id=data["requestId"],
            requester_name=data["requesterName"],
            requester_email=data["requesterEmail"],
            batch_id=data["batchId"],
            variety_id=data["varietyId"],
            pickup_date=data["pickupDate"],
            pickup_time=data["pickupTime"],
            exchange_location=data["exchangeLocation"],
            bottle_provided=bool(data["bottleProvided"]),
            bottle_volume_ml=int(volume) if volume is not None else None,
            cost_contribution=bool(data["costContribution"]),
            status=data["status"],
            reminders=reminders,
            created_at=data.get("createdAt", ""),
            updated_at=data.get("updatedAt", ""),
            requester_id=data.get("requesterId", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "requestId": self.request_id,
            "requesterName": self.requester_name,
            "requesterEmail": self.requester_email,
            "batchId": self.batch_id,
            "varietyId": self.variety_id,
            "pickupDate": self.pickup_date,
            "pickupTime": self.pickup_time,
            "exchangeLocation": self.exchange_location,
            "bottleProvided": self.bottle_provided,
            "costContribution": self.cost_contribution,
            "status": self.status,
            "reminders": [r.to_dict() for r in self.reminders],
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.bottle_volume_ml is not None:
            result["bottleVolumeMl"] = self.bottle_volume_ml
        if self.requester_id:
            result["requesterId"] = self.requester_id
        return result

    @staticmethod
    def validate(
        data: dict[str, Any],
        max_bottle_volume_ml: int,
        cutoff_date: str,
    ) -> list[str]:
        """Return a list of validation error messages (empty = valid)."""
        errors: list[str] = []

        required = [
            "requesterName",
            "requesterEmail",
            "batchId",
            "varietyId",
            "pickupDate",
            "pickupTime",
            "exchangeLocation",
        ]
        for field_name in required:
            if not data.get(field_name, "").strip():
                errors.append(f"{field_name} is required")

        email = data.get("requesterEmail", "")
        if email and not EMAIL_RE.match(email):
            errors.append("requesterEmail must be a valid email address")

        if data.get("bottleProvided"):
            vol = data.get("bottleVolumeMl")
            if vol is None:
                errors.append("bottleVolumeMl is required when bottleProvided is true")
            elif int(vol) > max_bottle_volume_ml:
                errors.append(
                    f"bottleVolumeMl ({vol}) exceeds maximum allowed ({max_bottle_volume_ml})"
                )

        pickup_date = data.get("pickupDate", "")
        if pickup_date and pickup_date <= cutoff_date:
            errors.append(
                f"pickupDate ({pickup_date}) must be after the batch cutoff date ({cutoff_date})"
            )

        return errors

"""Batch model — represents a single cook production run."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

BatchStatus = Literal["OPEN", "CLOSED", "COMPLETED"]


@dataclass
class Batch:
    batch_id: str
    batch_name: str
    cutoff_date: str           # YYYY-MM-DD
    max_bottle_volume_ml: int
    available_variety_ids: list[str]
    status: BatchStatus
    created_at: str = ""
    # Sparse map of ingredientId -> acquired (stored on the batch item)
    acquired_ingredients: dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Batch":
        return cls(
            batch_id=data["batchId"],
            batch_name=data["batchName"],
            cutoff_date=data["cutoffDate"],
            max_bottle_volume_ml=int(data["maxBottleVolumeMl"]),
            available_variety_ids=list(data.get("availableVarietyIds", [])),
            status=data["status"],
            created_at=data.get("createdAt", ""),
            acquired_ingredients=dict(data.get("acquiredIngredients", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "batchId": self.batch_id,
            "batchName": self.batch_name,
            "cutoffDate": self.cutoff_date,
            "maxBottleVolumeMl": self.max_bottle_volume_ml,
            "availableVarietyIds": self.available_variety_ids,
            "status": self.status,
            "createdAt": self.created_at,
            "acquiredIngredients": self.acquired_ingredients,
        }

    def is_cutoff_passed(self, today: date | None = None) -> bool:
        """Return True if the cutoff date has passed (today is after cutoff)."""
        check = today or date.today()
        cutoff = date.fromisoformat(self.cutoff_date)
        return check > cutoff

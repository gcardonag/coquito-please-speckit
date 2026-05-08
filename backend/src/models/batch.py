"""Batch model — represents a single cook production run."""
from __future__ import annotations

import os
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

    @classmethod
    def name_exists(cls, batch_name: str, exclude_batch_id: str | None = None) -> bool:
        """Return True if a batch with this name (case-insensitive) already exists.

        Pass exclude_batch_id when editing a batch so its own name is not flagged.
        """
        from src.services.dynamodb import scan_table, batches_table_name  # noqa: PLC0415

        items = scan_table(batches_table_name())
        needle = batch_name.strip().lower()
        for item in items:
            if item.get("batchId") == exclude_batch_id:
                continue
            if item.get("batchName", "").strip().lower() == needle:
                return True
        return False

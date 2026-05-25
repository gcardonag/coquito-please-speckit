"""BatchAccessGrant model — a record granting a user access to a batch."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BatchAccessGrant:
    batch_id: str
    user_id: str       # Cognito sub (UUID)
    email: str
    first_name: str
    last_name: str     # may be empty string when not set
    granted_at: str    # ISO 8601 UTC

    def to_dict(self) -> dict[str, Any]:
        return {
            "batchId": self.batch_id,
            "userId": self.user_id,
            "email": self.email,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "grantedAt": self.granted_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchAccessGrant":
        return cls(
            batch_id=data["batchId"],
            user_id=data["userId"],
            email=data["email"],
            first_name=data["firstName"],
            last_name=data.get("lastName", ""),
            granted_at=data["grantedAt"],
        )

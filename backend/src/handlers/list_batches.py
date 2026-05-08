"""list_batches — GET /api/v1/batches

Returns all batches sorted by createdAt descending with activeRequestCount per batch.
Chef role required.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from aws_lambda_powertools import Logger

from src.handlers._auth import require_chef
from src.services.dynamodb import batches_table_name, requests_table_name, scan_table


logger = Logger(service="coquito-list-batches")


def _response(status_code: int, body: Any) -> dict[str, Any]:
    return {"statusCode": status_code, "body": json.dumps(body)}


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for GET /api/v1/batches."""
    denied = require_chef(event)
    if denied:
        return denied

    batches = scan_table(batches_table_name())

    # Compute activeRequestCount per batch (non-CANCELLED requests)
    requests = scan_table(requests_table_name())
    counts: dict[str, int] = defaultdict(int)
    for req in requests:
        if req.get("status") != "CANCELLED":
            counts[req.get("batchId", "")] += 1

    result = []
    for item in batches:
        batch_id = item.get("batchId", "")
        result.append({
            "batchId": batch_id,
            "batchName": item.get("batchName", ""),
            "cutoffDate": item.get("cutoffDate", ""),
            "maxBottleVolumeMl": int(item.get("maxBottleVolumeMl", 0)),
            "status": item.get("status", ""),
            "availableVarietyIds": list(item.get("availableVarietyIds", [])),
            "activeRequestCount": counts[batch_id],
            "createdAt": item.get("createdAt", ""),
        })

    result.sort(key=lambda b: b["createdAt"], reverse=True)
    logger.info("list_batches", extra={"count": len(result)})

    return _response(200, {"batches": result})

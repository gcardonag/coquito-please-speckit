"""close_expired_batches — EventBridge nightly trigger (cron 00:05 UTC)

Scans all OPEN batches and transitions any whose cutoffDate has passed
to CLOSED status. Does not enforce chef role — invoked by EventBridge.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from aws_lambda_powertools import Logger

from src.models.batch import Batch
from src.services.dynamodb import batches_table_name, scan_table, update_item


logger = Logger(service="coquito-close-expired-batches")


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler — close all OPEN batches past their cutoff date."""
    today = date.today()
    items = scan_table(batches_table_name())

    closed_count = 0
    for item in items:
        if item.get("status") != "OPEN":
            continue
        batch = Batch.from_dict(item)
        if not batch.is_cutoff_passed(today):
            continue

        update_item(
            batches_table_name(),
            key={"batchId": batch.batch_id},
            update_expression="SET #st = :closed",
            expression_attribute_values={":closed": "CLOSED", ":open": "OPEN"},
            expression_attribute_names={"#st": "status"},
            condition_expression="#st = :open",
        )
        logger.info("auto_closed_batch", extra={"batchId": batch.batch_id, "cutoffDate": batch.cutoff_date})
        closed_count += 1

    return {"statusCode": 200, "body": json.dumps({"closedCount": closed_count})}

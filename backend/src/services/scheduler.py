"""EventBridge Scheduler service — create and delete one-time schedules."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError


def _get_client() -> Any:
    return boto3.client(
        "scheduler", region_name=os.environ.get("AWS_REGION", "us-east-1")
    )


def create_one_time_schedule(
    name: str,
    schedule_at: datetime,
    target_arn: str,
    input_payload: dict[str, Any],
) -> str:
    """Create a one-time EventBridge Scheduler schedule.

    Args:
        name: Unique schedule name (alphanumeric + hyphens, max 64 chars).
        schedule_at: The UTC datetime when the schedule should fire.
        target_arn: The Lambda function ARN to invoke.
        input_payload: JSON-serialisable dict passed to the Lambda as the event.

    Returns:
        The ARN of the created schedule.

    Raises:
        ClientError: If the schedule could not be created.
    """
    role_arn = os.environ["SCHEDULER_ROLE_ARN"]
    client = _get_client()

    # Format: at(yyyy-mm-ddThh:mm:ss)  UTC
    at_expr = f"at({schedule_at.strftime('%Y-%m-%dT%H:%M:%S')})"

    response = client.create_schedule(
        Name=name,
        ScheduleExpression=at_expr,
        ScheduleExpressionTimezone="UTC",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": target_arn,
            "RoleArn": role_arn,
            "Input": json.dumps(input_payload),
        },
        ActionAfterCompletion="DELETE",
    )
    return response["ScheduleArn"]


def delete_schedule(name: str) -> None:
    """Delete a named EventBridge Scheduler schedule.

    Idempotent — does not raise if the schedule does not exist.
    """
    client = _get_client()
    try:
        client.delete_schedule(Name=name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            return  # already deleted — idempotent
        raise

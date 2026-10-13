"""DynamoDB service helper — thin wrappers around boto3."""
from __future__ import annotations

import os
from typing import Any

import boto3
from botocore.exceptions import ClientError


class ItemNotFoundError(Exception):
    """Raised when a requested item does not exist in DynamoDB."""


class ConflictError(Exception):
    """Raised when a conditional write fails due to a conflicting item."""


def _get_client() -> Any:
    return boto3.client("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def _get_resource() -> Any:
    return boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def get_table(table_name: str) -> Any:
    return _get_resource().Table(table_name)


# ---- Table name helpers ----

def requests_table_name() -> str:
    return os.environ["DYNAMODB_REQUESTS_TABLE"]


def batches_table_name() -> str:
    return os.environ["DYNAMODB_BATCHES_TABLE"]


def varieties_table_name() -> str:
    return os.environ["DYNAMODB_VARIETIES_TABLE"]


def batch_access_table_name() -> str:
    return os.environ["DYNAMODB_BATCH_ACCESS_TABLE"]


# ---- CRUD helpers ----

def get_item(table_name: str, key: dict[str, Any]) -> dict[str, Any]:
    """Fetch a single item by primary key. Raises ItemNotFoundError if missing."""
    table = get_table(table_name)
    response = table.get_item(Key=key)
    item = response.get("Item")
    if item is None:
        raise ItemNotFoundError(f"Item not found in {table_name}: {key}")
    return item


def put_item(table_name: str, item: dict[str, Any]) -> None:
    """Write an item unconditionally."""
    table = get_table(table_name)
    table.put_item(Item=item)


def put_item_if_not_exists(table_name: str, item: dict[str, Any], key_attr: str) -> None:
    """Write an item only if the primary key does not already exist.

    Raises ConflictError if the item already exists.
    """
    table = get_table(table_name)
    try:
        table.put_item(
            Item=item,
            ConditionExpression=f"attribute_not_exists({key_attr})",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ConflictError(f"Item already exists in {table_name}") from exc
        raise


def update_item(
    table_name: str,
    key: dict[str, Any],
    update_expression: str,
    expression_attribute_values: dict[str, Any],
    expression_attribute_names: dict[str, str] | None = None,
    condition_expression: str | None = None,
) -> dict[str, Any]:
    """Update an item and return the updated attributes."""
    table = get_table(table_name)
    kwargs: dict[str, Any] = {
        "Key": key,
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": expression_attribute_values,
        "ReturnValues": "ALL_NEW",
    }
    if expression_attribute_names:
        kwargs["ExpressionAttributeNames"] = expression_attribute_names
    if condition_expression:
        kwargs["ConditionExpression"] = condition_expression
    try:
        response = table.update_item(**kwargs)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise ConflictError("Conditional update failed") from exc
        raise
    return response.get("Attributes", {})


def query_by_partition_key(
    table_name: str,
    partition_key_name: str,
    partition_key_value: str,
) -> list[dict[str, Any]]:
    """Query all items with a given partition key value (no GSI, uses primary key)."""
    from boto3.dynamodb.conditions import Key  # noqa: PLC0415
    table = get_table(table_name)
    response = table.query(
        KeyConditionExpression=Key(partition_key_name).eq(partition_key_value),
    )
    return response.get("Items", [])


def delete_item(table_name: str, key: dict[str, Any]) -> None:
    """Delete an item by primary key."""
    table = get_table(table_name)
    table.delete_item(Key=key)


def query_by_index(
    table_name: str,
    index_name: str,
    key_condition_expression: Any,
    expression_attribute_values: dict[str, Any],
) -> list[dict[str, Any]]:
    """Query a GSI and return all matching items."""
    table = get_table(table_name)
    response = table.query(
        IndexName=index_name,
        KeyConditionExpression=key_condition_expression,
        ExpressionAttributeValues=expression_attribute_values,
    )
    return response.get("Items", [])


def scan_table(
    table_name: str,
    filter_expression: Any | None = None,
) -> list[dict[str, Any]]:
    """Full table scan. Use sparingly — only for small tables (varieties)."""
    table = get_table(table_name)
    kwargs: dict[str, Any] = {}
    if filter_expression:
        kwargs["FilterExpression"] = filter_expression
    response = table.scan(**kwargs)
    return response.get("Items", [])

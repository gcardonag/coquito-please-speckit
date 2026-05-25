"""create_user — POST /api/v1/users (Chef-only).

Provisions a new authorized-user account in Cognito with first and last name.
Only Chefs can invoke this endpoint (enforced by role check on authorizer context).

Returns: 201 {"userId": sub, "email": email}
"""
import json
import os
from typing import Any

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

logger = Logger(service="coquito-create-user")


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def handler(event: dict, context: Any) -> dict:  # noqa: ANN401
    role = (event.get("requestContext") or {}).get("authorizer", {}).get("lambda", {}).get("role", "")
    if role != "chef":
        return _response(403, {"code": "FORBIDDEN", "message": "Chef access required"})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"code": "VALIDATION_ERROR", "message": "Invalid JSON body"})

    email = (body.get("email") or "").strip()
    if not email or "@" not in email:
        return _response(400, {"code": "VALIDATION_ERROR", "message": "A valid email address is required"})

    first_name = (body.get("firstName") or "").strip()
    if not first_name:
        return _response(400, {"code": "VALIDATION_ERROR", "message": "First name is required"})

    last_name = (body.get("lastName") or "").strip()

    user_pool_id = os.environ["COGNITO_USER_POOL_ID"]
    cognito = boto3.client("cognito-idp")

    attrs = [
        {"Name": "email", "Value": email},
        {"Name": "email_verified", "Value": "true"},
        {"Name": "given_name", "Value": first_name},
    ]
    if last_name:
        attrs.append({"Name": "family_name", "Value": last_name})

    try:
        create_response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=attrs,
            MessageAction="SUPPRESS",
        )
        user_sub = next(
            (attr["Value"] for attr in create_response["User"]["Attributes"] if attr["Name"] == "sub"),
            email,
        )

        cognito.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=email,
            GroupName="authorized-user",
        )

        logger.info("Authorized user created", extra={"event": "USER_CREATED"})

        return _response(201, {"userId": user_sub, "email": email})

    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code == "UsernameExistsException":
            return _response(409, {"code": "USER_EXISTS", "message": "A user with that email already exists"})
        logger.error("Failed to create user", extra={"reason": str(exc)})
        return _response(503, {"code": "COGNITO_ERROR", "message": "Failed to create user"})
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to create user", extra={"reason": str(exc)})
        return _response(503, {"code": "COGNITO_ERROR", "message": "Failed to create user"})

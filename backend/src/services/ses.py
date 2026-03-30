"""SES email service — send reminder and confirmation emails."""
from __future__ import annotations

import os
from typing import Any

import boto3
from botocore.exceptions import ClientError


class EmailDeliveryError(Exception):
    """Raised when SES fails to send an email."""


def _get_client() -> Any:
    return boto3.client("ses", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: str,
) -> None:
    """Send an email via AWS SES.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body_html: HTML body content.
        body_text: Plain-text fallback body.

    Raises:
        EmailDeliveryError: If SES returns an error.
    """
    from_address = os.environ["SES_FROM_ADDRESS"]
    client = _get_client()
    try:
        client.send_email(
            Source=from_address,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": body_html, "Charset": "UTF-8"},
                    "Text": {"Data": body_text, "Charset": "UTF-8"},
                },
            },
        )
    except ClientError as exc:
        raise EmailDeliveryError(
            f"Failed to send email to {to}: {exc.response['Error']['Message']}"
        ) from exc


# ---- Reminder email templates ----

def reminder_subject(days_until: int, variety_name: str) -> str:
    """Build a friendly, culturally warm reminder subject line."""
    if days_until == 1:
        return f"¡Mañana es el día! Your {variety_name} coquito is almost here 🥥"
    return f"¡Recuerda! Your {variety_name} coquito is coming up in {days_until} days 🥥"


def reminder_body_html(
    requester_name: str,
    variety_name: str,
    pickup_date: str,
    pickup_time: str,
    exchange_location: str,
    manage_url: str,
    days_until: int,
) -> str:
    """Build the HTML body for a reminder email."""
    if days_until == 1:
        countdown = "¡Mañana es el día! Tomorrow is the day!"
    else:
        countdown = f"Just {days_until} days to go!"

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: Georgia, serif; background: #fdf6e3; color: #1a1a1a; padding: 24px;">
  <div style="max-width: 540px; margin: 0 auto; background: #fff; border-radius: 12px;
              border: 1px solid #d4b896; padding: 32px;">
    <h1 style="color: #5c3d1e; font-size: 1.8rem; margin-bottom: 8px;">🥥 Coquito Please!</h1>
    <p style="color: #4a4a4a; font-size: 1.1rem; margin-bottom: 24px;">
      <em>Hecho con amor y tradición Puertorriqueña.</em>
    </p>

    <p>Hola <strong>{requester_name}</strong>,</p>

    <p style="font-size: 1.1rem;">{countdown}</p>

    <div style="background: #fdf6e3; border-radius: 8px; padding: 16px; margin: 24px 0;">
      <h2 style="color: #3b2410; font-size: 1.2rem; margin-bottom: 12px;">Your Order</h2>
      <p><strong>Variety:</strong> {variety_name}</p>
      <p><strong>Date:</strong> {pickup_date} at {pickup_time}</p>
      <p><strong>Location:</strong> {exchange_location}</p>
    </div>

    <p>
      Need to make changes? You can still update or cancel your order before the cut-off date.
    </p>

    <a href="{manage_url}"
       style="display:inline-block; background:#5c3d1e; color:#fdf6e3;
              text-decoration:none; padding:12px 24px; border-radius:8px;
              font-size:1rem; font-weight:bold; margin-top:8px;">
      View My Order
    </a>

    <hr style="margin: 24px 0; border: none; border-top: 1px solid #d4b896;">
    <p style="font-size: 0.85rem; color: #777;">
      El coquito es más que una bebida — es un abrazo en cada sorbo. ¡Salud!
    </p>
  </div>
</body>
</html>"""


def reminder_body_text(
    requester_name: str,
    variety_name: str,
    pickup_date: str,
    pickup_time: str,
    exchange_location: str,
    manage_url: str,
    days_until: int,
) -> str:
    """Build the plain-text body for a reminder email."""
    return f"""Hola {requester_name},

Your {variety_name} coquito is coming up in {days_until} day(s)!

Order details:
- Variety: {variety_name}
- Date: {pickup_date} at {pickup_time}
- Location: {exchange_location}

Manage your order: {manage_url}

El coquito es más que una bebida — es un abrazo en cada sorbo. ¡Salud!
"""

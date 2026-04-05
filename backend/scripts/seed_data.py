"""Idempotent seed script for baseline DynamoDB test data.

Writes exactly 2 Variety records and 1 Batch record.
Safe to run multiple times — uses put_item_if_not_exists to avoid
overwriting existing records.

Usage:
    DYNAMODB_VARIETIES_TABLE=coquito-varieties-prod \\
    DYNAMODB_BATCHES_TABLE=coquito-batches-prod \\
    AWS_REGION=us-east-1 \\
    uv run python scripts/seed_data.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from src.services.dynamodb import ConflictError, put_item_if_not_exists


_VARIETIES = [
    {
        "varietyId": "classic",
        "name": "Classic Coquito",
        "description": "Traditional Puerto Rican coquito with coconut cream and white rum.",
        "imageKey": "assets/classic.jpg",
        "bottleYieldMl": 750,
        "active": True,
        "ingredients": [
            {
                "ingredientId": "coconut-cream",
                "name": "Coconut cream",
                "quantityPerBottle": 400,
                "unit": "ml",
                "category": "dairy",
            },
            {
                "ingredientId": "condensed-milk",
                "name": "Condensed milk",
                "quantityPerBottle": 200,
                "unit": "ml",
                "category": "dairy",
            },
            {
                "ingredientId": "white-rum",
                "name": "White rum",
                "quantityPerBottle": 150,
                "unit": "ml",
                "category": "spirit",
            },
        ],
    },
    {
        "varietyId": "chocolate",
        "name": "Chocolate Coquito",
        "description": "Decadent chocolate twist on the classic recipe.",
        "imageKey": "assets/chocolate.jpg",
        "bottleYieldMl": 750,
        "active": True,
        "ingredients": [
            {
                "ingredientId": "coconut-cream",
                "name": "Coconut cream",
                "quantityPerBottle": 400,
                "unit": "ml",
                "category": "dairy",
            },
            {
                "ingredientId": "condensed-milk",
                "name": "Condensed milk",
                "quantityPerBottle": 200,
                "unit": "ml",
                "category": "dairy",
            },
            {
                "ingredientId": "chocolate-syrup",
                "name": "Chocolate syrup",
                "quantityPerBottle": 50,
                "unit": "ml",
                "category": "flavoring",
            },
            {
                "ingredientId": "white-rum",
                "name": "White rum",
                "quantityPerBottle": 150,
                "unit": "ml",
                "category": "spirit",
            },
        ],
    },
]


def seed_varieties() -> None:
    """Write seed varieties. Skips silently if a record already exists."""
    import os
    table_name = os.environ["DYNAMODB_VARIETIES_TABLE"]
    for variety in _VARIETIES:
        try:
            put_item_if_not_exists(table_name, variety, "varietyId")
            print(f"  [OK] Seeded variety: {variety['varietyId']}")
        except ConflictError:
            print(f"  [SKIP] Variety already exists: {variety['varietyId']}")


def seed_batch() -> None:
    """Write seed batch. Skips silently if the record already exists."""
    import os
    table_name = os.environ["DYNAMODB_BATCHES_TABLE"]
    batch = {
        "batchId": "batch-test-2026",
        "batchName": "Test Batch 2026",
        "cutoffDate": "2026-01-01",
        "maxBottleVolumeMl": 1000,
        "availableVarietyIds": ["classic", "chocolate"],
        "status": "OPEN",
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "acquiredIngredients": {},
    }
    try:
        put_item_if_not_exists(table_name, batch, "batchId")
        print(f"  [OK] Seeded batch: {batch['batchId']}")
    except ConflictError:
        print(f"  [SKIP] Batch already exists: {batch['batchId']}")


if __name__ == "__main__":
    print("Seeding varieties...")
    seed_varieties()
    print("Seeding batch...")
    seed_batch()
    print("Done.")
    sys.exit(0)

"""Variety model — represents a coquito variety and its ingredient recipe."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Ingredient:
    ingredient_id: str
    name: str
    quantity_per_bottle: float
    unit: str
    category: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Ingredient":
        return cls(
            ingredient_id=data["ingredientId"],
            name=data["name"],
            quantity_per_bottle=float(data["quantityPerBottle"]),
            unit=data["unit"],
            category=data["category"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ingredientId": self.ingredient_id,
            "name": self.name,
            "quantityPerBottle": self.quantity_per_bottle,
            "unit": self.unit,
            "category": self.category,
        }


@dataclass
class Variety:
    variety_id: str
    name: str
    description: str
    image_key: str
    ingredients: list[Ingredient] = field(default_factory=list)
    bottle_yield_ml: int = 750
    active: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Variety":
        ingredients = [Ingredient.from_dict(i) for i in data.get("ingredients", [])]
        return cls(
            variety_id=data["varietyId"],
            name=data["name"],
            description=data["description"],
            image_key=data.get("imageKey", ""),
            ingredients=ingredients,
            bottle_yield_ml=int(data.get("bottleYieldMl", 750)),
            active=bool(data.get("active", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "varietyId": self.variety_id,
            "name": self.name,
            "description": self.description,
            "imageKey": self.image_key,
            "ingredients": [i.to_dict() for i in self.ingredients],
            "bottleYieldMl": self.bottle_yield_ml,
            "active": self.active,
        }

    def image_url(self, cloudfront_base: str) -> str:
        """Build the full CloudFront URL for this variety's image."""
        return f"{cloudfront_base.rstrip('/')}/{self.image_key}"

    @staticmethod
    def filter_active(varieties: list["Variety"]) -> list["Variety"]:
        return [v for v in varieties if v.active]

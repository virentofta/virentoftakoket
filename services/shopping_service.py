from __future__ import annotations

from typing import Dict, List

from core.database import connection_scope
from models.shopping_list import ShoppingItem, ShoppingList
from models.recipe import Ingredient


class ShoppingService:
    def __init__(self) -> None:
        pass

    def get_list(self, profile_id: int = 1) -> ShoppingList:
        with connection_scope() as conn:
            cur = conn.execute(
                "SELECT name, amount, checked FROM shopping_items WHERE profile_id = ? ORDER BY id",
                (profile_id,),
            )
            items = [
                ShoppingItem(
                    ingredient=Ingredient(name=row[0], amount=row[1]),
                    checked=bool(row[2]),
                )
                for row in cur.fetchall()
            ]
        return ShoppingList(profile_id=profile_id, items=items)

    def add_item(self, name: str, amount: str | None = None, profile_id: int = 1) -> ShoppingList:
        with connection_scope() as conn:
            conn.execute(
                "INSERT INTO shopping_items (profile_id, name, amount, checked) VALUES (?, ?, ?, 0)",
                (profile_id, name, amount),
            )
            conn.commit()
        return self.get_list(profile_id)

    def toggle_item(self, index: int, profile_id: int = 1) -> ShoppingList:
        items = self.get_list(profile_id).items
        if 0 <= index < len(items):
            target = items[index]
            checked = 0 if target.checked else 1
            with connection_scope() as conn:
                conn.execute(
                    "UPDATE shopping_items SET checked = ? WHERE profile_id = ? AND name = ? AND amount = ?",
                    (checked, profile_id, target.ingredient.name, target.ingredient.amount),
                )
                conn.commit()
        return self.get_list(profile_id)

    def _parse_amount(self, amount: str | None):
        """Returnera (value, unit) där value är float och unit är lower-case, annars None."""
        if not amount:
            return None
        amount = amount.strip()
        match = None
        import re

        match = re.match(r"^([0-9]+(?:[.,][0-9]+)?)\s*(.*)$", amount)
        if not match:
            return None
        value_raw, unit = match.groups()
        try:
            value = float(value_raw.replace(",", "."))
        except ValueError:
            return None
        return value, unit.strip().lower()

    def set_from_recipes(self, recipes: list, profile_id: int = 1) -> ShoppingList:
        """Bygg inköpslista från recept och summera lika ingredienser/enheter.

        Volym/skedmått → ml, vikt → gram, styck → st. Okända enheter sparas som egna rader.
        """
        volume_map = {
            "ml": 1,
            "cl": 10,
            "dl": 100,
            "l": 1000,
            "msk": 15,
            "tsk": 5,
            "krm": 1,
        }
        weight_map = {
            "g": 1,
            "kg": 1000,
        }
        count_units = {"st": 1}

        aggregated: Dict[tuple[str, str], float] = {}
        loose: list[Ingredient] = []

        def add_item(name: str, unit_key: str, value: float):
            key = (name.strip().lower(), unit_key)
            aggregated[key] = aggregated.get(key, 0) + value

        for recipe in recipes:
            for ing in getattr(recipe, "ingredients", []):
                parsed = self._parse_amount(ing.amount)
                name_key = ing.name.strip().lower()
                if not parsed:
                    loose.append(Ingredient(name=ing.name, amount=ing.amount))
                    continue
                value, unit = parsed

                if unit in volume_map:
                    base_value = value * volume_map[unit]
                    add_item(name_key, "ml", base_value)
                elif unit in weight_map:
                    base_value = value * weight_map[unit]
                    add_item(name_key, "g", base_value)
                elif unit in count_units or unit == "":
                    add_item(name_key, unit or "st", value)
                else:
                    # okänd enhet, lägg som egen rad
                    loose.append(Ingredient(name=ing.name, amount=ing.amount))

        items: list[ShoppingItem] = []
        for (name_key, unit_key), value in aggregated.items():
            # välj presentabel enhet
            display_value = value
            display_unit = unit_key
            if unit_key == "ml" and value >= 100:
                display_value = value / 100
                display_unit = "dl"
            if unit_key == "g" and value >= 1000:
                display_value = value / 1000
                display_unit = "kg"

            formatted = (
                f"{int(display_value)}"
                if abs(display_value - int(display_value)) < 1e-6
                else f"{display_value:.1f}".replace(".", ",")
            )
            amount_str = f"{formatted} {display_unit}".strip()
            items.append(ShoppingItem(ingredient=Ingredient(name=name_key, amount=amount_str)))

        # Append non-parsable entries
        for ing in loose:
            items.append(ShoppingItem(ingredient=Ingredient(name=ing.name, amount=ing.amount)))

        with connection_scope() as conn:
            conn.execute("DELETE FROM shopping_items WHERE profile_id = ?", (profile_id,))
            conn.executemany(
                "INSERT INTO shopping_items (profile_id, name, amount, checked) VALUES (?, ?, ?, ?)",
                [(profile_id, item.ingredient.name, item.ingredient.amount, 0) for item in items],
            )
            conn.commit()

        return self.get_list(profile_id)


# Delad instans
shopping_service = ShoppingService()

__all__ = ["ShoppingService", "shopping_service"]

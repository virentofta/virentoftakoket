from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from models.recipe import Ingredient


class ShoppingItem(BaseModel):
    ingredient: Ingredient
    checked: bool = False


class ShoppingList(BaseModel):
    profile_id: Optional[int] = Field(None, description="Profilen som listan tillhör")
    items: List[ShoppingItem] = Field(default_factory=list)

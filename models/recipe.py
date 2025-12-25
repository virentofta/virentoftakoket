from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    name: str = Field(..., description="Ingrediensnamn")
    amount: Optional[str] = Field(None, description="Mängd eller mått")


class Recipe(BaseModel):
    id: Optional[int] = Field(None, description="Primärnyckel eller index")
    title: str = Field(..., description="Titel på receptet")
    description: Optional[str] = None
    servings: Optional[int] = Field(None, description="Antal portioner")
    image_url: Optional[str] = Field(None, description="Länk till bild")
    archived: bool = Field(False, description="Om receptet är arkiverat")
    ingredients: List[Ingredient] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_by: Optional[int] = Field(None, description="Profil-ID för skaparen")

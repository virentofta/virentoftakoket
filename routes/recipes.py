from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from models.recipe import Ingredient, Recipe
from services.recipe_service import recipe_service

router = APIRouter()


@router.get("/recipes", response_model=List[Recipe])
async def list_recipes(profile_id: int | None = None) -> List[Recipe]:
    return recipe_service.list_recipes(profile_id=profile_id)


@router.get("/recipes/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: int) -> Recipe:
    recipe = recipe_service.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe

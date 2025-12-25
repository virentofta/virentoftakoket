from __future__ import annotations

from typing import List, Optional

from models.recipe import Ingredient, Recipe
from services.recipe_repository import recipe_repo


class RecipeService:
    """DB-baserad service för recept med ingredienser, steg och taggar."""

    def list_recipes(self, profile_id: int | None = None, include_archived: bool = False) -> List[Recipe]:
        return recipe_repo.list_recipes(profile_id=profile_id, include_archived=include_archived)

    def get_recipe(self, recipe_id: int, include_archived: bool = True) -> Optional[Recipe]:
        return recipe_repo.get_recipe(recipe_id, include_archived=include_archived)

    def search_recipes(self, query: str, profile_id: int | None = None, include_archived: bool = False) -> List[Recipe]:
        return recipe_repo.search_recipes(query, profile_id=profile_id, include_archived=include_archived)

    def add_recipe(
        self,
        title: str,
        description: str | None,
        ingredients: List[Ingredient],
        steps: List[str],
        tags: List[str] | None = None,
        created_by: int | None = None,
        servings: int | None = None,
        image_url: str | None = None,
        archived: bool | None = False,
    ) -> Recipe:
        return recipe_repo.add_recipe(
            title=title,
            description=description,
            ingredients=ingredients,
            steps=steps,
            tags=tags or [],
            created_by=created_by,
            servings=servings,
            image_url=image_url,
            archived=archived or False,
        )

    def update_recipe(
        self,
        recipe_id: int,
        *,
        title: str | None = None,
        description: str | None = None,
        ingredients: List[Ingredient] | None = None,
        steps: List[str] | None = None,
        tags: List[str] | None = None,
        servings: int | None = None,
        image_url: str | None = None,
        archived: bool | None = None,
    ) -> Optional[Recipe]:
        return recipe_repo.update_recipe(
            recipe_id,
            title=title,
            description=description,
            ingredients=ingredients,
            steps=steps,
            tags=tags,
            servings=servings,
            image_url=image_url,
            archived=archived,
        )


recipe_service = RecipeService()

__all__ = ["RecipeService", "recipe_service"]

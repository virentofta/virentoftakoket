from __future__ import annotations

from typing import List, Optional

from core.database import connection_scope
from models.recipe import Ingredient, Recipe


class RecipeRepository:
    """DB-åtkomst för recept och relaterade tabeller."""

    def list_recipes(self, profile_id: int | None = None, include_archived: bool = False) -> List[Recipe]:
        with connection_scope() as conn:
            base = "SELECT id, title, description, servings, image_url, created_by, archived FROM recipes"
            filters = []
            params = []
            if profile_id:
                filters.append("created_by = ?")
                params.append(profile_id)
            if not include_archived:
                filters.append("(archived = 0 OR archived IS NULL)")
            where = f" WHERE {' AND '.join(filters)}" if filters else ""
            cur = conn.execute(base + where + " ORDER BY id", tuple(params))
            recipes = []
            for row in cur.fetchall():
                servings = self._coerce_servings(row[3])
                recipes.append(
                    Recipe(
                        id=row[0],
                        title=row[1],
                        description=row[2],
                        servings=servings,
                        image_url=row[4],
                        created_by=row[5],
                        archived=bool(row[6]) if row[6] is not None else False,
                        ingredients=self._get_ingredients(row[0]),
                        steps=self._get_steps(row[0]),
                        tags=self._get_tags(row[0]),
                    )
                )
            return recipes

    def get_recipe(self, recipe_id: int, include_archived: bool = True) -> Optional[Recipe]:
        with connection_scope() as conn:
            cur = conn.execute(
                "SELECT id, title, description, servings, image_url, created_by, archived FROM recipes WHERE id = ?",
                (recipe_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            servings = self._coerce_servings(row[3])
            if not include_archived and row[6]:
                return None
            return Recipe(
                id=row[0],
                title=row[1],
                description=row[2],
                servings=servings,
                image_url=row[4],
                created_by=row[5],
                archived=bool(row[6]) if row[6] is not None else False,
                ingredients=self._get_ingredients(recipe_id),
                steps=self._get_steps(recipe_id),
                tags=self._get_tags(recipe_id),
            )

    def add_recipe(
        self,
        title: str,
        description: str | None,
        ingredients: List[Ingredient],
        steps: List[str],
        tags: List[str],
        created_by: int | None,
        servings: int | None,
        image_url: str | None,
        archived: bool | None = False,
    ) -> Recipe:
        with connection_scope() as conn:
            cur = conn.execute(
                "INSERT INTO recipes (title, description, servings, image_url, created_by, archived) VALUES (?, ?, ?, ?, ?, ?)",
                (title, description, servings, image_url, created_by, 1 if archived else 0),
            )
            recipe_id = cur.lastrowid
            self._replace_ingredients(conn, recipe_id, ingredients)
            self._replace_steps(conn, recipe_id, steps)
            self._replace_tags(conn, recipe_id, tags)
            conn.commit()
        return self.get_recipe(recipe_id)  # type: ignore

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
        if not self.get_recipe(recipe_id):
            return None
        with connection_scope() as conn:
            conn.execute(
                "UPDATE recipes SET title = COALESCE(?, title), description = COALESCE(?, description), servings = COALESCE(?, servings), image_url = COALESCE(?, image_url), archived = COALESCE(?, archived) WHERE id = ?",
                (title, description, servings, image_url, archived if archived is not None else None, recipe_id),
            )
            if ingredients is not None:
                self._replace_ingredients(conn, recipe_id, ingredients)
            if steps is not None:
                self._replace_steps(conn, recipe_id, steps)
            if tags is not None:
                self._replace_tags(conn, recipe_id, tags)
            conn.commit()
        return self.get_recipe(recipe_id)

    def search_recipes(self, query: str, profile_id: int | None = None, include_archived: bool = False) -> List[Recipe]:
        q = query.lower().strip()
        if not q:
            return self.list_recipes(profile_id=profile_id, include_archived=include_archived)
        results: List[Recipe] = []
        for recipe in self.list_recipes(profile_id=profile_id, include_archived=include_archived):
            ingredient_names = " ".join([ing.name.lower() for ing in recipe.ingredients])
            haystack = " ".join([recipe.title.lower(), ingredient_names, " ".join([t.lower() for t in recipe.tags])])
            if q in haystack:
                results.append(recipe)
        return results

    # helpers
    def _replace_ingredients(self, conn, recipe_id: int, ingredients: List[Ingredient]):
        conn.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe_id,))
        conn.executemany(
            "INSERT INTO ingredients (recipe_id, name, amount) VALUES (?, ?, ?)",
            [(recipe_id, ing.name, ing.amount) for ing in ingredients],
        )

    def _replace_steps(self, conn, recipe_id: int, steps: List[str]):
        conn.execute("DELETE FROM steps WHERE recipe_id = ?", (recipe_id,))
        conn.executemany(
            "INSERT INTO steps (recipe_id, position, text) VALUES (?, ?, ?)",
            [(recipe_id, idx + 1, text) for idx, text in enumerate(steps)],
        )

    def _replace_tags(self, conn, recipe_id: int, tags: List[str]):
        conn.execute("DELETE FROM tags WHERE recipe_id = ?", (recipe_id,))
        conn.executemany(
            "INSERT INTO tags (recipe_id, tag) VALUES (?, ?)",
            [(recipe_id, tag) for tag in tags],
        )

    def _coerce_servings(self, raw) -> Optional[int]:
        """Tryck tillbaka servings till int eller None för att undvika valideringsfel."""
        if raw is None:
            return None
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            try:
                return int(raw)
            except ValueError:
                return None
        return None

    def _get_ingredients(self, recipe_id: int) -> List[Ingredient]:
        with connection_scope() as conn:
            cur = conn.execute("SELECT name, amount FROM ingredients WHERE recipe_id = ? ORDER BY id", (recipe_id,))
            return [Ingredient(name=row[0], amount=row[1]) for row in cur.fetchall()]

    def _get_steps(self, recipe_id: int) -> List[str]:
        with connection_scope() as conn:
            cur = conn.execute("SELECT text FROM steps WHERE recipe_id = ? ORDER BY position", (recipe_id,))
            return [row[0] for row in cur.fetchall()]

    def _get_tags(self, recipe_id: int) -> List[str]:
        with connection_scope() as conn:
            cur = conn.execute("SELECT tag FROM tags WHERE recipe_id = ? ORDER BY id", (recipe_id,))
            return [row[0] for row in cur.fetchall()]


recipe_repo = RecipeRepository()

__all__ = ["RecipeRepository", "recipe_repo"]

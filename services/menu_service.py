from __future__ import annotations

from datetime import date
from typing import Dict

from core.database import connection_scope
from models.weekly_menu import MenuEntry, WeeklyMenu


class MenuService:
    def __init__(self) -> None:
        pass

    def get_menu(self, profile_id: int = 1, week_number: int | None = None, year: int | None = None) -> WeeklyMenu:
        responsible_profile_id = None
        resolved_week = week_number or date.today().isocalendar().week
        resolved_year = year or date.today().isocalendar().year
        with connection_scope() as conn:
            cur = conn.execute(
                "SELECT day, recipe_id FROM menu_entries WHERE profile_id = ? AND (week_number IS NULL OR week_number = ?) AND (year IS NULL OR year = ?) ORDER BY id",
                (profile_id, resolved_week, resolved_year),
            )
            entries = [MenuEntry(day=row[0], recipe_id=row[1]) for row in cur.fetchall()]
            cur_meta = conn.execute(
                "SELECT responsible_profile_id, label, week_number, year FROM menu_meta WHERE profile_id = ? AND (year IS NULL OR year = ?)",
                (profile_id, resolved_year),
            )
            row = cur_meta.fetchone()
            if row:
                responsible_profile_id = row[0]
                resolved_week = row[2] or resolved_week
                resolved_year = row[3] or resolved_year
            else:
                week_number = resolved_week
        return WeeklyMenu(
            profile_id=profile_id,
            entries=entries,
            responsible_profile_id=responsible_profile_id,
            week_number=resolved_week,
            year=resolved_year,
        )

    def replace_menu(self, recipe_ids: list[int], profile_id: int = 1, week_number: int | None = None, year: int | None = None) -> WeeklyMenu:
        """Ersätt hela menyn med givna recept i veckoföljd (Mån–Sön)."""
        days = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
        resolved_week = week_number or date.today().isocalendar().week
        resolved_year = year or date.today().isocalendar().year
        with connection_scope() as conn:
            conn.execute(
                "DELETE FROM menu_entries WHERE profile_id = ? AND (week_number IS NULL OR week_number = ?) AND (year IS NULL OR year = ?)",
                (profile_id, resolved_week, resolved_year),
            )
            conn.executemany(
                "INSERT INTO menu_entries (profile_id, day, week_number, year, recipe_id) VALUES (?, ?, ?, ?, ?)",
                [
                    (profile_id, days[idx], resolved_week, resolved_year, recipe_id)
                    for idx, recipe_id in enumerate(recipe_ids[: len(days)])
                ],
            )
            conn.execute(
                "INSERT INTO menu_meta (profile_id, responsible_profile_id, week_number, year) VALUES (?, (SELECT responsible_profile_id FROM menu_meta WHERE profile_id = ?), ?, ?)\n"
                "ON CONFLICT(profile_id) DO UPDATE SET week_number = excluded.week_number, year = excluded.year",
                (profile_id, profile_id, resolved_week, resolved_year),
            )
            conn.commit()
        return self.get_menu(profile_id, week_number=resolved_week, year=resolved_year)

    def set_responsible(self, profile_id: int, responsible_profile_id: int | None, week_number: int | None = None, year: int | None = None) -> WeeklyMenu:
        resolved_week = week_number or date.today().isocalendar().week
        resolved_year = year or date.today().isocalendar().year
        with connection_scope() as conn:
            conn.execute(
                "INSERT INTO menu_meta (profile_id, responsible_profile_id, week_number, year) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(profile_id) DO UPDATE SET responsible_profile_id = excluded.responsible_profile_id, week_number = excluded.week_number, year = excluded.year",
                (profile_id, responsible_profile_id, resolved_week, resolved_year),
            )
            conn.commit()
        return self.get_menu(profile_id, week_number=resolved_week, year=resolved_year)

    def remove_entry(self, day: str, profile_id: int = 1, week_number: int | None = None, year: int | None = None) -> WeeklyMenu:
        resolved_week = week_number or date.today().isocalendar().week
        resolved_year = year or date.today().isocalendar().year
        with connection_scope() as conn:
            conn.execute(
                "DELETE FROM menu_entries WHERE profile_id = ? AND day = ? AND (week_number IS NULL OR week_number = ?) AND (year IS NULL OR year = ?)",
                (profile_id, day, resolved_week, resolved_year),
            )
            conn.commit()
        return self.get_menu(profile_id, week_number=resolved_week, year=resolved_year)

    def append_recipes(self, recipe_ids: list[int], profile_id: int = 1, week_number: int | None = None, year: int | None = None) -> WeeklyMenu:
        """Fyll på tomma dagar i menyn med valda recept i ordning Mån–Sön."""
        if not recipe_ids:
            return self.get_menu(profile_id, week_number=week_number, year=year)

        days = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
        resolved_week = week_number or date.today().isocalendar().week
        resolved_year = year or date.today().isocalendar().year
        with connection_scope() as conn:
            cur = conn.execute(
                "SELECT day FROM menu_entries WHERE profile_id = ? AND (week_number IS NULL OR week_number = ?) AND (year IS NULL OR year = ?)",
                (profile_id, resolved_week, resolved_year),
            )
            used_days = {row[0] for row in cur.fetchall()}
            remaining_days = [d for d in days if d not in used_days]
            pairs = list(zip(remaining_days, recipe_ids))
            if pairs:
                conn.executemany(
                    "INSERT INTO menu_entries (profile_id, day, week_number, year, recipe_id) VALUES (?, ?, ?, ?, ?)",
                    [(profile_id, day, resolved_week, resolved_year, rid) for day, rid in pairs],
                )
                conn.execute(
                    "INSERT INTO menu_meta (profile_id, week_number, year) VALUES (?, ?, ?) "
                    "ON CONFLICT(profile_id) DO UPDATE SET week_number = excluded.week_number, year = excluded.year",
                    (profile_id, resolved_week, resolved_year),
                )
                conn.commit()

        return self.get_menu(profile_id, week_number=resolved_week, year=resolved_year)


menu_service = MenuService()

__all__ = ["MenuService", "menu_service"]

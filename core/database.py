from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from core.config import settings


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Skapa en SQLite-anslutning mot den lokala databasen."""
    target = db_path or settings.data_dir / "app.db"
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def connection_scope(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Enkel context-manager för att öppna/stänga anslutningar."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Initiera tabeller om de inte finns och seeda grunddata."""
    schema = [
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            avatar_url TEXT,
            theme_preference TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            servings INTEGER,
            image_url TEXT,
            created_by INTEGER,
            archived INTEGER DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            amount TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            text TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL,
            tag TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS menu_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            week_number INTEGER,
            year INTEGER,
            recipe_id INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS menu_meta (
            profile_id INTEGER PRIMARY KEY,
            responsible_profile_id INTEGER,
            label TEXT,
            week_number INTEGER,
            year INTEGER
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS shopping_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            amount TEXT,
            checked INTEGER DEFAULT 0
        )
        """,
    ]

    with connection_scope() as conn:
        cur = conn.cursor()
        for stmt in schema:
            cur.execute(stmt)
        conn.commit()

        # Säkerställ att kolumn week_number finns (för befintliga databaser)
        cur.execute("PRAGMA table_info(menu_meta)")
        cols = [row[1] for row in cur.fetchall()]
        if "week_number" not in cols:
            cur.execute("ALTER TABLE menu_meta ADD COLUMN week_number INTEGER")
            conn.commit()
        if "year" not in cols:
            cur.execute("ALTER TABLE menu_meta ADD COLUMN year INTEGER")
            conn.commit()
        cur.execute("PRAGMA table_info(menu_entries)")
        cols_entries = [row[1] for row in cur.fetchall()]
        if "year" not in cols_entries:
            cur.execute("ALTER TABLE menu_entries ADD COLUMN year INTEGER")
            conn.commit()
        # Lägg till archived i recipes om den saknas
        cur.execute("PRAGMA table_info(recipes)")
        cols_recipes = [row[1] for row in cur.fetchall()]
        if "archived" not in cols_recipes:
            cur.execute("ALTER TABLE recipes ADD COLUMN archived INTEGER DEFAULT 0")
            conn.commit()
        # Lägg till theme_preference i profiler om den saknas
        cur.execute("PRAGMA table_info(profiles)")
        cols_profiles = [row[1] for row in cur.fetchall()]
        if "theme_preference" not in cols_profiles:
            cur.execute("ALTER TABLE profiles ADD COLUMN theme_preference TEXT")
            conn.commit()

        # Seed profiler om tomt
        cur.execute("SELECT COUNT(*) FROM profiles")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO profiles (id, name, email, avatar_url) VALUES (?, ?, ?, ?)",
                [
                    (1, "Per", "per@example.com", None),
                    (2, "Marika", "marika@example.com", None),
                    (3, "Sally", "sally@example.com", None),
                    (4, "Jack", "jack@example.com", None),
                ],
            )
            conn.commit()

        # Säkerställ att kolumn week_number finns i menu_entries
        cur.execute("PRAGMA table_info(menu_entries)")
        cols = [row[1] for row in cur.fetchall()]
        if "week_number" not in cols:
            cur.execute("ALTER TABLE menu_entries ADD COLUMN week_number INTEGER")
            conn.commit()

        # Seed ett exempelrecept om tomt
        cur.execute("SELECT COUNT(*) FROM recipes")
        if cur.fetchone()[0] == 0:
            cur.execute(
                "INSERT INTO recipes (title, description, servings, image_url, created_by) VALUES (?, ?, ?, ?, ?)",
                ("Exempelrecept", "Ett första recept att byta ut senare.", 2, None, 1),
            )
            recipe_id = cur.lastrowid
            cur.execute(
                "INSERT INTO ingredients (recipe_id, name, amount) VALUES (?, ?, ?)",
                (recipe_id, "Potatis", "2 st"),
            )
            cur.executemany(
                "INSERT INTO steps (recipe_id, position, text) VALUES (?, ?, ?)",
                [
                    (recipe_id, 1, "Skala potatis"),
                    (recipe_id, 2, "Koka tills mjuk"),
                ],
            )
            cur.executemany(
                "INSERT INTO tags (recipe_id, tag) VALUES (?, ?)",
                [
                    (recipe_id, "enkelt"),
                    (recipe_id, "snabbt"),
                ],
            )
            conn.commit()

from __future__ import annotations

from typing import Dict, List, Optional

from core.database import connection_scope
from models.profile import Profile


class ProfileService:
    """Profiler persisteras i SQLite (ingen auth, bara separation av data)."""

    def list_profiles(self) -> List[Profile]:
        with connection_scope() as conn:
            cur = conn.execute("SELECT id, name, email, avatar_url, theme_preference FROM profiles ORDER BY id")
            return [
                Profile(
                    id=row[0],
                    name=row[1],
                    email=row[2],
                    avatar_url=row[3],
                    theme_preference=row[4],
                )
                for row in cur.fetchall()
            ]

    def get_profile(self, profile_id: int) -> Optional[Profile]:
        with connection_scope() as conn:
            cur = conn.execute("SELECT id, name, email, avatar_url, theme_preference FROM profiles WHERE id = ?", (profile_id,))
            row = cur.fetchone()
            if not row:
                return None
            return Profile(
                id=row[0],
                name=row[1],
                email=row[2],
                avatar_url=row[3],
                theme_preference=row[4],
            )

    def create_profile(self, name: str, email: str | None = None, avatar_url: str | None = None) -> Profile:
        email = email or None
        avatar_url = avatar_url or None
        with connection_scope() as conn:
            cur = conn.execute(
                "INSERT INTO profiles (name, email, avatar_url, theme_preference) VALUES (?, ?, ?, ?)",
                (name, email, avatar_url, None),
            )
            profile_id = cur.lastrowid
            conn.commit()
        return self.get_profile(profile_id)  # type: ignore

    def update_profile(
        self,
        profile_id: int,
        *,
        name: str | None = None,
        email: str | None = None,
        avatar_url: str | None = None,
        theme_preference: str | None = None,
    ) -> Optional[Profile]:
        if self.get_profile(profile_id) is None:
            return None
        with connection_scope() as conn:
            cur = conn.execute(
                "UPDATE profiles SET name = COALESCE(?, name), email = COALESCE(?, email), avatar_url = COALESCE(?, avatar_url), theme_preference = COALESCE(?, theme_preference) WHERE id = ?",
                (name, email, avatar_url, theme_preference, profile_id),
            )
            conn.commit()
        return self.get_profile(profile_id)


# Delad instans
profile_service = ProfileService()

__all__ = ["ProfileService", "profile_service"]

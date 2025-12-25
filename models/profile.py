from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, EmailStr


class Profile(BaseModel):
    """Enkel profil för att särskilja data per användare (utan auth)."""

    id: Optional[int] = Field(None, description="Profil-ID")
    name: str = Field(..., description="Visningsnamn")
    email: Optional[EmailStr] = Field(None, description="Kontaktmail")
    avatar_url: Optional[str] = Field(None, description="Bild-URL")
    theme_preference: Optional[str] = Field(None, description="Föredraget tema (light/dark/auto)")

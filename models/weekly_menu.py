from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class MenuEntry(BaseModel):
    day: str = Field(..., description="Dag i veckan")
    recipe_id: Optional[int] = Field(None, description="ID för receptet")


class WeeklyMenu(BaseModel):
    profile_id: Optional[int] = Field(None, description="Profilen som menyn tillhör")
    responsible_profile_id: Optional[int] = Field(None, description="Profil som ansvarar för veckan")
    week_number: Optional[int] = Field(None, description="Veckonummer (ISO)")
    year: Optional[int] = Field(None, description="Årtal för menyn")
    week_start: Optional[date] = None
    entries: List[MenuEntry] = Field(default_factory=list)

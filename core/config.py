from __future__ import annotations

import os
from pathlib import Path


class Settings:
    """Grundläggande inställningar för appen."""

    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parent.parent
        self.data_dir = self.base_dir / "data"
        self.static_dir = self.base_dir / "static"
        self.template_dir = self.base_dir / "templates"
        self.database_url = os.getenv("DATABASE_URL", f"sqlite:///{self.data_dir / 'app.db'}")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()

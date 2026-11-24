"""Settings storage. Everything stays in the user's config directory."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any


def data_dir() -> Path:
    """Return the directory that holds the database, blobs and settings."""
    override = os.environ.get("OMOIDE_HOME")
    if override:
        return Path(override).expanduser()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Omoide"
    return Path.home() / ".omoide"


@dataclass
class Settings:
    hotkey: str = "ctrl+shift+v"
    theme: str = "dark"
    onboarded: bool = False
    capture_enabled: bool = True
    ocr_enabled: bool = True
    retention_days: int = 90
    store_titles: bool = False
    redact_agent: bool = True
    mcp_enabled: bool = False
    excluded_apps: list[str] = field(default_factory=list)
    poll_ms: int = 250
    max_text_bytes: int = 100_000
    max_image_bytes: int = 10_000_000

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        path = path or data_dir() / "settings.json"
        settings = cls()
        if not path.exists():
            return settings
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return settings
        valid = {item.name for item in fields(cls)}
        for key, value in raw.items():
            if key in valid:
                setattr(settings, key, value)
        return settings

    def save(self, path: Path | None = None) -> None:
        path = path or data_dir() / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        tmp.replace(path)

    def update(self, patch: dict[str, Any]) -> None:
        valid = {item.name for item in fields(self)}
        for key, value in patch.items():
            if key in valid:
                setattr(self, key, value)

    @property
    def db_path(self) -> Path:
        return data_dir() / "omoide.sqlite3"

    @property
    def blobs_dir(self) -> Path:
        return data_dir() / "blobs"

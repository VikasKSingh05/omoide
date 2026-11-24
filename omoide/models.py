"""Data containers shared by the capture, storage and UI layers."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any

from PIL import Image


@dataclass
class CapturedClip:
    """A rawclip read from the system clipboard."""

    kind: str  # text | image | html
    text: str = ""
    html: str | None = None
    image: Image.Image | None = None

    def content_hash(self) -> str:
        """A stable identity for deduplication."""
        payload = self.text.encode("utf-8", errors="replace")
        if self.html:
            payload += b"\0html\0" + self.html.encode("utf-8", errors="replace")
        if self.image is not None:
            payload += b"\0image\0" + self.image.tobytes()
        return hashlib.sha256(payload).hexdigest()


@dataclass
class ClipRow:
    """A stored clip."""

    id: int
    created_at: int
    kind: str
    text: str
    html: str | None
    blob_hash: str | None
    source_app: str
    source_title: str | None
    char_len: int
    paste_count: int
    last_pasted_at: int | None
    pinned: bool
    blocked: bool = False

    def to_dict(self, *, include_html: bool = False) -> dict[str, Any]:
        data = asdict(self)
        data["pinned"] = bool(self.pinned)
        data["blocked"] = bool(self.blocked)
        if not include_html:
            data.pop("html", None)
        return data


@dataclass
class SearchHit:
    """A clip plus the information needed to explain its ranking."""

    clip: ClipRow
    score: float = 0.0
    terms: list[str] = field(default_factory=list)
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = self.clip.to_dict()
        data.update(score=round(self.score, 4), terms=self.terms, snippet=self.snippet)
        return data

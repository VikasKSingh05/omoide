"""Query parsing, FTS query construction and safe snippet rendering."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FILTER_RE = re.compile(r"(?i)\b(app|since|kind|pin):([^\s]+)")
TERM_RE = re.compile(r"[\w\u4e00-\u9fff]{2,}", re.UNICODE)


@dataclass
class Query:
    text: str
    apps: list[str] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)
    since_days: int | None = None
    pinned_only: bool = False
    terms: list[str] = field(default_factory=list)


def parse_query(raw: str) -> Query:
    """Accept plain words plus a few explicit filters.

    Examples: ``invoice``, ``app:chrome timeout``, ``kind:image since:7d CUDA``.
    Unknown filter values are ignored rather than raising, so typing is calm.
    """
    apps: list[str] = []
    kinds: list[str] = []
    since_days: int | None = None
    pinned_only = False

    def consume(match: re.Match[str]) -> str:
        nonlocal since_days, pinned_only
        name = match.group(1).lower()
        value = match.group(2).strip()
        if name == "app" and value:
            apps.append(value.lower())
        elif name == "kind" and value.lower() in {"text", "image", "html"}:
            kinds.append(value.lower())
        elif name == "since":
            digits = re.match(r"(\d+)(d|day|days)?$", value, re.I)
            if digits:
                since_days = int(digits.group(1))
        elif name == "pin" and value.lower() in {"1", "true", "yes"}:
            pinned_only = True
        return " "

    without_filters = FILTER_RE.sub(consume, raw or "")
    text = re.sub(r"\s+", " ", without_filters).strip()

    terms = []
    for term in TERM_RE.findall(text.lower()):
        if term not in terms:
            terms.append(term)

    return Query(
        text=text,
        apps=apps,
        kinds=kinds,
        since_days=since_days,
        pinned_only=pinned_only,
        terms=terms,
    )


def build_fts_expression(text: str) -> str | None:
    """Turn user text into a safe FTS5 MATCH expression with prefix terms."""
    words = re.findall(r"\S+", text)
    if not words:
        return None
    parts = []
    for word in words:
        cleaned = word.replace('"', "").strip()
        if cleaned:
            parts.append(f'"{cleaned}"*')
    return " AND ".join(parts) if parts else None


def highlight_positions(text: str, terms: list[str]) -> list[tuple[int, int]]:
    """Return non-overlapping [start, end) ranges for the given terms."""
    haystack = text.lower()
    ranges: list[tuple[int, int]] = []
    for term in terms:
        if len(term) < 2:
            continue
        start = 0
        while True:
            found = haystack.find(term.lower(), start)
            if found < 0:
                break
            end = found + len(term)
            if not any(found < e and s < end for s, e in ranges):
                ranges.append((found, end))
            start = found + len(term)
    return sorted(ranges)


def make_snippet(text: str, terms: list[str], width: int = 260) -> str:
    """Return a short excerpt centred on the first match."""
    if not text:
        return ""
    if len(text) <= width:
        return text
    positions = highlight_positions(text, terms)
    start = max(0, positions[0][0] - width // 3) if positions else 0
    start = min(start, len(text) - width)
    end = start + width
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end] + suffix

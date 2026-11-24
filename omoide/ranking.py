"""The ranking formula. Kept in one place so it can be explained and tuned."""

from __future__ import annotations

from .models import ClipRow

WEIGHTS: dict[str, float] = {
    "bm25": 3.0,
    "substring": 2.0,
    "frequency": 2.0,
    "recency": 1.5,
    "same_app": 1.0,
    "pinned": 4.0,
    "blocked": -10.0,
}

HALF_LIFE_MS = 14 * 24 * 60 * 60 * 1000


def recency_decay(created_at_ms: int, now_ms: int, half_life_ms: int = HALF_LIFE_MS) -> float:
    """1.0 for a fresh clip, 0.5 at one half-life, approaching 0 for old clips."""
    age = max(0, now_ms - created_at_ms)
    return 0.5 ** (age / half_life_ms)


def score_hit(
    clip: ClipRow,
    *,
    fts_rank: float,
    substring: bool,
    foreground_app: str,
    now_ms: int,
    weights: dict[str, float] | None = None,
) -> float:
    """Return a higher-is-better relevance score.

    ``fts_rank`` is SQLite's bm25(), where more negative is better. We flip it
    and cap it so a single extremely long document cannot dominate.
    """
    w = weights or WEIGHTS
    text_score = min(max(-fts_rank, 0.0), 10.0)
    frequency = 0.0 if clip.paste_count <= 0 else _log1p(clip.paste_count)
    same_app = 1.0 if foreground_app and clip.source_app == foreground_app else 0.0
    return (
        w["bm25"] * text_score
        + w["substring"] * (1.0 if substring else 0.0)
        + w["frequency"] * frequency
        + w["recency"] * recency_decay(clip.created_at, now_ms)
        + w["same_app"] * same_app
        + w["pinned"] * (1.0 if clip.pinned else 0.0)
        + w["blocked"] * (1.0 if clip.blocked else 0.0)
    )


def _log1p(value: int) -> float:
    import math

    return math.log1p(value)

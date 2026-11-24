from omoide.models import ClipRow
from omoide.ranking import recency_decay, score_hit


def clip(**overrides):
    values = dict(
        id=1,
        created_at=1_700_000_000_000,
        kind="text",
        text="x",
        html=None,
        blob_hash=None,
        source_app="Chrome",
        source_title="",
        char_len=1,
        paste_count=0,
        last_pasted_at=None,
        pinned=False,
    )
    values.update(overrides)
    return ClipRow(**values)


def test_recency_decay():
    now = 1_700_000_000_000
    assert recency_decay(now, now) == 1.0
    half_life = 14 * 24 * 60 * 60 * 1000
    assert recency_decay(now - half_life, now) == 0.5


def test_ranking_terms():
    now = 1_700_000_000_000
    base = score_hit(clip(), fts_rank=-1.0, substring=False, foreground_app="", now_ms=now)
    assert base > 0
    pinned = score_hit(
        clip(pinned=True), fts_rank=-1.0, substring=False, foreground_app="", now_ms=now
    )
    assert pinned - base == 4.0
    same_app = score_hit(
        clip(), fts_rank=-1.0, substring=False, foreground_app="Chrome", now_ms=now
    )
    assert same_app > base
    blocked = score_hit(
        clip(blocked=True), fts_rank=-1.0, substring=False, foreground_app="", now_ms=now
    )
    assert blocked < 0

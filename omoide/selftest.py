"""Headless store/search check used by CI and the frozen-exe smoke test."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from .models import CapturedClip
from .store import Store


def run() -> int:
    """Exercise add/search/stats in an isolated store and write an optional marker."""
    output = os.environ.get("OMOIDE_SELFTEST_OUT")
    try:
        with tempfile.TemporaryDirectory(prefix="omoide-selftest-") as directory:
            root = Path(directory)
            store = Store(root / "selftest.sqlite3", root / "blobs")
            store.open()
            try:
                clip = store.add(
                    CapturedClip(kind="text", text="selftest deploy timeout"),
                    source_app="Terminal",
                )
                hits = store.search("deploy timeout")
                stats = store.stats()
                assert clip is not None, "store.add returned None"
                assert hits and hits[0].clip.id == clip.id, "search did not find the clip"
                assert stats["total"] == 1, f"unexpected stats: {stats}"
                message = f"ok: clip {clip.id}, {len(hits)} hit(s), {stats['total']} stored"
            finally:
                store.close()
        if output:
            Path(output).write_text(message + "\n", encoding="utf-8")
        return 0
    except Exception as exc:  # noqa: BLE001 - smoke test reports any failure
        message = f"selftest failed: {type(exc).__name__}: {exc}"
        if output:
            Path(output).write_text(message + "\n", encoding="utf-8")
        if sys.stderr is not None:
            print(message, file=sys.stderr)
        return 1

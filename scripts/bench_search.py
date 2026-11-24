"""Measure search latency over a synthetic 100k-clip corpus."""

from __future__ import annotations

import random
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from omoide.models import CapturedClip
from omoide.store import Store

COUNT = 100_000
QUERIES = (
    "timeout",
    "invoice",
    "99381",
    "deploy error",
    "chrome",
    "CUDA out of memory",
    "https://example.com",
    "last week",
)


def generate():
    random.seed(7)
    now = int(datetime.now(tz=UTC).timestamp() * 1000)
    apps = ("Chrome", "Terminal", "VS Code", "Mail", "Slack")
    for index in range(COUNT):
        template = index % 5
        if template == 0:
            text = f"invoice {index} amount {index * 7}.23 paid by vendor{index % 100}"
        elif template == 1:
            text = f"deploy timeout ref {index} in service-{index % 50} at 03:{index % 60}"
        elif template == 2:
            text = f"CUDA out of memory on gpu{index % 8} during batch {index}"
        elif template == 3:
            text = f"see https://example.com/ticket/{index} for the full thread"
        else:
            text = f"the quick brown fox {index} jumped over the lazy dog"
        yield (
            CapturedClip(kind="text", text=text),
            {
                "created_at": now - random.randint(0, 90 * 86_400_000),
                "source_app": apps[index % len(apps)],
            },
        )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="omoide-bench-") as directory:
        root = Path(directory)
        store = Store(root / "bench.sqlite3", root / "blobs")
        store.open()
        started = time.perf_counter()
        store.add_many(generate())
        print(f"indexed {COUNT} clips in {(time.perf_counter() - started):.1f} s")
        store.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        size = (root / "bench.sqlite3").stat().st_size
        print(f"database size: {size / 1_000_000:.1f} MB ({size / COUNT:.0f} B/clip)")

        for query in QUERIES:
            store.search(query)  # warm the page cache
            samples = []
            for _ in range(20):
                start = time.perf_counter()
                hits = store.search(query, limit=20)
                samples.append((time.perf_counter() - start) * 1000)
            samples.sort()
            print(
                f"{query!r:<28} median {samples[len(samples)//2]:6.2f} ms"
                f"  p95 {samples[int(len(samples)*0.95)-1]:6.2f} ms"
                f"  hits {len(hits)}"
            )
        print("stats:", store.stats())
        store.close()


if __name__ == "__main__":
    main()

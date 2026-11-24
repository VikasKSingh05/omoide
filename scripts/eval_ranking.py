"""Small deterministic ranking regression check.

This is not a learned relevance benchmark. It seeds a 5k-clip corpus with 24
"needle" clips, then checks that a distinctive query puts each needle at rank 1.
It catches ranking/indexing regressions without needing a labelled dataset.
"""

from __future__ import annotations

import json
import random
import statistics
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from omoide.models import CapturedClip
from omoide.store import Store

CORPUS_SIZE = 5_000
LIMIT = 10

NEEDLES: tuple[tuple[str, str], ...] = (
    ("deploy timeout in payments service ref ZQ-4812", "ZQ-4812"),
    ("invoice AB-99381 is approved for vendor 42", "AB-99381"),
    ("CUDA out of memory on gpu3 batch KL-7701", "KL-7701"),
    ("reset link for mailbox MX-2210 arrived", "MX-2210"),
    ("meeting notes for project ORION-19 are here", "ORION-19"),
    ("production token rotation ticket TR-6624", "TR-6624"),
    ("wifi password for studio is PP-3308", "PP-3308"),
    ("docker image registry mirror MR-1187", "MR-1187"),
    ("customer refund confirmation RF-9012", "RF-9012"),
    ("build failed at step ST-4471 in CI", "ST-4471"),
    ("database migration ID DM-5530 completed", "DM-5530"),
    ("flight confirmation code FL-8826", "FL-8826"),
    ("api endpoint for billing BL-1198", "BL-1198"),
    ("kernel panic reference KP-4407", "KP-4407"),
    ("schema review notes SR-7742", "SR-7742"),
    ("cache invalidation incident CI-2285", "CI-2285"),
    ("warranty claim number WC-6619", "WC-6619"),
    ("ssh host key fingerprint HK-9034", "HK-9034"),
    ("payroll export file PE-3376", "PE-3376"),
    ("conference badge code CB-5501", "CB-5501"),
    ("search relevance ticket RL-8043", "RL-8043"),
    ("backup restore point RP-9928", "RP-9928"),
    ("license key request LK-2267", "LK-2267"),
    ("shipping label ID SL-7194", "SL-7194"),
)

FILLER = (
    "the quick brown fox jumped over the lazy dog near the river",
    "please review the attached notes before the next meeting",
    "a short reminder to buy coffee and oat milk on the way home",
    "the build finished successfully with no warnings reported",
    "lunch reservation for four people at seven in the evening",
    "check the dashboard after the scheduled maintenance window",
    "this paragraph contains ordinary words for a clipboard index",
)


def generate():
    random.seed(11)
    now = int(datetime.now(tz=UTC).timestamp() * 1000)
    apps = ("Chrome", "Terminal", "VS Code", "Mail", "Slack")

    for index in range(CORPUS_SIZE - len(NEEDLES)):
        text = FILLER[index % len(FILLER)] + f" item {index}"
        yield (
            CapturedClip(kind="text", text=text),
            {
                "created_at": now - random.randint(0, 90 * 86_400_000),
                "source_app": apps[index % len(apps)],
            },
        )

    for index, (text, _key) in enumerate(NEEDLES):
        yield (
            CapturedClip(kind="text", text=text),
            {
                "created_at": now - index * 3_600_000,
                "source_app": apps[index % len(apps)],
            },
        )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="omoide-eval-") as directory:
        root = Path(directory)
        store = Store(root / "eval.sqlite3", root / "blobs")
        store.open()
        store.add_many(generate())

        reciprocal_ranks: list[float] = []
        found = 0
        latencies: list[float] = []
        misses: list[str] = []

        for _text, key in NEEDLES:
            row = store.conn.execute(
                "SELECT id FROM clips WHERE text LIKE ?", (f"%{key}%",)
            ).fetchone()
            if row is None:
                misses.append(f"{key}: seed row not found")
                reciprocal_ranks.append(0.0)
                continue
            relevant_id = int(row["id"])

            start = time.perf_counter()
            hits = store.search(key, limit=LIMIT)
            latencies.append((time.perf_counter() - start) * 1000)

            rank = next(
                (index for index, hit in enumerate(hits, start=1) if hit.clip.id == relevant_id),
                None,
            )
            if rank is None:
                misses.append(f"{key}: not in top {LIMIT}")
                reciprocal_ranks.append(0.0)
            else:
                found += 1
                reciprocal_ranks.append(1.0 / rank)

        result = {
            "corpus_size": CORPUS_SIZE,
            "queries": len(NEEDLES),
            "mrr_at_10": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4),
            "recall_at_10": round(found / len(NEEDLES), 4),
            "median_latency_ms": round(statistics.median(latencies), 3),
            "misses": misses,
        }
        print(json.dumps(result, indent=2))
        store.close()


if __name__ == "__main__":
    main()

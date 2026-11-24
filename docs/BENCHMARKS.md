# Benchmarks

All numbers below were measured on this machine, not estimated.

## Method and hardware

- CPU: 12th Gen Intel(R) Core(TM) i5-12450HX, 12 logical processors
- RAM: 15.7 GB
- OS: Windows
- Python 3.13.15, SQLite 3.50.4
- Corpus: 100,000 synthetic clips (invoices, deploy errors, CUDA errors, URLs, filler prose), one transaction, WAL checkpointed before measurement
- Query timing: 20 runs per query after one warm-up, median and p95 reported
- Reproduce with `$env:PYTHONPATH='.'; .\.venv\Scripts\python.exe scripts\bench_search.py`

## Search

| Query | Median | p95 |
| --- | ---: | ---: |
| `timeout` | 18.0 ms | 29.5 ms |
| `invoice` | 17.3 ms | 21.9 ms |
| `CUDA out of memory` | 27.6 ms | 28.4 ms |
| `https://example.com` | 28.6 ms | 48.7 ms |
| `99381` (rare substring) | 0.24 ms | 0.36 ms |
| `deploy error` (no hits) | 0.79 ms | 0.94 ms |

Indexing 100k clips took ~30 s on this CPU. The checkpointed database is **48.4 MB**, about **484 B/clip** including both FTS indexes and the content table. The original plan targeted <10 ms and ≤256 B/clip; neither was met, and this document reports reality. The tradeoff buys substring search that word indexes alone cannot do.

## OCR

- Synthetic 1920x1080 screenshot with two lines of 40 px text.
- First call including model load: ~1.3 s.
- Warm median over five calls: **241 ms** (samples 226–250 ms).
- Both phrases recognized exactly: `CUDA out of memory`, `invoice total 99381`.
- Reproduce with `$env:PYTHONPATH='.'; .\.venv\Scripts\python.exe scripts\check_ocr.py`.

## Ranking regression

- 5,000 synthetic clips with 24 distinctive "needle" queries.
- MRR@10 **1.0**, Recall@10 **1.0**, 0 misses.
- Median query latency: **0.22–0.33 ms** across repeated runs.
- This is a determinism/regression check, not a human-labelled relevance study. See `docs/EVAL.md`.

## Caveats

- Synthetic corpora favour regular token distributions; real histories may behave differently.
- Cold start of the frozen executable is not measured yet (week 4).
- OCR accuracy depends on font, contrast and language; only Latin text was tested.
- These are single-machine numbers. Do not read them as cross-platform claims.

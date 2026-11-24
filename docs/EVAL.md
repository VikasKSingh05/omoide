# Ranking evaluation

## What this measures

`scripts/eval_ranking.py` is a deterministic regression check, not a learned relevance benchmark:

- 5,000 synthetic clips are inserted into a fresh temp database.
- 24 "needle" clips contain distinctive tokens such as `ZQ-4812` or `AB-99381`.
- Each query is that token; the expected result is the single needle clip.
- MRR@10 and Recall@10 are computed over the top 10 hits.

This catches broken indexing, broken query parsing, and large ranking regressions. It does **not** prove relevance on real user queries.

## Result

Measured on the development machine (see `BENCHMARKS.md`):

| Metric | Value |
| --- | ---: |
| Corpus size | 5,000 clips |
| Queries | 24 |
| MRR@10 | **1.0** |
| Recall@10 | **1.0** |
| Median query latency | 0.22–0.33 ms across repeated runs |
| Misses | 0 |

Reproduce with:

```powershell
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe scripts\eval_ranking.py
```

## Next step

The original plan called for 200 human-labelled queries over a 5k-clip set. That dataset does not exist yet, so this deterministic check is published in its place. A real relevance eval remains open work; see `docs/ISSUES_FOUND.md`.

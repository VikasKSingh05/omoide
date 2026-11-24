# Architecture

Omoide is a layered Python app. The rule that matters: **the core never imports the GUI or Win32 GUI modules**. Everything OS-specific arrives as an injected provider, which keeps search, ranking and storage testable without a desktop session.

```
omoide/
  capture.py       Win32 clipboard change detection + format reading
  provenance.py    foreground process -> app identity
  sanitizer.py     credential/denylist filtering and agent redaction
  ocr.py           offline OCR engine
  store.py         SQLite schema, writes, two indexes, blob GC
  search.py        query parsing, FTS expressions, snippets
  ranking.py       the score formula
  service.py       background capture loop
  paste.py         clipboard write, focus restore, synthetic Ctrl+V
  mcp_server.py    read-only tools over stdio
  cli.py           typer CLI
  app.py           pywebview window, tray, hotkey, JS bridge
  ui/              plain HTML/CSS/JS overlay
```

## Why two indexes

- `clips_fts` uses FTS5 `unicode61`. It answers word queries with BM25 ranking and typo/prefix tolerance.
- `clips_tri` uses FTS5 `trigram`. It answers substrings inside IDs, URLs and error codes that word tokenization splits apart.
- Both are FTS5 external-content tables over `clips`, maintained by INSERT/DELETE/UPDATE triggers, so they cannot drift from the source rows.

Retrieval takes up to 100 candidates from each index, merges by clip id, then applies the ranking formula in Python. The trigram scan is skipped when word search already returned enough candidates, which keeps common queries fast.

## Ranking

```
score = 3.0 * bm25
      + 2.0 * substring_match
      + 2.0 * log(1 + paste_count)
      + 1.5 * recency_decay(14d half-life)
      + 1.0 * (source_app == foreground_app)
      + 4.0 * pinned
      - 10.0 * blocked
```

All weights live in `ranking.py`. `foreground_app` comes from `Win32ForegroundProvider` at query time, so a clip from the app you are currently using floats upward.

## Threading

| Thread | Responsibility |
| --- | --- |
| main / WebView2 | window, JS bridge, tray registration |
| `omoide-capture` | polls clipboard sequence number and writes new clips |
| `omoide-tray` | pystray menu loop |

`Store` owns one SQLite connection with `check_same_thread=False` and a re-entrant lock around every operation. WAL mode lets the capture loop write while the UI queries.

## Privacy boundary

- No network calls in the app or MCP server.
- OCR models ship with `rapidocr-onnxruntime`; nothing is uploaded.
- Credential-manager apps are rejected by provenance before storage.
- Secret-looking clips are stored only as `[blocked: possible credential]`.
- MCP tools are read-only, budgeted, and wrap content in `<clipboard-data>` so agents treat it as data rather than instructions.
- MCP is opt-in: both the CLI and `serve()` refuse to start unless `mcp_enabled` is set in Settings or `OMOIDE_MCP_ENABLED=1` is supplied for a one-off run.
- First-run onboarding writes `onboarded: true` only after the user confirms capture, OCR, hotkey and the privacy notice.

See `SECURITY.md` for the threat model and its limits.

## Known limitations

- HTML flavor is captured and stored, but rich-text paste fidelity across all apps is not guaranteed.
- OCR assumes horizontal text; angle classification is disabled for speed.
- The trigram index roughly doubles index size (see `BENCHMARKS.md`).

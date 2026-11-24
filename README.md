# Omoide

**You don't remember what you copied. You remember what was in it.**

Omoide is a local-first, content-searchable clipboard history for Windows. It finds the command, URL, error message, or text inside a screenshot you copied — without an account, a cloud service, or telemetry.

> **v1.0.0** · Windows 10/11 · MIT licensed. Numbers in this README are [measured on one machine](docs/BENCHMARKS.md), not marketing estimates.

## The 5-second demo

1. Copy a screenshot containing an error such as `CUDA out of memory`.
2. Press **Ctrl+Shift+V**.
3. Type `CUDA` — the screenshot appears with its OCR'd text searchable.
4. Press **Enter** — the clip is restored to the clipboard and pasted into the app you came from.

The same flow works for hex codes, invoice numbers, URLs, and commands.

## Why it exists

Every clipboard manager remembers *that* you copied something. Omoide remembers *what was in it*:

- **Content search:** FTS5 word search plus trigram substring search for partial IDs and URLs.
- **Screenshot OCR:** offline ONNX models read text from clipboard images; nothing is uploaded.
- **Provenance:** every clip records the source app; clips from the app you are currently using float upward.
- **Habit-aware ranking:** clips you actually paste often rise in the results.
- **Agent surface:** read-only MCP tools let Claude Desktop or Cursor search the same history.
- **Private by default:** password managers are excluded, secret-looking clips are blocked, window titles are off.

### How this differs from other clipboard tools

| Capability | Omoide | Ditto | Windows Clipboard History | Raycast Clipboard |
| --- | --- | --- | --- | --- |
| Content search inside screenshots | **Yes (local OCR)** | No¹ | No¹ | No¹ |
| Substring search for error codes / IDs | **Yes (trigram)** | Partial¹ | Unmeasured | Unmeasured |
| Source-app provenance + same-app boost | **Yes** | Unmeasured | No¹ | Unmeasured |
| Paste-frequency ranking | **Yes** | Unmeasured | No¹ | Unmeasured |
| Read-only MCP tools for coding agents | **Yes** | No¹ | No¹ | No¹ |
| Local-only, no account | **Yes** | Yes¹ | Yes¹ | Partial¹ |
| Free and open source | **Yes (MIT)** | Yes¹ | No¹ | No¹ |

¹ Feature status not independently measured for this project; verify against the current product before citing.

## Install

### From a release

Download `OmoideSetup.exe` from the latest GitHub release, run it, and verify the SHA-256 against `SHA256SUMS`. Omoide installs per-user; no administrator prompt is required.

### From source

```powershell
git clone https://github.com/VikasKSingh05/omoide
cd omoide
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m omoide.cli gui
```

Full instructions: [docs/INSTALL.md](docs/INSTALL.md).

## Keyboard shortcuts

| Key | Action |
| --- | --- |
| `Ctrl+Shift+V` | Summon the overlay (configurable) |
| `↑` / `↓` | Move selection |
| `Enter` | Paste into the previous app |
| `Ctrl+Enter` | Copy only, no synthetic paste |
| `Ctrl+P` | Pin / unpin |
| `Delete` | Delete clip |
| `Esc` | Close overlay or settings |

Search filters: `app:chrome`, `kind:image`, `since:7d`, `pin:true`. Plain words work too.

## CLI

```powershell
omoide find "timeout"
omoide find "invoice" --json
omoide find "CUDA" --app Chrome --since 7
omoide stats
omoide pin 12
omoide rm 12
```

From a source checkout, prefix commands with `.\.venv\Scripts\python.exe -m omoide.cli`.

## MCP for coding agents

MCP access is **off until you enable it** in Omoide → Settings → "Enable MCP tools". The server is stdio-only and read-only: `search_clips`, `get_clip`, `recent_clips`, `clip_stats`. Results are capped at 20 clips and 4,000 characters per clip, wrapped as untrusted clipboard data, and re-scanned for secrets.

Example Claude Desktop configuration (source install):

```json
{
  "mcpServers": {
    "omoide": {
      "command": "C:\\path\\to\\omoide\\.venv\\Scripts\\omoide.exe",
      "args": ["mcp"]
    }
  }
}
```

For a one-off run you can set `OMOIDE_MCP_ENABLED=1` instead of changing settings. The CLI (and therefore `mcp`) ships with a source install; the release `.exe` is the desktop overlay only.

## Measured results

| Metric | Result |
| --- | ---: |
| Search, 100k clips, `timeout` | 18.0 ms median / 29.5 ms p95 |
| Search, 100k clips, rare substring `99381` | 0.24 ms median |
| Index size, 100k clips | 48.4 MB (484 B/clip) |
| OCR, 1080p screenshot, warm | 241 ms median |
| Ranking regression, 5k clips / 24 queries | MRR@10 1.0, Recall@10 1.0 (0.22–0.33 ms median across runs) |

Method, hardware, and caveats: [docs/BENCHMARKS.md](docs/BENCHMARKS.md) and [docs/EVAL.md](docs/EVAL.md).

## Architecture

The core never imports the GUI or Win32 GUI modules. Clipboard, OCR, and foreground-app access arrive as injected providers, so search, ranking, and storage are testable without a desktop session.

```text
clipboard sequence change
  -> capture (text / HTML / image)
  -> sanitizer (secret patterns + app denylist)
  -> provenance (foreground exe -> app name)
  -> store (SQLite + FTS5 word index + trigram index + blob store)
  -> search/rank -> pywebview overlay, CLI, or MCP
```

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Spikes and decisions: [docs/SPIKES.md](docs/SPIKES.md). Privacy: [SECURITY.md](SECURITY.md).

## Testing

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe scripts\eval_ranking.py
.\.venv\Scripts\python.exe scripts\bench_search.py
.\.venv\Scripts\python.exe scripts\check_ocr.py
```

CI runs lint, tests, the ranking check, a PyInstaller build, and a frozen-executable smoke test on `windows-latest`.

## What this is not

- No sync, account, mobile app, or cloud search.
- No RTF fidelity guarantee; plain text and HTML source are captured where available.
- No non-Latin OCR language packs in v1.
- No write/delete tools over MCP — it is deliberately read-only.
- Secret filtering is damage reduction, not a guarantee. See [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).

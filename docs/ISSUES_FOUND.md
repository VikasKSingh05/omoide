# Issues found during dogfooding

| Date | Issue | Severity | Status |
| --- | --- | --- | --- |
| 2026-11-24 | `winsdk` OCR cannot build on Python 3.13 without MSVC | Blocker | Fixed: switched to `rapidocr-onnxruntime` |
| 2026-11-24 | RapidOCR default `limit_type=min` upscales small images and takes ~3 s per 1080p screenshot | High | Fixed: `max/960` + angle classification off, warm median 241 ms |
| 2026-11-24 | Common-word FTS queries were slower than the original <10 ms target (~18–30 ms over 100k clips) | Medium | Accepted and published in `BENCHMARKS.md` |
| 2026-11-24 | index size is 484 B/clip, above the 256 B target | Medium | Accepted: cost of the trigram index |
| 2026-11-24 | WebView2 registry check in the first environment script disagreed with the filesystem check | Low | Fixed: filesystem path is authoritative in `SPIKES.md` |
| 2026-11-24 | Inno Setup is not installed on this machine, so the installer cannot be smoke-tested locally | Medium | Mitigated: release CI builds it |
| 2026-11-24 | `--selftest` was unreliable in the windowed PyInstaller exe; it started the full GUI or hung during GUI imports | High | Fixed: dedicated `omoide/entry.py` checks the trigger and runs the store smoke test before importing pywebview; CI uses `Start-Process -Wait` |
| 2026-11-24 | MCP opt-in message used a Unicode arrow and crashed on a cp1252 console | Medium | Fixed: ASCII `->` used in CLI output |
| 2026-11-24 | First frozen-GUI capture probe changed the clipboard before one-file startup finished and saw no clip | Low | Verified: with a 15 s startup wait the clip is captured; checklist now waits for the tray icon |
| 2026-11-24 | No human-labelled relevance set; the 200-query MRR eval is still open | Medium | Open |
| 2026-11-24 | MCP has a `limit` cap but no cursor pagination | Low | Open |
| 2026-11-24 | WebView2 runtime bootstrapper and clear missing-runtime message are not implemented | Medium | Open |
| 2026-11-24 | Global hotkey, focus restoration and synthetic paste need the `MANUAL_TEST.md` checklist on real apps | High | Open |
| 2026-11-24 | Demo GIF is not recorded | Low | Open |

Add every annoyance here before polishing. Triage before each release.

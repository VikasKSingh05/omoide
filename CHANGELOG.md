# Changelog

All notable changes to this project are documented here.

## [1.0.0] - 2026-11-24

### Added
- SQLite-backed clipboard capture with deduplication and FTS5 word + trigram substring indexes.
- Win32 clipboard change detection via `GetClipboardSequenceNumber`.
- Foreground process provenance with credential-app denylist.
- Offline OCR of clipboard screenshots via RapidOCR, with agent redaction.
- Search overlay UI with keyboard navigation, preview, pin and delete.
- Tray icon, configurable global hotkey, first-run setup, light/dark theme and settings drawer.
- CLI (`find`, `recent`, `stats`, `pin`, `rm`, `mcp`, `gui`).
- Read-only MCP server over stdio, disabled until explicitly enabled in Settings.
- pytest suite, ruff CI, PyInstaller build, Inno Setup script and release workflow.
- Benchmark, spike, ranking-eval and manual-test documentation.

### Changed
- Switched OCR from `winsdk` to `rapidocr-onnxruntime` after the former required MSVC on Python 3.13.
- Tuned RapidOCR to cap the detection side at 960 px, cutting warm 1080p inference from ~3 s to ~241 ms.
- README now publishes measured numbers and an honest limitation list.

### Fixed
- Frozen-exe smoke test now runs from a dedicated entry point before GUI imports, so CI cannot hang on pywebview startup.

## [Unreleased]

- Planned: WebView2 bootstrapper first-run handling, relevance eval with a human-labelled set, cursor pagination for MCP.

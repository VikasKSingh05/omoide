# Manual test checklist

Run this before publishing a release. Automated tests cover the data layer, but hotkeys, focus and clipboard formats need a real desktop.

## Fresh install and first run

- [ ] Install `OmoideSetup.exe`; no administrator prompt appears.
- [ ] Start menu icon launches Omoide; a tray icon appears (one-file startup can take ~10 s).
- [ ] First-run setup opens on step 1 of 3.
- [ ] Capture and OCR checkboxes persist after finishing setup.
- [ ] Hotkey change takes effect without a full restart where possible; otherwise a warning is shown.
- [ ] Theme toggle persists after closing and reopening the overlay.

## Text capture and search

- [ ] Copy `deploy timeout 4812` from Chrome.
- [ ] Press the hotkey; overlay opens and input has focus.
- [ ] Type `timeout`; the clip appears with the term highlighted.
- [ ] Type `4812`; the trigram index still finds it.
- [ ] Press Enter; overlay closes, previous app regains focus, `Ctrl+V` inserts the clip.
- [ ] Paste count increments by one in the preview.
- [ ] Copy the same text again; no duplicate row is created.

## Image OCR

- [ ] Copy a screenshot containing readable text.
- [ ] Search for a word visible only in the image.
- [ ] Result shows as `IMG` with a thumbnail and recognized text.
- [ ] Enter pastes the image, not the OCR text, into the target app.

## Provenance and privacy

- [ ] Copy from VS Code; source shows `VS Code`.
- [ ] Enable window titles, copy again, then disable; title is stored only while enabled.
- [ ] Copy from a password manager (or set one as an excluded app); nothing is captured.
- [ ] Copy a fake `AKIA...` key; only `[blocked: possible credential]` is stored.
- [ ] Screenshot containing a fake secret: image is discarded, stub remains.

## Paste targets

Verify focus restoration and paste in:

- [ ] VS Code
- [ ] Chrome address bar and a text field
- [ ] Windows Terminal / PowerShell
- [ ] Notepad

## Settings and lifecycle

- [ ] Pause capture; new copies are ignored.
- [ ] Resume capture; copies are indexed again.
- [ ] Change retention to 1 day; old clips are removed at startup or settings save.
- [ ] Pin a clip; it ranks above similar unpinned clips.
- [ ] Delete a clip; it disappears and its blob is garbage-collected.
- [ ] Quit from tray; restart; clips and settings survive.
- [ ] Global hotkey works while a fullscreen app is focused.

## MCP

- [ ] MCP disabled by default; `omoide mcp` prints the opt-in message.
- [ ] Enable MCP in Settings; `omoide mcp` starts and stays on stdio.
- [ ] `search_clips` returns wrapped `<clipboard-data>`.
- [ ] A fake secret passed through `get_clip` is redacted.
- [ ] No write/delete tools are advertised.

## Release

- [ ] SHA-256 in `SHA256SUMS` matches the downloaded installer.
- [ ] An external tester installs and finds a clip without instructions.

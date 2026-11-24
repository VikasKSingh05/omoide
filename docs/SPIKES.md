# Day-0 spikes

Run before feature work. Results are recorded here so decisions are reproducible.

## 1. SQLite FTS5 and trigram

- **Status:** passed
- Python 3.13.15 ships SQLite 3.50.4 on this machine.
- `CREATE VIRTUAL TABLE ... USING fts5(...)` and `tokenize='trigram'` both work.
- `LIKE '%fragment%'` uses the trigram index.

## 2. WebView2 runtime

- **Status:** passed on this machine
- `C:\Program Files (x86)\Microsoft\EdgeWebView\Application` contains version `158.0.4370.33`.
- The `pywebview` shell can therefore use the native WebView2 backend. Other Windows 10 machines may need the Evergreen runtime bootstrapper; first-run handling is still to be added.

## 3. OCR engine

- **Status:** switched
- `winsdk` (Windows.Media.Ocr) has no wheel for Python 3.13 here and building it from source requires MSVC, which is not installed. Dropped.
- `rapidocr-onnxruntime` 1.2.3 works fully offline with bundled models.
- Its default `Det.limit_type='min', limit_side_len=736` upscales small images dramatically. Omoide passes `det_limit_type='max', det_limit_side_len=960` and `use_angle_cls=False`.
- Measured on a synthetic 1920x1080 screenshot: first call ~1.3 s (model load), warm median ~240 ms, both target phrases recognized.

## 4. Packaging (PyInstaller)

- **Status:** passed for the executable; installer build is CI-only
- `PyInstaller 6.22.3` produced `dist/Omoide.exe` (~125 MB one-file build) from `omoide.spec`.
- The executable supports a headless store/search check used by CI. The frozen entry point checks for `dist\omoide-selftest.trigger` before importing the GUI, then exits. Launch with `Start-Process -Wait` (the build is `--noconsole`). `OMOIDE_SELFTEST_OUT` captures the result to a file. `OMOIDE_SELFTEST=1` and `--selftest` remain supported for source runs.
- `installer.iss` is ready. Inno Setup is not installed on this development machine, so the installer is built in the release workflow rather than locally.

## 5. Hotkey / synthetic paste

- **Status:** pending real-GUI verification
- Unit tests cover the capture service and suppression logic. A manual check in three apps is still required; see `docs/MANUAL_TEST.md`.

## 6. Search performance (100k clips)

- **Status:** measured, see `BENCHMARKS.md`
- Common-word queries sit around 18–30 ms, rare substring queries under 1 ms.
- The original <10 ms target was not met; the README publishes measured numbers instead.

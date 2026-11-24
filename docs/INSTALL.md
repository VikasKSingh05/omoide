# Install

Windows 10 or 11 only for v1.

## From a GitHub release

1. Download `OmoideSetup.exe` from the latest release.
2. Verify its SHA-256 against `SHA256SUMS` in the same release:
   ```powershell
   Get-FileHash .\OmoideSetup.exe -Algorithm SHA256
   ```
3. Run the installer. It installs per-user; no administrator prompt is required.
4. Launch **Omoide** from the Start menu. It lives in the tray; press **Ctrl+Shift+V** to summon search.
5. Complete the three-step first-run setup. Nothing is sent anywhere.

A standalone `Omoide.exe` is also attached to each release if you prefer not to install.

## From source

```powershell
git clone https://github.com/VikasKSingh05/omoide
cd omoide
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m omoide.cli gui
```

The CLI works without a GUI session:

```powershell
.\.venv\Scripts\python.exe -m omoide.cli find "timeout"
.\.venv\Scripts\python.exe -m omoide.cli stats
```

## Requirements

- WebView2 runtime. Included in Windows 11; Windows 10 may need the [Evergreen runtime](https://developer.microsoft.com/microsoft-edge/webview2/).
- No API keys, account, or network access.

## Data location

Clips, blobs, and settings live in `%APPDATA%\Omoide` unless `OMOIDE_HOME` is set. Deleting that directory removes the entire index. Quit Omoide from the tray before deleting it.

## Enable MCP

MCP is disabled by default. Open the overlay with the hotkey, click the gear icon, and check **Enable MCP tools**. The server uses stdio only; it opens no network listener. To start it, use `omoide mcp` from a source install — the release `.exe` is the desktop overlay only.

## Uninstall

Quit from the tray icon, then run **Uninstall Omoide** from the Start menu. For a source install, delete the virtualenv and `%APPDATA%\Omoide`.

## Known gaps

- The WebView2 bootstrapper is not bundled; a clear first-run message is still to be added for machines without the runtime.
- Global hotkey registration can fail if another app owns the same combination. Change it in Settings; the tray still works.

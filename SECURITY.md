# Security and privacy

## What Omoide does

- Runs entirely on your machine. No account, no telemetry, no cloud search.
- Stores clips in `%APPDATA%\Omoide` (or `OMOIDE_HOME` when set).
- Reads the clipboard only when the Windows clipboard sequence number changes.
- Uses local OCR models bundled with `rapidocr-onnxruntime`.

## What is excluded

- Apps whose process name contains `1password`, `bitwarden`, `keepass`, `kwallet`, `lastpass`, `dashlane`, `enpass`, `authy`, `authenticator`, `credential`, `vault` or `passwords` are never captured.
- Text matching known credential patterns (AWS keys, GitHub tokens, OpenAI-style keys, Slack tokens, JWTs, PEM private keys, `password=`/`token=` assignments with high-entropy values) is replaced with `[blocked: possible credential]`.
- When OCR text in an image looks like a credential, the image itself is discarded.
- Specific apps can be added to the excluded list in Settings.

## Agent access

MCP access is **disabled by default** and must be enabled in Omoide → Settings → "Enable MCP tools". The server is read-only: `search_clips`, `get_clip`, `recent_clips`, `clip_stats`. It has no write or delete tools.

- Response limit: 20 clips and 4,000 characters per clip; callers can lower it with `limit`.
- Clip text is wrapped in `<clipboard-data>` and labelled untrusted data.
- `redact_agent` (on by default) runs the same secret patterns over returned text.
- stdio only; no HTTP listener in v1.
- For a one-off scripted run, `OMOIDE_MCP_ENABLED=1` overrides the setting without persisting it.

## Threat model and limits

- **Local malware or another process running as you** can read the index. Omoide cannot prevent this. Restrict the data directory ACL to your user and encrypt the volume if that matters.
- **False negatives in secret detection are possible.** Pattern matching is damage reduction, not a guarantee. Pause capture when handling credentials or 2FA codes.
- **Screenshots of one-time codes** are searchable if OCR reads them. Delete the clip or pause capture.
- **Window titles** are off by default. If enabled, they are stored as plain text and trimmed to 120 characters.
- The index is sensitive because it contains clipboard content. Do not sync the config directory to shared storage.

## Reporting a vulnerability

Open a private security advisory on the repository, or email the maintainer. Please do not publish details before a fix is available.

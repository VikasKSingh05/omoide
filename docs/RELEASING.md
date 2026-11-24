# Releasing

Releases are built by GitHub Actions from a version tag. Inno Setup is installed in CI, so you do not need it locally.

## Pre-flight

1. Update `pyproject.toml`, `omoide/__init__.py` and `installer.iss` to the same version.
2. Update `CHANGELOG.md` with the release date.
3. Run all checks locally:
   ```powershell
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe -m pytest
   $env:PYTHONPATH='.'
   .\.venv\Scripts\python.exe scripts\eval_ranking.py
   .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean omoide.spec
   $env:OMOIDE_HOME=Join-Path $env:TEMP 'omoide-release-check'
   $env:OMOIDE_SELFTEST_OUT='.\selftest.txt'
   $trigger = '.\dist\omoide-selftest.trigger'
   New-Item -ItemType File -Force $trigger | Out-Null
   try {
     $proc = Start-Process -FilePath '.\dist\Omoide.exe' -Wait -PassThru
     if ($proc.ExitCode -ne 0) { throw "smoke test exited with $($proc.ExitCode)" }
     Get-Content $env:OMOIDE_SELFTEST_OUT
   }
   finally {
     Remove-Item $trigger -ErrorAction SilentlyContinue
   }
   ```
4. Work through `docs/MANUAL_TEST.md`. Do not tag with an unchecked **High** item.

## Tag and publish

```powershell
git checkout main
git pull
git tag v1.0.0
git push origin v1.0.0
```

The `Release` workflow then:

- runs lint and tests,
- builds `dist/Omoide.exe`,
- builds `installer-output/OmoideSetup.exe` with the tag version,
- writes `SHA256SUMS`,
- creates a GitHub release with generated notes and attaches all three files.

## After publishing

- Confirm the three assets are attached and checksums verify.
- Add the demo GIF and updated benchmark table to the release description if the numbers changed.
- Announce the release; add any discovered annoyances to `docs/ISSUES_FOUND.md`.

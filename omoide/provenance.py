"""Where did this clip come from? Win32 implementation plus a testable fake."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Protocol

FRIENDLY_NAMES: dict[str, str] = {
    "chrome.exe": "Chrome",
    "msedge.exe": "Edge",
    "firefox.exe": "Firefox",
    "code.exe": "VS Code",
    "windowsterminal.exe": "Terminal",
    "cmd.exe": "Command Prompt",
    "powershell.exe": "PowerShell",
    "pwsh.exe": "PowerShell",
    "explorer.exe": "Explorer",
    "notepad.exe": "Notepad",
    "outlook.exe": "Outlook",
    "winword.exe": "Word",
    "excel.exe": "Excel",
    "slack.exe": "Slack",
    "discord.exe": "Discord",
    "telegram.exe": "Telegram",
    "whatsapp.exe": "WhatsApp",
    "obsidian.exe": "Obsidian",
    "devenv.exe": "Visual Studio",
    "python.exe": "Python",
    "windows-terminal.exe": "Terminal",
}


@dataclass(frozen=True)
class AppInfo:
    name: str = ""
    title: str = ""


class ForegroundProvider(Protocol):
    def current(self) -> AppInfo: ...


class FakeForegroundProvider:
    def __init__(self, apps: list[AppInfo] | None = None) -> None:
        self.apps = apps or []
        self.index = 0

    def current(self) -> AppInfo:
        if not self.apps:
            return AppInfo()
        app = self.apps[min(self.index, len(self.apps) - 1)]
        self.index += 1
        return app


class Win32ForegroundProvider:
    def __init__(self, *, store_titles: bool = False) -> None:
        self.store_titles = store_titles

    def current(self) -> AppInfo:
        try:
            import win32api
            import win32con
            import win32gui
            import win32process
        except ImportError:
            return AppInfo()

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return AppInfo()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if not handle:
                return AppInfo()
            try:
                path = win32process.GetModuleFileNameEx(handle, 0)
            finally:
                win32api.CloseHandle(handle)

            exe = os.path.basename(path or "").lower()
            name = FRIENDLY_NAMES.get(exe) or os.path.splitext(exe)[0].replace("_", " ").title()
            title = ""
            if self.store_titles:
                title = re.sub(r"[\r\n\t]+", " ", win32gui.GetWindowText(hwnd))[:120].strip()
            return AppInfo(name=name, title=title)
        except Exception:
            # Provenance is a bonus; it must never break capture.
            return AppInfo()


def friendly_name(exe: str) -> str:
    lowered = (exe or "").lower()
    return FRIENDLY_NAMES.get(lowered) or os.path.splitext(lowered)[0].title()

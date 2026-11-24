"""Read the Windows clipboard only when it actually changed."""

from __future__ import annotations

import ctypes
import re
from typing import Protocol

from PIL import Image, ImageGrab

from .models import CapturedClip

HTML_HEADER_RE = re.compile(
    rb"StartHTML:(-?\d+).*?EndHTML:(-?\d+).*?StartFragment:(-?\d+).*?EndFragment:(-?\d+)",
    re.S,
)


class ClipboardReader(Protocol):
    def sequence(self) -> int: ...

    def read(self) -> CapturedClip | None: ...


class FakeClipboardReader:
    """Returns queued clips one at a time; useful without a real clipboard."""

    def __init__(self, clips: list[CapturedClip] | None = None) -> None:
        self.clips = list(clips or [])
        self.seq = 0

    def sequence(self) -> int:
        # A queued clip counts as a change so poll_once() actually reads it.
        return self.seq + 1 if self.clips else self.seq

    def read(self) -> CapturedClip | None:
        if not self.clips:
            return None
        self.seq += 1
        return self.clips.pop(0)


class Win32ClipboardReader:
    def sequence(self) -> int:
        try:
            return int(ctypes.windll.user32.GetClipboardSequenceNumber())
        except Exception:
            return 0

    def read(self) -> CapturedClip | None:
        try:
            import win32clipboard
        except ImportError:
            return None

        try:
            win32clipboard.OpenClipboard()
        except Exception:
            return None

        formats: set[int] = set()
        text = ""
        html: str | None = None
        try:
            fmt = 0
            while True:
                fmt = win32clipboard.EnumClipboardFormats(fmt)
                if not fmt:
                    break
                formats.add(fmt)

            if win32clipboard.CF_UNICODETEXT in formats:
                value = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                text = value or ""
            if "HTML Format" in _format_names(win32clipboard, formats):
                html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
                try:
                    raw = win32clipboard.GetClipboardData(html_format)
                    if isinstance(raw, bytes):
                        html = _html_fragment(raw)
                except Exception:
                    html = None
        except Exception:
            text = ""
        finally:
            win32clipboard.CloseClipboard()

        if text.strip() or (html and html.strip()):
            return CapturedClip(
                kind="html" if html else "text",
                text=text[:100_000],
                html=(html or None),
            )

        if win32clipboard.CF_DIB in formats:
            try:
                image = ImageGrab.grabclipboard()
            except Exception:
                return None
            if isinstance(image, Image.Image):
                return CapturedClip(kind="image", image=image)

        return None


def _format_names(win32clipboard: object, formats: set[int]) -> set[str]:
    names: set[str] = set()
    for fmt in formats:
        if fmt in (1, 2, 3, 13):
            continue
        try:
            names.add(win32clipboard.GetClipboardFormatName(fmt))  # type: ignore[attr-defined]
        except Exception:
            continue
    return names


def _html_fragment(raw: bytes) -> str:
    """Extract the HTML fragment from CF_HTML without trusting its offsets."""
    match = HTML_HEADER_RE.search(raw[:4096])
    if not match:
        return ""
    start, end = int(match.group(3)), int(match.group(4))
    if start < 0 or end <= start or end > len(raw):
        return ""
    return raw[start:end].decode("utf-8", errors="replace")[:50_000]

"""Restore a clip to the clipboard and paste it into the previous app."""

from __future__ import annotations

import ctypes
import struct
from pathlib import Path
from typing import Protocol

from PIL import Image

from .models import ClipRow


class ClipboardWriter(Protocol):
    def write_text(self, text: str, html: str | None = None) -> None: ...

    def write_image(self, image: Image.Image) -> None: ...


class FakeClipboardWriter:
    def __init__(self) -> None:
        self.text: str | None = None
        self.html: str | None = None
        self.image: Image.Image | None = None

    def write_text(self, text: str, html: str | None = None) -> None:
        self.text = text
        self.html = html

    def write_image(self, image: Image.Image) -> None:
        self.image = image


class Win32ClipboardWriter:
    def write_text(self, text: str, html: str | None = None) -> None:
        import win32clipboard
        import win32con

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            if html:
                html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
                win32clipboard.SetClipboardData(html_format, _wrap_html(html))
        finally:
            win32clipboard.CloseClipboard()

    def write_image(self, image: Image.Image) -> None:
        import win32clipboard
        import win32con

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_DIB, _dib_bytes(image))
        finally:
            win32clipboard.CloseClipboard()


class PasteController:
    def __init__(
        self,
        writer: ClipboardWriter,
        blobs_dir: Path,
        *,
        send_keys: bool = True,
        key_sender: object | None = None,
    ) -> None:
        self.writer = writer
        self.blobs_dir = blobs_dir
        self.send_keys = send_keys
        self.key_sender = key_sender

    def apply(self, clip: ClipRow) -> None:
        if clip.kind == "image" and clip.blob_hash:
            path = blob_path(self.blobs_dir, clip.blob_hash)
            if path.exists():
                with Image.open(path) as image:
                    self.writer.write_image(image.copy())
                    return
        self.writer.write_text(clip.text, clip.html)

    def send_paste(self) -> None:
        if not self.send_keys:
            return
        sender = self.key_sender
        if sender is None:
            import keyboard

            sender = keyboard
        sender.send("ctrl+v")  # type: ignore[attr-defined]

    def paste(self, clip: ClipRow) -> None:
        self.apply(clip)
        self.send_paste()

    def last_written_hash(self, clip: ClipRow) -> str | None:
        """Used by the capture service to ignore the paste we just performed."""
        return clip.blob_hash or None


def blob_path(blobs_dir: Path, digest: str) -> Path:
    return blobs_dir / digest[:2] / f"{digest}.png"


def _dib_bytes(image: Image.Image) -> bytes:
    """CF_DIB: BITMAPINFOHEADER plus bottom-up 32-bit BGRA rows."""
    rgba = image.convert("RGBA")
    width, height = rgba.size
    source = rgba.tobytes()
    bgra = bytearray(len(source))
    bgra[0::4] = source[2::4]
    bgra[1::4] = source[1::4]
    bgra[2::4] = source[0::4]
    bgra[3::4] = source[3::4]

    row_size = width * 4
    header = struct.pack(
        "<IiiHHIIiiII",
        40,
        width,
        height,
        1,
        32,
        0,
        row_size * height,
        0,
        0,
        0,
        0,
    )
    rows = b"".join(bgra[y * row_size : (y + 1) * row_size] for y in reversed(range(height)))
    return header + rows


def _wrap_html(html: str) -> bytes:
    """Wrap an HTML fragment in the CF_HTML envelope Windows expects."""
    prefix = "<html><body><!--StartFragment-->"
    suffix = "<!--EndFragment--></body></html>"
    body = (prefix + html + suffix).encode("utf-8")
    prefix_bytes = len(prefix.encode("utf-8"))
    html_bytes = len(html.encode("utf-8"))

    def header(start_html: int, end_html: int, start_frag: int, end_frag: int) -> bytes:
        return (
            "Version:0.9\r\n"
            f"StartHTML:{start_html:010d}\r\n"
            f"EndHTML:{end_html:010d}\r\n"
            f"StartFragment:{start_frag:010d}\r\n"
            f"EndFragment:{end_frag:010d}\r\n"
        ).encode("ascii")

    head = header(0, 0, 0, 0)
    return header(
        len(head),
        len(head) + len(body),
        len(head) + prefix_bytes,
        len(head) + prefix_bytes + html_bytes,
    ) + body


def restore_focus(hwnd: int) -> None:
    """Best-effort: give focus back to the window that was active before summon."""
    if not hwnd:
        return
    try:
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

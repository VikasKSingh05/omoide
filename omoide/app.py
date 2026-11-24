"""Desktop overlay: pywebview window, tray icon, hotkey and the JS bridge."""

from __future__ import annotations

import ctypes
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import webview

from .bootstrap import selftest_requested
from .capture import Win32ClipboardReader
from .config import Settings
from .ocr import NoopOcrEngine, RapidOcrEngine
from .paste import PasteController, Win32ClipboardWriter, restore_focus
from .provenance import Win32ForegroundProvider
from .selftest import run as run_selftest
from .service import CaptureService
from .store import Store

UI_PATH = Path(__file__).parent / "ui" / "index.html"


class OmoideApp:
    """Public methods are exposed to JavaScript as `window.pywebview.api`."""

    def __init__(self) -> None:
        self.settings = Settings.load()
        self.store = Store(self.settings.db_path, self.settings.blobs_dir)
        self.store.open()
        self.store.cleanup(self.settings.retention_days)

        self.provider = Win32ForegroundProvider(store_titles=self.settings.store_titles)
        self.ocr_engine = RapidOcrEngine() if self.settings.ocr_enabled else NoopOcrEngine()
        self.service = CaptureService(
            self.settings,
            self.store,
            Win32ClipboardReader(),
            self.provider,
            self.ocr_engine,
        )
        self.paster = PasteController(
            Win32ClipboardWriter(), self.settings.blobs_dir
        )
        self.window: Any = None
        self.icon: Any = None
        self._previous_hwnd = 0
        self._closing = False

    # -- JavaScript API --------------------------------------------------

    def search(self, query: str = "") -> dict[str, Any]:
        started = time.perf_counter()
        hits = self.store.search(
            query,
            limit=30,
            foreground_app=self.provider.current().name,
        )
        return {
            "hits": [hit.to_dict() for hit in hits],
            "count": len(hits),
            "took_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    def paste(self, clip_id: int) -> dict[str, Any]:
        clip = self.store.get(int(clip_id))
        if clip is None:
            return {"ok": False, "error": "clip not found"}
        self.service.suppress_paste(clip.text)
        self.paster.apply(clip)
        self.hide()
        restore_focus(self._previous_hwnd)
        self.paster.send_paste()
        self.store.record_paste(int(clip_id))
        return {"ok": True}

    def copy_only(self, clip_id: int) -> dict[str, Any]:
        clip = self.store.get(int(clip_id))
        if clip is None:
            return {"ok": False, "error": "clip not found"}
        self.service.suppress_paste(clip.text)
        self.paster.apply(clip)
        return {"ok": True}

    def pin(self, clip_id: int, pinned: bool = True) -> dict[str, Any]:
        self.store.pin(int(clip_id), bool(pinned))
        return {"ok": True}

    def delete(self, clip_id: int) -> dict[str, Any]:
        self.store.delete(int(clip_id))
        return {"ok": True}

    def get_settings(self) -> dict[str, Any]:
        return asdict(self.settings)

    def update_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(patch, dict):
            return {"ok": False, "error": "invalid settings"}
        self.settings.update(patch)
        self.settings.save()
        self.provider.store_titles = self.settings.store_titles
        if "ocr_enabled" in patch:
            self.ocr_engine = (
                RapidOcrEngine() if self.settings.ocr_enabled else NoopOcrEngine()
            )
            self.service.ocr = self.ocr_engine
        if "retention_days" in patch:
            self.store.cleanup(self.settings.retention_days)
        if "hotkey" in patch:
            self._register_hotkey()
        if not self.settings.capture_enabled:
            self.service._last_sequence = Win32ClipboardReader().sequence()
        return {"ok": True}

    def get_stats(self) -> dict[str, Any]:
        return self.store.stats()

    def get_image(self, digest: str | None) -> str:
        return self.store.blob_data_url(digest)

    def show(self) -> None:
        try:
            self._previous_hwnd = int(ctypes.windll.user32.GetForegroundWindow())
        except Exception:
            self._previous_hwnd = 0
        if self.window is None:
            return
        if not self.window.visible:
            self.window.show()
        self.window.evaluate_js(
            "document.getElementById('search')?.focus();"
            "window.omoideFocus && window.omoideFocus();"
        )

    def hide(self) -> None:
        if self.window is not None:
            self.window.hide()

    def quit(self) -> dict[str, Any]:
        self._shutdown()
        return {"ok": True}

    # -- lifecycle ------------------------------------------------------

    def set_window(self, window: Any) -> None:
        self.window = window
        window.events.closing += self._shutdown

    def start_capture(self) -> None:
        threading.Thread(target=self.service.run, name="omoide-capture", daemon=True).start()

    def _register_hotkey(self) -> None:
        try:
            import keyboard

            keyboard.unhook_all_hotkeys()
            keyboard.add_hotkey(self.settings.hotkey, self.show, suppress=False)
        except Exception as exc:
            # The UI still works via the tray; report it rather than crashing.
            print(f"hotkey registration failed: {exc}")

    def _run_tray(self) -> None:
        import pystray
        from PIL import Image, ImageDraw, ImageFont

        image = Image.new("RGBA", (64, 64), (18, 19, 26, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((4, 4, 60, 60), radius=16, fill=(72, 94, 172, 255))
        try:
            font = ImageFont.load_default(size=34)  # type: ignore[call-arg]
        except TypeError:
            font = ImageFont.load_default()
        draw.text((22, 10), "O", font=font, fill=(245, 246, 250, 255))

        def toggle_capture(icon: Any, _item: Any) -> None:
            self.settings.capture_enabled = not self.settings.capture_enabled
            self.settings.save()
            icon.update_menu()

        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda *_: self.show(), default=True),
            pystray.MenuItem(
                "Pause capture" if self.settings.capture_enabled else "Resume capture",
                toggle_capture,
            ),
            pystray.MenuItem("Quit", lambda *_: self.quit()),
        )
        self.icon = pystray.Icon("Omoide", image, "Omoide", menu)
        self.icon.run()

    def _shutdown(self, *_args: Any) -> None:
        if self._closing:
            return
        self._closing = True
        self.service.stop()
        try:
            if self.icon is not None:
                self.icon.stop()
        except Exception:
            pass
        try:
            self.store.close()
        except Exception:
            pass


def selftest() -> int:
    """Backwards-compatible wrapper for the standalone smoke check."""
    return run_selftest()


def main() -> None:
    if selftest_requested():
        raise SystemExit(selftest())

    app = OmoideApp()
    app.start_capture()
    threading.Thread(target=app._run_tray, name="omoide-tray", daemon=True).start()

    window = webview.create_window(
        "Omoide",
        UI_PATH.as_uri(),
        js_api=app,
        width=920,
        height=620,
        min_size=(620, 420),
        frameless=True,
        easy_drag=False,
        on_top=True,
        resizable=True,
    )
    app.set_window(window)
    webview.start(app._register_hotkey, debug=False)


if __name__ == "__main__":
    main()

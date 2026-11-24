"""The background capture loop. Deliberately dependency-injected for tests."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .capture import ClipboardReader
from .config import Settings
from .models import CapturedClip, ClipRow
from .ocr import OcrEngine
from .provenance import ForegroundProvider
from .sanitizer import Sanitizer, is_blocked_app
from .store import Store


class CaptureService:
    def __init__(
        self,
        settings: Settings,
        store: Store,
        reader: ClipboardReader,
        provenance: ForegroundProvider,
        ocr: OcrEngine,
        *,
        on_capture: Callable[[ClipRow], None] | None = None,
        now_ms: Callable[[], int] | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.reader = reader
        self.provenance = provenance
        self.ocr = ocr
        self.on_capture = on_capture
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))
        self._last_sequence = reader.sequence()
        self._suppress_until = 0
        self._suppress_text = ""
        self._stop = threading.Event()

    def suppress_paste(self, text: str, *, window_ms: int = 1_200) -> None:
        """Ignore the clipboard write we just made when pasting a clip."""
        self._suppress_until = self.now_ms() + window_ms
        self._suppress_text = text

    def poll_once(self) -> ClipRow | None:
        now = self.now_ms()
        sequence = self.reader.sequence()
        if sequence == self._last_sequence:
            return None
        self._last_sequence = sequence

        captured = self.reader.read()
        if captured is None:
            return None
        if now < self._suppress_until and captured.text == self._suppress_text:
            return None

        app = self.provenance.current()
        if self._is_excluded(app.name):
            return None

        if captured.kind == "image" and self.settings.ocr_enabled:
            try:
                captured.text = self.ocr.recognize(captured.image)  # type: ignore[arg-type]
            except Exception:
                captured.text = ""

        if len(captured.text.encode("utf-8", errors="replace")) > self.settings.max_text_bytes:
            captured.text = captured.text[: self.settings.max_text_bytes // 2]
        if captured.html and len(captured.html) > 50_000:
            captured.html = None
        if captured.image is not None and captured.image.width * captured.image.height > 40_000_000:
            captured.image = None

        sanitizer = Sanitizer(
            extra_blocked_apps=tuple(self.settings.excluded_apps),
            redact_agent=self.settings.redact_agent,
        )
        decision = sanitizer.check(captured.text, app.name)
        blocked = not decision.allowed
        if blocked:
            # Do not keep the screenshot itself if it contained a credential.
            captured = CapturedClip(
                kind=captured.kind,
                text=decision.text,
                html=None,
                image=None,
            )

        clip = self.store.add(
            captured,
            source_app=app.name,
            source_title=app.title if self.settings.store_titles else "",
            blocked=blocked,
            created_at=now,
        )
        if clip is not None and self.on_capture is not None:
            self.on_capture(clip)
        return clip

    def run(self) -> None:
        self._stop.clear()
        while not self._stop.is_set():
            if self.settings.capture_enabled:
                try:
                    self.poll_once()
                except Exception:
                    # A bad clipboard format must never kill the daemon.
                    pass
            else:
                self._last_sequence = self.reader.sequence()
            self._stop.wait(max(0.05, self.settings.poll_ms / 1000))

    def stop(self) -> None:
        self._stop.set()

    def _is_excluded(self, app_name: str) -> bool:
        if not app_name:
            return False
        if is_blocked_app(app_name):
            return True
        lowered = app_name.lower()
        return any(item and item.lower() in lowered for item in self.settings.excluded_apps)

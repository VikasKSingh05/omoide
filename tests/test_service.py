from PIL import Image

from omoide.capture import FakeClipboardReader
from omoide.config import Settings
from omoide.models import CapturedClip
from omoide.ocr import FakeOcrEngine
from omoide.provenance import AppInfo, FakeForegroundProvider
from omoide.service import CaptureService


def make_service(store, clips, apps, *, ocr_text="", excluded=()):
    settings = Settings(excluded_apps=list(excluded))
    service = CaptureService(
        settings,
        store,
        FakeClipboardReader(clips),
        FakeForegroundProvider(apps),
        FakeOcrEngine(ocr_text),
        now_ms=lambda: 1_700_000_000_000,
    )
    # The fake starts with clips already queued, so mark the first poll as a change.
    service._last_sequence = -1
    return service


def test_capture_records_provenance(store):
    service = make_service(
        store,
        [CapturedClip(kind="text", text="hello from chrome")],
        [AppInfo(name="Chrome")],
    )
    clip = service.poll_once()
    assert clip is not None
    assert clip.source_app == "Chrome"
    assert store.search("hello")


def test_ocr_text_becomes_searchable(store):
    service = make_service(
        store,
        [CapturedClip(kind="image", image=Image.new("RGB", (4, 4)))],
        [AppInfo(name="Chrome")],
        ocr_text="CUDA error in screenshot",
    )
    clip = service.poll_once()
    assert clip is not None
    assert "CUDA" in clip.text
    assert store.search("CUDA")


def test_secret_is_not_indexed(store):
    service = make_service(
        store,
        [CapturedClip(kind="text", text="AKIAIOSFODNN7EXAMPLE")],
        [AppInfo(name="Chrome")],
    )
    clip = service.poll_once()
    assert clip is not None and clip.blocked
    assert not store.search("AKIA")


def test_excluded_app_and_self_paste_suppression(store):
    service = make_service(
        store,
        [
            CapturedClip(kind="text", text="from 1Password"),
            CapturedClip(kind="text", text="pasted back"),
        ],
        [AppInfo(name="1Password"), AppInfo(name="Chrome")],
    )
    assert service.poll_once() is None
    service.suppress_paste("pasted back", window_ms=10_000)
    assert service.poll_once() is None


def test_no_change_means_no_capture(store):
    service = make_service(store, [], [])
    assert service.poll_once() is None

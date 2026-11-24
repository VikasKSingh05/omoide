from PIL import Image

from omoide.models import CapturedClip


def test_add_and_search(store):
    clip = store.add(
        CapturedClip(kind="text", text="the deploy timeout was 30 seconds"),
        source_app="Terminal",
        created_at=1_700_000_000_000,
    )
    assert clip is not None

    hits = store.search("deploy timeout")
    assert [hit.clip.id for hit in hits] == [clip.id]
    assert hits[0].terms == ["deploy", "timeout"]
    assert "timeout" in hits[0].snippet


def test_dedupe(store):
    first = store.add(CapturedClip(kind="text", text="duplicate me"), source_app="Chrome")
    second = store.add(CapturedClip(kind="text", text="duplicate me"), source_app="Chrome")
    assert first is not None
    assert second is None
    assert store.stats()["total"] == 1


def test_substring_search_on_ids(store):
    store.add(CapturedClip(kind="text", text="order AB-99381 shipped"), source_app="Mail")
    assert store.search("99381")


def test_pin_paste_and_delete(store):
    clip = store.add(CapturedClip(kind="text", text="remember this"), source_app="Chrome")
    assert clip is not None
    store.pin(clip.id, True)
    store.record_paste(clip.id)
    updated = store.get(clip.id)
    assert updated is not None
    assert updated.pinned is True
    assert updated.paste_count == 1
    store.delete(clip.id)
    assert store.get(clip.id) is None


def test_image_clip_stores_blob_and_ocr_text(store):
    image = Image.new("RGB", (8, 8), (255, 0, 0))
    clip = store.add(
        CapturedClip(kind="image", text="CUDA out of memory", image=image),
        source_app="Chrome",
    )
    assert clip is not None and clip.blob_hash
    assert store.search("CUDA")
    assert store.blob_data_url(clip.blob_hash).startswith("data:image/png;base64,")


def test_filters(store):
    store.add(CapturedClip(kind="text", text="invoice 42"), source_app="Chrome")
    store.add(CapturedClip(kind="image", text="invoice screenshot"), source_app="Mail")
    assert len(store.search("invoice", limit=10)) == 2
    assert all(h.clip.source_app == "Chrome" for h in store.search("invoice app:chrome"))
    assert all(h.clip.kind == "image" for h in store.search("invoice kind:image"))


def test_stats_and_retention(store):
    store.add(
        CapturedClip(kind="text", text="old clip"), source_app="Chrome", created_at=1_000
    )
    store.add(
        CapturedClip(kind="text", text="new clip"),
        source_app="Chrome",
        created_at=9_999_999_999_999,
    )
    stats = store.stats()
    assert stats["total"] == 2
    assert store.cleanup(retention_days=1) == 1
    assert store.stats()["total"] == 1

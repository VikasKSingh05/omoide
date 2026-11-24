"""Small end-to-end smoke test using OMOIDE_HOME as an isolated data dir."""

from omoide.config import Settings
from omoide.models import CapturedClip
from omoide.search import parse_query
from omoide.store import Store


def main() -> None:
    settings = Settings.load()
    store = Store(settings.db_path, settings.blobs_dir)
    store.open()
    try:
        store.add(
            CapturedClip(kind="text", text="deploy timeout was 30 seconds on Tuesday"),
            source_app="Terminal",
        )
        store.add(
            CapturedClip(kind="text", text="invoice AB-99381 is ready"),
            source_app="Chrome",
        )
        query = "timeout"
        hits = store.search(query)
        print("data dir:", settings.db_path.parent)
        print("stats:", store.stats())
        print("query:", parse_query(query))
        print("hits:", [(hit.clip.id, hit.clip.text, hit.score) for hit in hits])
    finally:
        store.close()


if __name__ == "__main__":
    main()

from pathlib import Path

import pytest

from omoide.store import Store


@pytest.fixture
def store(tmp_path: Path):
    instance = Store(tmp_path / "omoide.sqlite3", tmp_path / "blobs")
    instance.open()
    yield instance
    instance.close()

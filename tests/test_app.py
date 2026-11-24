from omoide.app import selftest


def test_selftest_uses_isolated_store(tmp_path, monkeypatch):
    output = tmp_path / "selftest.txt"
    monkeypatch.setenv("OMOIDE_SELFTEST_OUT", str(output))

    assert selftest() == 0
    assert output.read_text(encoding="utf-8").startswith("ok: clip 1")

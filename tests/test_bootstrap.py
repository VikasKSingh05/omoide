import sys

from omoide import bootstrap


def test_selftest_requested_by_trigger(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["Omoide.exe"])
    monkeypatch.delenv("OMOIDE_SELFTEST", raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Omoide.exe"))

    assert not bootstrap.selftest_requested()

    (tmp_path / "omoide-selftest.trigger").write_text("", encoding="utf-8")

    assert bootstrap.selftest_requested()


def test_selftest_requested_by_env_and_argv(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Omoide.exe"))
    monkeypatch.delenv("OMOIDE_SELFTEST", raising=False)

    monkeypatch.setattr(sys, "argv", ["Omoide.exe", "--selftest"])
    assert bootstrap.selftest_requested()

    monkeypatch.setattr(sys, "argv", ["Omoide.exe"])
    monkeypatch.setenv("OMOIDE_SELFTEST", "1")
    assert bootstrap.selftest_requested()

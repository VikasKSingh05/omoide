from omoide.config import Settings


def test_defaults_are_private():
    settings = Settings()
    assert settings.capture_enabled is True
    assert settings.store_titles is False
    assert settings.redact_agent is True
    assert settings.mcp_enabled is False
    assert settings.onboarded is False


def test_update_ignores_unknown_keys():
    settings = Settings()
    settings.update({"theme": "light", "not_a_setting": True})
    assert settings.theme == "light"
    assert not hasattr(settings, "not_a_setting")


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("OMOIDE_HOME", str(tmp_path))
    settings = Settings(hotkey="ctrl+alt+v", onboarded=True, excluded_apps=["Slack"])
    settings.save()

    loaded = Settings.load()
    assert loaded.hotkey == "ctrl+alt+v"
    assert loaded.onboarded is True
    assert loaded.excluded_apps == ["Slack"]
    assert loaded.db_path == tmp_path / "omoide.sqlite3"

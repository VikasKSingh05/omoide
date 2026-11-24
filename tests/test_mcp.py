import pytest

from omoide.config import Settings
from omoide.mcp_server import _as_text, _clip_payload, serve
from omoide.sanitizer import Sanitizer


def test_payload_redacts_and_budgets_text():
    payload = _clip_payload(
        {
            "id": 7,
            "kind": "text",
            "text": "token = ghp_abcdefghijklmnopqrstuvwxyz0123456789 " + "x" * 5000,
            "source_app": "Chrome",
            "created_at": 1,
            "paste_count": 0,
            "pinned": False,
            "score": 1.0,
        },
        Sanitizer(),
    )
    assert "ghp_" not in payload["text"]
    assert "[redacted]" in payload["text"]
    assert len(payload["text"]) <= 4000
    assert "html" not in payload


def test_wrapper_marks_content_as_untrusted():
    wrapped = _as_text([{"id": 1}])
    assert wrapped.startswith("<clipboard-data>")
    assert "untrusted clipboard content" in wrapped
    assert wrapped.endswith("</clipboard-data>")


def test_serve_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("OMOIDE_MCP_ENABLED", raising=False)
    monkeypatch.setattr(Settings, "load", classmethod(lambda cls: cls(mcp_enabled=False)))
    with pytest.raises(SystemExit):
        serve()

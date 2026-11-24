from omoide.sanitizer import Sanitizer


def test_detects_secrets():
    sanitizer = Sanitizer()
    decision = sanitizer.check("my key is AKIAIOSFODNN7EXAMPLE", "Chrome")
    assert not decision.allowed
    assert decision.blocked
    assert "secret" in decision.reason


def test_blocks_password_managers():
    sanitizer = Sanitizer()
    decision = sanitizer.check("something harmless", "1Password")
    assert not decision.allowed
    assert decision.reason == "blocked source app"


def test_allows_normal_text():
    sanitizer = Sanitizer()
    decision = sanitizer.check("deploy timeout in staging", "VS Code")
    assert decision.allowed and decision.text == "deploy timeout in staging"


def test_redact_for_agents():
    sanitizer = Sanitizer()
    result = sanitizer.redact("token = ghp_abcdefghijklmnopqrstuvwxyz0123456789")
    assert "ghp_" not in result
    assert "[redacted]" in result

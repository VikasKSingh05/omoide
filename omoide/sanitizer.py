"""Keep credentials and blocked sources out of the index."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Best-effort damage reduction, not a guarantee. See SECURITY.md.
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.I)
    for pattern in (
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"\bAKIA[0-9A-Z]{16}\b",
        r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
        r"github_pat_[A-Za-z0-9_]{20,}",
        r"\bsk-[A-Za-z0-9_-]{20,}\b",
        r"\bsk_live_[A-Za-z0-9]{16,}\b",
        r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
        r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
        r"(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9+/=_-]{16,}",
    )
)

# Password managers and credential helpers should never be indexed.
BLOCKED_APP_PARTS: tuple[str, ...] = (
    "1password",
    "bitwarden",
    "keepass",
    "kwallet",
    "lastpass",
    "dashlane",
    "enpass",
    "authy",
    "authenticator",
    "credential",
    "vault",
    "passwords",
)


def is_blocked_app(app_name: str) -> bool:
    lowered = (app_name or "").lower()
    return any(part in lowered for part in BLOCKED_APP_PARTS)


@dataclass
class Decision:
    allowed: bool
    text: str
    reason: str = ""
    blocked: bool = False


class Sanitizer:
    def __init__(
        self,
        *,
        extra_blocked_apps: tuple[str, ...] = (),
        redact_agent: bool = True,
    ) -> None:
        self.blocked_parts = BLOCKED_APP_PARTS + tuple(
            item.lower() for item in extra_blocked_apps if item
        )
        self.redact_agent = redact_agent

    def check(self, text: str, source_app: str) -> Decision:
        lowered_app = (source_app or "").lower()
        if any(part in lowered_app for part in self.blocked_parts):
            return Decision(False, "", "blocked source app", True)
        if self._has_secret(text):
            return Decision(False, "[blocked: possible credential]", "secret pattern", True)
        return Decision(True, text)

    def redact(self, text: str) -> str:
        """Used before returning clip content to an agent."""
        if not self.redact_agent:
            return text
        for pattern in SECRET_PATTERNS:
            text = pattern.sub("[redacted]", text)
        return text

    @staticmethod
    def _has_secret(text: str) -> bool:
        return any(pattern.search(text) for pattern in SECRET_PATTERNS)

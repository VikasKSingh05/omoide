"""Startup checks that must run before any GUI libraries are imported."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def selftest_requested() -> bool:
    """Return True for source flags or the frozen-exe sentinel file."""
    trigger = Path(sys.executable).with_name("omoide-selftest.trigger")
    return (
        "--selftest" in sys.argv
        or os.environ.get("OMOIDE_SELFTEST") == "1"
        or trigger.exists()
    )


def maybe_run_selftest() -> None:
    """Run the headless check and exit before loading pywebview, if requested."""
    if selftest_requested():
        from .selftest import run

        raise SystemExit(run())

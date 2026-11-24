"""PyInstaller entry point: run headless checks before importing the GUI."""

from __future__ import annotations

from omoide.bootstrap import maybe_run_selftest


def run() -> None:
    maybe_run_selftest()
    from omoide.app import main

    main()


if __name__ == "__main__":
    run()

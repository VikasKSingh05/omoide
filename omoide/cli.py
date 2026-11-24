"""Command-line sibling of the desktop app."""

from __future__ import annotations

import json
import os
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from .config import Settings
from .store import Store

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


def _open_store() -> tuple[Store, Settings]:
    settings = Settings.load()
    store = Store(settings.db_path, settings.blobs_dir)
    store.open()
    store.cleanup(settings.retention_days)
    return store, settings


def _relative(timestamp_ms: int) -> str:
    seconds = max(0, int((datetime.now().timestamp() * 1000 - timestamp_ms) / 1000))
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86_400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86_400}d ago"


@app.command()
def find(
    query: str = typer.Argument(..., help="Words, or filters like app:chrome kind:image"),
    limit: int = typer.Option(20, "--limit", "-n"),
    as_json: bool = typer.Option(False, "--json"),
    app_filter: str | None = typer.Option(None, "--app"),
    since: int | None = typer.Option(None, "--since", help="Only clips from the last N days"),
) -> None:
    """Search clips by what was in them."""
    raw = query
    if app_filter:
        raw += f" app:{app_filter}"
    if since:
        raw += f" since:{since}d"
    store, _ = _open_store()
    try:
        hits = store.search(raw, limit=limit)
    finally:
        store.close()

    if as_json:
        console.print_json(json.dumps([hit.to_dict() for hit in hits], ensure_ascii=False))
        return
    if not hits:
        console.print("[dim]No matching clips.[/dim]")
        return

    table = Table(box=None, header_style="bold cyan")
    table.add_column("ID", justify="right", no_wrap=True)
    table.add_column("When", no_wrap=True)
    table.add_column("Source", no_wrap=True)
    table.add_column("Kind", no_wrap=True)
    table.add_column("Text")
    for hit in hits:
        clip = hit.clip
        text = hit.snippet.replace("\n", " ")
        if clip.pinned:
            text = "[yellow]PIN[/yellow] " + text
        table.add_row(
            str(clip.id),
            _relative(clip.created_at),
            clip.source_app or "-",
            clip.kind,
            text,
        )
    console.print(table)


@app.command()
def recent(limit: int = typer.Option(20, "--limit", "-n")) -> None:
    """List the newest clips."""
    store, _ = _open_store()
    try:
        clips = store.recent(limit)
    finally:
        store.close()
    for clip in clips:
        console.print(
            f"[cyan]{clip.id:>6}[/cyan]  {_relative(clip.created_at):<10}"
            f"  {(clip.source_app or '-'):<18}  {clip.text[:100]!r}"
        )


@app.command()
def stats() -> None:
    """Show index statistics."""
    store, _ = _open_store()
    try:
        data = store.stats()
    finally:
        store.close()
    for key, value in data.items():
        console.print(f"{key}: {value}")


@app.command()
def pin(clip_id: int, value: bool = typer.Option(True, "--value/--unpin")) -> None:
    """Pin or unpin a clip."""
    store, _ = _open_store()
    try:
        store.pin(clip_id, value)
    finally:
        store.close()
    console.print(f"clip {clip_id} pinned={value}")


@app.command(name="rm")
def remove(clip_id: int) -> None:
    """Delete a clip."""
    store, _ = _open_store()
    try:
        store.delete(clip_id)
    finally:
        store.close()
    console.print(f"clip {clip_id} deleted")


@app.command()
def mcp() -> None:
    """Start the read-only MCP server on stdio."""
    settings = Settings.load()
    if not settings.mcp_enabled and os.environ.get("OMOIDE_MCP_ENABLED") != "1":
        console.print(
            "[red]MCP access is disabled.[/red] Enable it in Omoide -> Settings, "
            "or set OMOIDE_MCP_ENABLED=1 for a one-off run."
        )
        raise typer.Exit(code=1)
    from .mcp_server import serve

    serve()


@app.command()
def gui() -> None:
    """Start the desktop overlay."""
    from .app import main as app_main

    app_main()


if __name__ == "__main__":
    app()

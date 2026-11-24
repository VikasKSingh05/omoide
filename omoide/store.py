"""SQLite storage with two indexes: words (FTS5) and substrings (trigram)."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from .models import CapturedClip, ClipRow, SearchHit
from .paste import blob_path
from .ranking import score_hit
from .search import build_fts_expression, make_snippet, parse_query

SCHEMA = """
CREATE TABLE IF NOT EXISTS clips (
  id INTEGER PRIMARY KEY,
  created_at INTEGER NOT NULL,
  kind TEXT NOT NULL,
  text TEXT NOT NULL DEFAULT '',
  html TEXT,
  blob_hash TEXT,
  content_hash TEXT NOT NULL UNIQUE,
  source_app TEXT NOT NULL DEFAULT '',
  source_title TEXT,
  char_len INTEGER NOT NULL DEFAULT 0,
  paste_count INTEGER NOT NULL DEFAULT 0,
  last_pasted_at INTEGER,
  pinned INTEGER NOT NULL DEFAULT 0,
  blocked INTEGER NOT NULL DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS clips_fts USING fts5(
  text, content='clips', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);
CREATE VIRTUAL TABLE IF NOT EXISTS clips_tri USING fts5(
  text, content='clips', content_rowid='id', tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS clips_ai AFTER INSERT ON clips BEGIN
  INSERT INTO clips_fts(rowid, text) VALUES (new.id, new.text);
  INSERT INTO clips_tri(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS clips_ad AFTER DELETE ON clips BEGIN
  INSERT INTO clips_fts(clips_fts, rowid, text) VALUES('delete', old.id, old.text);
  INSERT INTO clips_tri(clips_tri, rowid, text) VALUES('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS clips_au AFTER UPDATE OF text ON clips BEGIN
  INSERT INTO clips_fts(clips_fts, rowid, text) VALUES('delete', old.id, old.text);
  INSERT INTO clips_tri(clips_tri, rowid, text) VALUES('delete', old.id, old.text);
  INSERT INTO clips_fts(rowid, text) VALUES (new.id, new.text);
  INSERT INTO clips_tri(rowid, text) VALUES (new.id, new.text);
END;

CREATE TABLE IF NOT EXISTS app_pastes (
  app TEXT PRIMARY KEY, count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE INDEX IF NOT EXISTS idx_clips_created ON clips(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_clips_app ON clips(source_app);
"""


class Store:
    def __init__(self, db_path: Path, blobs_dir: Path) -> None:
        self.db_path = Path(db_path)
        self.blobs_dir = Path(blobs_dir)
        self._lock = threading.RLock()
        self.conn: sqlite3.Connection | None = None

    def open(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.blobs_dir.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    def close(self) -> None:
        with self._lock:
            if self.conn is not None:
                self.conn.close()
                self.conn = None

    def _connection(self) -> sqlite3.Connection:
        if self.conn is None:
            self.open()
        assert self.conn is not None
        return self.conn

    # -- writes ---------------------------------------------------------

    def add(
        self,
        clip: CapturedClip,
        *,
        source_app: str,
        source_title: str = "",
        blocked: bool = False,
        created_at: int | None = None,
    ) -> ClipRow | None:
        """Insert a clip. Returns None if its content was already indexed."""
        digest = clip.content_hash()
        blob_hash = self._save_image(clip.image) if clip.image is not None else None
        now = created_at or int(time.time() * 1000)
        with self._lock:
            conn = self._connection()
            try:
                cursor = conn.execute(
                    """INSERT INTO clips
                       (created_at, kind, text, html, blob_hash, content_hash,
                        source_app, source_title, char_len, blocked)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        now,
                        clip.kind,
                        clip.text,
                        clip.html,
                        blob_hash,
                        digest,
                        source_app or "",
                        source_title or "",
                        len(clip.text),
                        int(blocked),
                    ),
                )
            except sqlite3.IntegrityError:
                conn.rollback()
                return None
            conn.commit()
            return self.get(cursor.lastrowid)

    def add_many(
        self,
        items: Iterable[tuple[CapturedClip, dict[str, object]]],
    ) -> int:
        """Bulk insert in one transaction. Used by imports and benchmarks."""
        inserted = 0
        with self._lock:
            conn = self._connection()
            conn.execute("BEGIN")
            try:
                for clip, metadata in items:
                    blob_hash = (
                        self._save_image(clip.image) if clip.image is not None else None
                    )
                    digest = clip.content_hash()
                    now = int(metadata.get("created_at") or time.time() * 1000)
                    conn.execute(
                        """INSERT OR IGNORE INTO clips
                           (created_at, kind, text, html, blob_hash, content_hash,
                            source_app, source_title, char_len, blocked)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            now,
                            clip.kind,
                            clip.text,
                            clip.html,
                            blob_hash,
                            digest,
                            str(metadata.get("source_app") or ""),
                            str(metadata.get("source_title") or ""),
                            len(clip.text),
                            int(bool(metadata.get("blocked"))),
                        ),
                    )
                    inserted += 1
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return inserted

    def record_paste(self, clip_id: int) -> None:
        with self._lock:
            conn = self._connection()
            row = conn.execute(
                "SELECT source_app FROM clips WHERE id = ?", (clip_id,)
            ).fetchone()
            if row is None:
                return
            now = int(time.time() * 1000)
            conn.execute(
                """UPDATE clips
                   SET paste_count = paste_count + 1, last_pasted_at = ?
                   WHERE id = ?""",
                (now, clip_id),
            )
            conn.execute(
                """INSERT INTO app_pastes(app, count) VALUES (?, 1)
                   ON CONFLICT(app) DO UPDATE SET count = count + 1""",
                (row["source_app"] or "",),
            )
            conn.commit()

    def pin(self, clip_id: int, value: bool = True) -> None:
        with self._lock:
            conn = self._connection()
            conn.execute("UPDATE clips SET pinned = ? WHERE id = ?", (int(value), clip_id))
            conn.commit()

    def delete(self, clip_id: int) -> None:
        with self._lock:
            conn = self._connection()
            conn.execute("DELETE FROM clips WHERE id = ?", (clip_id,))
            conn.commit()

    # -- reads ----------------------------------------------------------

    def get(self, clip_id: int) -> ClipRow | None:
        with self._lock:
            row = self._connection().execute(
                "SELECT * FROM clips WHERE id = ?", (clip_id,)
            ).fetchone()
            return _to_clip(row) if row else None

    def recent(self, limit: int = 30) -> list[ClipRow]:
        with self._lock:
            rows = self._connection().execute(
                "SELECT * FROM clips ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [_to_clip(row) for row in rows]

    def all_apps(self) -> list[str]:
        with self._lock:
            rows = self._connection().execute(
                """SELECT DISTINCT source_app FROM clips
                   WHERE source_app <> '' ORDER BY source_app"""
            ).fetchall()
            return [row["source_app"] for row in rows]

    def stats(self) -> dict[str, object]:
        with self._lock:
            row = self._connection().execute(
                """SELECT COUNT(*) AS total,
                          SUM(CASE WHEN kind='text' THEN 1 ELSE 0 END) AS text_count,
                          SUM(CASE WHEN kind='image' THEN 1 ELSE 0 END) AS image_count,
                          SUM(CASE WHEN blocked=1 THEN 1 ELSE 0 END) AS blocked_count,
                          MIN(created_at) AS oldest
                   FROM clips"""
            ).fetchone()
        total = row["total"] or 0
        oldest = row["oldest"]
        oldest_day = (
            datetime.fromtimestamp(oldest / 1000, tz=UTC).date().isoformat()
            if oldest
            else None
        )
        return {
            "total": total,
            "text": row["text_count"] or 0,
            "image": row["image_count"] or 0,
            "blocked": row["blocked_count"] or 0,
            "oldest_day": oldest_day,
        }

    def search(
        self,
        raw_query: str,
        *,
        limit: int = 30,
        foreground_app: str = "",
        now_ms: int | None = None,
    ) -> list[SearchHit]:
        query = parse_query(raw_query)
        fts_expression = build_fts_expression(query.text)
        candidates: dict[int, tuple[float, bool]] = {}

        with self._lock:
            conn = self._connection()
            if fts_expression:
                try:
                    rows = conn.execute(
                        """SELECT rowid AS id, bm25(clips_fts) AS rank
                           FROM clips_fts WHERE clips_fts MATCH ?
                           ORDER BY bm25(clips_fts) LIMIT 100"""
                        , (fts_expression,)
                    ).fetchall()
                    for row in rows:
                        candidates[int(row["id"])] = (float(row["rank"]), False)
                except sqlite3.OperationalError:
                    # A malformed query must not break the UI. Fall back to trigram.
                    pass

            # The trigram index is for rare substrings. If word search already
            # returned plenty of candidates, skip the more expensive scan.
            if len(query.text.strip()) >= 3 and len(candidates) < limit * 2:
                rows = conn.execute(
                    "SELECT rowid AS id FROM clips_tri WHERE text LIKE ? LIMIT 100",
                    (f"%{query.text.strip()}%",),
                ).fetchall()
                for row in rows:
                    clip_id = int(row["id"])
                    if clip_id in candidates:
                        rank, _ = candidates[clip_id]
                        candidates[clip_id] = (rank, True)
                    else:
                        candidates[clip_id] = (0.0, True)

            if not candidates:
                return []

            ids = list(candidates)
            placeholders = ",".join("?" for _ in ids)
            clauses = [f"id IN ({placeholders})"]
            params: list[object] = list(ids)
            if query.apps:
                app_clauses = []
                for app in query.apps:
                    app_clauses.append("LOWER(source_app) LIKE ?")
                    params.append(f"%{app}%")
                clauses.append("(" + " OR ".join(app_clauses) + ")")
            if query.kinds:
                clauses.append("kind IN (" + ",".join("?" for _ in query.kinds) + ")")
                params.extend(query.kinds)
            if query.since_days is not None:
                clauses.append("created_at >= ?")
                params.append((now_ms or int(time.time() * 1000)) - query.since_days * 86_400_000)
            if query.pinned_only:
                clauses.append("pinned = 1")

            rows = conn.execute(
                f"SELECT * FROM clips WHERE {' AND '.join(clauses)}", params
            ).fetchall()

        now = now_ms or int(time.time() * 1000)
        hits: list[SearchHit] = []
        for row in rows:
            clip = _to_clip(row)
            fts_rank, substring = candidates.get(clip.id, (0.0, False))
            value = score_hit(
                clip,
                fts_rank=fts_rank,
                substring=substring,
                foreground_app=foreground_app,
                now_ms=now,
            )
            hits.append(
                SearchHit(
                    clip=clip,
                    score=value,
                    terms=query.terms,
                    snippet=make_snippet(clip.text, query.terms),
                )
            )
        hits.sort(key=lambda hit: (hit.score, hit.clip.created_at), reverse=True)
        return hits[:limit]

    # -- maintenance ----------------------------------------------------

    def cleanup(self, retention_days: int) -> int:
        cutoff = int(time.time() * 1000) - retention_days * 86_400_000
        with self._lock:
            conn = self._connection()
            cursor = conn.execute("DELETE FROM clips WHERE created_at < ?", (cutoff,))
            conn.commit()
            removed = cursor.rowcount
        self.gc_blobs()
        return max(0, removed)

    def gc_blobs(self) -> int:
        with self._lock:
            used = {
                row["blob_hash"]
                for row in self._connection().execute(
                    "SELECT DISTINCT blob_hash FROM clips WHERE blob_hash IS NOT NULL"
                ).fetchall()
            }
        removed = 0
        if not self.blobs_dir.exists():
            return 0
        for path in self.blobs_dir.glob("*/*"):
            if path.name.split(".")[0] not in used and path.is_file():
                path.unlink(missing_ok=True)
                removed += 1
        return removed

    def _save_image(self, image: object) -> str:
        from io import BytesIO

        if image is None:
            raise ValueError("no image")
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)  # type: ignore[attr-defined]
        data = buffer.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        path = blob_path(self.blobs_dir, digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        return digest

    def blob_data_url(self, digest: str | None) -> str:
        import base64

        if not digest:
            return ""
        path = blob_path(self.blobs_dir, digest)
        if not path.exists():
            return ""
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"


def _to_clip(row: sqlite3.Row) -> ClipRow:
    return ClipRow(
        id=int(row["id"]),
        created_at=int(row["created_at"]),
        kind=row["kind"],
        text=row["text"] or "",
        html=row["html"],
        blob_hash=row["blob_hash"],
        source_app=row["source_app"] or "",
        source_title=row["source_title"] or "",
        char_len=int(row["char_len"]),
        paste_count=int(row["paste_count"]),
        last_pasted_at=row["last_pasted_at"],
        pinned=bool(row["pinned"]),
        blocked=bool(row["blocked"]),
    )

"""Day-0 environment checks. Run with the project's virtualenv."""

import sqlite3
import sys
import winreg


def check_sqlite() -> None:
    print("Python:", sys.version.split()[0])
    print("SQLite:", sqlite3.sqlite_version)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE VIRTUAL TABLE fts USING fts5(text)")
    print("FTS5: available")
    conn.execute("CREATE VIRTUAL TABLE tri USING fts5(text, tokenize='trigram')")
    print("Trigram tokenizer: available")
    conn.execute("INSERT INTO tri(text) VALUES ('the quick brown fox')")
    rows = conn.execute("SELECT rowid FROM tri WHERE text LIKE '%uick%'").fetchall()
    print("Trigram LIKE lookup:", "works" if rows else "NO MATCH")
    conn.close()


def check_webview2() -> None:
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeWebView\Installations"
        ) as key:
            version, _ = winreg.QueryValueEx(key, "Version")
        print("WebView2 runtime:", version)
    except OSError as exc:
        print("WebView2 runtime: NOT FOUND -", exc)


def main() -> None:
    check_sqlite()
    check_webview2()


if __name__ == "__main__":
    main()

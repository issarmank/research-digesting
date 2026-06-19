import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "memory" / "seen_urls.db"


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_urls (
            url        TEXT PRIMARY KEY,
            topic      TEXT,
            first_seen TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS digests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            topic       TEXT,
            run_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            digest_json TEXT
        )
    """)
    conn.commit()


def _is_new_url(conn: sqlite3.Connection, url: str, topic: str) -> bool:
    existing = conn.execute(
        "SELECT 1 FROM seen_urls WHERE url = ?", (url,)
    ).fetchone()
    if existing:
        return False
    conn.execute(
        "INSERT INTO seen_urls (url, topic, first_seen) VALUES (?, ?, ?)",
        (url, topic, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return True


def save_digest(digest, topic: str) -> None:
    with sqlite3.connect(_DB_PATH) as conn:
        _init_db(conn)
        conn.execute(
            "INSERT INTO digests (topic, run_at, digest_json) VALUES (?, ?, ?)",
            (topic, datetime.now(timezone.utc).isoformat(), json.dumps(digest.model_dump())),
        )
        conn.commit()


def list_digests(limit: int = 20) -> list[dict]:
    with sqlite3.connect(_DB_PATH) as conn:
        _init_db(conn)
        rows = conn.execute(
            "SELECT id, topic, run_at, digest_json FROM digests ORDER BY run_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"id": r[0], "topic": r[1], "run_at": r[2], "digest_json": r[3]} for r in rows]


def deduplicate(scout_output: str, topic: str) -> list[dict]:
    """
    Parse URLs out of the Scout's plain-text output, filter against the
    seen_urls DB, insert new ones, and return the surviving article blocks.
    """
    # Split the scout output into per-article blocks on numbered list items
    blocks = re.split(r"\n(?=\d+\.)", scout_output.strip())

    with sqlite3.connect(_DB_PATH) as conn:
        _init_db(conn)
        new_articles = []
        for block in blocks:
            url_match = re.search(r"https?://\S+", block)
            if not url_match:
                continue
            url = url_match.group(0).rstrip(".,)")
            if _is_new_url(conn, url, topic):
                new_articles.append({"raw": block.strip(), "url": url})

    return new_articles

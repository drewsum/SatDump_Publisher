import sqlite3
from pathlib import Path
import time


SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    path TEXT PRIMARY KEY,
    timestamp TEXT,
    format TEXT,
    width INTEGER,
    height INTEGER,
    size INTEGER,
    sha256 TEXT,
    scanned_at TEXT
);
"""


def ensure_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute(SCHEMA)
    conn.commit()
    return conn


def upsert_image(conn, *, path, timestamp, format, width, height, size, sha256):
    now = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO images(path, timestamp, format, width, height, size, sha256, scanned_at) VALUES (?,?,?,?,?,?,?,?) "
        "ON CONFLICT(path) DO UPDATE SET timestamp=excluded.timestamp, format=excluded.format, width=excluded.width, height=excluded.height, size=excluded.size, sha256=excluded.sha256, scanned_at=excluded.scanned_at;",
        (path, timestamp, format, width, height, size, sha256, now),
    )
    conn.commit()


def list_images(conn):
    cur = conn.cursor()
    cur.execute("SELECT path, timestamp, format, width, height, size, sha256, scanned_at FROM images ORDER BY timestamp DESC")
    rows = cur.fetchall()
    return rows

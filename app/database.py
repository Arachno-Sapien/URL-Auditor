"""
SQLite database module for audit logging.

Demonstrates SQL knowledge with:
- Proper schema design with appropriate column types
- Parameterized queries (no SQL injection)
- Indexes for common query patterns
- Timestamp tracking

Uses SQLite so there's zero external infrastructure to set up.
"""

import sqlite3
import os
from datetime import datetime, timezone

# Database file location — in project root by default, configurable via env
DB_PATH = os.environ.get("AUDITOR_DB_PATH", "audits.db")


def get_connection():
    """Get a SQLite connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read performance
    return conn


def init_db():
    """
    Initialize the database schema.
    Safe to call multiple times — uses IF NOT EXISTS.
    """
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS audits (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                url             TEXT    NOT NULL,
                status_code     INTEGER,
                response_ms     INTEGER,
                title           TEXT,
                meta_description TEXT,
                h1_count        INTEGER,
                total_images    INTEGER,
                images_missing_alt INTEGER,
                word_count      INTEGER,
                og_image        TEXT,
                error_message   TEXT,
                audited_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_audits_url ON audits(url);
            CREATE INDEX IF NOT EXISTS idx_audits_date ON audits(audited_at);
        """)
        # Migration: add og_image if it doesn't exist
        try:
            conn.execute("ALTER TABLE audits ADD COLUMN og_image TEXT;")
        except sqlite3.OperationalError:
            pass  # Column already exists
        conn.commit()
    finally:
        conn.close()


def log_audit(url, result=None, error_message=None):
    """
    Log an audit result to the database.

    Args:
        url (str): The audited URL.
        result (dict|None): The audit result data, or None if the audit failed.
        error_message (str|None): Error message if the audit failed.

    Returns:
        int: The ID of the inserted row.
    """
    conn = get_connection()
    try:
        if result:
            cursor = conn.execute(
                """
                INSERT INTO audits (url, status_code, response_ms, title,
                    meta_description, h1_count, total_images,
                    images_missing_alt, word_count, og_image, audited_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    url,
                    result.get("status_code"),
                    result.get("response_time_ms"),
                    result.get("title"),
                    result.get("meta_description"),
                    result.get("h1_count"),
                    result.get("total_images"),
                    result.get("images_missing_alt"),
                    result.get("word_count"),
                    result.get("og_image"),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO audits (url, error_message, audited_at)
                VALUES (?, ?, ?)
                """,
                (url, error_message, datetime.now(timezone.utc).isoformat()),
            )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_recent_audits(limit=10):
    """
    Retrieve recent audit records.

    Args:
        limit (int): Maximum number of records to return.

    Returns:
        list[dict]: Recent audit records, newest first.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, url, status_code, response_ms, title, h1_count,
                   word_count, images_missing_alt, og_image, error_message, audited_at
            FROM audits
            ORDER BY audited_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_previous_audit(url):
    """
    Retrieve the most recent successful audit for a given URL.
    
    Args:
        url (str): The audited URL.
        
    Returns:
        dict|None: The audit record, or None if no previous successful audit exists.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, url, status_code, response_ms, title, meta_description,
                   h1_count, total_images, images_missing_alt, word_count, og_image,
                   audited_at
            FROM audits
            WHERE url = ? AND status_code IS NOT NULL
            ORDER BY audited_at DESC
            LIMIT 1
            """,
            (url,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

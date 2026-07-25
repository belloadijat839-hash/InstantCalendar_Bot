"""
Simple SQLite storage layer for InstantCalendar_Bot.

Table: events
    id          INTEGER PRIMARY KEY
    user_id     INTEGER   -- Telegram user id, so each user only sees their own events
    title       TEXT
    event_date  TEXT      -- ISO format YYYY-MM-DD
    event_time  TEXT      -- HH:MM or NULL
    note        TEXT      -- optional free text, may be NULL
    created_at  TEXT      -- ISO timestamp
"""

import sqlite3
from datetime import datetime, date
from contextlib import contextmanager

from bot.config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_time TEXT,
                note TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_user_date ON events(user_id, event_date)"
        )


def add_event(user_id: int, title: str, event_date: str, event_time: str | None = None, note: str | None = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO events (user_id, title, event_date, event_time, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, title, event_date, event_time, note, datetime.utcnow().isoformat()),
        )
        return cur.lastrowid


def get_events_for_day(user_id: int, event_date: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM events WHERE user_id = ? AND event_date = ? ORDER BY event_time IS NULL, event_time",
            (user_id, event_date),
        )
        return cur.fetchall()


def get_events_for_month(user_id: int, year: int, month: int) -> list[sqlite3.Row]:
    prefix = f"{year:04d}-{month:02d}"
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM events WHERE user_id = ? AND event_date LIKE ? ORDER BY event_date, event_time IS NULL, event_time",
            (user_id, f"{prefix}%"),
        )
        return cur.fetchall()


def get_all_events(user_id: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM events WHERE user_id = ? ORDER BY event_date, event_time IS NULL, event_time",
            (user_id,),
        )
        return cur.fetchall()


def delete_event(event_id: int, user_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "DELETE FROM events WHERE id = ? AND user_id = ?", (event_id, user_id)
        )
        return cur.rowcount > 0


def days_with_events_in_month(user_id: int, year: int, month: int) -> set[int]:
    """Return the set of day-of-month integers that have at least one event."""
    rows = get_events_for_month(user_id, year, month)
    return {int(r["event_date"].split("-")[2]) for r in rows}

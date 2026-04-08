"""
Storage module: persists seen listings, chat configs, and filters using SQLite.
"""

import sqlite3
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "listings.db")


class Storage:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS seen_listings (
                    listing_id TEXT PRIMARY KEY,
                    seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS chats (
                    chat_id INTEGER PRIMARY KEY,
                    active INTEGER DEFAULT 0,
                    filters TEXT DEFAULT '{}'
                );
            """)
        logger.info(f"Database initialized at {self.db_path}")

    # ── Seen listings ──────────────────────────────────────────────────────────

    def is_seen(self, listing_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM seen_listings WHERE listing_id = ?", (listing_id,)
            ).fetchone()
            return row is not None

    def mark_seen(self, listing_id: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO seen_listings (listing_id) VALUES (?)",
                (listing_id,),
            )

    def get_seen_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM seen_listings").fetchone()[0]

    # ── Chat management ────────────────────────────────────────────────────────

    def register_chat(self, chat_id: int):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO chats (chat_id, active, filters) VALUES (?, 0, '{}')",
                (chat_id,),
            )

    def set_active(self, chat_id: int, active: bool):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO chats (chat_id, active, filters) VALUES (?, ?, '{}') "
                "ON CONFLICT(chat_id) DO UPDATE SET active = excluded.active",
                (chat_id, 1 if active else 0),
            )

    def is_active(self, chat_id: int) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT active FROM chats WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            return bool(row["active"]) if row else False

    def get_active_chats(self) -> list[int]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT chat_id FROM chats WHERE active = 1"
            ).fetchall()
            return [r["chat_id"] for r in rows]

    # ── Filters ────────────────────────────────────────────────────────────────

    def get_filters(self, chat_id: int) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT filters FROM chats WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            if row:
                try:
                    return json.loads(row["filters"] or "{}")
                except json.JSONDecodeError:
                    return {}
            return {}

    def set_filter(self, chat_id: int, key: str, value):
        filters = self.get_filters(chat_id)
        if value is None:
            filters.pop(key, None)
        else:
            filters[key] = value
        self._save_filters(chat_id, filters)

    def reset_filters(self, chat_id: int):
        self._save_filters(chat_id, {})

    def _save_filters(self, chat_id: int, filters: dict):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO chats (chat_id, active, filters) VALUES (?, 0, ?) "
                "ON CONFLICT(chat_id) DO UPDATE SET filters = excluded.filters",
                (chat_id, json.dumps(filters, ensure_ascii=False)),
            )

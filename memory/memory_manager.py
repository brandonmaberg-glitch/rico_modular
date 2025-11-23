"""Memory manager for RICO's SQLite-backed memory system."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any

from .memory_schema import DB_PATH, create_tables

# Ensure tables exist on module import
create_tables()


def get_current_timestamp() -> str:
    """Return the current UTC timestamp as an ISO-formatted string."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def connect() -> sqlite3.Connection:
    """Return a SQLite connection to the memory database."""
    return sqlite3.connect(DB_PATH)


def save_long_term_memory(
    text: str,
    category: str,
    importance: float = 0.5,
    embedding: bytes | None = None,
) -> int:
    """Insert a new long-term memory and return its ID."""
    timestamp = get_current_timestamp()
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO long_term_memory (text, category, importance, last_updated, embedding)
            VALUES (?, ?, ?, ?, ?)
            """,
            (text, category, importance, timestamp, embedding),
        )
        conn.commit()
        return cursor.lastrowid


def get_long_term_memories(category: str | None = None) -> list[tuple[Any, ...]]:
    """Return all long-term memories, optionally filtered by category."""
    with connect() as conn:
        cursor = conn.cursor()
        if category is None:
            cursor.execute("SELECT id, text, category, importance, last_updated, embedding FROM long_term_memory")
        else:
            cursor.execute(
                "SELECT id, text, category, importance, last_updated, embedding FROM long_term_memory WHERE category = ?",
                (category,),
            )
        return cursor.fetchall()


def update_long_term_importance(memory_id: int, new_importance: float) -> None:
    """Update the importance of a long-term memory entry."""
    timestamp = get_current_timestamp()
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE long_term_memory
            SET importance = ?, last_updated = ?
            WHERE id = ?
            """,
            (new_importance, timestamp, memory_id),
        )
        conn.commit()


def delete_long_term_memory(memory_id: int) -> None:
    """Delete a long-term memory by its ID."""
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM long_term_memory WHERE id = ?", (memory_id,))
        conn.commit()


def set_short_term(key: str, value: str, ttl_seconds: int = 300) -> None:
    """Store a short-term memory entry with a time-to-live."""
    expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).replace(microsecond=0).isoformat() + "Z"
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO short_term_memory (key, value, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                expires_at = excluded.expires_at
            """,
            (key, value, expires_at),
        )
        conn.commit()


def get_short_term(key: str) -> str | None:
    """Retrieve a short-term memory value if it has not expired."""
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value, expires_at FROM short_term_memory WHERE key = ?", (key,))
        row = cursor.fetchone()

        if row is None:
            return None

        value, expires_at = row
        if expires_at and datetime.fromisoformat(expires_at.replace("Z", "")) < datetime.utcnow():
            cursor.execute("DELETE FROM short_term_memory WHERE key = ?", (key,))
            conn.commit()
            return None

        return value


def clear_expired_short_term() -> None:
    """Remove all expired short-term memory entries."""
    now = get_current_timestamp()
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM short_term_memory WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,),
        )
        conn.commit()


def save_skill_memory(skill: str, key: str, value: str) -> None:
    """Upsert a skill-specific memory entry."""
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO skill_memory (skill, memory_key, memory_value)
            VALUES (?, ?, ?)
            ON CONFLICT(skill, memory_key) DO UPDATE SET
                memory_value = excluded.memory_value
            """,
            (skill, key, value),
        )
        conn.commit()


def get_skill_memory(skill: str, key: str) -> tuple[Any, ...] | None:
    """Retrieve a skill-specific memory entry."""
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT skill, memory_key, memory_value FROM skill_memory WHERE skill = ? AND memory_key = ?",
            (skill, key),
        )
        return cursor.fetchone()

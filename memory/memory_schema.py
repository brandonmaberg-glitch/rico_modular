"""SQLite schema creation for RICO memory system."""
from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "memory.db"


def create_tables() -> None:
    """Create memory tables if they do not already exist."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS long_term_memory (
                id INTEGER PRIMARY KEY,
                text TEXT NOT NULL,
                category TEXT,
                importance REAL,
                last_updated TEXT,
                embedding BLOB
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS short_term_memory (
                key TEXT PRIMARY KEY,
                value TEXT,
                expires_at TEXT
            );
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS skill_memory (
                skill TEXT,
                memory_key TEXT,
                memory_value TEXT,
                PRIMARY KEY (skill, memory_key)
            );
            """
        )

        conn.commit()


if __name__ == "__main__":
    create_tables()

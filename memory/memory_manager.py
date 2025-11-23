"""Memory manager for RICO's SQLite-backed memory system."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from openai import OpenAI

from .memory_schema import DB_PATH, create_tables

client = OpenAI()

# Ensure tables exist on module import
create_tables()


def get_current_timestamp() -> str:
    """Return the current UTC timestamp as an ISO-formatted string."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def connect() -> sqlite3.Connection:
    """Return a SQLite connection to the memory database."""
    return sqlite3.connect(DB_PATH)


def generate_embedding(text: str) -> bytes:
    """Generate and return an embedding for the given text as bytes."""
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    embedding = response.data[0].embedding
    embedding_array = np.array(embedding, dtype=np.float32)
    return embedding_array.tobytes()


def clean_memory(text: str) -> str | None:
    """Validate and normalize memory text, rejecting unsuitable entries."""

    if not text:
        return None

    cleaned = text.strip()
    if len(cleaned) < 10:
        return None

    lower_text = cleaned.lower()

    question_starters = (
        "what",
        "who",
        "how",
        "when",
        "why",
        "is",
        "does",
        "do",
        "are",
        "can",
        "should",
    )
    if "?" in cleaned or any(
        lower_text.startswith(word + " ") or lower_text == word for word in question_starters
    ):
        return None

    pronouns = {"he", "she", "they", "him", "her", "them", "that", "this"}
    tokens = {token.strip(".,!?") for token in lower_text.split()}
    if pronouns.intersection(tokens):
        return None

    filler_phrases = {"lol", "that's funny", "thats funny", "okay", "ok", "sure"}
    if lower_text in filler_phrases:
        return None

    verbs = {
        "is",
        "has",
        "likes",
        "prefers",
        "owns",
        "lives",
        "drives",
        "always",
        "typically",
        "usually",
    }
    if not verbs.intersection(tokens) and not any(verb in lower_text for verb in verbs):
        return None

    return cleaned


def categorise_memory(text: str) -> str:
    """Return a category for the given memory text using rule-based detection."""

    lower_text = text.lower()

    user_profile_patterns = (
        "my name is",
        "i live in",
        "i am from",
        "my partner is",
        "i was born",
        "i work at",
    )
    if "years old" in lower_text or any(pattern in lower_text for pattern in user_profile_patterns):
        return "user_profile"

    user_preferences_patterns = (
        "i like",
        "i love",
        "i prefer",
        "my favourite",
        "i enjoy",
        "my preferred",
    )
    if any(pattern in lower_text for pattern in user_preferences_patterns):
        return "user_preferences"

    car_data_patterns = (
        "boost",
        "horsepower",
        "engine",
        "ecu",
        "tyres",
        "skyline",
        "gtst",
        "r33",
        "oil",
        "diagnostic",
    )
    if any(pattern in lower_text for pattern in car_data_patterns):
        return "car_data"

    system_settings_patterns = (
        "call me",
        "address me as",
        "default location",
        "default weather",
        "default skill",
        "set mode to",
    )
    if (
        any(pattern in lower_text for pattern in system_settings_patterns)
        or ("use" in lower_text and "voice" in lower_text)
    ):
        return "system_settings"

    patterns_patterns = (
        "i usually",
        "i tend to",
        "i always",
        "i often",
    )
    if any(pattern in lower_text for pattern in patterns_patterns):
        return "patterns"

    return "general"


def should_save_memory(text: str) -> str:
    """Return whether a memory should be saved, rejected, or confirmed."""

    cleaned = clean_memory(text)
    if cleaned is None:
        return "no"

    lower_text = cleaned.lower()

    preference_keywords = {"likes", "prefers", "loves", "enjoys"}
    car_keywords = {"car", "vehicle", "engine", "tesla", "bmw", "drive", "drives"}
    location_keywords = {"from", "live", "lives", "born", "origin"}
    system_keywords = {"setting", "settings", "configuration", "config", "system"}
    behavior_keywords = {"always", "usually", "typically", "every day", "routine", "habit"}

    if any(keyword in lower_text for keyword in preference_keywords):
        return "yes"
    if any(keyword in lower_text for keyword in car_keywords):
        return "yes"
    if any(keyword in lower_text for keyword in location_keywords):
        return "yes"
    if any(keyword in lower_text for keyword in system_keywords):
        return "yes"
    if any(keyword in lower_text for keyword in behavior_keywords):
        return "yes"

    return "ask"


def process_memory_suggestion(suggestion: dict) -> bool:
    """Handle LLM-provided memory suggestions and persist when approved."""

    should_write = suggestion.get("should_write_memory") if suggestion else None
    memory_text = suggestion.get("memory_to_write") if suggestion else None

    if should_write == "no":
        return False

    if should_write == "ask":
        return "ask"

    if should_write == "yes":
        cleaned = clean_memory(memory_text)
        if cleaned is None:
            return False
        category = categorise_memory(cleaned)
        importance = estimate_importance(cleaned)
        save_long_term_memory(cleaned, category, importance)
        return True

    return False


def estimate_importance(text: str) -> float:
    """Estimate the importance of a memory based on its content."""

    lower_text = text.lower()

    if any(keyword in lower_text for keyword in {"likes", "prefers", "loves", "enjoys"}):
        return 0.8
    if any(keyword in lower_text for keyword in {"car", "vehicle", "engine", "drive", "drives"}):
        return 0.9
    if any(keyword in lower_text for keyword in {"from", "live", "born", "origin"}):
        return 0.7
    if any(keyword in lower_text for keyword in {"setting", "settings", "configuration", "system"}):
        return 0.8
    if any(keyword in lower_text for keyword in {"always", "usually", "typically", "routine", "habit"}):
        return 0.6

    return 0.5


def save_long_term_memory(
    text: str,
    category: str,
    importance: float | None = None,
    embedding: bytes | None = None,
) -> int | None:
    """Insert a new long-term memory and return its ID."""
    cleaned_text = clean_memory(text)
    if cleaned_text is None:
        return None

    category = categorise_memory(cleaned_text)
    timestamp = get_current_timestamp()
    if embedding is None:
        embedding = generate_embedding(cleaned_text)
    if importance is None:
        importance = estimate_importance(cleaned_text)
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO long_term_memory (text, category, importance, last_updated, embedding)
            VALUES (?, ?, ?, ?, ?)
            """,
            (cleaned_text, category, importance, timestamp, embedding),
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


def embedding_from_blob(blob: bytes) -> np.ndarray:
    """Convert a stored embedding BLOB back into a NumPy array."""
    return np.frombuffer(blob, dtype=np.float32)


def decay_memories() -> None:
    """Gradually lower memory importance based on time since last update."""

    now = datetime.utcnow()
    memories = get_long_term_memories()

    for memory_id, _text, _category, importance, last_updated, _embedding in memories:
        try:
            last_updated_dt = (
                datetime.fromisoformat(last_updated.replace("Z", ""))
                if last_updated
                else now
            )
        except ValueError:
            last_updated_dt = now

        elapsed_days = (now - last_updated_dt).total_seconds() / 86400
        new_importance = max(0.0, importance - 0.01 * elapsed_days)

        update_long_term_importance(memory_id, new_importance)


def refresh_memory(memory_id: int) -> None:
    """Increase importance for a recently accessed memory."""

    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT importance FROM long_term_memory WHERE id = ?",
            (memory_id,),
        )
        row = cursor.fetchone()

        if row is None:
            return

        current_importance = row[0]
        new_importance = min(1.0, current_importance + 0.05)

        update_long_term_importance(memory_id, new_importance)


def prune_low_importance(threshold: float = 0.15) -> None:
    """Remove memories that fall below the importance threshold."""

    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM long_term_memory WHERE importance < ?",
            (threshold,),
        )
        conn.commit()


def get_relevant_memories(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Return the most relevant long-term memories for a query using embeddings."""
    query_embedding_array = embedding_from_blob(generate_embedding(query))
    query_norm = np.linalg.norm(query_embedding_array)

    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, text, category, importance, last_updated, embedding FROM long_term_memory WHERE embedding IS NOT NULL"
        )
        memories = []
        for memory_id, text, category, importance, last_updated, embedding_blob in cursor.fetchall():
            memory_embedding_array = embedding_from_blob(embedding_blob)
            memory_norm = np.linalg.norm(memory_embedding_array)
            if query_norm == 0 or memory_norm == 0:
                similarity = 0.0
            else:
                similarity = float(
                    np.dot(query_embedding_array, memory_embedding_array)
                    / (query_norm * memory_norm)
                )

            memories.append(
                {
                    "id": memory_id,
                    "text": text,
                    "category": category,
                    "importance": importance,
                    "last_updated": last_updated,
                    "similarity": similarity,
                }
            )

    memories.sort(key=lambda item: item["similarity"], reverse=True)
    top_memories = memories[:top_k]

    for memory in top_memories:
        refresh_memory(memory["id"])

    return top_memories


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


def set_context(key: str, value: str, ttl_seconds: int = 60) -> None:
    """Store contextual short-term memory with a default one-minute TTL."""

    set_short_term(key, value, ttl_seconds)


def get_context(key: str) -> str | None:
    """Retrieve contextual short-term memory if it has not expired."""

    return get_short_term(key)


def clear_context(key: str) -> None:
    """Remove a specific contextual short-term memory entry."""

    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM short_term_memory WHERE key = ?", (key,))
        conn.commit()


def clear_all_context() -> None:
    """Remove all contextual short-term memory entries."""

    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM short_term_memory")
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


def periodic_memory_maintenance():
    """Hook to run periodic memory housekeeping tasks."""

    decay_memories()
    prune_low_importance()

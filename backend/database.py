"""
SQLite session storage for SarkarSaathi.
Stores user sessions with extracted profile data.
"""
import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "sarkar_saathi.db")


def init_db() -> None:
    """Initialize SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   TEXT PRIMARY KEY,
            profile_json TEXT,
            query_text   TEXT,
            created_at   TEXT,
            updated_at   TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"[database] SQLite initialized at {DB_PATH}")


def create_session() -> str:
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO sessions (session_id, profile_json, query_text, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, "{}", "", now, now)
    )
    conn.commit()
    conn.close()
    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a session by ID."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT session_id, profile_json, query_text, created_at FROM sessions WHERE session_id = ?",
        (session_id,)
    ).fetchone()
    conn.close()
    if row:
        return {
            "session_id": row[0],
            "profile": json.loads(row[1]),
            "query_text": row[2],
            "created_at": row[3],
        }
    return None


def save_session(session_id: str, profile_dict: Dict, query_text: str) -> None:
    """Update an existing session with new profile data."""
    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO sessions (session_id, profile_json, query_text, created_at, updated_at) VALUES (?, ?, ?, COALESCE((SELECT created_at FROM sessions WHERE session_id = ?), ?), ?)",
        (session_id, json.dumps(profile_dict), query_text, session_id, now, now)
    )
    conn.commit()
    conn.close()

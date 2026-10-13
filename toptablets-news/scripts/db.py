"""
db.py - SQLite storage and state machine for toptablets-news automation.
Manages story lifecycle:
discovered -> qualified / rejected -> research_pending -> verified -> drafted -> quality_passed -> published / failed
"""
import sqlite3
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "news.db")


class NewsDatabase:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guid TEXT UNIQUE,
                url TEXT UNIQUE,
                decoded_url TEXT,
                headline TEXT NOT NULL,
                publisher TEXT,
                published_date TEXT,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_summary TEXT,
                content_text TEXT,
                india_relevant INTEGER DEFAULT 0,
                tablet_relevant INTEGER DEFAULT 0,
                brand TEXT,
                device_names TEXT,
                story_type TEXT DEFAULT 'product_launch',
                editorial_score REAL DEFAULT 0,
                status TEXT DEFAULT 'discovered',
                rejection_reason TEXT,
                topic_id INTEGER,
                fact_sheet TEXT,
                article_json TEXT,
                wp_post_id INTEGER,
                wp_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_title TEXT,
                device_key TEXT UNIQUE,
                story_type TEXT,
                primary_story_id INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage TEXT NOT NULL,
                story_id INTEGER,
                old_status TEXT,
                new_status TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

    def save_discovered_story(self, story: Dict[str, Any]) -> Optional[int]:
        """Insert story if not already known. Return story ID or None if duplicate."""
        guid = story.get("guid") or story.get("url")
        url = story.get("url")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM stories WHERE guid = ? OR url = ?", (guid, url))
            row = cursor.fetchone()
            if row:
                return None  # Already exists

            cursor.execute("""
            INSERT INTO stories (
                guid, url, decoded_url, headline, publisher, published_date,
                raw_summary, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'discovered')
            """, (
                guid,
                url,
                story.get("decoded_url") or url,
                story.get("headline", "").strip(),
                story.get("publisher", ""),
                story.get("published_date", ""),
                story.get("raw_summary", "")
            ))
            story_id = cursor.lastrowid
            self.log_transition(conn, "discovery", story_id, None, "discovered", "Story fetched from feed")
            conn.commit()
            return story_id

    def update_story_status(self, story_id: int, new_status: str, stage: str, details: str = "", extra_fields: Dict[str, Any] = None, conn: Optional[sqlite3.Connection] = None):
        """Update story status and record transition log."""
        should_close = False
        if conn is None:
            conn = self.get_connection()
            should_close = True

        cursor = conn.cursor()
        cursor.execute("SELECT status FROM stories WHERE id = ?", (story_id,))
        row = cursor.fetchone()
        old_status = row["status"] if row else None

        set_clause = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [new_status]

        if extra_fields:
            for k, v in extra_fields.items():
                set_clause.append(f"{k} = ?")
                params.append(json.dumps(v) if isinstance(v, (dict, list)) else v)

        params.append(story_id)
        query = f"UPDATE stories SET {', '.join(set_clause)} WHERE id = ?"
        cursor.execute(query, params)

        self.log_transition(conn, stage, story_id, old_status, new_status, details)
        conn.commit()
        if should_close:
            conn.close()

    def log_transition(self, conn: sqlite3.Connection, stage: str, story_id: Optional[int], old_status: Optional[str], new_status: str, details: str):
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO pipeline_logs (stage, story_id, old_status, new_status, details)
        VALUES (?, ?, ?, ?, ?)
        """, (stage, story_id, old_status, new_status, details))

    def get_stories_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stories WHERE status = ? ORDER BY id ASC LIMIT ?", (status, limit))
            return [dict(r) for r in cursor.fetchall()]

    def get_story_by_id(self, story_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stories WHERE id = ?", (story_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_story_urls(self) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT url, decoded_url FROM stories")
            urls = []
            for r in cursor.fetchall():
                if r["url"]:
                    urls.append(r["url"])
                if r["decoded_url"]:
                    urls.append(r["decoded_url"])
            return urls

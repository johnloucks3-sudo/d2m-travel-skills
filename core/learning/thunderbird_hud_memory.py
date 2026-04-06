"""
Thunderbird HUD Conversation Memory
=====================================

SQLite-backed conversation memory for the HUD/API.
Stores Q&A pairs and injects recent context into EARA prompts.

Usage:
  from thunderbird_hud_memory import HudMemory
  mem = HudMemory()
  mem.store("what's Furlow's balance?", "Furlow balance is $15,486...")
  context = mem.get_recent_context(limit=10)  # formatted string for injection
"""

import json
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / "Thunderbird" / "hud_memory.db"


class HudMemory:
    """Persistent conversation memory for the Thunderbird HUD."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._init_db()

    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_query TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                tool_used TEXT,
                client_detected TEXT,
                persona_used TEXT,
                session_id TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                fact TEXT NOT NULL,
                source TEXT,
                category TEXT,
                UNIQUE(fact)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_time ON conversations(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id)")
        conn.commit()
        conn.close()

    def store(self, user_query: str, assistant_response: str,
              tool_used: str = None, client_detected: str = None,
              persona_used: str = None, session_id: str = None):
        """Store a Q&A exchange."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO conversations
            (timestamp, user_query, assistant_response, tool_used, client_detected, persona_used, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            user_query[:2000],
            assistant_response[:4000],
            tool_used,
            client_detected,
            persona_used,
            session_id,
        ))
        conn.commit()
        conn.close()

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get the most recent N exchanges."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        # Return in chronological order (oldest first)
        return [dict(r) for r in reversed(rows)]

    def get_recent_context(self, limit: int = 10) -> str:
        """Get recent exchanges formatted for prompt injection."""
        exchanges = self.get_recent(limit)
        if not exchanges:
            return ""

        lines = ["CONVERSATION HISTORY (most recent exchanges):"]
        for ex in exchanges:
            ts = ex["timestamp"][:16].replace("T", " ")
            lines.append(f"\n[{ts}]")
            lines.append(f"YODA: {ex['user_query']}")
            # Truncate long responses for context window
            # Increased from 500 to 2000 — Claude 1M context (GA) can handle richer history
            resp = ex["assistant_response"]
            if len(resp) > 2000:
                resp = resp[:2000] + "..."
            lines.append(f"EARA: {resp}")

        return "\n".join(lines)

    def store_fact(self, fact: str, source: str = "conversation", category: str = "general"):
        """Store a learned fact for long-term memory."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT OR IGNORE INTO facts (timestamp, fact, source, category)
                VALUES (?, ?, ?, ?)
            """, (datetime.now(timezone.utc).isoformat(), fact, source, category))
            conn.commit()
        except Exception as e:
            logger.warning(f"Fact store error: {e}")
        conn.close()

    def search_facts(self, query: str, limit: int = 5) -> List[Dict]:
        """Search stored facts by keyword."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM facts WHERE fact LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def search_conversations(self, query: str, limit: int = 10) -> List[Dict]:
        """Search past conversations by keyword."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM conversations WHERE user_query LIKE ? OR assistant_response LIKE ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self) -> Dict:
        """Get memory stats."""
        conn = sqlite3.connect(self.db_path)
        total_convs = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        total_facts = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]

        # Conversations today
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_convs = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE timestamp LIKE ?",
            (f"{today}%",)
        ).fetchone()[0]

        # Most discussed clients
        clients = conn.execute(
            "SELECT client_detected, COUNT(*) as cnt FROM conversations "
            "WHERE client_detected IS NOT NULL GROUP BY client_detected ORDER BY cnt DESC LIMIT 5"
        ).fetchall()

        # Most used tools
        tools = conn.execute(
            "SELECT tool_used, COUNT(*) as cnt FROM conversations "
            "WHERE tool_used IS NOT NULL GROUP BY tool_used ORDER BY cnt DESC LIMIT 5"
        ).fetchall()

        conn.close()

        return {
            "total_conversations": total_convs,
            "today_conversations": today_convs,
            "total_facts": total_facts,
            "top_clients": [{"client": r[0], "count": r[1]} for r in clients],
            "top_tools": [{"tool": r[0], "count": r[1]} for r in tools],
        }

    def clear_old(self, days: int = 30):
        """Clear conversations older than N days."""
        conn = sqlite3.connect(self.db_path)
        cutoff = datetime.now(timezone.utc).isoformat()[:10]
        # Simple approach: delete by date prefix comparison
        conn.execute(
            "DELETE FROM conversations WHERE timestamp < datetime('now', ? || ' days')",
            (f"-{days}",)
        )
        conn.commit()
        conn.close()

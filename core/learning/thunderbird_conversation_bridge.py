#!/usr/bin/env python3
"""
Thunderbird Conversation Bridge
===============================
Shared persistent memory for both OpenCode Bot and D2MC2 Bot.
- Both bots read/write the same SQLite DB
- Context injection makes conversations feel native to each platform
- Sessions persist across bot restarts
- bot_source field lets us filter: 'goose' or 'd2mc2' or both
"""

import sqlite3
import threading
import time
import json
import os
from datetime import datetime
from typing import Optional
from pathlib import Path

DB_PATH = Path.home() / "Thunderbird" / "conversation_bridge.db"

class ConversationBridge:
    """Thread-safe SQLite-backed conversation memory shared between all Thunderbird bots."""
    
    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    bot_source TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    user_id INTEGER,
                    user_message TEXT,
                    bot_response TEXT,
                    tool_calls TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    session_id TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_bot ON conversations(chat_id, bot_source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)")
            conn.commit()
            conn.close()
    
    def add(self, chat_id: str, bot_source: str, user_message: str, 
            bot_response: str, user_id: int = None, 
            tool_calls: list = None, session_id: str = None, tokens_used: int = 0):
        """Add a conversation turn to persistent storage."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                "INSERT INTO conversations (chat_id, bot_source, timestamp, user_id, user_message, bot_response, tool_calls, tokens_used, session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (chat_id, bot_source, time.time(), user_id, user_message, bot_response,
                 json.dumps(tool_calls) if tool_calls else json.dumps([]), tokens_used, session_id)
            )
            conn.commit()
            conn.close()
    
    def get_recent_context(self, chat_id: str, bot_source: str = None, limit: int = 15) -> str:
        """Get last N messages as a formatted context string for prompt injection."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM conversations WHERE chat_id = ?"
            params = [chat_id]
            if bot_source:
                query += " AND bot_source = ?"
                params.append(bot_source)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            conn.close()
        
        if not rows:
            return ""
        
        rows.reverse()  # Chronological order
        context_lines = []
        for row in rows:
            source_label = "Goose" if row["bot_source"] == "opencode" else "Claude" if row["bot_source"] == "d2mc2" else row["bot_source"]
            context_lines.append(f"[{source_label}] User: {row['user_message']}")
            if row['bot_response']:
                context_lines.append(f"[{source_label}] {source_label}: {row['bot_response'][:500]}")
        
        return "\n".join(context_lines[-limit*2:])  # Cap output length
    
    def get_session(self, session_id: str) -> list:
        """Get all conversations for a specific session, chronological."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM conversations WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,)
            ).fetchall()
            conn.close()
        return [dict(r) for r in rows]
    
    def search(self, query_text: str, chat_id: str = None, limit: int = 5) -> list:
        """Keyword search across past conversations."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            q = "SELECT * FROM conversations WHERE (user_message LIKE ? OR bot_response LIKE ?)"
            params = [f"%{query_text}%", f"%{query_text}%"]
            if chat_id:
                q += " AND chat_id = ?"
                params.append(chat_id)
            q += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(q, params).fetchall()
            conn.close()
        return [dict(r) for r in rows]
    
    def stats(self, chat_id: str = None) -> dict:
        """Get conversation statistics."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            if chat_id:
                total = conn.execute("SELECT COUNT(*) FROM conversations WHERE chat_id = ?", (chat_id,)).fetchone()[0]
                goose_count = conn.execute("SELECT COUNT(*) FROM conversations WHERE chat_id = ? AND bot_source = 'goose'", (chat_id,)).fetchone()[0]
                d2mc2_count = conn.execute("SELECT COUNT(*) FROM conversations WHERE chat_id = ? AND bot_source = 'd2mc2'", (chat_id,)).fetchone()[0]
                total_tokens = conn.execute("SELECT COALESCE(SUM(tokens_used), 0) FROM conversations WHERE chat_id = ?", (chat_id,)).fetchone()[0]
            else:
                total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
                goose_count = conn.execute("SELECT COUNT(*) FROM conversations WHERE bot_source = 'goose'").fetchone()[0]
                d2mc2_count = conn.execute("SELECT COUNT(*) FROM conversations WHERE bot_source = 'd2mc2'").fetchone()[0]
                total_tokens = conn.execute("SELECT COALESCE(SUM(tokens_used), 0) FROM conversations").fetchone()[0]
            
            oldest = conn.execute("SELECT MIN(timestamp) FROM conversations").fetchone()[0]
            newest = conn.execute("SELECT MAX(timestamp) FROM conversations").fetchone()[0]
            conn.close()
        
        return {
            "total_conversations": total,
            "goose_conversations": goose_count,
            "d2mc2_conversations": d2mc2_count,
            "total_tokens_used": total_tokens,
            "oldest": datetime.fromtimestamp(oldest).isoformat() if oldest else None,
            "newest": datetime.fromtimestamp(newest).isoformat() if newest else None,
        }
    
    def clear_chat(self, chat_id: str, bot_source: str = None):
        """Delete all conversations for a chat (used by /clear command)."""
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            if bot_source:
                conn.execute("DELETE FROM conversations WHERE chat_id = ? AND bot_source = ?", (chat_id, bot_source))
            else:
                conn.execute("DELETE FROM conversations WHERE chat_id = ?", (chat_id,))
            conn.commit()
            conn.close()

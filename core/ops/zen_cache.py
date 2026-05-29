"""
zen_cache.py — DeepSeek V4 Flash response cache
Dreams2Memories Travel, LLC

Hashes (model + prompt) → stores response in SQLite.
Returns cached response on exact match to save ZEN API calls.
TTL: 24 hours default.

Usage:
    from core.ops.zen_cache import ZenCache
    cache = ZenCache()
    key = cache.make_key("deepseek-v4-flash", "system prompt", "user prompt")
    cached = cache.get(key)
    if not cached:
        response = call_deepseek(...)
        cache.set(key, response)
"""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB = Path(__file__).resolve().parent.parent.parent / "storage" / "ai_costs.db"
DEFAULT_TTL_HOURS = 24


class ZenCache:
    """Prompt response cache for ZEN models. SQLite-backed, auto-creates table."""

    def __init__(self, db_path: str | Path = None, ttl_hours: int = DEFAULT_TTL_HOURS):
        self.db_path = Path(db_path or DB)
        self.ttl = timedelta(hours=ttl_hours)
        self._init_db()
        self._hits = 0
        self._misses = 0

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS zen_cache (
                key_hash TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                prompt_hash TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_zen_cache_expires
            ON zen_cache(expires_at)
        """)
        conn.commit()
        conn.close()

    def make_key(self, model: str, system: str, user: str) -> str:
        """Generate cache key from model + prompts."""
        raw = f"{model}||{system}||{user}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, key_hash: str) -> str | None:
        """Return cached response if valid, None otherwise."""
        conn = sqlite3.connect(str(self.db_path))
        row = conn.execute(
            "SELECT response, expires_at FROM zen_cache WHERE key_hash = ?",
            (key_hash,)
        ).fetchone()
        if row:
            response, expires_at = row
            expires = datetime.fromisoformat(expires_at)
            if expires > datetime.now(timezone.utc):
                conn.execute(
                    "UPDATE zen_cache SET hit_count = hit_count + 1 WHERE key_hash = ?",
                    (key_hash,)
                )
                conn.commit()
                conn.close()
                self._hits += 1
                return response
            else:
                conn.execute("DELETE FROM zen_cache WHERE key_hash = ?", (key_hash,))
                conn.commit()
        conn.close()
        self._misses += 1
        return None

    def set(self, key_hash: str, model: str, prompt_hash: str, response: str):
        """Store response in cache. Also records API call for rate limit tracking."""
        # Record DeepSeek API call for metronome rate limit monitoring
        try:
            metronome = Path(__file__).resolve().parent.parent.parent / "OpsCenter" / "metronome.py"
            subprocess.run(
                [sys.executable or "python3", str(metronome), "--record-deepseek-call"],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

        now = datetime.now(timezone.utc)
        expires = now + self.ttl
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            INSERT OR REPLACE INTO zen_cache
            (key_hash, model, prompt_hash, response, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (key_hash, model, prompt_hash, response, now.isoformat(), expires.isoformat()))
        conn.commit()
        conn.close()

    def stats(self) -> dict:
        """Return cache hit/miss stats."""
        conn = sqlite3.connect(str(self.db_path))
        total = conn.execute("SELECT COUNT(*) FROM zen_cache").fetchone()[0]
        expired = conn.execute(
            "SELECT COUNT(*) FROM zen_cache WHERE expires_at < ?",
            (datetime.now(timezone.utc).isoformat(),)
        ).fetchone()[0]
        top_hits = conn.execute(
            "SELECT model, hit_count FROM zen_cache ORDER BY hit_count DESC LIMIT 5"
        ).fetchall()
        conn.close()
        total_ops = self._hits + self._misses
        hit_pct = (self._hits / total_ops * 100) if total_ops > 0 else 0
        return {
            "cache_entries": total,
            "expired_entries": expired,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_pct": round(hit_pct, 1),
            "top_hits": [{"model": m, "hits": h} for m, h in top_hits],
        }

    def clear_expired(self) -> int:
        """Remove expired entries. Returns count removed."""
        conn = sqlite3.connect(str(self.db_path))
        now = datetime.now(timezone.utc).isoformat()
        count = conn.execute("DELETE FROM zen_cache WHERE expires_at < ?", (now,)).rowcount
        conn.commit()
        conn.close()
        return count

    def clear_all(self):
        """Wipe entire cache."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM zen_cache")
        conn.commit()
        conn.close()
        self._hits = 0
        self._misses = 0


if __name__ == "__main__":
    import sys
    cache = ZenCache()
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        s = cache.stats()
        print(f"Cache entries: {s['cache_entries']}")
        print(f"Expired: {s['expired_entries']}")
        print(f"Session hits: {s['hits']}")
        print(f"Session misses: {s['misses']}")
        print(f"Hit rate: {s['hit_rate_pct']}%")
        if s['top_hits']:
            print(f"Top models: {s['top_hits']}")
    elif len(sys.argv) > 1 and sys.argv[1] == "--clear":
        cache.clear_all()
        print("Cache cleared")
    elif len(sys.argv) > 1 and sys.argv[1] == "--prune":
        removed = cache.clear_expired()
        print(f"Removed {removed} expired entries")
    else:
        print("Usage: python3 zen_cache.py [--stats|--clear|--prune]")

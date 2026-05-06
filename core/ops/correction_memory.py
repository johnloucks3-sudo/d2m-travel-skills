#!/usr/bin/env python3
"""
correction_memory.py — Layer 4 of the Hale Escalation System
=============================================================
Self-healing routing memory.

When Commander corrects a response (frustration, reprimand, "wrong",
"again", "I told you"), log the topic. After 2 corrections on a similar
topic, auto-lock that topic class to Sonnet permanently. Locks expire
after 30 days of no further corrections.

This module is consulted FIRST in the substrate-selection chain
(before keyword_router.classify_substrate). Locked topics override
everything else.

Author: Thunderbird Wing | 2026-05-04 | SO_HALE_REAL_AUTONOMY_20260504
"""

import json
import re
import hashlib
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ─── Storage location ────────────────────────────────────────────────────
DEFAULT_STORE = Path("/home/john/Thunderbird/state/correction_memory.json")
LOCK_THRESHOLD = 2          # corrections before auto-lock
LOCK_TTL_DAYS = 30          # locks expire after N days of no corrections
TOPIC_KEYWORD_MAX = 8       # how many keywords define a "topic"

# ─── Correction-detection patterns ───────────────────────────────────────
# Any pattern match in commander_message = a correction event.
DIRECT_CORRECTION = [
    r'(?:^|\W)no(?:[,.\s!]|$)',
    r'\bwrong\b',
    r"\bthat'?s\s+not\s+right\b",
    r'\byou\s+missed\b',
    r"\byou\s+didn'?t\b",
    r'\bnot\s+what\s+i\s+(?:asked|wanted|said)\b',
]
FRUSTRATION = [
    r'(?:^|\W)again(?:[,.\s!]|$)',
    r'(?:^|\W)still(?:[,.\s!]|$)',
    r"\bi\s+(?:told|already\s+told)\s+you\b",
    r'\bfor\s+the\s+(?:nth|\d+(?:st|nd|rd|th)?|last|hundredth|millionth)\s+time\b',
    r'\bhow\s+many\s+times\b',
]
REPRIMAND = [
    r'\bunacceptable\b',
    r'\bthis\s+is\s+(?:ridiculous|nonsense|wrong|broken|bad|terrible)\b',
    r"\bwhy\s+don'?t\s+you\b",
    r"\bwhy\s+didn'?t\s+you\b",
    r'\bcome\s+on\b',
]
CAJOLING = [
    r"\bi\s+shouldn'?t\s+have\s+to\b",
    r'\byou\s+should\s+know\b',
    r'\byou\s+should\s+have\b',
    r'\bdo\s+i\s+have\s+to\s+(?:tell|ask|repeat)\b',
]

CORRECTION_RE = re.compile(
    '|'.join(DIRECT_CORRECTION + FRUSTRATION + REPRIMAND + CAJOLING),
    re.IGNORECASE,
)

# ─── Topic-extraction stopwords ──────────────────────────────────────────
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "should",
    "could", "may", "might", "must", "shall", "can", "to", "of", "in",
    "on", "at", "for", "by", "with", "about", "as", "from", "this", "that",
    "these", "those", "it", "its", "i", "you", "he", "she", "we", "they",
    "me", "him", "her", "us", "them", "my", "your", "his", "our", "their",
    "and", "or", "but", "if", "then", "else", "so", "not", "no", "yes",
    "what", "when", "where", "why", "how", "which", "who", "whom",
    "please", "thanks", "thank", "okay", "ok", "now", "just", "only",
    "very", "really", "more", "less", "some", "any", "all", "each",
}


def _extract_topic_keywords(text: str, limit: int = TOPIC_KEYWORD_MAX) -> list:
    """Pull salient keywords from text (lowercase alphanumeric ≥4 chars,
    minus stopwords). Used to build a topic vector for similarity matching.
    """
    if not text:
        return []
    tokens = re.findall(r'[A-Za-z][A-Za-z0-9_-]{3,}', text.lower())
    seen = set()
    out = []
    for t in tokens:
        if t in _STOPWORDS or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= limit:
            break
    return out


def _topic_hash(keywords: list) -> str:
    """Stable hash of a sorted keyword set — defines a 'topic class'."""
    canonical = '|'.join(sorted(set(keywords)))
    return hashlib.sha1(canonical.encode('utf-8')).hexdigest()[:16]


def _topic_similarity(a: list, b: list) -> float:
    """Jaccard similarity between two keyword lists."""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CorrectionMemory:
    """Persistent memory of Commander corrections and topic locks."""

    def __init__(self, store_path: Optional[Path] = None,
                 lock_threshold: int = LOCK_THRESHOLD,
                 lock_ttl_days: int = LOCK_TTL_DAYS,
                 similarity_threshold: float = 0.45):
        self.store_path = Path(store_path) if store_path else DEFAULT_STORE
        self.lock_threshold = lock_threshold
        self.lock_ttl_days = lock_ttl_days
        self.similarity_threshold = similarity_threshold
        self._data = self._load()

    # ─── Persistence ────────────────────────────────────────────────────
    def _load(self) -> dict:
        if not self.store_path.exists():
            return {}
        try:
            return json.loads(self.store_path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.store_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self._data, indent=2, sort_keys=True))
        os.replace(tmp, self.store_path)

    # ─── Public API ─────────────────────────────────────────────────────
    @staticmethod
    def is_correction(commander_message: str) -> bool:
        """True if the message looks like a correction/reprimand."""
        if not commander_message:
            return False
        return bool(CORRECTION_RE.search(commander_message))

    def log_correction(self, commander_message: str,
                       prior_request: str,
                       prior_response: str = "") -> dict:
        """Record a correction event.

        Pulls topic keywords from prior_request (the request that produced
        the bad response), then increments the matching topic's count.
        Auto-locks once threshold reached.

        Returns dict describing the topic state after logging.
        """
        if not self.is_correction(commander_message):
            return {"logged": False, "reason": "no correction pattern"}

        keywords = _extract_topic_keywords(prior_request)
        if not keywords:
            return {"logged": False, "reason": "no extractable topic"}

        # Find existing similar topic, else create new
        existing_hash = self._find_similar_topic(keywords)
        if existing_hash is None:
            existing_hash = _topic_hash(keywords)
            self._data[existing_hash] = {
                "topic_keywords": keywords,
                "topic_summary": " ".join(keywords[:5]),
                "correction_count": 0,
                "first_seen": _now_iso(),
                "last_seen": _now_iso(),
                "auto_locked": False,
                "last_correction_excerpt": commander_message[:200],
            }

        topic = self._data[existing_hash]
        topic["correction_count"] += 1
        topic["last_seen"] = _now_iso()
        topic["last_correction_excerpt"] = commander_message[:200]

        # Merge keywords (don't lose new vocabulary)
        merged = list(dict.fromkeys(topic["topic_keywords"] + keywords))[:TOPIC_KEYWORD_MAX]
        topic["topic_keywords"] = merged

        if topic["correction_count"] >= self.lock_threshold:
            topic["auto_locked"] = True

        self._save()
        return {
            "logged": True,
            "topic_hash": existing_hash,
            "correction_count": topic["correction_count"],
            "auto_locked": topic["auto_locked"],
            "topic_summary": topic["topic_summary"],
        }

    def should_autoroute_sonnet(self, request: str) -> bool:
        """True if the incoming request matches an active locked topic."""
        if not request:
            return False
        self._prune_expired()
        keywords = _extract_topic_keywords(request)
        if not keywords:
            return False
        for topic_hash, topic in self._data.items():
            if not topic.get("auto_locked"):
                continue
            sim = _topic_similarity(keywords, topic.get("topic_keywords", []))
            if sim >= self.similarity_threshold:
                return True
        return False

    def get_lock_reason(self, request: str) -> Optional[dict]:
        """Return diagnostic info about the lock that fired (or None)."""
        keywords = _extract_topic_keywords(request)
        if not keywords:
            return None
        best = None
        for topic_hash, topic in self._data.items():
            if not topic.get("auto_locked"):
                continue
            sim = _topic_similarity(keywords, topic.get("topic_keywords", []))
            if sim >= self.similarity_threshold and (best is None or sim > best[1]):
                best = (topic_hash, sim, topic)
        if best is None:
            return None
        topic_hash, sim, topic = best
        return {
            "topic_hash": topic_hash,
            "similarity": round(sim, 3),
            "topic_summary": topic.get("topic_summary"),
            "correction_count": topic.get("correction_count"),
            "last_seen": topic.get("last_seen"),
        }

    def _find_similar_topic(self, keywords: list) -> Optional[str]:
        """Return the hash of an existing topic above similarity threshold."""
        best_hash, best_sim = None, 0.0
        for topic_hash, topic in self._data.items():
            sim = _topic_similarity(keywords, topic.get("topic_keywords", []))
            if sim >= self.similarity_threshold and sim > best_sim:
                best_hash, best_sim = topic_hash, sim
        return best_hash

    def _prune_expired(self) -> int:
        """Drop topics whose last_seen is older than lock_ttl_days. Returns count pruned."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.lock_ttl_days)
        to_drop = []
        for topic_hash, topic in self._data.items():
            try:
                last = datetime.fromisoformat(topic.get("last_seen", ""))
            except ValueError:
                continue
            if last < cutoff:
                to_drop.append(topic_hash)
        for h in to_drop:
            del self._data[h]
        if to_drop:
            self._save()
        return len(to_drop)

    def stats(self) -> dict:
        """Snapshot of memory state."""
        self._prune_expired()
        locked = sum(1 for t in self._data.values() if t.get("auto_locked"))
        return {
            "total_topics": len(self._data),
            "locked_topics": locked,
            "store_path": str(self.store_path),
            "lock_threshold": self.lock_threshold,
            "lock_ttl_days": self.lock_ttl_days,
        }

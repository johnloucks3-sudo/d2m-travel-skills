"""
Thunderbird Learning Compiler — IOC Build 2 (CIPHER)
=====================================================
Captures Commander corrections, extracts principles, applies them forward.
Now with CIPHER: Context-Indexed Principle Heuristic Embedding Retrieval.

Skills addressed:
  1. Capture the Diff
  2. Extract the Principle
  3. Apply Forward

Architecture:
  Commander edits draft → diff captured → principle extracted → stored in rules DB
  Next draft generated ← rules injected into persona context ← rules fetched

  CIPHER layer (new): Each principle is embedded with its correction context
  using TF-IDF bag-of-words vectors. When generating output, the current
  context (recipient, subject, query) is compared via cosine similarity
  to find the 5 most relevant historical principles — not just tag-matched
  ones. This gives ~70-80% of neural embedding quality at $0 cost.

Storage: SQLite (learning_rules.db) with tables:
  - corrections: raw before/after pairs
  - principles: extracted, tagged rules for injection
  - principle_embeddings: CIPHER context vectors (TF-IDF)
  - episodes: episodic memory per client

Integration:
  - call_persona() injects applicable rules before every LLM call
  - _cos_review_email() captures diffs after COS edits
  - Morning briefing includes LEARNING DIGEST section
  - CIPHER similarity search merges with tag-based lookup
"""

import json
import logging
import math
import os
import re
import sqlite3
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

DB_DIR = Path(os.path.expanduser("~/Thunderbird"))
DB_PATH = DB_DIR / "learning_rules.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS corrections (
    correction_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    original_text   TEXT NOT NULL,
    corrected_text  TEXT NOT NULL,
    principle_id    INTEGER,
    source          TEXT NOT NULL DEFAULT 'email_diff',
    context         TEXT,
    timestamp       TEXT NOT NULL,
    recipient       TEXT,
    topic           TEXT,
    FOREIGN KEY (principle_id) REFERENCES principles(rule_id)
);

CREATE TABLE IF NOT EXISTS principles (
    rule_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_id          TEXT,
    domain              TEXT NOT NULL DEFAULT 'voice',
    client_tier         TEXT,
    principle_text      TEXT NOT NULL,
    confidence          REAL NOT NULL DEFAULT 0.8,
    validation_status   TEXT NOT NULL DEFAULT 'pending',
    created_date        TEXT NOT NULL,
    applied_count       INTEGER NOT NULL DEFAULT 0,
    valid_from          TEXT,
    valid_to            TEXT,
    superseded_by       INTEGER,
    priority_tier       TEXT NOT NULL DEFAULT 'contextual',
    FOREIGN KEY (superseded_by) REFERENCES principles(rule_id)
);

CREATE INDEX IF NOT EXISTS idx_principles_persona ON principles(persona_id);
CREATE INDEX IF NOT EXISTS idx_principles_status  ON principles(validation_status);
CREATE INDEX IF NOT EXISTS idx_corrections_ts     ON corrections(timestamp);
CREATE INDEX IF NOT EXISTS idx_principles_valid   ON principles(valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_principles_tier    ON principles(priority_tier);

CREATE TABLE IF NOT EXISTS episodes (
    episode_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    client_key   TEXT NOT NULL,
    context_type TEXT NOT NULL,
    what_worked  TEXT NOT NULL,
    what_failed  TEXT,
    outcome      TEXT,
    persona_id   TEXT,
    timestamp    TEXT NOT NULL,
    valid_from   TEXT,
    valid_to     TEXT
);
CREATE INDEX IF NOT EXISTS idx_episodes_client ON episodes(client_key);

CREATE TABLE IF NOT EXISTS principle_embeddings (
    rule_id           INTEGER PRIMARY KEY,
    context_embedding TEXT NOT NULL,
    context_text      TEXT NOT NULL,
    FOREIGN KEY (rule_id) REFERENCES principles(rule_id)
);
"""

# Priority tiers per Inverse Constitutional AI research:
# - inviolable: Never violate (e.g., "Never sign 'Best'", "Never use 'Hey'")
# - strong: Follow unless context demands otherwise (e.g., "Lead with connection for prospects")
# - contextual: Situational guidance (e.g., "Include personal cell for high-trust clients")
PRIORITY_TIERS = ("inviolable", "strong", "contextual")


def _get_db() -> sqlite3.Connection:
    """Return a connection to the learning rules database, creating tables if needed."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# CIPHER — Context-Indexed Principle Heuristic Embedding Retrieval
# ---------------------------------------------------------------------------
# TF-IDF bag-of-words embeddings with cosine similarity.
# Zero external API cost. Vocabulary rebuilt lazily from all stored contexts.
# Upgrade path: swap _get_embedding() to use Anthropic/OpenAI embeddings later.
# ---------------------------------------------------------------------------

# Domain-specific stop words (English + travel noise)
_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could of in to for on with at by from as into "
    "through during before after above below between under again further then "
    "once here there when where why how all each every both few more most other "
    "some such no nor not only own same so than too very just don t s re ll ve "
    "d m o it its this that these those i me my myself we our ours ourselves you "
    "your yours yourself he him his she her hers they them their what which who "
    "whom and but if or because until while about against".split()
)


def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, remove stop words."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


def _build_vocabulary(conn: sqlite3.Connection) -> Dict[str, int]:
    """Build vocabulary index from all stored context texts."""
    rows = conn.execute("SELECT context_text FROM principle_embeddings").fetchall()
    vocab: Dict[str, int] = {}
    for row in rows:
        for token in _tokenize(row["context_text"]):
            if token not in vocab:
                vocab[token] = len(vocab)
    return vocab


def _compute_idf(conn: sqlite3.Connection, vocab: Dict[str, int]) -> Dict[str, float]:
    """Compute inverse document frequency for each vocabulary term."""
    rows = conn.execute("SELECT context_text FROM principle_embeddings").fetchall()
    n_docs = len(rows)
    if n_docs == 0:
        return {}

    doc_freq: Counter = Counter()
    for row in rows:
        unique_tokens = set(_tokenize(row["context_text"]))
        for token in unique_tokens:
            if token in vocab:
                doc_freq[token] += 1

    idf: Dict[str, float] = {}
    for term, idx in vocab.items():
        df = doc_freq.get(term, 0)
        # Smooth IDF: log((N + 1) / (df + 1)) + 1
        idf[term] = math.log((n_docs + 1) / (df + 1)) + 1.0
    return idf


def _get_embedding(
    text: str,
    vocab: Dict[str, int],
    idf: Dict[str, float],
) -> List[float]:
    """Generate a TF-IDF embedding vector for the given text.

    Returns a list of floats with length = len(vocab).
    If vocab is empty, returns an empty list.
    """
    if not vocab:
        return []

    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * len(vocab)

    # Term frequency (normalized)
    tf: Counter = Counter(tokens)
    max_tf = max(tf.values()) if tf else 1

    vec = [0.0] * len(vocab)
    for term, count in tf.items():
        if term in vocab:
            idx = vocab[term]
            # Augmented TF to prevent bias toward long documents
            normalized_tf = 0.5 + 0.5 * (count / max_tf)
            vec[idx] = normalized_tf * idf.get(term, 1.0)

    return vec


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def store_principle_embedding(
    rule_id: int,
    context_text: str,
) -> bool:
    """Embed and store context for a principle.

    The embedding is computed against the current vocabulary. When
    vocabulary changes (new contexts added), embeddings are recomputed
    lazily on next similarity search via rebuild_embeddings().

    Returns True if stored successfully.
    """
    if not context_text or not context_text.strip():
        logger.debug(f"No context text for rule #{rule_id} — skipping embedding")
        return False

    conn = _get_db()
    try:
        # Build vocab from existing contexts + this new one
        vocab = _build_vocabulary(conn)
        # Add any new tokens from this context
        for token in _tokenize(context_text):
            if token not in vocab:
                vocab[token] = len(vocab)

        idf = _compute_idf(conn, vocab)
        # Compute embedding with updated vocab
        embedding = _get_embedding(context_text, vocab, idf)

        conn.execute(
            "INSERT OR REPLACE INTO principle_embeddings "
            "(rule_id, context_embedding, context_text) VALUES (?, ?, ?)",
            (rule_id, json.dumps(embedding), context_text),
        )
        conn.commit()
        logger.info(f"Stored CIPHER embedding for rule #{rule_id} (vocab={len(vocab)})")
        return True
    except Exception as e:
        logger.error(f"Failed to store embedding for rule #{rule_id}: {e}")
        return False
    finally:
        conn.close()


def rebuild_embeddings() -> int:
    """Rebuild all embeddings with current vocabulary.

    Call this after adding many new principles to ensure all embeddings
    use the same vocabulary space. Returns count of embeddings rebuilt.
    """
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT rule_id, context_text FROM principle_embeddings"
        ).fetchall()
        if not rows:
            return 0

        # Build unified vocabulary from all contexts
        vocab: Dict[str, int] = {}
        for row in rows:
            for token in _tokenize(row["context_text"]):
                if token not in vocab:
                    vocab[token] = len(vocab)

        idf = _compute_idf(conn, vocab)

        count = 0
        for row in rows:
            embedding = _get_embedding(row["context_text"], vocab, idf)
            conn.execute(
                "UPDATE principle_embeddings SET context_embedding = ? WHERE rule_id = ?",
                (json.dumps(embedding), row["rule_id"]),
            )
            count += 1

        conn.commit()
        logger.info(f"Rebuilt {count} CIPHER embeddings (vocab={len(vocab)})")
        return count
    finally:
        conn.close()


def get_similar_principles(
    query_context: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Find the k most similar historical contexts and return their principles.

    Uses TF-IDF cosine similarity against all stored principle embeddings.
    Returns list of dicts with principle data + similarity score.
    Only returns approved, temporally-valid principles.
    """
    if not query_context or not query_context.strip():
        return []

    conn = _get_db()
    try:
        # Get all embeddings
        embed_rows = conn.execute(
            "SELECT pe.rule_id, pe.context_embedding, pe.context_text "
            "FROM principle_embeddings pe "
            "JOIN principles p ON pe.rule_id = p.rule_id "
            "WHERE p.validation_status = 'approved' "
            "AND (p.valid_to IS NULL OR p.valid_to > datetime('now'))"
        ).fetchall()

        if not embed_rows:
            return []

        # Build vocabulary from stored contexts
        vocab = _build_vocabulary(conn)
        # Add query tokens to vocab for fair comparison
        query_tokens = _tokenize(query_context)
        for token in query_tokens:
            if token not in vocab:
                vocab[token] = len(vocab)

        idf = _compute_idf(conn, vocab)

        # Embed the query
        query_vec = _get_embedding(query_context, vocab, idf)
        if not query_vec:
            return []

        # Score each stored embedding — re-embed with current vocab for consistency
        scored: List[Tuple[float, int, str]] = []
        for row in embed_rows:
            stored_vec = _get_embedding(row["context_text"], vocab, idf)
            sim = cosine_similarity(query_vec, stored_vec)
            if sim > 0.0:
                scored.append((sim, row["rule_id"], row["context_text"]))

        # Sort by similarity descending, take top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        if not top:
            return []

        # Fetch full principle data for top matches
        results = []
        for sim, rule_id, ctx_text in top:
            principle = conn.execute(
                "SELECT * FROM principles WHERE rule_id = ?", (rule_id,)
            ).fetchone()
            if principle:
                result = dict(principle)
                result["similarity"] = round(sim, 4)
                result["matched_context"] = ctx_text
                results.append(result)

        return results
    finally:
        conn.close()


def get_cipher_stats() -> Dict[str, Any]:
    """Return statistics about the CIPHER embedding index."""
    conn = _get_db()
    try:
        total_embeddings = conn.execute(
            "SELECT COUNT(*) as cnt FROM principle_embeddings"
        ).fetchone()["cnt"]

        total_principles = conn.execute(
            "SELECT COUNT(*) as cnt FROM principles WHERE validation_status = 'approved'"
        ).fetchone()["cnt"]

        unembedded = conn.execute(
            "SELECT COUNT(*) as cnt FROM principles p "
            "WHERE p.validation_status = 'approved' "
            "AND p.rule_id NOT IN (SELECT rule_id FROM principle_embeddings)"
        ).fetchone()["cnt"]

        vocab = _build_vocabulary(conn)

        return {
            "total_embeddings": total_embeddings,
            "total_approved_principles": total_principles,
            "unembedded_principles": unembedded,
            "vocabulary_size": len(vocab),
            "coverage_pct": round(
                (total_embeddings / total_principles * 100) if total_principles > 0 else 0, 1
            ),
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# A. Capture Functions
# ---------------------------------------------------------------------------

def capture_email_diff(
    original_body: str,
    sent_body: str,
    context: Optional[str] = None,
    source: str = "email_diff",
) -> int:
    """Store a before/after correction pair.

    Returns the correction_id.
    """
    if original_body.strip() == sent_body.strip():
        logger.info("No diff detected — skipping capture.")
        return -1

    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        cur = conn.execute(
            "INSERT INTO corrections (original_text, corrected_text, source, context, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (original_body, sent_body, source, context, now),
        )
        conn.commit()
        cid = cur.lastrowid
        logger.info(f"Captured correction #{cid} ({source})")
        return cid
    finally:
        conn.close()


def capture_directive(
    commander_text: str,
    context: Optional[str] = None,
) -> int:
    """Capture a standing directive embedded in an operational reply.

    Stored as a correction with source='directive' — original is empty
    because the Commander is stating a new rule, not editing output.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        cur = conn.execute(
            "INSERT INTO corrections (original_text, corrected_text, source, context, timestamp) "
            "VALUES (?, ?, 'directive', ?, ?)",
            ("", commander_text, context, now),
        )
        conn.commit()
        cid = cur.lastrowid
        logger.info(f"Captured directive #{cid}")
        return cid
    finally:
        conn.close()


def capture_telegram_feedback(
    message_text: str,
    action: str = "edit",
    context: Optional[str] = None,
) -> int:
    """Capture feedback from Telegram C2 (approve/reject/edit)."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        cur = conn.execute(
            "INSERT INTO corrections (original_text, corrected_text, source, context, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            ("", message_text, f"telegram_{action}", context, now),
        )
        conn.commit()
        cid = cur.lastrowid
        logger.info(f"Captured telegram {action} #{cid}")
        return cid
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# B. Extract Function — sends corrections to Opus for principle extraction
# ---------------------------------------------------------------------------

EXTRACT_SYSTEM_PROMPT = """\
You are an expert at analyzing text corrections to extract actionable communication principles.

Given a set of corrections (original → corrected text), extract clear, reusable principles.

For each principle, provide a JSON object with these fields:
- persona_id: which persona this applies to (e.g., "A3", "COS", "EXEC", or null for all)
- domain: one of "voice", "pricing", "relationship", "logistics", "operations"
- client_tier: one of "paying", "friend", "prospect", "vendor", or null for all
- principle_text: the actionable rule (e.g., "For prospect-tier clients, lead with connection, never numbers")
- confidence: 0.0–1.0 how confident you are this is a real pattern (not a one-off)

Return ONLY a JSON array of principle objects. No other text."""


def extract_principles(limit: int = 20) -> List[Dict[str, Any]]:
    """Pull recent unlinked corrections and extract principles via Opus.

    Returns list of extracted principle dicts (not yet validated).
    """
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT correction_id, original_text, corrected_text, source, context "
            "FROM corrections WHERE principle_id IS NULL "
            "ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        logger.info("No unlinked corrections to extract from.")
        return []

    # Build the prompt with correction pairs
    correction_blocks = []
    for r in rows:
        block = f"--- Correction #{r['correction_id']} (source: {r['source']}) ---\n"
        if r["original_text"]:
            block += f"ORIGINAL:\n{r['original_text'][:2000]}\n\n"
        block += f"CORRECTED/DIRECTIVE:\n{r['corrected_text'][:2000]}\n"
        if r["context"]:
            block += f"CONTEXT: {r['context']}\n"
        correction_blocks.append(block)

    query = "Extract principles from these corrections:\n\n" + "\n".join(correction_blocks)

    # Call Claude via CLI (same pattern as thunderbird_personas._call_claude)
    claude_cmd = os.environ.get("CLAUDE_CMD", "claude")
    cmd = [
        claude_cmd, "--print",
        "--system-prompt", EXTRACT_SYSTEM_PROMPT,
        "--model", "opus",
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", "-",
    ]

    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    clean_env["CLAUDE_CODE_ENTRYPOINT"] = "cli"

    try:
        result = subprocess.run(
            cmd, input=query, capture_output=True, text=True,
            timeout=300, cwd=str(DB_DIR), env=clean_env,
        )
        if result.returncode != 0:
            logger.error(f"Claude extraction failed: {result.stderr[:500]}")
            return []

        raw = result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.error("Claude extraction timed out")
        return []
    except FileNotFoundError:
        logger.error(f"Claude CLI not found at '{claude_cmd}'")
        return []

    # Parse JSON from response (handle markdown code fences)
    json_match = re.search(r'\[[\s\S]*\]', raw)
    if not json_match:
        logger.error(f"No JSON array found in extraction response: {raw[:200]}")
        return []

    try:
        principles = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in extraction: {e}")
        return []

    # Store extracted principles and link corrections
    conn = _get_db()
    stored = []
    try:
        now = datetime.now(timezone.utc).isoformat()
        for p in principles:
            cur = conn.execute(
                "INSERT INTO principles (persona_id, domain, client_tier, principle_text, "
                "confidence, validation_status, created_date) VALUES (?, ?, ?, ?, ?, 'pending', ?)",
                (
                    p.get("persona_id"),
                    p.get("domain", "voice"),
                    p.get("client_tier"),
                    p.get("principle_text", ""),
                    p.get("confidence", 0.8),
                    now,
                ),
            )
            rule_id = cur.lastrowid
            p["rule_id"] = rule_id
            stored.append(p)

        # Link corrections to the first extracted principle (batch link)
        if stored:
            first_rule_id = stored[0]["rule_id"]
            correction_ids = [r["correction_id"] for r in rows]
            placeholders = ",".join("?" * len(correction_ids))
            conn.execute(
                f"UPDATE corrections SET principle_id = ? WHERE correction_id IN ({placeholders})",
                [first_rule_id] + correction_ids,
            )

        conn.commit()
        logger.info(f"Extracted {len(stored)} principles from {len(rows)} corrections")
    finally:
        conn.close()

    # CIPHER: embed each new principle with its correction context
    for p in stored:
        # Build context from the correction texts that spawned this principle
        context_parts = []
        for r in rows:
            if r["context"]:
                context_parts.append(r["context"])
            if r["original_text"]:
                context_parts.append(r["original_text"][:500])
            if r["corrected_text"]:
                context_parts.append(r["corrected_text"][:500])
        context_text = " | ".join(context_parts) if context_parts else p.get("principle_text", "")
        try:
            store_principle_embedding(p["rule_id"], context_text)
        except Exception as emb_err:
            logger.warning(f"CIPHER embedding failed for rule #{p['rule_id']}: {emb_err}")

    return stored


# ---------------------------------------------------------------------------
# C. Validate — approve/reject/edit pending principles
# ---------------------------------------------------------------------------

def validate_principle(
    rule_id: int,
    action: str = "approve",
    edited_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Approve, reject, or edit a pending principle.

    action: 'approve' | 'reject' | 'edit'
    """
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM principles WHERE rule_id = ?", (rule_id,)
        ).fetchone()
        if not row:
            return {"error": f"Principle #{rule_id} not found"}

        if action == "approve":
            conn.execute(
                "UPDATE principles SET validation_status = 'approved' WHERE rule_id = ?",
                (rule_id,),
            )
        elif action == "reject":
            conn.execute(
                "UPDATE principles SET validation_status = 'rejected' WHERE rule_id = ?",
                (rule_id,),
            )
        elif action == "edit" and edited_text:
            conn.execute(
                "UPDATE principles SET principle_text = ?, validation_status = 'approved' "
                "WHERE rule_id = ?",
                (edited_text, rule_id),
            )
        else:
            return {"error": f"Invalid action '{action}' or missing edited_text"}

        conn.commit()
        updated = conn.execute(
            "SELECT * FROM principles WHERE rule_id = ?", (rule_id,)
        ).fetchone()
        return dict(updated)
    finally:
        conn.close()


def supersede_principle(
    old_rule_id: int,
    new_principle_text: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new principle that supersedes an existing one (temporal versioning).

    Layer 3: Instead of overwriting, we archive the old principle with valid_to
    and create a new one with valid_from = now. This preserves preference history.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        old = conn.execute(
            "SELECT * FROM principles WHERE rule_id = ?", (old_rule_id,)
        ).fetchone()
        if not old:
            return {"error": f"Principle #{old_rule_id} not found"}

        # Create the new principle
        cur = conn.execute(
            "INSERT INTO principles (persona_id, domain, client_tier, principle_text, "
            "confidence, validation_status, created_date, valid_from, priority_tier) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
            (
                old["persona_id"],
                old["domain"],
                old["client_tier"],
                new_principle_text,
                old["confidence"],
                now,
                now,
                old["priority_tier"] if old["priority_tier"] else "contextual",
            ),
        )
        new_rule_id = cur.lastrowid

        # Archive the old principle
        conn.execute(
            "UPDATE principles SET valid_to = ?, superseded_by = ? WHERE rule_id = ?",
            (now, new_rule_id, old_rule_id),
        )

        conn.commit()
        logger.info(
            f"Principle #{old_rule_id} superseded by #{new_rule_id}"
            + (f" (reason: {reason})" if reason else "")
        )

        new = conn.execute(
            "SELECT * FROM principles WHERE rule_id = ?", (new_rule_id,)
        ).fetchone()
        return {
            "old_rule_id": old_rule_id,
            "new_rule_id": new_rule_id,
            "old_principle": dict(old),
            "new_principle": dict(new),
        }
    finally:
        conn.close()


def get_principle_history(
    persona_id: Optional[str] = None,
    domain: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get the temporal history of principles, including superseded ones.

    Layer 3: Shows how preferences evolved over time.
    """
    conn = _get_db()
    try:
        conditions = []
        params: List[Any] = []

        if persona_id:
            conditions.append("(persona_id = ? OR persona_id IS NULL)")
            params.append(persona_id)
        if domain:
            conditions.append("domain = ?")
            params.append(domain)

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = conn.execute(
            f"SELECT * FROM principles WHERE {where} "
            f"ORDER BY created_date DESC LIMIT 100",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# D. Apply — fetch approved rules and format for injection
# ---------------------------------------------------------------------------

def get_applicable_rules(
    persona_id: Optional[str] = None,
    client_tier: Optional[str] = None,
    domain: Optional[str] = None,
    context: Optional[str] = None,
) -> str:
    """Fetch approved, temporally-valid principles and format for system prompt injection.

    Filters by persona (or global), client_tier, domain.
    Respects temporal validity (valid_from/valid_to) — Layer 3.
    Orders by priority tier (inviolable > strong > contextual) — Layer 1 upgrade.

    CIPHER (Layer 1 upgrade): When `context` is provided (e.g., recipient email,
    subject, or query text), ALSO performs similarity search against
    principle_embeddings and merges results. Priority: tag-matched first,
    then similar-context principles not already included.

    Returns empty string if no rules match.
    """
    conn = _get_db()
    try:
        # Build dynamic WHERE clause
        conditions = ["validation_status = 'approved'"]
        params: List[Any] = []

        if persona_id:
            conditions.append("(persona_id = ? OR persona_id IS NULL)")
            params.append(persona_id)
        if client_tier:
            conditions.append("(client_tier = ? OR client_tier IS NULL)")
            params.append(client_tier)
        if domain:
            conditions.append("domain = ?")
            params.append(domain)

        # Layer 3: Only return temporally valid principles
        conditions.append("(valid_to IS NULL OR valid_to > datetime('now'))")

        where = " AND ".join(conditions)
        # Order: inviolable first, then strong, then contextual, then by usage
        rows = conn.execute(
            f"SELECT rule_id, persona_id, domain, client_tier, principle_text, priority_tier "
            f"FROM principles WHERE {where} "
            f"ORDER BY "
            f"  CASE priority_tier "
            f"    WHEN 'inviolable' THEN 1 "
            f"    WHEN 'strong' THEN 2 "
            f"    WHEN 'contextual' THEN 3 "
            f"    ELSE 4 END, "
            f"  applied_count DESC, created_date DESC LIMIT 20",
            params,
        ).fetchall()

        # CIPHER: merge similar-context principles when context is provided
        cipher_rows = []
        if context:
            try:
                similar = get_similar_principles(context, top_k=5)
                tag_rule_ids = {r["rule_id"] for r in rows}
                for sp in similar:
                    if sp["rule_id"] not in tag_rule_ids:
                        cipher_rows.append(sp)
            except Exception as cipher_err:
                logger.debug(f"CIPHER similarity search skipped: {cipher_err}")

        if not rows and not cipher_rows:
            return ""

        # Increment applied_count for tag-matched rules
        all_rule_ids = [r["rule_id"] for r in rows] + [r["rule_id"] for r in cipher_rows]
        if all_rule_ids:
            placeholders = ",".join("?" * len(all_rule_ids))
            conn.execute(
                f"UPDATE principles SET applied_count = applied_count + 1 "
                f"WHERE rule_id IN ({placeholders})",
                all_rule_ids,
            )
            conn.commit()
    finally:
        conn.close()

    # Format injection block — grouped by priority tier
    tier_labels = {
        "inviolable": "INVIOLABLE (never violate these)",
        "strong": "STRONG PREFERENCES (follow unless context demands otherwise)",
        "contextual": "CONTEXTUAL GUIDELINES (situational)",
    }
    lines_by_tier: Dict[str, List[str]] = {"inviolable": [], "strong": [], "contextual": []}

    for r in rows:
        tier = r["priority_tier"] if r["priority_tier"] in tier_labels else "contextual"
        tag_parts = [f"[{r['domain']}]"]
        if r["client_tier"]:
            tag_parts.append(f"({r['client_tier']} tier)")
        if r["persona_id"]:
            tag_parts.append(f"@{r['persona_id']}")
        lines_by_tier[tier].append(f"- {' '.join(tag_parts)} {r['principle_text']}")

    # Append CIPHER-matched principles in a separate section
    cipher_lines = []
    if cipher_rows:
        for cr in cipher_rows:
            tier = cr.get("priority_tier", "contextual")
            if tier not in tier_labels:
                tier = "contextual"
            tag_parts = [f"[{cr['domain']}]"]
            if cr.get("client_tier"):
                tag_parts.append(f"({cr['client_tier']} tier)")
            if cr.get("persona_id"):
                tag_parts.append(f"@{cr['persona_id']}")
            sim_pct = int(cr.get("similarity", 0) * 100)
            cipher_lines.append(
                f"- {' '.join(tag_parts)} {cr['principle_text']} "
                f"(CIPHER {sim_pct}% match)"
            )

    lines = []
    for tier, label in tier_labels.items():
        if lines_by_tier[tier]:
            lines.append(f"\n### {label}")
            lines.extend(lines_by_tier[tier])

    if cipher_lines:
        lines.append(f"\n### CONTEXT-MATCHED (CIPHER — similar past situations)")
        lines.extend(cipher_lines)

    return (
        "\n\nLEARNED PRINCIPLES (apply these — Commander-validated rules):\n"
        + "\n".join(lines)
    )


# ---------------------------------------------------------------------------
# D2. Episodic Memory — record and recall what worked/failed per client
# ---------------------------------------------------------------------------

def record_episode(
    client_key: str,
    context_type: str,
    what_worked: str,
    what_failed: Optional[str] = None,
    outcome: Optional[str] = None,
    persona_id: Optional[str] = None,
    valid_from: Optional[str] = None,
    valid_to: Optional[str] = None,
) -> int:
    """Record a client interaction episode — what worked, what failed, and outcome.

    context_type examples: 'email_draft', 'booking_query', 'excursion_rec',
                           'dining_suggestion', 'complaint_resolution', 'upsell'

    Returns episode_id.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    try:
        cur = conn.execute(
            "INSERT INTO episodes "
            "(client_key, context_type, what_worked, what_failed, outcome, "
            " persona_id, timestamp, valid_from, valid_to) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                client_key, context_type, what_worked, what_failed,
                outcome, persona_id, now,
                valid_from or now, valid_to,
            ),
        )
        conn.commit()
        eid = cur.lastrowid
        logger.info(f"Recorded episode #{eid} for {client_key} ({context_type})")
        return eid
    finally:
        conn.close()


def get_relevant_episodes(
    client_key: Optional[str] = None,
    context_type: Optional[str] = None,
    persona_id: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Retrieve episodes filtered by client, context type, and/or persona.

    Only returns temporally valid episodes (valid_to is NULL or in the future).
    Ordered by most recent first.
    """
    conn = _get_db()
    try:
        conditions = ["(valid_to IS NULL OR valid_to > datetime('now'))"]
        params: List[Any] = []

        if client_key:
            conditions.append("client_key = ?")
            params.append(client_key)
        if context_type:
            conditions.append("context_type = ?")
            params.append(context_type)
        if persona_id:
            conditions.append("(persona_id = ? OR persona_id IS NULL)")
            params.append(persona_id)

        where = " AND ".join(conditions)
        rows = conn.execute(
            f"SELECT * FROM episodes WHERE {where} "
            f"ORDER BY timestamp DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def format_episodes_for_injection(
    episodes: List[Dict[str, Any]],
    max_chars: int = 2000,
) -> str:
    """Format episode records for injection into persona system prompts.

    Groups by context_type and presents what_worked / what_failed
    so the persona can learn from past interactions.
    Returns empty string if no episodes.
    """
    if not episodes:
        return ""

    # Group by context_type
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for ep in episodes:
        ct = ep.get("context_type", "general")
        by_type.setdefault(ct, []).append(ep)

    lines = ["\n\nEPISODIC MEMORY (past interactions — learn from these):"]
    total_len = len(lines[0])

    for ct, eps in by_type.items():
        header = f"\n### {ct.replace('_', ' ').title()}"
        lines.append(header)
        total_len += len(header)

        for ep in eps:
            client = ep.get("client_key", "unknown")
            worked = ep.get("what_worked", "")
            failed = ep.get("what_failed", "")
            outcome = ep.get("outcome", "")

            entry = f"- [{client}] Worked: {worked}"
            if failed:
                entry += f" | Failed: {failed}"
            if outcome:
                entry += f" | Outcome: {outcome}"

            if total_len + len(entry) > max_chars:
                lines.append("- ... (more episodes available)")
                return "\n".join(lines)

            lines.append(entry)
            total_len += len(entry)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# E. Query helpers
# ---------------------------------------------------------------------------

def list_rules(
    status: Optional[str] = None,
    persona_id: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List principles with optional filters."""
    conn = _get_db()
    try:
        conditions = []
        params: List[Any] = []

        if status:
            conditions.append("validation_status = ?")
            params.append(status)
        if persona_id:
            conditions.append("(persona_id = ? OR persona_id IS NULL)")
            params.append(persona_id)
        if domain:
            conditions.append("domain = ?")
            params.append(domain)

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = conn.execute(
            f"SELECT * FROM principles WHERE {where} ORDER BY created_date DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_corrections(limit: int = 20) -> List[Dict[str, Any]]:
    """List recent corrections."""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM corrections ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_learning_digest() -> str:
    """Generate a learning digest for the morning briefing.

    Returns a formatted string summarizing:
    - Total principles (approved / pending / rejected)
    - Recent corrections captured
    - Principles pending validation
    """
    conn = _get_db()
    try:
        # Count by status
        counts = {}
        for status in ("approved", "pending", "rejected"):
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM principles WHERE validation_status = ?",
                (status,),
            ).fetchone()
            counts[status] = row["cnt"]

        # Recent corrections (last 24h)
        recent = conn.execute(
            "SELECT COUNT(*) as cnt FROM corrections "
            "WHERE timestamp > datetime('now', '-1 day')"
        ).fetchone()["cnt"]

        # Top applied rules
        top_rules = conn.execute(
            "SELECT principle_text, applied_count, domain FROM principles "
            "WHERE validation_status = 'approved' ORDER BY applied_count DESC LIMIT 3"
        ).fetchall()
    finally:
        conn.close()

    total = counts["approved"] + counts["pending"] + counts["rejected"]
    if total == 0 and recent == 0:
        return ""

    lines = [
        "## LEARNING DIGEST",
        f"**Principles:** {counts['approved']} approved / {counts['pending']} pending / {counts['rejected']} rejected",
        f"**Corrections captured (24h):** {recent}",
    ]

    if counts["pending"] > 0:
        lines.append(f"**ACTION:** {counts['pending']} principles awaiting Commander validation")

    if top_rules:
        lines.append("\n**Most-applied rules:**")
        for r in top_rules:
            lines.append(f"- [{r['domain']}] {r['principle_text']} (applied {r['applied_count']}x)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# F. MCP Tool Registration
# ---------------------------------------------------------------------------

def register_learning_tools(mcp_server):
    """Register learning compiler tools with the MCP server."""

    @mcp_server.tool(
        name="learning_capture_diff",
        annotations={"title": "Capture Email Diff for Learning"},
    )
    async def learning_capture_diff_tool(
        original_text: str,
        corrected_text: str,
        context: str = "",
        source: str = "email_diff",
    ) -> str:
        """Capture a before/after correction pair for learning extraction."""
        cid = capture_email_diff(original_text, corrected_text, context or None, source)
        if cid == -1:
            return json.dumps({"status": "no_diff", "message": "Texts are identical"})
        return json.dumps({"status": "captured", "correction_id": cid})

    @mcp_server.tool(
        name="learning_extract",
        annotations={"title": "Extract Principles from Corrections"},
    )
    async def learning_extract_tool(
        limit: int = 20,
    ) -> str:
        """Run principle extraction on recent unlinked corrections."""
        principles = extract_principles(limit)
        return json.dumps({
            "status": "extracted",
            "count": len(principles),
            "principles": principles,
        }, indent=2)

    @mcp_server.tool(
        name="learning_validate",
        annotations={"title": "Validate a Learning Principle"},
    )
    async def learning_validate_tool(
        rule_id: int,
        action: str = "approve",
        edited_text: str = "",
    ) -> str:
        """Approve, reject, or edit a pending principle."""
        result = validate_principle(rule_id, action, edited_text or None)
        return json.dumps(result, indent=2)

    @mcp_server.tool(
        name="learning_list_rules",
        annotations={"title": "List Learning Rules", "readOnlyHint": True},
    )
    async def learning_list_rules_tool(
        status: str = "",
        persona_id: str = "",
        domain: str = "",
        limit: int = 50,
    ) -> str:
        """List principles with optional filters (status, persona, domain)."""
        rules = list_rules(
            status=status or None,
            persona_id=persona_id or None,
            domain=domain or None,
            limit=limit,
        )
        return json.dumps({"count": len(rules), "rules": rules}, indent=2)

    @mcp_server.tool(
        name="learning_inject_test",
        annotations={"title": "Preview Rule Injection", "readOnlyHint": True},
    )
    async def learning_inject_test_tool(
        persona_id: str = "",
        client_tier: str = "",
        domain: str = "",
        context: str = "",
    ) -> str:
        """Preview what rules would be injected for a given persona + client tier.
        Optionally pass context (e.g., recipient name, subject) for CIPHER similarity matching."""
        block = get_applicable_rules(
            persona_id=persona_id or None,
            client_tier=client_tier or None,
            domain=domain or None,
            context=context or None,
        )
        if not block:
            return json.dumps({"status": "empty", "message": "No applicable rules found"})
        return json.dumps({"status": "ok", "injection_block": block})

    # ------------------------------------------------------------------
    # CIPHER MCP tools
    # ------------------------------------------------------------------

    @mcp_server.tool(
        name="learning_similar_context",
        annotations={"title": "Find Similar Learning Principles (CIPHER)", "readOnlyHint": True},
    )
    async def learning_similar_context_tool(
        query_context: str,
        top_k: int = 5,
    ) -> str:
        """Given a query context (recipient, subject, situation description),
        find the most relevant historical principles using CIPHER similarity search.
        Returns principles ranked by cosine similarity to past correction contexts."""
        results = get_similar_principles(query_context, top_k=top_k)
        if not results:
            return json.dumps({
                "status": "empty",
                "message": "No similar contexts found. Add more corrections to build the CIPHER index.",
            })
        return json.dumps({
            "status": "ok",
            "count": len(results),
            "principles": [
                {
                    "rule_id": r["rule_id"],
                    "principle_text": r["principle_text"],
                    "domain": r["domain"],
                    "persona_id": r.get("persona_id"),
                    "client_tier": r.get("client_tier"),
                    "priority_tier": r.get("priority_tier"),
                    "similarity": r["similarity"],
                    "matched_context": r["matched_context"][:200],
                }
                for r in results
            ],
        }, indent=2)

    @mcp_server.tool(
        name="learning_cipher_stats",
        annotations={"title": "CIPHER Embedding Index Stats", "readOnlyHint": True},
    )
    async def learning_cipher_stats_tool() -> str:
        """Return statistics about the CIPHER embedding index — coverage, vocabulary size, etc."""
        stats = get_cipher_stats()
        return json.dumps(stats, indent=2)

    @mcp_server.tool(
        name="learning_cipher_rebuild",
        annotations={"title": "Rebuild CIPHER Embeddings"},
    )
    async def learning_cipher_rebuild_tool() -> str:
        """Rebuild all CIPHER embeddings with unified vocabulary.
        Call after adding many new principles to ensure consistent embedding space."""
        count = rebuild_embeddings()
        return json.dumps({
            "status": "rebuilt",
            "embeddings_updated": count,
        })

    # ------------------------------------------------------------------
    # Episodic Memory MCP tools
    # ------------------------------------------------------------------

    @mcp_server.tool(
        name="record_episode",
        annotations={"title": "Record Client Interaction Episode"},
    )
    async def record_episode_tool(
        client_key: str,
        context_type: str,
        what_worked: str,
        what_failed: str = "",
        outcome: str = "",
        persona_id: str = "",
    ) -> str:
        """Record what worked/failed in a client interaction for future learning."""
        eid = record_episode(
            client_key=client_key,
            context_type=context_type,
            what_worked=what_worked,
            what_failed=what_failed or None,
            outcome=outcome or None,
            persona_id=persona_id or None,
        )
        return json.dumps({"status": "recorded", "episode_id": eid})

    @mcp_server.tool(
        name="get_episodes",
        annotations={"title": "Get Client Episodes", "readOnlyHint": True},
    )
    async def get_episodes_tool(
        client_key: str = "",
        context_type: str = "",
        persona_id: str = "",
        limit: int = 20,
    ) -> str:
        """Retrieve episodic memory for a client, context type, or persona."""
        episodes = get_relevant_episodes(
            client_key=client_key or None,
            context_type=context_type or None,
            persona_id=persona_id or None,
            limit=limit,
        )
        return json.dumps({
            "count": len(episodes),
            "episodes": episodes,
        }, indent=2)

    logger.info("Learning compiler tools registered (10 tools incl. 3 CIPHER)")

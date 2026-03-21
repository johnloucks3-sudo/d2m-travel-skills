"""
Thunderbird Learning Compiler — IOC Build 1
============================================
Captures Commander corrections, extracts principles, applies them forward.

Skills addressed:
  1. Capture the Diff
  2. Extract the Principle
  3. Apply Forward

Architecture:
  Commander edits draft → diff captured → principle extracted → stored in rules DB
  Next draft generated ← rules injected into persona context ← rules fetched

Storage: SQLite (learning_rules.db) with two tables:
  - corrections: raw before/after pairs
  - principles: extracted, tagged rules for injection

Integration:
  - call_persona() injects applicable rules before every LLM call
  - _cos_review_email() captures diffs after COS edits
  - Morning briefing includes LEARNING DIGEST section
"""

import json
import logging
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Any

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
    import re
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
) -> str:
    """Fetch approved, temporally-valid principles and format for system prompt injection.

    Filters by persona (or global), client_tier, domain.
    Respects temporal validity (valid_from/valid_to) — Layer 3.
    Orders by priority tier (inviolable > strong > contextual) — Layer 1 upgrade.
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

        if not rows:
            return ""

        # Increment applied_count
        rule_ids = [r["rule_id"] for r in rows]
        placeholders = ",".join("?" * len(rule_ids))
        conn.execute(
            f"UPDATE principles SET applied_count = applied_count + 1 "
            f"WHERE rule_id IN ({placeholders})",
            rule_ids,
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

    lines = []
    for tier, label in tier_labels.items():
        if lines_by_tier[tier]:
            lines.append(f"\n### {label}")
            lines.extend(lines_by_tier[tier])

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
    ) -> str:
        """Preview what rules would be injected for a given persona + client tier."""
        block = get_applicable_rules(
            persona_id=persona_id or None,
            client_tier=client_tier or None,
            domain=domain or None,
        )
        if not block:
            return json.dumps({"status": "empty", "message": "No applicable rules found"})
        return json.dumps({"status": "ok", "injection_block": block})

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

    logger.info("Learning compiler tools registered (7 tools)")

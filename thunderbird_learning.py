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
    applied_count       INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_principles_persona ON principles(persona_id);
CREATE INDEX IF NOT EXISTS idx_principles_status  ON principles(validation_status);
CREATE INDEX IF NOT EXISTS idx_corrections_ts     ON corrections(timestamp);
"""


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


# ---------------------------------------------------------------------------
# D. Apply — fetch approved rules and format for injection
# ---------------------------------------------------------------------------

def get_applicable_rules(
    persona_id: Optional[str] = None,
    client_tier: Optional[str] = None,
    domain: Optional[str] = None,
) -> str:
    """Fetch approved principles and format as an injection block for system prompts.

    Filters by persona (or global), client_tier, and domain.
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

        where = " AND ".join(conditions)
        rows = conn.execute(
            f"SELECT rule_id, persona_id, domain, client_tier, principle_text "
            f"FROM principles WHERE {where} "
            f"ORDER BY applied_count DESC, created_date DESC LIMIT 15",
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

    # Format injection block
    lines = []
    for r in rows:
        tag_parts = [f"[{r['domain']}]"]
        if r["client_tier"]:
            tag_parts.append(f"({r['client_tier']} tier)")
        if r["persona_id"]:
            tag_parts.append(f"@{r['persona_id']}")
        lines.append(f"- {' '.join(tag_parts)} {r['principle_text']}")

    return (
        "\n\nLEARNED PRINCIPLES (apply these — Commander-validated rules):\n"
        + "\n".join(lines)
    )


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

    logger.info("Learning compiler tools registered (5 tools)")

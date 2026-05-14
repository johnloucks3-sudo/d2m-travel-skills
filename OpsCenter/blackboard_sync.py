"""
blackboard_sync.py — Thunderbird Blackboard Auto-Instantiation Engine
======================================================================
Reads blackboard state and injects it into all six entry points automatically.
Runs every 5 minutes via systemd timer.

Entry points served:
  1. CLAUDE.md              → Claude Code on YOGA (auto-loaded)
  2. OPENCODE_INIT.md     → OpenCode (paste-in kept current)
  3. CLAUDE_DESKTOP_INIT.md → Claude Desktop / Chromebook (paste-in kept current)
  4. blackboard_summary.txt → OpenCode TOM + SSH MOTD + Hale context
  5. .bashrc MOTD           → reads blackboard_summary.txt (one-time setup)
  6. task_processor.py      → Hale reads blackboard_summary.txt (one-time edit)

Zero LLM calls. Pure Python file I/O. Never crashes.

Author: Claude Sonnet 4.6 | Date: 2026-03-30
"""

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Paths ──
ROOT        = Path(__file__).resolve().parent.parent
OPSCENTER   = ROOT / "OpsCenter"
COLLAB      = OPSCENTER / "collaboration"
SUMMARY_TXT = COLLAB / "blackboard_summary.txt"
BLACKBOARD  = COLLAB / "blackboard.md"
RATE_LIMIT  = COLLAB / "rate_limit_status.md"
ROUTING_LOG = COLLAB / "routing_log.md"
SESSION     = ROOT / "session_autosave_latest.md"
CLAUDE_MD   = ROOT / "CLAUDE.md"
OPENCODE_INIT = OPSCENTER / "OPENCODE_INIT.md"
DESKTOP_INIT = OPSCENTER / "CLAUDE_DESKTOP_INIT.md"

MT = timezone(timedelta(hours=-6))
SENTINEL_START = "# BLACKBOARD_START"
SENTINEL_END   = "# BLACKBOARD_END"


def _safe_read(path: Path, default: str = "") -> str:
    """Read a file safely — never raises."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return default


def _safe_write(path: Path, content: str) -> bool:
    """Write a file safely — never raises."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"[blackboard_sync] Write failed {path}: {e}")
        return False


def _extract_field(text: str, field: str, default: str = "UNKNOWN") -> str:
    """Extract a field value from markdown: 'field: value'"""
    match = re.search(rf"^{re.escape(field)}[:\s]+(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else default


def _parse_blackboard() -> dict:
    """Parse blackboard.md for key state fields."""
    text = _safe_read(BLACKBOARD)
    return {
        "claude_budget":   _extract_field(text, "Claude budget status", "UNKNOWN"),
        "active_tasks":    _extract_field(text, "Active tasks", "0"),
        "last_ruling":     _extract_field(text, "Last Deepseek ruling", "NONE"),
        "directives":      _extract_field(text, "Standing directives", "see blackboard.md"),
    }


def _parse_rate_limits() -> dict:
    """Parse rate_limit_status.md for current budget status."""
    text = _safe_read(RATE_LIMIT)
    return {
        "claude":   _extract_field(text, "Claude Sonnet", "UNKNOWN"),
        "groq":     _extract_field(text, "Groq", "UNKNOWN"),
        "deepseek": _extract_field(text, "Deepseek", "UNKNOWN"),
        "opencode": _extract_field(text, "OpenCode", "GREEN"),
    }


def _parse_routing_log() -> str:
    """Get last 3 entries from routing_log.md."""
    text = _safe_read(ROUTING_LOG)
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
    recent = lines[-3:] if len(lines) >= 3 else lines
    return " | ".join(recent) if recent else "No recent routing entries"


def _parse_session() -> dict:
    """Extract open items and next priorities from session_autosave_latest.md."""
    text = _safe_read(SESSION)
    open_items = ""
    next_priorities = ""
    in_open = False
    in_next = False
    open_lines = []
    next_lines = []
    for line in text.splitlines():
        if "## OPEN ITEMS" in line or "### Open" in line.upper():
            in_open, in_next = True, False
            continue
        if "## NEXT" in line.upper() or "### NEXT" in line.upper():
            in_next, in_open = True, False
            continue
        if line.startswith("## ") and in_open:
            in_open = False
        if line.startswith("## ") and in_next:
            in_next = False
        if in_open and line.strip():
            open_lines.append(line.strip().lstrip("-[ ]x").strip())
        if in_next and line.strip():
            next_lines.append(line.strip().lstrip("-[ ]x").strip())
    open_items = "; ".join(open_lines[:3]) if open_lines else "none logged"
    next_priorities = "; ".join(next_lines[:2]) if next_lines else "check session_autosave_latest.md"
    return {"open_items": open_items, "next_priorities": next_priorities}


def _build_summary(bb: dict, rl: dict, session: dict) -> str:
    """Build the 10-line blackboard_summary.txt content."""
    ts = datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")
    lines = [
        f"=== THUNDERBIRD BLACKBOARD [{ts}] ===",
        f"Budget: Claude {rl['claude']} | OpenCode {rl['opencode']} | Groq {rl['groq']} | Deepseek {rl['deepseek']}",
        f"Active tasks: {bb['active_tasks']}",
        f"Last Deepseek ruling: {bb['last_ruling']}",
        f"Open items: {session['open_items']}",
        f"Next priority: {session['next_priorities']}",
        f"Standing: Claude=judgment | OpenCode=ops | Deepseek=arbitrator | PII fence: Deepseek",
        f"Session checkpoint: {SESSION}",
        f"Full blackboard: {BLACKBOARD}",
        "================================================",
    ]
    return "\n".join(lines) + "\n"


def _build_md_block(summary: str) -> str:
    """Build the markdown sentinel block for init files."""
    ts = datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")
    return (
        f"{SENTINEL_START} — auto-updated by blackboard_sync.py — do not edit manually\n"
        f"<!-- Last sync: {ts} -->\n"
        f"```\n{summary}```\n"
        f"{SENTINEL_END}\n"
    )


def _inject_sentinel(file_path: Path, block: str) -> bool:
    """
    Inject block between BLACKBOARD_START and BLACKBOARD_END sentinels.
    If sentinels don't exist, appends them to end of file.
    Never corrupts existing content.
    """
    text = _safe_read(file_path)
    pattern = rf"{re.escape(SENTINEL_START)}.*?{re.escape(SENTINEL_END)}\n?"
    if re.search(pattern, text, re.DOTALL):
        updated = re.sub(pattern, block, text, flags=re.DOTALL)
    else:
        updated = text.rstrip("\n") + "\n\n" + block
    return _safe_write(file_path, updated)


def _append_routing_log(msg: str):
    """Append one-line entry to routing_log.md."""
    ts = datetime.now(MT).strftime("%Y-%m-%dT%H:%M:%S MT")
    entry = f"[{ts}] | SYNC-000 | blackboard_sync | system | 0 | COMPLETE | {msg}\n"
    try:
        with open(ROUTING_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def run_sync():
    """Main sync function — called by systemd timer every 5 minutes."""
    print(f"[blackboard_sync] Starting sync at {datetime.now(MT).strftime('%H:%M MT')}")

    # ── Read all sources ──
    bb      = _parse_blackboard()
    rl      = _parse_rate_limits()
    session = _parse_session()

    # ── Build summary ──
    summary = _build_summary(bb, rl, session)
    md_block = _build_md_block(summary)

    # ── Write blackboard_summary.txt (OpenCode TOM + SSH MOTD + Hale) ──
    ok1 = _safe_write(SUMMARY_TXT, summary)

    # ── Inject into CLAUDE.md ──
    ok2 = _inject_sentinel(CLAUDE_MD, md_block)

    # ── Inject into OPENCODE_INIT.md ──
    ok3 = _inject_sentinel(OPENCODE_INIT, md_block)

    # ── Inject into CLAUDE_DESKTOP_INIT.md ──
    ok4 = _inject_sentinel(DESKTOP_INIT, md_block)

    results = {
        "blackboard_summary.txt": ok1,
        "CLAUDE.md":              ok2,
        "OPENCODE_INIT.md":       ok3,
        "CLAUDE_DESKTOP_INIT.md": ok4,
    }
    failed = [k for k, v in results.items() if not v]
    status = f"OK ({len(results) - len(failed)}/4 files)" if not failed else f"PARTIAL — failed: {failed}"
    print(f"[blackboard_sync] {status}")
    _append_routing_log(status)
    return len(failed) == 0


if __name__ == "__main__":
    import sys
    success = run_sync()
    sys.exit(0 if success else 1)

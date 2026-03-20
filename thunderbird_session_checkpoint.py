"""
Thunderbird Session Checkpoint — Auto-Save Protocol
====================================================
Standing Order 2026-03-16: Every 10 minutes, COS writes a session checkpoint to
session_autosave_latest.md capturing decisions, directives, dossier updates,
WF changes, and infra notes. Prevents continuity loss from battery/power flux.

Usage:
  python3 thunderbird_session_checkpoint.py          # Write checkpoint, print summary
  python3 thunderbird_session_checkpoint.py --json   # Write checkpoint, print JSON result

MCP Integration:
  register_checkpoint_tools(mcp) — exposes session_checkpoint tool

Scheduler Integration:
  job_session_checkpoint() — async job for APScheduler (every 10 min, 0800-2300 MT)
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

THUNDERBIRD_DIR = Path(os.path.expanduser("~/Thunderbird"))
CHECKPOINT_FILE = THUNDERBIRD_DIR / "session_autosave_latest.md"
TELEGRAM_LOG_DIR = THUNDERBIRD_DIR / "memory"
DOSSIER_DIR = THUNDERBIRD_DIR / "dossiers"
LEARNING_DB = THUNDERBIRD_DIR / "learning_rules.db"
TODO_CANDIDATES = [
    THUNDERBIRD_DIR / "dani_followups.md",
    THUNDERBIRD_DIR / "tool_validation_plan.md",
]

# ---------------------------------------------------------------------------
# Collectors
# ---------------------------------------------------------------------------


def _collect_git_log(n: int = 5) -> List[str]:
    """Return last n git commits as short strings."""
    try:
        result = subprocess.run(
            ["git", "log", f"--oneline", f"-{n}"],
            cwd=str(THUNDERBIRD_DIR),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
    except Exception as e:
        logger.warning(f"git log failed: {e}")
    return []


def _collect_uncommitted(max_files: int = 20) -> Dict[str, List[str]]:
    """Return dict with modified/untracked file lists."""
    result: Dict[str, List[str]] = {"modified": [], "new": []}
    try:
        diff = subprocess.run(
            ["git", "diff", "--name-status", "HEAD"],
            cwd=str(THUNDERBIRD_DIR),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if diff.returncode == 0:
            for line in diff.stdout.strip().splitlines():
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    status, fname = parts[0].strip(), parts[1].strip()
                    if status.startswith("A"):
                        result["new"].append(fname)
                    else:
                        result["modified"].append(fname)

        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(THUNDERBIRD_DIR),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if untracked.returncode == 0:
            for fname in untracked.stdout.strip().splitlines():
                if fname.strip():
                    result["new"].append(fname.strip())
    except Exception as e:
        logger.warning(f"git diff/ls-files failed: {e}")

    # Cap lists to avoid bloat
    for k in result:
        result[k] = result[k][:max_files]
    return result


def _collect_sss_pending() -> int:
    """Return count of SSS items in 'coordinating' or 'draft' status (in-memory store)."""
    try:
        from thunderbird_sss import _SSS_STORE
        return sum(1 for s in _SSS_STORE.values() if s.status in ("draft", "coordinating"))
    except Exception:
        return 0


def _collect_learning_pending() -> int:
    """Return count of learning rules with validation_status='pending'."""
    try:
        import sqlite3
        if not LEARNING_DB.exists():
            return 0
        conn = sqlite3.connect(str(LEARNING_DB))
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM principles WHERE validation_status='pending'"
            ).fetchone()
            return row[0] if row else 0
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"Learning DB query failed: {e}")
        return 0


def _collect_recent_telegram_log(lines: int = 5) -> List[str]:
    """Return the last N non-empty lines from the most-recent Telegram session log."""
    try:
        logs = sorted(TELEGRAM_LOG_DIR.glob("session_telegram_*.md"), reverse=True)
        if not logs:
            return []
        latest = logs[0]
        content = latest.read_text(encoding="utf-8", errors="replace")
        all_lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        return all_lines[-lines:]
    except Exception as e:
        logger.warning(f"Telegram log read failed: {e}")
        return []


def _collect_active_todos() -> List[str]:
    """Return first 10 todo-style lines from known todo files."""
    todos: List[str] = []
    for candidate in TODO_CANDIDATES:
        if not candidate.exists():
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
            for ln in text.splitlines():
                stripped = ln.strip()
                if stripped and (
                    stripped.startswith("- [ ]")
                    or stripped.startswith("* [ ]")
                    or stripped.startswith("TODO")
                    or stripped.startswith("PENDING")
                ):
                    todos.append(f"[{candidate.name}] {stripped}")
                    if len(todos) >= 10:
                        break
        except Exception:
            continue
    return todos


def _collect_recent_dossiers(n: int = 5) -> List[str]:
    """Return names of the N most-recently modified dossier files."""
    try:
        if not DOSSIER_DIR.exists():
            return []
        files = sorted(
            DOSSIER_DIR.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return [f.name for f in files[:n]]
    except Exception as e:
        logger.warning(f"Dossier scan failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Checkpoint builder
# ---------------------------------------------------------------------------


def build_checkpoint() -> Dict[str, Any]:
    """Collect all session state and return as a structured dict."""
    now_mt = datetime.now()  # APScheduler sets TZ, but we format naively for readability
    now_utc = datetime.now(timezone.utc)

    commits = _collect_git_log(5)
    uncommitted = _collect_uncommitted()
    sss_pending = _collect_sss_pending()
    learning_pending = _collect_learning_pending()
    telegram_log = _collect_recent_telegram_log(5)
    todos = _collect_active_todos()
    recent_dossiers = _collect_recent_dossiers(5)

    return {
        "generated_at": now_mt.strftime("%Y-%m-%d %H:%M:%S MT"),
        "generated_utc": now_utc.isoformat(),
        "commits": commits,
        "uncommitted": uncommitted,
        "sss_pending": sss_pending,
        "learning_pending": learning_pending,
        "telegram_log": telegram_log,
        "todos": todos,
        "recent_dossiers": recent_dossiers,
    }


def render_checkpoint_md(data: Dict[str, Any]) -> str:
    """Render checkpoint dict to Markdown."""
    lines: List[str] = [
        "# Thunderbird Session Checkpoint",
        f"## Generated: {data['generated_at']}",
        "",
        "---",
        "",
    ]

    # Recent commits
    lines.append("### Recent Commits")
    if data["commits"]:
        for c in data["commits"]:
            lines.append(f"- {c}")
    else:
        lines.append("- (no commits found)")
    lines.append("")

    # Uncommitted changes
    lines.append("### Uncommitted Changes")
    modified = data["uncommitted"].get("modified", [])
    new_files = data["uncommitted"].get("new", [])
    if not modified and not new_files:
        lines.append("- (clean working tree)")
    else:
        for f in modified:
            lines.append(f"- {f} (modified)")
        for f in new_files:
            lines.append(f"- {f} (new)")
    lines.append("")

    # Active work
    lines.append("### Active Work")
    lines.append(f"- SSS: {data['sss_pending']} pending decision(s)")
    lines.append(f"- Learning: {data['learning_pending']} rules pending validation")
    lines.append("")

    # Recent dossiers
    lines.append("### Recently Touched Dossiers")
    if data["recent_dossiers"]:
        for d in data["recent_dossiers"]:
            lines.append(f"- {d}")
    else:
        lines.append("- (none)")
    lines.append("")

    # Open TODOs
    if data["todos"]:
        lines.append("### Open TODOs")
        for t in data["todos"]:
            lines.append(f"- {t}")
        lines.append("")

    # Recent Telegram log tail
    lines.append("### Recent Telegram C2 Log (last 5 lines)")
    if data["telegram_log"]:
        for ln in data["telegram_log"]:
            lines.append(f"  {ln}")
    else:
        lines.append("  (no Telegram session logs found)")
    lines.append("")

    lines.append("---")
    lines.append(f"*Auto-generated by COS · Thunderbird OS · Auto-Save Protocol 2026-03-16*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_session_checkpoint(notes: str = "") -> Dict[str, Any]:
    """Collect state, write checkpoint file, return summary dict.

    Args:
        notes: Optional freeform notes to append (from Commander or COS).

    Returns:
        Dict with keys: status, file, generated_at, sss_pending,
        learning_pending, uncommitted_count, commits_seen.
    """
    try:
        data = build_checkpoint()

        md = render_checkpoint_md(data)

        # Append any freeform notes
        if notes and notes.strip():
            md += f"\n### Session Notes (Manual)\n{notes.strip()}\n"

        CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
        CHECKPOINT_FILE.write_text(md, encoding="utf-8")

        uncommitted_count = (
            len(data["uncommitted"].get("modified", []))
            + len(data["uncommitted"].get("new", []))
        )

        logger.info(
            f"Session checkpoint written: {CHECKPOINT_FILE} "
            f"({uncommitted_count} uncommitted, "
            f"{data['sss_pending']} SSS pending, "
            f"{data['learning_pending']} learning pending)"
        )

        return {
            "status": "ok",
            "file": str(CHECKPOINT_FILE),
            "generated_at": data["generated_at"],
            "sss_pending": data["sss_pending"],
            "learning_pending": data["learning_pending"],
            "uncommitted_count": uncommitted_count,
            "commits_seen": len(data["commits"]),
        }

    except Exception as e:
        logger.error(f"Session checkpoint FAILED: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# MCP tool registration
# ---------------------------------------------------------------------------


def register_checkpoint_tools(mcp_server) -> None:
    """Register session_checkpoint MCP tool."""

    @mcp_server.tool(
        name="session_checkpoint",
        annotations={"title": "Write Session Checkpoint (Auto-Save)"},
    )
    async def session_checkpoint_tool(notes: str = "") -> str:
        """Write a session checkpoint to session_autosave_latest.md.

        Captures recent git commits, uncommitted files, SSS pending decisions,
        learning rules awaiting validation, recent Telegram C2 log tail,
        open TODOs, and recently modified dossiers.

        Args:
            notes: Optional freeform notes from Commander or COS to append.
        """
        result = run_session_checkpoint(notes=notes)
        return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Scheduler job (called by thunderbird_scheduler.py)
# ---------------------------------------------------------------------------


async def job_session_checkpoint() -> None:
    """APScheduler-compatible async job — write checkpoint, log result."""
    result = run_session_checkpoint()
    if result.get("status") == "ok":
        logger.info(
            f"Auto-save checkpoint written at {result['generated_at']} "
            f"— {result['uncommitted_count']} uncommitted, "
            f"{result['sss_pending']} SSS, "
            f"{result['learning_pending']} learning pending"
        )
    else:
        logger.error(f"Auto-save checkpoint FAILED: {result.get('error')}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = run_session_checkpoint()
    if "--json" in sys.argv:
        print(json.dumps(result, indent=2))
    else:
        print(f"Checkpoint written: {result.get('file', 'FAILED')}")
        if result.get("status") == "ok":
            print(f"  Generated:    {result['generated_at']}")
            print(f"  Uncommitted:  {result['uncommitted_count']} file(s)")
            print(f"  SSS pending:  {result['sss_pending']}")
            print(f"  Learning:     {result['learning_pending']} rules pending")
            print(f"  Commits seen: {result['commits_seen']}")
        else:
            print(f"  ERROR: {result.get('error')}")

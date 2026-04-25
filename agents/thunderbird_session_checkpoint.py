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
HTML_CHECKPOINT_FILE = THUNDERBIRD_DIR / "session_autosave_latest.html"
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
# HTML renderer — Midnight Galaxy theme
# ---------------------------------------------------------------------------

def render_checkpoint_html(data: Dict[str, Any]) -> str:
    """Render checkpoint dict to Midnight Galaxy HTML report."""
    ts = data["generated_at"]
    commits = data["commits"]
    modified = data["uncommitted"].get("modified", [])
    new_files = data["uncommitted"].get("new", [])
    todos = data["todos"]
    dossiers = data["recent_dossiers"]
    sss = data["sss_pending"]
    learning = data["learning_pending"]
    total_uncommitted = len(modified) + len(new_files)

    def _commit_row(c: str) -> str:
        parts = c.split(" ", 1)
        h = parts[0] if parts else ""
        msg = parts[1] if len(parts) > 1 else c
        ctype = "feat"
        label = "feat"
        for t in ("fix", "chore", "docs", "refactor", "test"):
            if msg.lower().startswith(t):
                ctype = t if t in ("fix", "chore") else "feat"
                label = t
                break
        return (
            f'<div class="commit">'
            f'<span class="commit-hash">{h}</span>'
            f'<span class="commit-type type-{ctype}">{label}</span>'
            f'<span class="commit-msg">{msg}</span>'
            f'</div>'
        )

    def _file_rows(files: List[str], badge: str) -> str:
        cls = "badge-new" if badge == "new" else "badge-mod"
        return "".join(
            f'<li><span>{f}</span><span class="badge {cls}">{badge}</span></li>'
            for f in files[:10]
        )

    def _todo_rows(todos: List[str]) -> str:
        return "".join(
            f'<div class="todo"><span class="todo-box"></span><span>{t.split("] ", 1)[-1]}</span></div>'
            for t in todos
        )

    def _dossier_rows(ds: List[str]) -> str:
        return "".join(f'<div class="dossier">{d}</div>' for d in ds)

    commits_html = "".join(_commit_row(c) for c in commits) or '<span style="color:#4a4e8f">No commits found</span>'
    files_html = _file_rows(modified, "mod") + _file_rows(new_files, "new") or '<li style="color:#4a4e8f">Clean working tree</li>'
    todos_html = _todo_rows(todos) or '<div style="color:#4a4e8f;font-size:12px">No open TODOs</div>'
    dossiers_html = _dossier_rows(dossiers) or '<div style="color:#4a4e8f;font-size:12px">None</div>'

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:FreeSans,-apple-system,'Segoe UI',sans-serif;background:#2b1e3e;color:#e6e6fa;padding:28px;min-height:100vh}}
  .header{{margin-bottom:24px;border-bottom:1px solid #4a4e8f;padding-bottom:16px;display:flex;justify-content:space-between;align-items:flex-end}}
  .header h1{{font-size:22px;font-weight:700;color:#e6e6fa;letter-spacing:1px}}
  .header .sub{{font-size:11px;color:#a490c2;letter-spacing:2px;text-transform:uppercase;margin-top:3px}}
  .header-right{{text-align:right;font-size:11px;color:#4a4e8f}}
  .header-right .ts{{color:#a490c2;font-size:12px}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}}
  .grid-3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:14px}}
  .card{{background:rgba(74,78,143,.12);border:1px solid rgba(164,144,194,.18);border-radius:10px;padding:16px 18px}}
  .card-title{{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#a490c2;margin-bottom:12px;display:flex;align-items:center;gap:8px}}
  .card-title .dot{{width:6px;height:6px;border-radius:50%;background:#a490c2;display:inline-block}}
  .stat{{text-align:center;padding:14px 10px}}
  .stat-num{{font-size:28px;font-weight:700;color:#a490c2;line-height:1}}
  .stat-label{{font-size:10px;color:#4a4e8f;letter-spacing:1px;text-transform:uppercase;margin-top:5px}}
  .commit{{display:flex;gap:10px;margin-bottom:8px;align-items:flex-start;font-size:12px}}
  .commit-hash{{color:#4a4e8f;font-family:monospace;font-size:11px;min-width:58px;padding-top:1px}}
  .commit-type{{font-size:9px;padding:2px 7px;border-radius:10px;font-weight:700;letter-spacing:.5px;white-space:nowrap;margin-top:1px}}
  .type-feat{{background:rgba(164,144,194,.25);color:#a490c2}}
  .type-fix{{background:rgba(74,78,143,.4);color:#8890d4}}
  .type-chore{{background:rgba(74,78,143,.2);color:#6668a0}}
  .commit-msg{{color:#c8c8e8;line-height:1.4}}
  .file-list{{list-style:none}}
  .file-list li{{font-size:11px;font-family:monospace;color:#8890d4;padding:3px 0;border-bottom:1px solid rgba(74,78,143,.2);display:flex;justify-content:space-between;align-items:center}}
  .file-list li:last-child{{border-bottom:none}}
  .badge{{font-size:9px;padding:1px 6px;border-radius:8px;font-family:sans-serif;font-weight:700}}
  .badge-mod{{background:rgba(74,78,143,.4);color:#8890d4}}
  .badge-new{{background:rgba(164,144,194,.25);color:#a490c2}}
  .dossier{{font-size:12px;color:#c8c8e8;padding:6px 0;border-bottom:1px solid rgba(74,78,143,.2);display:flex;align-items:center;gap:8px}}
  .dossier::before{{content:'◆';font-size:8px;color:#4a4e8f}}
  .dossier:last-child{{border-bottom:none}}
  .todo{{font-size:12px;color:#8890d4;padding:5px 0;border-bottom:1px solid rgba(74,78,143,.15);display:flex;align-items:center;gap:8px}}
  .todo:last-child{{border-bottom:none}}
  .todo-box{{width:11px;height:11px;border:1px solid #4a4e8f;border-radius:2px;display:inline-block;flex-shrink:0}}
  .footer{{margin-top:20px;border-top:1px solid #4a4e8f;padding-top:12px;display:flex;justify-content:space-between;font-size:10px;color:#4a4e8f}}
  .footer .theme-badge{{color:#a490c2}}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>Thunderbird OS — Session Report</h1>
    <div class="sub">Dreams2Memories Travel, LLC · COS Auto-Save</div>
  </div>
  <div class="header-right">
    <div class="ts">{ts}</div>
    <div>Auto-Save Checkpoint</div>
  </div>
</div>
<div class="grid-3">
  <div class="card stat"><div class="stat-num">{len(commits)}</div><div class="stat-label">Recent Commits</div></div>
  <div class="card stat"><div class="stat-num">{total_uncommitted}</div><div class="stat-label">Uncommitted Files</div></div>
  <div class="card stat"><div class="stat-num">{len(todos)}</div><div class="stat-label">Open TODOs</div></div>
</div>
<div class="grid">
  <div class="card">
    <div class="card-title"><span class="dot"></span>Recent Commits</div>
    {commits_html}
  </div>
  <div class="card">
    <div class="card-title"><span class="dot"></span>Recently Touched Dossiers</div>
    {dossiers_html}
  </div>
</div>
<div class="grid">
  <div class="card">
    <div class="card-title"><span class="dot"></span>Uncommitted Changes</div>
    <ul class="file-list">{files_html}</ul>
  </div>
  <div class="card">
    <div class="card-title"><span class="dot"></span>Open TODOs</div>
    {todos_html}
    <div style="margin-top:10px;font-size:10px;color:#4a4e8f">SSS: {sss} pending · Learning: {learning} pending</div>
  </div>
</div>
<div class="footer">
  <span>Auto-generated by COS · Thunderbird OS · Auto-Save Protocol</span>
  <span class="theme-badge">◆ Midnight Galaxy</span>
</div>
</body></html>"""


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

        # Also write Midnight Galaxy HTML report
        html = render_checkpoint_html(data)
        HTML_CHECKPOINT_FILE.write_text(html, encoding="utf-8")

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


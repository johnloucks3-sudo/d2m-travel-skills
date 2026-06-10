"""Delta briefing generator.

Reads the event store + current state and produces a structured Markdown
briefing meant for injection at session startup. The briefing answers:

  1. Since the last closed session, what changed?
  2. What was open at session close that hasn't moved?
  3. What decisions in the event store contradict the current live state?
  4. What should the agent do first?
"""
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .event_store import EventStore, THUNDERBIRD_ROOT
from .watchers.file_watcher import SINGLE_FILES, GLOB_PATTERNS

log = logging.getLogger(__name__)


def _git_log_oneline(limit: int = 20) -> list[tuple[str, str]]:
    try:
        proc = subprocess.run(
            ["git", "log", f"-{limit}", "--pretty=format:%h\t%s\t%ar"],
            cwd=THUNDERBIRD_ROOT, capture_output=True, text=True, timeout=10, check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []
    if proc.returncode != 0:
        return []
    rows = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            rows.append((parts[0], parts[1], parts[2]))
        elif len(parts) == 2:
            rows.append((parts[0], parts[1], ""))
    return rows


def _safe_read(path: Path, max_bytes: int = 200_000) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.read(max_bytes)
    except (OSError, ValueError):
        return ""


def _resolve_watched_paths() -> list[Path]:
    paths: list[Path] = []
    for rel in SINGLE_FILES:
        paths.append(THUNDERBIRD_ROOT / rel)
    for pat in GLOB_PATTERNS:
        try:
            paths.extend(THUNDERBIRD_ROOT.glob(pat))
        except OSError:
            pass
    return paths


def _fmt_age(mtime: float) -> str:
    now = datetime.now().timestamp()
    secs = now - mtime
    if secs < 60:
        return f"{int(secs)}s ago"
    if secs < 3600:
        return f"{int(secs/60)}m ago"
    if secs < 86400:
        return f"{secs/3600:.1f}h ago"
    return f"{secs/86400:.1f}d ago"


class DeltaBriefingGenerator:
    """Produces a Markdown briefing from the event store + current state."""

    def __init__(self, store: EventStore | None = None):
        self.store = store or EventStore()

    def generate(self, current_session_id: str | None = None) -> str:
        prev = self.store.get_latest_session(exclude_id=current_session_id)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines: list[str] = []
        lines.append(f"## STATE BRIDGE BRIEFING — {now_str}")
        lines.append("")

        if prev is None:
            lines.append("### First-run baseline")
            lines.append("- No prior session data on file. Building baseline now.")
            lines.append("")
            lines.extend(self._current_state_block())
            return "\n".join(lines)

        prev_start = prev.get("started_at", "?")
        prev_end = prev.get("ended_at") or "still open"
        lines.append(f"### Since last session ({prev_start} → {prev_end})")
        lines.append("")

        # Use either ended_at or started_at as the cut-off
        since_ts = prev.get("ended_at") or prev.get("started_at")
        events = self.store.get_events_since(since_ts, limit=500) if since_ts else []

        # Group events
        commits = [e for e in events if e["event_type"] == "commit"]
        file_changes = [e for e in events if e["event_type"] == "file_change"]
        mission_updates = [e for e in events if e["event_type"] == "mission_update"]
        decisions = [e for e in events if e["event_type"] == "decision"]
        checkpoints = [e for e in events if e["event_type"] == "checkpoint"]

        # Commits
        if commits:
            lines.append(f"**Commits since last session:** {len(commits)}")
            for c in commits[-10:]:
                detail = c.get("detail") or {}
                sha = detail.get("sha") or c.get("entity_key") or "?"
                subj = c.get("summary") or detail.get("subject") or ""
                lines.append(f"- `{sha}` {subj}")
            lines.append("")
        else:
            # Fall back to git log so the briefing isn't empty on a clean DB
            log_rows = _git_log_oneline(10)
            if log_rows:
                lines.append("**Recent commits (no in-DB delta — showing git log):**")
                for sha, subj, ago in log_rows[:5]:
                    lines.append(f"- `{sha}` {subj}  _{ago}_")
                lines.append("")

        # File changes
        if file_changes:
            # Collapse to most recent per file
            seen: dict[str, dict] = {}
            for e in file_changes:
                k = e.get("entity_key") or "?"
                seen[k] = e
            lines.append(f"**Files touched since last session:** {len(seen)}")
            for k, e in list(seen.items())[:15]:
                lines.append(f"- `{k}` — {e.get('summary', '')}")
            lines.append("")

        # Mission updates
        if mission_updates:
            lines.append(f"**Mission board changes:** {len(mission_updates)}")
            for e in mission_updates[-15:]:
                lines.append(f"- {e.get('summary', '')}")
            lines.append("")

        # Decisions
        if decisions:
            lines.append(f"**Decisions logged:** {len(decisions)}")
            for d in decisions[-10:]:
                lines.append(f"- {d.get('entity_key', '?')}: {d.get('summary', '')}")
            lines.append("")

        # Decision drift — for any decision in this delta, check if earlier
        # decisions for the same entity_key disagree
        drift_lines: list[str] = []
        seen_keys: set[str] = set()
        for d in decisions:
            key = d.get("entity_key")
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)
            chain = self.store.get_decision_drift(key)
            if len(chain) > 1:
                newest = chain[0].get("summary", "")
                older = chain[1].get("summary", "")
                if newest != older:
                    drift_lines.append(f"- `{key}`: previously {older!r} → now {newest!r}")
        if drift_lines:
            lines.append("**Decision drift detected:**")
            lines.extend(drift_lines)
            lines.append("")

        # Pending from last session
        pending = prev.get("open_issues_list") or []
        if pending:
            lines.append("### Pending from last session")
            for item in pending[:15]:
                lines.append(f"- {item}")
            lines.append("")

        # Empty delta path
        if not (commits or file_changes or mission_updates or decisions or checkpoints):
            lines.append("_No changes since last session — continuing clean._")
            lines.append("")

        # Current state snapshot
        lines.extend(self._current_state_block())

        # Suggested next actions
        lines.extend(self._suggest_actions(commits, file_changes, mission_updates,
                                            pending, drift_lines))

        return "\n".join(lines)

    # ---- snapshot blocks ----

    def _current_state_block(self) -> list[str]:
        lines = ["### Current state snapshot"]
        # Recently-modified watched files
        paths = _resolve_watched_paths()
        rows = []
        for p in paths:
            try:
                mt = p.stat().st_mtime
            except (OSError, FileNotFoundError):
                continue
            try:
                rel = str(p.relative_to(THUNDERBIRD_ROOT))
            except ValueError:
                rel = str(p)
            rows.append((rel, mt))
        rows.sort(key=lambda r: r[1], reverse=True)
        if rows:
            lines.append("**Most recently touched watched files:**")
            for rel, mt in rows[:8]:
                lines.append(f"- `{rel}` ({_fmt_age(mt)})")
            lines.append("")

        # Mission summary
        mb_path = THUNDERBIRD_ROOT / "OpsCenter" / "mission_board.json"
        if mb_path.exists():
            try:
                data = json.loads(mb_path.read_text(encoding="utf-8"))
                missions = data.get("missions") or data.get("tasks") or []
                open_ms = [m for m in missions
                           if isinstance(m, dict)
                           and m.get("status") not in ("complete", "completed", "archived", "closed")]
                p0 = [m for m in open_ms if m.get("priority") == "P0"]
                p1 = [m for m in open_ms if m.get("priority") == "P1"]
                lines.append(f"**Mission board:** {len(open_ms)} open ({len(p0)} P0, {len(p1)} P1)")
                for m in p0[:5]:
                    lines.append(f"  - 🔴 {m.get('id')}: {m.get('title', '')[:90]}")
                lines.append("")
            except (OSError, json.JSONDecodeError):
                pass

        # Hale state pulse
        hale_state = THUNDERBIRD_ROOT / "hale_state.json"
        if hale_state.exists():
            try:
                data = json.loads(hale_state.read_text(encoding="utf-8"))
                fp = data.get("financial_pulse") or {}
                if fp:
                    pipe = fp.get("total_d2m_pipeline")
                    if pipe is not None:
                        lines.append(f"**Financial pulse:** D2M pipeline ${pipe:,.2f}")
                        lines.append("")
            except (OSError, json.JSONDecodeError):
                pass
        return lines

    def _suggest_actions(self, commits, file_changes, mission_updates,
                         pending, drift) -> list[str]:
        out = ["### Suggested next actions"]
        rank = 1
        if drift:
            out.append(f"{rank}. Resolve decision drift items above before further changes.")
            rank += 1
        if pending:
            out.append(f"{rank}. Pick up {min(len(pending), 3)} pending item(s) from last session.")
            rank += 1
        if mission_updates:
            out.append(f"{rank}. Review mission board deltas — {len(mission_updates)} change(s) since last session.")
            rank += 1
        if not (drift or pending or mission_updates):
            out.append(f"{rank}. No carry-over flagged. Confirm AM brief priorities and proceed.")
        out.append("")
        return out


if __name__ == "__main__":  # smoke test
    logging.basicConfig(level=logging.INFO)
    print(DeltaBriefingGenerator().generate())

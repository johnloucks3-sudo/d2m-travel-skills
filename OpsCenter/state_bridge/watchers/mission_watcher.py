"""Mission board watcher — diffs mission_board.json state across ticks.

Reads `OpsCenter/mission_board.json` directly (faster + structured) rather
than scraping the CLI output. Falls back to `mission_board_sync.py list` if
the JSON is unreadable. Records new missions, status/priority/assignment
changes as `mission_update` events.
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from ..event_store import EventStore, THUNDERBIRD_ROOT

log = logging.getLogger(__name__)

MISSION_BOARD_JSON = THUNDERBIRD_ROOT / "OpsCenter" / "mission_board.json"
MISSION_BOARD_CLI = THUNDERBIRD_ROOT / "OpsCenter" / "mission_board_sync.py"

TRACKED_FIELDS = ("status", "priority", "assigned_to", "title")


class MissionWatcher:
    """Tracks mission board entries by ID."""

    def __init__(self, store: EventStore, board_path: Path = MISSION_BOARD_JSON):
        self.store = store
        self.board_path = Path(board_path)
        # mission_id -> snapshot of TRACKED_FIELDS
        self._state: dict[str, dict[str, Any]] = {}
        self._initialized = False

    def _load_missions(self) -> list[dict[str, Any]]:
        """Load missions from JSON, fall back to CLI parse."""
        if self.board_path.exists():
            try:
                data = json.loads(self.board_path.read_text(encoding="utf-8"))
                missions = data.get("missions") or data.get("tasks") or []
                if isinstance(missions, list):
                    return [m for m in missions if isinstance(m, dict)]
            except (OSError, json.JSONDecodeError) as exc:
                log.warning("mission_board.json read failed: %s — trying CLI", exc)
        return self._load_via_cli()

    def _load_via_cli(self) -> list[dict[str, Any]]:
        """Parse the CLI list output into mission dicts. Best-effort."""
        try:
            proc = subprocess.run(
                ["python3", str(MISSION_BOARD_CLI), "list"],
                cwd=THUNDERBIRD_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            log.warning("mission CLI failed: %s", exc)
            return []
        missions: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for line in proc.stdout.splitlines():
            s = line.strip()
            if not s or s.startswith("=") or "MISSION BOARD" in s:
                continue
            if "MISSION-" in s and ":" in s:
                if current:
                    missions.append(current)
                parts = s.split("MISSION-", 1)[1].split(":", 1)
                if len(parts) == 2:
                    mid = "MISSION-" + parts[0].strip()
                    title = parts[1].strip()
                    current = {"id": mid, "title": title,
                               "status": "", "priority": "", "assigned_to": ""}
            elif current and "Status:" in s:
                # "Status: foo | Priority: bar | To: baz ⏰ ..."
                for chunk in s.split("|"):
                    c = chunk.strip()
                    if c.startswith("Status:"):
                        current["status"] = c[7:].strip()
                    elif c.startswith("Priority:"):
                        current["priority"] = c[9:].strip()
                    elif c.startswith("To:"):
                        current["assigned_to"] = c[3:].strip()
        if current:
            missions.append(current)
        return missions

    def _snapshot(self, m: dict[str, Any]) -> dict[str, Any]:
        return {k: m.get(k, "") for k in TRACKED_FIELDS}

    def initialize(self, session_id: str) -> int:
        for m in self._load_missions():
            mid = m.get("id")
            if mid:
                self._state[mid] = self._snapshot(m)
        self._initialized = True
        log.info("mission_watcher: seeded %d missions", len(self._state))
        return len(self._state)

    def tick(self, session_id: str) -> int:
        if not self._initialized:
            self.initialize(session_id)
            return 0
        changes = 0
        current_ids: set[str] = set()
        for m in self._load_missions():
            mid = m.get("id")
            if not mid:
                continue
            current_ids.add(mid)
            snap = self._snapshot(m)
            prev = self._state.get(mid)
            if prev is None:
                self.store.record_event(
                    session_id=session_id,
                    event_type="mission_update",
                    entity_type="mission",
                    entity_key=mid,
                    summary=f"new mission: {snap.get('title', '')[:120]}",
                    detail={"action": "created", "fields": snap},
                )
                self._state[mid] = snap
                changes += 1
                continue
            diffs = {k: (prev[k], snap[k]) for k in TRACKED_FIELDS if prev.get(k) != snap.get(k)}
            if diffs:
                # Build a compact human-readable summary
                pieces = [f"{k}: {old!r} → {new!r}" for k, (old, new) in diffs.items()]
                self.store.record_event(
                    session_id=session_id,
                    event_type="mission_update",
                    entity_type="mission",
                    entity_key=mid,
                    summary=f"{mid}: " + "; ".join(pieces)[:300],
                    detail={"action": "updated", "diffs": {k: {"prev": p, "now": n}
                                                            for k, (p, n) in diffs.items()}},
                )
                self._state[mid] = snap
                changes += 1
        # Deletions
        removed = set(self._state.keys()) - current_ids
        for mid in removed:
            self.store.record_event(
                session_id=session_id,
                event_type="mission_update",
                entity_type="mission",
                entity_key=mid,
                summary=f"{mid} removed from board",
                detail={"action": "removed"},
            )
            del self._state[mid]
            changes += 1
        if changes:
            log.info("mission_watcher: %d change(s)", changes)
        return changes

    def board_snapshot(self) -> list[dict[str, Any]]:
        """Used by briefing — current mission rows (no events recorded)."""
        return self._load_missions()

"""File watcher — polls stat() mtime for designated key files.

Watches:
  - OpsCenter/collaboration/blackboard.md
  - OpsCenter/opencode_memory.md
  - dossiers/*.md         (glob — picks up additions)
  - AGENTS.md

Any mtime change records a `file_change` event. Missing files are tolerated
silently — they simply aren't tracked until they appear.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ..event_store import EventStore, THUNDERBIRD_ROOT

log = logging.getLogger(__name__)

# Single-file watch list (path relative to Thunderbird root)
SINGLE_FILES = [
    "OpsCenter/collaboration/blackboard.md",
    "OpsCenter/opencode_memory.md",
    "AGENTS.md",
    "hale_state.json",
    "hale_brief.md",
]

# Glob patterns to expand on every tick
GLOB_PATTERNS = [
    "dossiers/*.md",
]


class FileWatcher:
    """Polls mtime for a fixed set of files plus glob patterns."""

    def __init__(self, store: EventStore, root: Path = THUNDERBIRD_ROOT):
        self.store = store
        self.root = Path(root)
        self._mtimes: dict[str, float] = {}
        self._initialized = False

    def _resolve_paths(self) -> list[Path]:
        paths: list[Path] = []
        for rel in SINGLE_FILES:
            paths.append(self.root / rel)
        for pat in GLOB_PATTERNS:
            try:
                paths.extend(self.root.glob(pat))
            except OSError as exc:
                log.warning("glob %s failed: %s", pat, exc)
        return paths

    def _safe_mtime(self, path: Path) -> float | None:
        try:
            return path.stat().st_mtime
        except (FileNotFoundError, OSError):
            return None

    def initialize(self, session_id: str) -> int:
        """Seed mtime map without recording events."""
        for p in self._resolve_paths():
            mt = self._safe_mtime(p)
            if mt is not None:
                self._mtimes[str(p)] = mt
        self._initialized = True
        log.info("file_watcher: seeded %d files", len(self._mtimes))
        return len(self._mtimes)

    def tick(self, session_id: str) -> int:
        """Detect mtime changes. Returns count of events recorded."""
        if not self._initialized:
            self.initialize(session_id)
            return 0
        changes = 0
        for p in self._resolve_paths():
            key = str(p)
            mt = self._safe_mtime(p)
            if mt is None:
                # File deleted — record once
                if key in self._mtimes:
                    self.store.record_event(
                        session_id=session_id,
                        event_type="file_change",
                        entity_type="file",
                        entity_key=str(p.relative_to(self.root) if p.is_absolute() else p),
                        summary=f"{p.name} removed",
                        detail={"path": key, "action": "deleted"},
                    )
                    del self._mtimes[key]
                    changes += 1
                continue
            prev = self._mtimes.get(key)
            if prev is None:
                # New file appeared
                self.store.record_event(
                    session_id=session_id,
                    event_type="file_change",
                    entity_type="file",
                    entity_key=str(p.relative_to(self.root) if p.is_absolute() else p),
                    summary=f"{p.name} created",
                    detail={"path": key, "action": "created", "mtime": mt},
                )
                self._mtimes[key] = mt
                changes += 1
            elif mt != prev:
                self.store.record_event(
                    session_id=session_id,
                    event_type="file_change",
                    entity_type="file",
                    entity_key=str(p.relative_to(self.root) if p.is_absolute() else p),
                    summary=f"{p.name} modified",
                    detail={"path": key, "action": "modified",
                            "mtime_prev": prev, "mtime_now": mt},
                )
                self._mtimes[key] = mt
                changes += 1
        if changes:
            log.info("file_watcher: %d change(s)", changes)
        return changes

    def dirty_snapshot(self) -> list[str]:
        """Return list of currently-tracked files sorted by mtime DESC.

        Top entries are the most recently touched — used by the briefing's
        'recently changed' section.
        """
        rows = []
        for p in self._resolve_paths():
            mt = self._safe_mtime(p)
            if mt is None:
                continue
            try:
                rel = str(p.relative_to(self.root))
            except ValueError:
                rel = str(p)
            rows.append((rel, mt))
        rows.sort(key=lambda r: r[1], reverse=True)
        return [r[0] for r in rows]

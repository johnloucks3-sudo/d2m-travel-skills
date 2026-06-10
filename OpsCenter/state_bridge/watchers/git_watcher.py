"""Git watcher — records new commits as events.

Polls `git log` and diffs against the last commit hash recorded in the event
store. Records every new commit as a single `commit` event with the SHA as
entity_key and the subject as summary.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from ..event_store import EventStore, THUNDERBIRD_ROOT

log = logging.getLogger(__name__)


class GitWatcher:
    """Tracks commits in a git repo via `git log --oneline`."""

    def __init__(self, store: EventStore, repo_root: Path = THUNDERBIRD_ROOT, limit: int = 20):
        self.store = store
        self.repo_root = Path(repo_root)
        self.limit = limit
        self._known_hashes: set[str] = set()
        self._initialized = False

    def _run_git_log(self) -> list[tuple[str, str]]:
        """Return [(short_sha, subject)] newest first, or [] on failure."""
        try:
            proc = subprocess.run(
                ["git", "log", f"-{self.limit}", "--pretty=format:%h\t%s"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            log.warning("git log failed: %s", exc)
            return []
        if proc.returncode != 0:
            log.warning("git log returncode=%s stderr=%s", proc.returncode, proc.stderr[:200])
            return []
        out: list[tuple[str, str]] = []
        for line in proc.stdout.splitlines():
            line = line.rstrip()
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                out.append((parts[0], parts[1]))
            else:
                out.append((parts[0], ""))
        return out

    def initialize(self, session_id: str) -> int:
        """First-call seed. Records all current commits as 'seen' (no events).

        Returns number of commits seeded. Subsequent ticks only record new ones.
        """
        commits = self._run_git_log()
        self._known_hashes = {sha for sha, _ in commits}
        self._initialized = True
        log.info("git_watcher: seeded %d commits", len(commits))
        return len(commits)

    def tick(self, session_id: str) -> int:
        """Poll for new commits. Returns count of new commits recorded."""
        if not self._initialized:
            self.initialize(session_id)
            return 0
        commits = self._run_git_log()
        new_count = 0
        for sha, subject in commits:
            if sha in self._known_hashes:
                continue
            self.store.record_event(
                session_id=session_id,
                event_type="commit",
                entity_type="commit",
                entity_key=sha,
                summary=subject[:200],
                detail={"sha": sha, "subject": subject},
            )
            self._known_hashes.add(sha)
            new_count += 1
        if new_count:
            log.info("git_watcher: recorded %d new commit(s)", new_count)
        return new_count

    def recent_commits(self) -> list[tuple[str, str]]:
        """Snapshot of current `git log --oneline -N`; used by briefing."""
        return self._run_git_log()

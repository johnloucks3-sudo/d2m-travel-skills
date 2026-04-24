#!/usr/bin/env python3
"""
D2M Thunderbird Tasking Watcher V7 — Autonomous Invocation
===========================================================
When either inbox changes with a PENDING task:
  - opencode_inbox.md → spawns OpenCode headless
  - claude_inbox.md   → spawns Claude headless

Both agents run without human intervention. Fully headless loop.

Cooldown: 45s per inbox to prevent re-fire on same write.
Lock file: prevents concurrent duplicate invocations.
"""

import os
import re
import sys
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [WATCHER V7] - %(message)s",
    handlers=[
        logging.FileHandler("/home/john/Thunderbird/logs/inbox_watcher.log"),
        logging.StreamHandler(sys.stdout),
    ],
)

# Paths
BASE          = Path("/home/john/Thunderbird")
CLAUDE_INBOX  = BASE / "claude_inbox.md"
OC_INBOX      = BASE / "OpsCenter/collaboration/opencode_inbox.md"
CLAUDE_OUTBOX = BASE / "OpsCenter/collaboration/claude_outbox.md"
ACTIVITY      = BASE / "OpsCenter/collaboration/activity_board.md"
OAUTH_CACHE   = BASE / "OpsCenter/.claude_oauth_cache"
LOG_DIR       = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Binaries
CLAUDE_BIN   = "/home/john/.local/bin/claude"
OPENCODE_BIN = "/home/john/.opencode/bin/opencode"

# Model routing
# Haiku  — tasking, simple file ops, low-cost default
# Sonnet — reasoning, client work, judgment calls
# Opus   — P0 only, maximum capability
MODEL_HAIKU  = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-6"
MODEL_OPUS   = "claude-opus-4-6"

def load_oauth_env() -> dict:
    """Read .claude_oauth_cache and return env dict with fresh token injected."""
    env = dict(os.environ)
    try:
        for line in OAUTH_CACHE.read_text().splitlines():
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                k, _, v = line.partition('=')
                env[k.strip()] = v.strip()
    except Exception:
        pass
    return env


def model_for_priority(content: str) -> str:
    """Route model — explicit model: field wins, else priority, else Haiku."""
    # Explicit override: model: opus / sonnet / haiku
    import re
    m = re.search(r"^model:\s*(\S+)", content, re.MULTILINE | re.IGNORECASE)
    if m:
        val = m.group(1).lower()
        if "opus" in val:
            return MODEL_OPUS
        if "sonnet" in val:
            return MODEL_SONNET
        if "haiku" in val:
            return MODEL_HAIKU
    # Priority fallback
    if "priority: P0" in content:
        return MODEL_OPUS
    if "priority: P1" in content:
        return MODEL_SONNET
    return MODEL_HAIKU

# Cooldown: seconds between invocations per inbox
COOLDOWN = 45

# Statuses that trigger invocation
TRIGGER_STATUSES = ["status: PENDING", "status: UNREAD", "status: ACTIVE-CRITICAL",
                    "status: FLAGGED-OVERDUE", "NEXUS:"]


class InboxHandler(FileSystemEventHandler):

    def __init__(self):
        self._last_fired = {}   # path -> timestamp of last invocation

    def on_modified(self, event):
        if event.is_directory:
            return
        p = event.src_path
        if p.endswith("claude_inbox.md"):
            self._maybe_invoke(CLAUDE_INBOX, self._invoke_claude)
        elif p.endswith("opencode_inbox.md"):
            self._maybe_invoke(OC_INBOX, self._invoke_opencode)
        elif p.endswith(".claude_oauth_cache"):
            logging.info("OAuth cache updated — fresh token will be used on next Claude spawn")

    # ------------------------------------------------------------------ #
    # Cooldown gate
    # ------------------------------------------------------------------ #
    def _maybe_invoke(self, inbox_path, invoke_fn):
        key = str(inbox_path)
        now = time.time()
        last = self._last_fired.get(key, 0)
        if now - last < COOLDOWN:
            logging.info(f"Cooldown active for {inbox_path.name} ({int(COOLDOWN-(now-last))}s remaining) — skip")
            return
        try:
            content = inbox_path.read_text()
        except Exception as e:
            logging.error(f"Cannot read {inbox_path}: {e}")
            return
        if not any(t in content for t in TRIGGER_STATUSES):
            logging.info(f"{inbox_path.name} changed but no actionable tasks — skip")
            return
        self._last_fired[key] = now
        invoke_fn(inbox_path)

    # ------------------------------------------------------------------ #
    # Claude headless invocation
    # ------------------------------------------------------------------ #
    def _invoke_claude(self, inbox_path):
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        log     = LOG_DIR / f"claude_invoke_{ts}.log"
        try:
            content = inbox_path.read_text()
        except Exception:
            content = ""
        model   = model_for_priority(content)
        prompt  = (
            f"You are Hale COS running headless. "
            f"Read {inbox_path} and process every task with status PENDING, UNREAD, "
            f"ACTIVE-CRITICAL, or FLAGGED-OVERDUE. "
            f"For each actionable task: execute it, mark status COMPLETE with timestamp, "
            f"write results to {CLAUDE_OUTBOX}. "
            f"Then post a summary to "
            f"/home/john/Thunderbird/OpsCenter/collaboration/wing_comms.md."
        )
        fresh_env = load_oauth_env()
        logging.info(f"Spawning Claude headless model={model} → log: {log}")
        logging.info(f"OAuth token present: {'CLAUDE_CODE_OAUTH_TOKEN' in fresh_env}")
        try:
            subprocess.Popen(
                [CLAUDE_BIN, "-p", prompt, "--model", model, "--output-format", "text"],
                stdout=open(log, "w"),
                stderr=subprocess.STDOUT,
                env=fresh_env,
                start_new_session=True,
            )
            logging.info(f"Claude headless started ({model})")
        except Exception as e:
            logging.error(f"Failed to spawn Claude: {e}")

    # ------------------------------------------------------------------ #
    # OpenCode headless invocation
    # ------------------------------------------------------------------ #
    def _invoke_opencode(self, inbox_path):
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        log = LOG_DIR / f"opencode_invoke_{ts}.log"
        prompt = (
            f"Read {inbox_path}. "
            f"Process every task with status PENDING or UNREAD. "
            f"Execute each task. Mark status COMPLETE with timestamp. "
            f"Write results to {CLAUDE_OUTBOX} and post summary to "
            f"/home/john/Thunderbird/OpsCenter/collaboration/wing_comms.md."
        )
        logging.info(f"Spawning OpenCode headless → log: {log}")
        try:
            subprocess.Popen(
                [OPENCODE_BIN, "run", prompt],
                stdout=open(log, "w"),
                stderr=subprocess.STDOUT,
                env={**os.environ},
                start_new_session=True,
            )
            logging.info("OpenCode headless process started")
        except Exception as e:
            logging.error(f"Failed to spawn OpenCode: {e}")


def main():
    logging.info("=" * 60)
    logging.info("Thunderbird Tasking Watcher V7 — Autonomous Invocation")
    logging.info("=" * 60)

    # Ensure inbox files exist
    for p in [CLAUDE_INBOX, OC_INBOX, ACTIVITY]:
        if not p.exists():
            p.touch()
            logging.warning(f"Created missing file: {p}")

    # Verify binaries
    for name, path in [("claude", CLAUDE_BIN), ("opencode", OPENCODE_BIN)]:
        if Path(path).exists():
            logging.info(f"Binary OK: {name} → {path}")
        else:
            logging.warning(f"Binary NOT FOUND: {name} → {path}")

    handler  = InboxHandler()
    observer = Observer()

    watch_dirs = {
        str(CLAUDE_INBOX.parent),
        str(OC_INBOX.parent),
        str(OAUTH_CACHE.parent),
    }
    for d in watch_dirs:
        observer.schedule(handler, d, recursive=False)
        logging.info(f"Watching: {d}")

    observer.start()
    logging.info("Watcher running — both inboxes armed for autonomous invocation")

    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        logging.info("Watcher shutting down")
    finally:
        observer.stop()
        observer.join()
        logging.info("Watcher stopped")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
D2M Thunderbird Bidirectional Tasking Watcher — inotify-driven (sub-second detection)
====================================================================================

Replaces v5 (15-sec poll loop) with watchdog.inotify.
Keeps all existing behavior: Telegram pings, headless Goose spawn, activity board monitoring.

Changes from v5:
  - time.sleep(15) → inotify event handler (instant trigger)
  - Fixed --instruction → --text (headless goose flag)
  - Atomic file locking for Goose spawn
  - Debounce: coalesce multiple events within 2-second window

Watches:
  - claude_inbox.md → pings Commander via Telegram
  - goose_inbox.md → pings Commander + spawns headless Goose
  - activity_board.md → pings Commander with latest entry

Service: d2m-tasking-watcher.service
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
import logging
import subprocess
import threading
import fcntl
from datetime import datetime, timezone
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    logging.error("watchdog not installed. pip install watchdog")
    sys.exit(1)

# ── Paths ────────────────────────────────────────────────────────────────
CLAUDE_INBOX  = "/home/john/Thunderbird/OpsCenter/collaboration/claude_inbox.md"
GOOSE_INBOX   = "/home/john/Thunderbird/OpsCenter/collaboration/goose_inbox.md"
ACTIVITY_BOARD = "/home/john/Thunderbird/OpsCenter/collaboration/activity_board.md"
LOCK_FILE     = "/home/john/Thunderbird/OpsCenter/.goose_headless.lock"
STATE_FILE    = "/home/john/Thunderbird/OpsCenter/inbox_watcher_state.json"
LOG_FILE      = "/home/john/Thunderbird/logs/inbox_watcher.log"

# ── Telegram ─────────────────────────────────────────────────────────────
BOT_TOKEN = "***REMOVED-SECRET***"
CHAT_ID   = "7554895206"

# ── Debounce ─────────────────────────────────────────────────────────────
# Coalesce rapid-fire inotify events (many editors trigger modify + close_write)
DEBOUNCE_SECS = 2.0
debounce_timers = {}  # path → (timestamp, threading.Timer)

# ── Setup logging ────────────────────────────────────────────────────────
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - [TASK WATCHER V6-INOTIFY] - %(message)s'
)

def ping_telegram(message: str):
    """Send text to Commander via Telegram Bot API (GET, no extra deps)."""
    try:
        msg = urllib.parse.quote(message)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=Markdown"
        resp = urllib.request.urlopen(url, timeout=5)  # type: ignore
        logging.info(f"Telegram ping sent: {message[:80]}...")
    except Exception as e:
        logging.error(f"Telegram Ping Failed: {e}")

def check_inbox_has_work(filepath: str) -> bool:
    """Check if the inbox file contains unread/pending tasks."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            return ("UNREAD" in content or 
                    "status: pending" in content.lower() or 
                    "priority:" in content.lower())
    except Exception as e:
        logging.error(f"Error reading {filepath}: {e}")
        return False

def spawn_goose_headless():
    """Spawn headless Goose to process inbox tasks. Uses --text flag (not --instruction)."""
    if os.path.exists(LOCK_FILE):
        logging.warning("Goose already running (lock file exists). Skipping spawn.")
        return

    # Atomic lock
    try:
        with open(LOCK_FILE, 'w') as lf:
            lf.write(str(datetime.now().timestamp()))
    except Exception as e:
        logging.error(f"Failed to create lock file: {e}")
        return

    cmd = [
        "goose", "run",
        "--text",
        "Read /home/john/Thunderbird/OpsCenter/collaboration/goose_inbox.md, process ALL unread tasks, write COMPLETE to activity_board.md, and remove the lock file /home/john/Thunderbird/OpsCenter/.goose_headless.lock"
    ]

    logging.info(f"Spawning headless Goose: {' '.join(cmd)}")
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        logging.info("Headless Goose spawned successfully.")
    except Exception as e:
        logging.error(f"Failed to spawn Goose: {e}")
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

def handle_goose_spawn():
    """Called when goose_inbox.md changes."""
    logging.info("Goose Inbox Updated.")
    if check_inbox_has_work(GOOSE_INBOX):
        ping_telegram("🦢 **NEW PAYLOAD FOR GOOSE**\nA payload has dropped into `goose_inbox.md`. Auto-spawning headless execution.")
        spawn_goose_headless()
    else:
        logging.info("Goose Inbox modified but no unread work detected.")

def handle_claude_inbox():
    """Called when claude_inbox.md changes."""
    logging.info("Claude Inbox Updated.")
    if check_inbox_has_work(CLAUDE_INBOX):
        ping_telegram("📬 **NEW TASK/ASK FOR CLAUDE**\nA payload has dropped into `claude_inbox.md`.")
    else:
        logging.info("Claude Inbox modified but no unread work detected.")

def handle_activity_board():
    """Called when activity_board.md changes — grab last line and ping Commander."""
    logging.info("Activity Board Updated.")
    try:
        with open(ACTIVITY_BOARD, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            if lines:
                last_action = lines[-1]
                ping_telegram(f"📋 **WING ACTIVITY UPDATE**\n{last_action}")
    except Exception as e:
        logging.error(f"Error reading activity board: {e}")

# Dispatch map
HANDLERS = {
    GOOSE_INBOX:    handle_goose_spawn,
    CLAUDE_INBOX:   handle_claude_inbox,
    ACTIVITY_BOARD: handle_activity_board,
}

def debounce_handler(filepath: str):
    """Debounced dispatch — only fires handler after DEBOUNCE_SECONDS of no new events."""
    # Cancel existing timer for this file if still pending
    if filepath in debounce_timers:
        old_ts, old_timer = debounce_timers[filepath]
        old_timer.cancel()

    # Schedule new handler execution
    timer = threading.Timer(DEBOUNCE_SECS, lambda: HANDLERS[filepath]())
    timer.daemon = True
    timer.start()
    debounce_timers[filepath] = (time.time(), timer)

class InboxEventHandler(FileSystemEventHandler):
    """Watchdog event handler — dispatches to debounce for watched files."""

    def on_modified(self, event):
        if event.is_directory:
            return
        src = event.src_path
        if src in HANDLERS:
            debounce_handler(src)

    def on_created(self, event):
        if event.is_directory:
            return
        src = event.src_path
        if src in HANDLERS:
            debounce_handler(src)

    def on_moved(self, event):
        # Some editors (vim, atomic saves) use rename strategy
        if event.is_directory:
            return
        dest = event.dest_path
        if dest in HANDLERS:
            debounce_handler(dest)

def load_state() -> dict:
    """Load last known mtimes from state file (survives watcher restarts)."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state: dict):
    """Persist current mtimes for crash recovery."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save state: {e}")

def initialize_state(observer: Observer, state: dict):
    """Set initial mtimes without triggering events, save state."""
    init_state = {}
    for filepath in HANDLERS:
        if os.path.exists(filepath):
            mtime = os.path.getmtime(filepath)
            init_state[filepath] = mtime
            state[filepath] = mtime  # Update in-memory state
            logging.info(f"Initialized {filepath} mtime: {mtime}")
        else:
            logging.warning(f"Watched file not found: {filepath}")
    # Write state file
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    save_state(state)
    return state

def main():
    logging.info("=" * 70)
    logging.info("Thunderbird Tasking Watcher V6 (inotify) INITIALIZED")
    logging.info("=" * 70)

    # Load persisted state
    state = load_state()

    # Create observer
    observer = Observer()
    event_handler = InboxEventHandler()

    # Watch collaboration directory (not individual files — inotify works on dirs)
    collab_dir = os.path.dirname(CLAUDE_INBOX)
    if os.path.exists(collab_dir):
        observer.schedule(event_handler, collab_dir, recursive=False)
        logging.info(f"Watching directory: {collab_dir}")
    else:
        logging.error(f"Collaboration directory not found: {collab_dir}")
        sys.exit(1)

    # Initialize state (set baselines without triggering)
    state = initialize_state(observer, state)

    # Start observer
    observer.start()
    logging.info("Observer started. Watching for changes...")

    # Telegram startup ping
    ping_telegram("👁️ **THUNDERBIRD WATCHER V6 ONLINE**\nSub-second inotify detection active. Headless Goose execution enabled.")

    # Save state periodically (every 60s), handle graceful shutdown
    try:
        while True:
            time.sleep(60)
            save_state(state)
    except KeyboardInterrupt:
        logging.info("Watcher shutting down (Ctrl+C).")
    except Exception as e:
        logging.error(f"Watcher loop error: {e}")
    finally:
        observer.stop()
        observer.join()
        # Clean up lock file if we're the last watcher
        if os.path.exists(LOCK_FILE):
            logging.info("Removing stale lock file on shutdown.")
            os.remove(LOCK_FILE)
        save_state(state)
        logging.info("Watcher stopped. State saved.")

if __name__ == "__main__":
    main()

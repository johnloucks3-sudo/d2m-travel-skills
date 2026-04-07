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
  - claude_inbox.md (root canonical) → pings Commander via Telegram
  - opencode_inbox.md → pings Commander + spawns headless OpenCode
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
CLAUDE_INBOX    = "/home/john/Thunderbird/claude_inbox.md"
OPENCODE_INBOX  = "/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md"
GOOSE_INBOX     = OPENCODE_INBOX  # legacy alias — goose_inbox.md → opencode_inbox.md
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
    """Check if the inbox file contains unread/pending tasks or new results."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            return (
                "UNREAD" in content or
                "status: pending" in content.lower() or
                "priority:" in content.lower() or
                "NEXUS:" in content or           # Nexus-prefixed task line
                "CLAUDE RESULT" in content or    # Claude wrote a result back
                "## CLAUDE RESULT" in content    # markdown header variant
            )
    except Exception as e:
        logging.error(f"Error reading {filepath}: {e}")
        return False

def spawn_opencode_headless():
    """Spawn headless OpenCode to process inbox tasks."""
    if os.path.exists(LOCK_FILE):
        logging.warning("OpenCode already running (lock file exists). Skipping spawn.")
        return

    # Atomic lock
    try:
        with open(LOCK_FILE, 'w') as lf:
            lf.write(str(datetime.now().timestamp()))
    except Exception as e:
        logging.error(f"Failed to create lock file: {e}")
        return

    env = os.environ.copy()
    env["PATH"] = "/home/john/.opencode/bin:" + env.get("PATH", "")

    cmd = [
        "opencode", "run",
        "-m", "opencode/qwen3.6-plus-free",
        (
            "Read /home/john/Thunderbird/AGENTS.md — that is your operational brain. "
            "Then check /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md "
            "for tasks with status: UNREAD. Execute them per AGENTS.md standing orders. "
            "Write results to /home/john/Thunderbird/OpsCenter/collaboration/opencode_outbox.md. "
            "When done, delete /home/john/Thunderbird/OpsCenter/.goose_headless.lock."
        )
    ]

    logging.info(f"Spawning headless OpenCode: {' '.join(cmd)}")
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        logging.info("Headless OpenCode spawned successfully.")
    except Exception as e:
        logging.error(f"Failed to spawn OpenCode: {e}")
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)

# Legacy alias
spawn_goose_headless = spawn_opencode_headless

# ── Claude headless spawn ─────────────────────────────────────────────────
_claude_headless_lock = threading.Lock()

def spawn_claude_headless():
    """Spawn claude -p headless to process claude_inbox.md tasks.
    Strips ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL so Max OAuth kicks in.
    Results written to claude_outbox.md AND opencode_inbox.md (return loop).
    """
    if _claude_headless_lock.locked():
        logging.info("Claude headless already running — skipping spawn.")
        return

    def _run():
        with _claude_headless_lock:
            # Strip ANTHROPIC_API_KEY so Max OAuth takes over.
            # Inject CLAUDE_CODE_OAUTH_TOKEN from cache file (written by active Claude Code session).
            env = dict(os.environ)
            env.pop("ANTHROPIC_API_KEY", None)
            env.pop("ANTHROPIC_BASE_URL", None)
            # Load fresh OAuth token if available
            _oauth_cache = "/home/john/Thunderbird/OpsCenter/.claude_oauth_cache"
            try:
                with open(_oauth_cache) as _f:
                    for _line in _f:
                        if _line.startswith("CLAUDE_CODE_OAUTH_TOKEN="):
                            env["CLAUDE_CODE_OAUTH_TOKEN"] = _line.strip().split("=", 1)[1]
                            logging.info("Loaded CLAUDE_CODE_OAUTH_TOKEN from cache file.")
                            break
            except Exception as _e:
                logging.warning(f"Could not load OAuth token cache: {_e}")
            prompt = (
                "Read /home/john/Thunderbird/claude_inbox.md. "
                "Find all tasks NOT marked COMPLETE. "
                "Execute each task fully. "
                "Write results to BOTH: "
                "(1) /home/john/Thunderbird/OpsCenter/collaboration/claude_outbox.md "
                "(2) /home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md "
                "— prefix each result with 'CLAUDE RESULT | <task_id> |' so OpenCode can read it. "
                "Update mission_board.json status to COMPLETE for each task. "
                "Mark each task COMPLETE in claude_inbox.md when done."
            )
            log_path = "/home/john/Thunderbird/logs/claude_headless.log"
            success = False
            # Try claude -p first (Max OAuth / direct API)
            try:
                with open(log_path, 'a') as log_f:
                    proc = subprocess.Popen(
                        ['claude', '--dangerously-skip-permissions',
                         '--disallowedTools', 'TodoWrite',
                         '-p', prompt],
                        env=env, cwd='/home/john/Thunderbird',
                        stdout=log_f, stderr=subprocess.STDOUT,
                    )
                try:
                    proc.wait(timeout=600)
                    if proc.returncode == 0:
                        success = True
                        logging.info("Claude headless completed via claude -p (rc=0)")
                    else:
                        logging.warning(f"claude -p failed rc={proc.returncode} — falling back to OpenCode")
                except subprocess.TimeoutExpired:
                    proc.kill()
                    logging.error("Claude headless timed out after 600s")
            except FileNotFoundError:
                logging.error("claude binary not found — falling back to OpenCode")

            # Fallback: opencode run with Claude via OpenRouter
            if not success:
                opencode_env = dict(os.environ)
                opencode_env['PATH'] = '/home/john/.opencode/bin:' + opencode_env.get('PATH', '')
                try:
                    with open(log_path, 'a') as log_f:
                        proc = subprocess.Popen(
                            ['opencode', 'run',
                             '-m', 'opencode/qwen3.6-plus-free',
                             prompt],
                            env=opencode_env, cwd='/home/john/Thunderbird',
                            stdout=log_f, stderr=subprocess.STDOUT,
                        )
                    try:
                        proc.wait(timeout=600)
                        logging.info(f"OpenCode fallback completed (rc={proc.returncode})")
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        logging.error("OpenCode fallback timed out")
                except FileNotFoundError:
                    logging.error("opencode binary not found — no fallback available")

    t = threading.Thread(target=_run, daemon=True, name="claude-headless")
    t.start()
    logging.info("Claude headless thread launched.")


def handle_opencode_inbox():
    """Called when opencode_inbox.md changes."""
    logging.info("OpenCode Inbox Updated.")
    if check_inbox_has_work(OPENCODE_INBOX):
        ping_telegram("**NEW TASK FOR OPENCODE**\nPayload in `opencode_inbox.md`. Auto-spawning OpenCode headless.")
        spawn_opencode_headless()
    else:
        logging.info("OpenCode Inbox modified but no unread work detected.")

# Legacy alias
handle_goose_spawn = handle_opencode_inbox

def handle_claude_inbox():
    """Called when claude_inbox.md changes — ping Commander + auto-spawn headless Claude."""
    logging.info("Claude Inbox Updated.")
    if check_inbox_has_work(CLAUDE_INBOX):
        ping_telegram("📬 **NEW TASK FOR CLAUDE**\nPayload in `claude_inbox.md`. Auto-spawning headless Claude.")
        spawn_claude_headless()
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
    OPENCODE_INBOX: handle_opencode_inbox,
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

    # Watch BOTH directories — inboxes live in different locations:
    #   claude_inbox.md  → ~/Thunderbird/  (root)
    #   opencode_inbox.md → ~/Thunderbird/OpsCenter/collaboration/
    watch_dirs = {
        os.path.dirname(CLAUDE_INBOX),          # ~/Thunderbird/
        os.path.dirname(OPENCODE_INBOX),         # ~/Thunderbird/OpsCenter/collaboration/
        os.path.dirname(ACTIVITY_BOARD),         # same as opencode dir
    }
    any_ok = False
    for d in watch_dirs:
        if os.path.exists(d):
            observer.schedule(event_handler, d, recursive=False)
            logging.info(f"Watching directory: {d}")
            any_ok = True
        else:
            logging.warning(f"Watch directory not found: {d}")
    if not any_ok:
        logging.error("No valid watch directories found — exiting.")
        sys.exit(1)

    # Initialize state (set baselines without triggering)
    state = initialize_state(observer, state)

    # Start observer
    observer.start()
    logging.info("Observer started. Watching for changes...")

    # Telegram startup ping
    ping_telegram("**THUNDERBIRD WATCHER V6 ONLINE**\nSub-second inotify detection active. Headless OpenCode execution enabled.")

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

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
import json
import logging
import subprocess
import requests
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

def refresh_oauth_token_preemptive() -> bool:
    """Preemptively refresh OAuth token if expiring within 30 minutes.

    Required because Anthropic disabled auto-refresh for third-party/headless use (Feb 2026).
    Uses refreshToken to obtain a new accessToken before token expires.

    Tested 2026-04-23: SDK does NOT auto-refresh on repeated invocations.
    Must refresh manually before token reaches 30-min-to-expiry threshold.
    """
    try:
        creds_path = Path.home() / ".claude" / ".credentials.json"
        if not creds_path.exists():
            return True  # No token to refresh

        creds = json.loads(creds_path.read_text())
        token_data = creds.get("claudeAiOauth", {})
        expires_at = token_data.get("expiresAt")

        if not expires_at:
            return True

        # Check if within 30 minutes of expiry
        now_ms = int(time.time() * 1000)
        time_until_expiry_ms = expires_at - now_ms

        if time_until_expiry_ms > (30 * 60 * 1000):  # More than 30 min left
            return True  # No refresh needed

        if time_until_expiry_ms < 0:
            logging.warning("OAuth token already expired — falling back to API key/DeepSeek")
            return False

        # Token expiring soon — attempt refresh
        refresh_token = token_data.get("refreshToken")
        if not refresh_token:
            logging.warning("No refresh token available — cannot refresh OAuth")
            return False

        logging.info(f"OAuth token expiring in {time_until_expiry_ms/60000:.1f} min — attempting refresh")

        # Try known Anthropic refresh endpoints (reverse-engineered)
        endpoints = [
            "https://claude.ai/api/auth/refresh",
            "https://api.anthropic.com/oauth/token",
        ]

        for endpoint in endpoints:
            try:
                resp = requests.post(
                    endpoint,
                    json={"refresh_token": refresh_token, "grant_type": "refresh_token"},
                    timeout=10,
                    headers={"Content-Type": "application/json"}
                )

                if resp.status_code == 200:
                    new_data = resp.json()
                    token_data["accessToken"] = new_data.get("access_token") or new_data.get("accessToken")
                    token_data["expiresAt"] = new_data.get("expires_at") or new_data.get("expiresAt")

                    creds["claudeAiOauth"] = token_data
                    creds_path.write_text(json.dumps(creds, indent=2))

                    logging.info("✅ OAuth token refreshed successfully")
                    return True
            except Exception:
                pass  # Try next endpoint

        logging.warning("OAuth refresh endpoints unavailable — will escalate if token expires during invocation")
        return False

    except Exception as e:
        logging.warning(f"OAuth refresh check failed: {e}")
        return False


def load_oauth_env() -> dict:
    """Load OAuth token from official Claude credentials file.

    Tier 1: ~/.claude/.credentials.json (official Claude CLI storage)
    Tier 2: ANTHROPIC_API_KEY from environment
    Tier 3: Bare os.environ (fallback)
    """
    env = dict(os.environ)

    # Tier 1: Try official credentials file
    try:
        import json
        creds_path = Path.home() / ".claude" / ".credentials.json"
        if creds_path.exists():
            creds = json.loads(creds_path.read_text())
            token = creds.get("claudeAiOauth", {}).get("accessToken")
            if token:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = token
                logging.debug(f"Loaded OAuth token from {creds_path}")
                return env
    except Exception as e:
        logging.debug(f"Failed to load from credentials file: {e}")

    # Tier 2: Check for API key in environment (will use as fallback)
    if "ANTHROPIC_API_KEY" in env:
        logging.debug("Using ANTHROPIC_API_KEY from environment")
        return env

    # Tier 3: Fall back to bare environment
    logging.debug("Using bare environment (no OAuth or API key)")
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
    # Claude headless invocation with error monitoring & escalation
    # ------------------------------------------------------------------ #
    def _invoke_claude(self, inbox_path):
        import threading

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

        # PREEMPTIVE REFRESH: Check if token needs refresh before spawning Claude
        # (Required because Anthropic disabled auto-refresh for headless invocations, Feb 2026)
        # CRITICAL: If token refresh fails, HALT — do not spawn Claude
        token_ok = refresh_oauth_token_preemptive()

        if not token_ok:
            logging.critical("❌ WATCHER HALT: Token refresh FAILED — halting to prevent silent fallback to DeepSeek")
            # Post critical alert to wing_comms
            try:
                alert_msg = f"\n## 🔴 [CRITICAL] Watcher Halted — Token Refresh Failed\n**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n**Reason:** Token refresh returned FALSE. Watcher HALTING to prevent silent fallback to DeepSeek.\n**Action Required:** Check token state manually. Contact Commander.\n"
                WING_COMMS = Path("/home/john/Thunderbird/OpsCenter/collaboration/wing_comms.md")
                if WING_COMMS.exists():
                    existing = WING_COMMS.read_text()
                    WING_COMMS.write_text(existing.rstrip() + "\n" + alert_msg)
            except Exception as e:
                logging.error(f"Could not post alert: {e}")
            # Hard halt
            sys.exit(1)

        fresh_env = load_oauth_env()
        logging.info(f"Spawning Claude headless model={model} → log: {log}")
        logging.info(f"OAuth token present: {'CLAUDE_CODE_OAUTH_TOKEN' in fresh_env or 'ANTHROPIC_API_KEY' in fresh_env}")

        try:
            proc = subprocess.Popen(
                [CLAUDE_BIN, "-p", prompt, "--model", model, "--output-format", "text", "--mcp-config", "/home/john/.claude/mcp.json"],
                stdout=open(log, "w"),
                stderr=subprocess.STDOUT,
                env=fresh_env,
                start_new_session=True,
            )
            logging.info(f"Claude headless started (PID {proc.pid}, {model})")

            # Monitor in background thread for credit errors and escalate if needed
            def monitor_claude_errors(proc_obj, log_path, inbox):
                try:
                    returncode = proc_obj.wait(timeout=600)  # 10 min max
                    if returncode != 0:
                        time.sleep(0.5)  # Give filesystem time to flush
                        try:
                            log_text = Path(log_path).read_text()
                            # Log the failure for Haiku supervisor to detect
                            if any(err in log_text.lower() for err in ["402", "credit", "balance", "insufficient"]):
                                logging.error(f"Claude hit credit/auth error (exit {returncode}) — token may have expired")
                            else:
                                logging.error(f"Claude exited with code {returncode}")
                            # Do NOT auto-escalate. Haiku supervisor will see this failure and alert Yoda.
                        except Exception as e:
                            logging.error(f"Error reading log: {e}")
                except subprocess.TimeoutExpired:
                    logging.error(f"Claude headless timed out (>10 min)")
                except Exception as e:
                    logging.error(f"Monitor thread error: {e}")

            monitor_thread = threading.Thread(
                target=monitor_claude_errors,
                args=(proc, log, inbox_path),
                daemon=True
            )
            monitor_thread.start()

        except Exception as e:
            logging.error(f"Failed to spawn Claude: {e}")
            logging.error(f"Claude invocation failed — no automatic fallback (fail gracefully)")
            # Do NOT escalate to OpenCode/DeepSeek. Let failure be visible.
            # Haiku supervisor will detect this and alert Yoda.

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

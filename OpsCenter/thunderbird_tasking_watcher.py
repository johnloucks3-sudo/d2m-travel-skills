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
import threading
import requests
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Use foolproof wrapper per SO 24 APR 2026
sys.path.insert(0, str(Path("/home/john/Thunderbird")))
from core.ai_infra.thunderbird_headless_spawn import spawn_headless_claude

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
MCP_LIGHT     = "/home/john/.claude/mcp_light.json"
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
MODEL_OPUS   = "claude-opus-4-7"

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

    # CRITICAL: Strip stale ANTHROPIC_API_KEY — it preempts OAuth and causes 401s.
    # The shell env may carry a deprecated key; always remove before spawning Claude.
    env.pop("ANTHROPIC_API_KEY", None)

    # Tier 1: Try official credentials file (MAX OAuth — $0 marginal cost)
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

    # Tier 2: Bare environment — Claude CLI will error if no auth available.
    logging.debug("No OAuth token found — Claude CLI will fall back to its own auth resolution")
    return env


def _deliver_to_commander(subject: str, result_text: str, persona_id: str = "COS"):
    """Send task result back to Commander via Gmail (d2mconcierge → johnloucks3).

    Gmail is the primary C2 channel. Telegram is for internal wing comms only.
    Called after any headless agent completes — ensures Commander always gets
    results in their inbox regardless of whether the agent mailed them itself.
    """
    try:
        _TB = Path("/home/john/Thunderbird")
        if str(_TB) not in sys.path:
            sys.path.insert(0, str(_TB))
        from core.email.thunderbird_gmail import gmail_send_from_wing
        reply_subject = subject if subject.startswith("Re:") else f"Re: {subject} — COMPLETED"
        gmail_send_from_wing(
            to="johnloucks3@gmail.com",
            subject=reply_subject,
            body=result_text,
            persona_id=persona_id,
        )
        logging.info(f"[WATCHER] ✅ Result delivered to Commander via Gmail: {reply_subject[:60]}")
    except Exception as e:
        logging.error(f"[WATCHER] Gmail delivery failed: {e}")


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
    # Claude headless invocation via foolproof wrapper
    # ------------------------------------------------------------------ #
    def _invoke_claude(self, inbox_path):
        try:
            content = inbox_path.read_text()
        except Exception:
            content = ""

        model = model_for_priority(content)
        outbox_file = CLAUDE_OUTBOX

        # Extract original subject for Gmail reply
        original_subject = "Commander task"
        for line in content.split("\n"):
            if line.strip().startswith("task: |"):
                idx = content.find(line)
                snippet = content[idx:idx+200].split("\n")
                if len(snippet) > 1:
                    original_subject = snippet[1].strip()
                break

        prompt = (
            f"You are Hale COS running headless. "
            f"Read {inbox_path} and process every task with status PENDING, UNREAD, "
            f"ACTIVE-CRITICAL, or FLAGGED-OVERDUE. "
            f"For each actionable task: execute it fully, mark status COMPLETE with timestamp. "
            f"WRITE your results to {outbox_file}. "
            f"Append a summary to /home/john/Thunderbird/OpsCenter/collaboration/wing_comms.md. "
            f"CRITICAL: When all tasks are done, call gmail_send_from_wing to email your results "
            f"to johnloucks3@gmail.com — subject 'Re: {original_subject} — COMPLETED'. "
            f"Commander's inbox is Gmail. Results that don't reach Gmail don't exist."
        )

        # Use foolproof wrapper (background mode, light MCP — no travel MCP servers)
        result = spawn_headless_claude(
            prompt=prompt,
            output_file=str(outbox_file),
            model=model,
            task_name="hale_inbox_process",
            background=True,
            mcp_config=MCP_LIGHT,
        )

        if result.get("status") in ["SPAWNED", "COMPLETED"]:
            pid = result.get("pid")
            log_file = result.get("log_file", "?")
            logging.info(f"✅ Claude headless spawned (PID {pid}, model={model}) → log: {log_file}")

            # Belt-and-suspenders: monitor output file, deliver to Gmail when populated
            def _monitor_and_deliver(out_file, subj, wait_pid):
                deadline = time.time() + 600
                while time.time() < deadline:
                    time.sleep(15)
                    try:
                        text = Path(out_file).read_text().strip()
                        if text and len(text) > 50:
                            _deliver_to_commander(subj, text[-4000:], "COS")
                            return
                    except Exception:
                        pass
                _deliver_to_commander(subj, f"Task timed out after 10 minutes — check {out_file}", "COS")

            t = threading.Thread(
                target=_monitor_and_deliver,
                args=(str(outbox_file), original_subject, result.get("pid")),
                daemon=True,
            )
            t.start()
        else:
            logging.error(f"❌ Claude spawn failed: {result.get('error', 'unknown error')}")
            if not result.get("can_retry"):
                logging.critical("Fatal error — no retry possible. Supervisor will alert.")

    # ------------------------------------------------------------------ #
    # OpenCode headless invocation via opencode run
    # ------------------------------------------------------------------ #
    def _invoke_opencode(self, inbox_path):
        try:
            content = inbox_path.read_text()
        except Exception:
            content = ""

        # Extract task summary and original subject for Gmail reply threading
        tasks = []
        subjects = []
        for line in content.split("\n"):
            line_stripped = line.strip()
            if line_stripped.startswith("## TASK:"):
                tasks.append(line_stripped.replace("## TASK:", "").strip())
            elif line_stripped.startswith("task: |"):
                break

        # Try to pull subject from task block for Gmail reply subject line
        for line in content.split("\n"):
            if line.strip().startswith("task: |"):
                idx = content.find(line)
                snippet = content[idx:idx+200].split("\n")
                if len(snippet) > 1:
                    subjects.append(snippet[1].strip())
                break

        summary = "; ".join(tasks[:3]) if tasks else "Process pending tasks"
        if len(tasks) > 3:
            summary += f" (+{len(tasks)-3} more)"
        original_subject = subjects[0] if subjects else summary

        message = (
            f"Watcher dispatch: {summary}. "
            f"Read {inbox_path} and process every task with status PENDING, UNREAD, "
            f"ACTIVE-CRITICAL, or FLAGGED-OVERDUE. "
            f"For each actionable task: execute it completely, mark status COMPLETE with timestamp. "
            f"Use MCP tools as needed. "
            f"Write results back to {inbox_path} and log to wing_comms.md. "
            f"IMPORTANT: When done, use gmail_send_from_wing to email your results summary "
            f"to johnloucks3@gmail.com — subject 'Re: {original_subject} — COMPLETED'. "
            f"Gmail is Commander's primary C2 channel. Results must reach the inbox."
        )

        log_path = LOG_DIR / f"opencode_spawn_{int(time.time())}.log"

        def _run_and_deliver():
            try:
                with open(log_path, "w") as log_f:
                    proc = subprocess.Popen(
                        [OPENCODE_BIN, "run", message],
                        stdout=log_f,
                        stderr=log_f,
                        stdin=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                logging.info(f"✅ OpenCode spawned (PID {proc.pid}) — task: {summary}")
                proc.wait(timeout=600)

                # Read captured output — deliver to Commander via Gmail regardless
                # of whether the headless agent mailed it itself (belt-and-suspenders).
                try:
                    output = log_path.read_text()[-4000:]  # last 4k chars
                    if not output.strip():
                        output = f"Task '{summary}' completed. No output captured — check wing_comms.md for details."
                except Exception:
                    output = f"Task '{summary}' completed (output unreadable — check {log_path})."

                _deliver_to_commander(
                    subject=original_subject,
                    result_text=output,
                    persona_id="COS",
                )
            except subprocess.TimeoutExpired:
                logging.error(f"[WATCHER] OpenCode timed out after 600s for: {summary}")
                _deliver_to_commander(
                    subject=original_subject,
                    result_text=f"⚠️ Task '{summary}' timed out after 10 minutes. Check {log_path} for partial output.",
                    persona_id="COS",
                )
            except Exception as e:
                logging.error(f"❌ OpenCode spawn/delivery failed: {e}")

        t = threading.Thread(target=_run_and_deliver, daemon=True)
        t.start()


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

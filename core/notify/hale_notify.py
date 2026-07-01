#!/usr/bin/env python3
"""
hale_notify.py — Autonomous Wing Notification Router
=====================================================
Routes alerts to HALE/STERLING first. Escalates to Commander ONLY on:
  - Repair failed AND system is client-affecting
  - Financial commitment required
  - Genuinely unresolvable without Commander action

All other alerts → internal log + Telegram with [AUTONOMY] tag (no action required).
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")

RELAY = ROOT / "core/relay/wing_relay.py"
NOTIFY_LOG = ROOT / "logs/hale_notify.log"
SYS_PYTHON = "/usr/bin/python3"
VENV_PYTHON = str(ROOT / ".venv/bin/python3")

COMMANDER_TELEGRAM_ID = 7554895206


def _log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    line = f"[{ts}] {msg}"
    NOTIFY_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(NOTIFY_LOG, "a") as f:
        f.write(line + "\n")
    print(line)


def _relay(msg: str):
    """Send via wing_relay.py → Telegram."""
    try:
        subprocess.run(
            [SYS_PYTHON, str(RELAY), "send", "CC", msg],
            timeout=15, capture_output=True,
        )
    except Exception as e:
        _log(f"Relay failed: {e}")


def notify_hale(bot: str, task: str, error: str, repaired: bool = False,
                client_affecting: bool = False):
    """
    Route a bot failure notification.

    - repaired=True       → [AUTONOMY REPAIR] Telegram (brief, no action needed)
    - repaired=False + client_affecting → escalate to Commander
    - repaired=False + NOT client_affecting → log + monitor note, no action needed
    """
    ts = datetime.now(timezone.utc).strftime("%H:%M UTC")

    if repaired:
        msg = (
            f"⚡ *HALE AUTONOMY* [{ts}]\n"
            f"Bot `{bot}` / `{task}` failed → auto-repaired.\n"
            f"Error: `{error[:120]}`\n"
            f"_No Commander action needed._"
        )
        _log(f"AUTONOMY-REPAIR: {bot}/{task} repaired.")
        _relay(msg)

    elif client_affecting:
        msg = (
            f"🔴 *COMMANDER ACTION REQUIRED* [{ts}]\n"
            f"`{bot}/{task}` failed. Auto-repair unsuccessful.\n"
            f"*CLIENT-AFFECTING — needs your attention.*\n"
            f"Error: `{error[:200]}`"
        )
        _log(f"ESCALATE-CLIENT: {bot}/{task} — {error[:100]}")
        _relay(msg)

    else:
        msg = (
            f"🟡 *HALE MONITOR* [{ts}]\n"
            f"`{bot}/{task}` failed (non-client). Repair queued.\n"
            f"`{error[:120]}`"
        )
        _log(f"MONITOR: {bot}/{task} — {error[:100]}")
        _relay(msg)


def notify_sterling(issue: str, detail: str):
    """Notify Sterling of process/code failures via his inbox."""
    ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
    _log(f"STERLING-NOTIFY: {issue} — {detail[:100]}")
    sterling_inbox = ROOT / "OpsCenter/collaboration/sterling_inbox.md"
    sterling_inbox.parent.mkdir(parents=True, exist_ok=True)
    entry = (
        f"\n---\n**[{ts}] HALE → STERLING: {issue}**\n"
        f"{detail}\n"
        f"_Auto-routed by hale_notify.py_\n"
    )
    with open(sterling_inbox, "a") as f:
        f.write(entry)
    msg = f"⚙️ *STERLING QUEUE* [{ts}]\n{issue}\n`{detail[:150]}`"
    _relay(msg)


def ci_auto_repair(skill_id: str) -> bool:
    """Attempt autonomous repair of a CI skill. Returns True if repaired."""
    repair_map = {
        "credential-keepalive": [
            VENV_PYTHON, str(ROOT / "scripts/keepalive_supervisor.py"), "--force-all"
        ],
        "fare-watch-centrav": [
            VENV_PYTHON, str(ROOT / "scripts/centrav_session_relogin.py"), "--force"
        ],
        "portal-access": [
            VENV_PYTHON, str(ROOT / "scripts/portal_keepalive.py")
        ],
    }
    cmd = repair_map.get(skill_id)
    if not cmd:
        return False
    _log(f"CI-REPAIR: attempting auto-repair for {skill_id}")
    try:
        result = subprocess.run(cmd, timeout=120, capture_output=True, text=True)
        success = result.returncode == 0
        _log(f"CI-REPAIR: {skill_id} → {'OK' if success else 'FAIL'} rc={result.returncode}")
        return success
    except Exception as e:
        _log(f"CI-REPAIR: {skill_id} exception — {e}")
        return False


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("bot")
    p.add_argument("task")
    p.add_argument("error")
    p.add_argument("--repaired", action="store_true")
    p.add_argument("--client-affecting", action="store_true", dest="client")
    args = p.parse_args()
    notify_hale(args.bot, args.task, args.error,
                repaired=args.repaired, client_affecting=args.client)

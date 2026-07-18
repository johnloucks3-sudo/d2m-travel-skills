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
NOTIFY_DIGEST = ROOT / "OpsCenter/state/notify_digest.jsonl"
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


def _digest(kind: str, bot: str, task: str, error: str):
    """Roll a NON-actionable event into the digest the EOD/morning brief reads
    (MISSION-669: auto-repaired + non-client MONITOR + routine Sterling routing
    stop hitting real-time Telegram — the Commander sees them batched in the
    brief instead). Structured JSONL so brief_data_generator can window it to
    the last 24h. Best-effort — a digest write must never break the caller."""
    try:
        NOTIFY_DIGEST.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.now(timezone.utc).isoformat(),
               "kind": kind, "bot": bot, "task": task, "error": (error or "")[:300]}
        with open(NOTIFY_DIGEST, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:
        _log(f"Digest write failed: {e}")


def _relay(msg: str):
    """Send via wing_relay.py → Telegram. RESERVED for actionable escalations
    only (client-affecting / financial / Three-Gates) — see MISSION-669."""
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
        # Auto-repaired = "No Commander action needed" → digest only, not
        # real-time Telegram (MISSION-669, Commander directive 2026-07-17).
        _log(f"AUTONOMY-REPAIR: {bot}/{task} repaired.")
        _digest("autonomy_repair", bot, task, error)

    elif client_affecting:
        # Actionable — keep real-time Telegram escalation.
        msg = (
            f"🔴 *COMMANDER ACTION REQUIRED* [{ts}]\n"
            f"`{bot}/{task}` failed. Auto-repair unsuccessful.\n"
            f"*CLIENT-AFFECTING — needs your attention.*\n"
            f"Error: `{error[:200]}`"
        )
        _log(f"ESCALATE-CLIENT: {bot}/{task} — {error[:100]}")
        _digest("escalate_client", bot, task, error)
        _relay(msg)

    else:
        # Non-client MONITOR ("repair queued", no action needed) → digest only.
        _log(f"MONITOR: {bot}/{task} — {error[:100]}")
        _digest("monitor", bot, task, error)


def _emergency_voice_backup(bot: str, task: str, error: str):
    """Backup channel for client-affecting P0s, alongside Telegram (not a
    replacement) -- proven live 2026-07-10, test call confirmed clear audio.
    Never raises: a failed backup call must not break the primary escalation."""
    try:
        from core.voice.emergency_voice_notify import emergency_call
        message = (
            f"Thunderbird Wing emergency. {bot} failed on {task}. "
            f"This is client affecting and needs your attention. "
            f"Check Telegram for details."
        )
        result = emergency_call(message)
        _log(f"EMERGENCY-VOICE: {bot}/{task} — call status {result.get('status')}")
    except Exception as e:
        _log(f"EMERGENCY-VOICE FAILED (non-fatal, Telegram already sent): {e}")


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
    # Routine process/code routing — lands in Sterling's inbox + the digest,
    # not real-time Telegram (MISSION-669). Sterling reads the inbox; the
    # Commander sees it batched in the brief.
    _digest("sterling_queue", issue, "", detail)


def ci_auto_repair(skill_id: str) -> bool:
    """Attempt autonomous repair of a CI skill. Returns True if repaired.

    CUTOVER 2026-07-02 (Sterling A7): routed through the SAFE safety-contract
    runner (rapid_repair / run_capability with the conservative armed-tier
    policy) instead of the raw ci_auto_repair_engine.run_repair. SAFE tiers
    auto-apply; CAUTION+DESTRUCTIVE stage. STAGED / not-repaired returns False.
    (This helper currently has no callers — routed anyway as defense-in-depth so
    no code path can raw-fire ungated destructive repairs.)
    """
    _log(f"CI-REPAIR: attempting SAFE auto-repair for {skill_id}")
    try:
        from core.ci.repairs.rapid_repair import _load_policy
        from core.ci.repairs.schema import run_capability, Decision
        import core.ci.repairs.rapid_repair  # noqa: F401  (registers all clusters)
        r = run_capability(skill_id, apply=True, armed_tiers=_load_policy())
        success = (r.decision == Decision.AUTO_APPLIED
                   and r.verify_after.value == "GREEN")
        _log(f"CI-REPAIR: {skill_id} → {r.decision.value} "
             f"(verify={r.verify_after.value}) → {'OK' if success else 'not-recovered'}")
        return success
    except ImportError:
        # Fallback: direct subprocess for the most critical skills
        repair_map = {
            "credential-keepalive": [
                VENV_PYTHON, str(ROOT / "scripts/keepalive_supervisor.py"), "--force-all"
            ],
            "fare-watch-centrav": [
                VENV_PYTHON, str(ROOT / "scripts/centrav_session_relogin.py"), "--force"
            ],
            "portal-access": [
                VENV_PYTHON, str(ROOT / "scripts/centrav_session_relogin.py")
            ],
            "regent-portal-live": [
                VENV_PYTHON, str(ROOT / "scripts/rssc_session_keepalive.py")
            ],
            "dani-identity-layer": [
                "systemctl", "--user", "restart", "thunderbird-telegram-gw.service"
            ],
            "supertimer-bot-health": [
                "systemctl", "--user", "restart", "thunderbird-supertimer.service"
            ],
        }
        cmd = repair_map.get(skill_id)
        if not cmd:
            _log(f"CI-REPAIR: {skill_id} — no repair registered")
            return False
        try:
            result = subprocess.run(cmd, timeout=120, capture_output=True, text=True)
            success = result.returncode == 0
            _log(f"CI-REPAIR: {skill_id} (fallback) → {'OK' if success else 'FAIL'} rc={result.returncode}")
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

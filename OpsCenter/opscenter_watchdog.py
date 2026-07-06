"""
OpsCenter Self-Healing Watchdog
===============================
Runs every 2 minutes. Checks services, MCP, queues.
Auto-restarts crashed services. Detects crash loops.
Alerts Commander via direct Telegram HTTP (independent of C2 bot).

Author: Victoria "Victory" Hale, SES-6 (VCSAF)
"""

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from OpsCenter.incident_queue import enqueue_incident
except ImportError:
    try:
        from incident_queue import enqueue_incident
    except ImportError:
        def enqueue_incident(event):
            pass  # fallback: swallow silently if queue unavailable

# ── Paths ──
ROOT = Path(__file__).resolve().parent.parent
OPSCENTER = ROOT / "OpsCenter"
QUEUE_FILE = OPSCENTER / "01_TASK_QUEUE.json"
STATE_FILE = ROOT / "logs" / "watchdog_state.json"
WATCHDOG_LOG = ROOT / "logs" / "watchdog.log"
MCP_URL = "http://127.0.0.1:8765/mcp"

# ── Thresholds ──
STUCK_THRESHOLD_SECONDS = 300   # 5 min
CRASH_LOOP_THRESHOLD = 3        # restarts in window
CRASH_LOOP_WINDOW = 600         # 10 min
NETWORK_BACKOFF_MIN = 10

# ── Rapid-fail detection ──
# A service that exits within this many seconds of restart is code-broken,
# not transiently crashing. Use per-service values where startup is slow.
RAPID_FAIL_TIMEOUT: dict[str, int] = {
    "thunderbird-mcp": 10,   # 68 module imports take 3-4s normally
}
RAPID_FAIL_DEFAULT = 5       # seconds for all other services

# ── Services to monitor ──
# IMPORTANT: Only long-running daemons here. Oneshot timer-triggered services
# (e.g. thunderbird-blackboard-sync) must NOT be listed — systemctl is-active
# returns "inactive" after a successful oneshot run, which triggers false crash
# loop alerts. Monitor those by checking their timer status instead.
# NOTE: thunderbird-telegram-c2 removed 2026-04-04 — gateway owns that bot now.
SERVICES = {
    "thunderbird-telegram-gw": "Telegram Gateway",
    "thunderbird-overwatch": "Hale-Loop Daemon",
    "thunderbird-mcp": "MCP Server",
}

# ── System mode (graceful degradation) ──
# GREEN: All systems nominal
# YELLOW: 1-2 services down / MCP unresponsive / disk > 75%
# RED: 3+ services down OR (MCP dead AND Chrome dead) OR disk > 85%
MODE_FILE = ROOT / "logs" / "system_mode.json"

# ── Heartbeat config ──
HEARTBEAT_HOUR_MT = 8   # 0800 MT daily
DISK_WARN_PCT = 85      # alert if disk > 85% full

# ── Mountain Time ──
MT = timezone(timedelta(hours=-6))

# ── Telegram (direct, independent of C2 bot) ──
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_C2_BOT_TOKEN", "")
TELEGRAM_COMMANDER_ID = os.environ.get("TELEGRAM_COMMANDER_ID", "")


def _log(msg: str):
    ts = datetime.now(MT).strftime("%Y-%m-%d %H:%M:%S MT")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(WATCHDOG_LOG, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {
            "restart_history": {},
            "network_down_since": None,
            "last_alert_sent": {},
        }


def _save_state(state: dict):
    tmp = STATE_FILE.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(state, indent=2))
        tmp.rename(STATE_FILE)
    except OSError as e:
        _log(f"State save failed: {e}")


def _send_alert(text: str) -> bool:
    """DEPRECATED 2026-05-13: All alerts now route through Hale incident queue.
    Watchdog no longer pages Commander directly. hale_incident_router.py triages."""
    _log(f"[muted→hale_queue] {text[:200]}")
    return True


def _check_network() -> bool:
    """Quick TCP check to Google DNS — is the internet reachable?"""
    try:
        sock = socket.create_connection(("8.8.8.8", 53), timeout=5)
        sock.close()
        return True
    except (socket.timeout, OSError):
        return False


def _is_service_active(name: str) -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", name],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def _restart_service(name: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "restart", name],
            capture_output=True, text=True, timeout=30,
        )
        success = result.returncode == 0
        output = result.stderr.strip() or result.stdout.strip() or "OK"
        return success, output
    except Exception as e:
        return False, str(e)


def _check_mcp_responding() -> bool:
    """Verify MCP server answers JSON-RPC, not just has a port open."""
    try:
        import requests
        resp = requests.post(
            MCP_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            timeout=10,
        )
        data = resp.json()
        tools = data.get("result", {}).get("tools", [])
        return len(tools) > 50  # we expect 140+
    except Exception:
        return False


def _check_queue_stuck() -> tuple[bool, list]:
    """Check if any tasks have been in queue longer than threshold."""
    try:
        if not QUEUE_FILE.exists():
            return False, []
        queue = json.loads(QUEUE_FILE.read_text())
        if not queue:
            return False, []
    except Exception:
        return False, []

    now = datetime.now(timezone.utc)
    stuck = []
    for task in queue:
        queued_at = task.get("queued_at")
        if not queued_at:
            continue
        try:
            ts = datetime.fromisoformat(queued_at)
            age = (now - ts).total_seconds()
            if age > STUCK_THRESHOLD_SECONDS:
                stuck.append(task)
        except (ValueError, TypeError):
            continue

    return bool(stuck), stuck


def _is_crash_looping(name: str, state: dict) -> bool:
    history = state.get("restart_history", {}).get(name, [])
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=CRASH_LOOP_WINDOW)).isoformat()
    recent = [r for r in history if r.get("timestamp", "") > cutoff]
    return len(recent) >= CRASH_LOOP_THRESHOLD


def _get_journal_tail(svc_name: str, lines: int = 15) -> str:
    """Fetch last N journal lines for a service. Truncated to ~800 chars for Telegram."""
    try:
        result = subprocess.run(
            ["journalctl", "--user", "-u", svc_name, f"-n{lines}", "--no-pager",
             "--output=short-iso"],
            capture_output=True, text=True, timeout=10,
        )
        text = (result.stdout or result.stderr or "").strip()
        if len(text) > 800:
            text = "..." + text[-797:]
        return text or "(no journal output)"
    except Exception as e:
        return f"(journal fetch failed: {e})"


def _reset_failed_service(svc_name: str) -> None:
    """Clear systemd start-limit-hit state so a fresh restart is permitted."""
    try:
        subprocess.run(
            ["systemctl", "--user", "reset-failed", svc_name],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass


def _check_disk() -> tuple[bool, str]:
    """Check disk usage — alert if over threshold."""
    import shutil
    try:
        usage = shutil.disk_usage("/home")
        pct = (usage.used / usage.total) * 100
        free_gb = usage.free / (1024 ** 3)
        if pct > DISK_WARN_PCT:
            return True, f"DISK {pct:.0f}% full — only {free_gb:.1f} GB free"
        return False, f"Disk OK ({pct:.0f}% used, {free_gb:.0f} GB free)"
    except Exception as e:
        return False, f"Disk check error: {e}"


def _compute_system_mode(down_services: list[str], mcp_ok: bool, disk_warn: bool) -> str:
    """
    Compute GREEN / YELLOW / RED based on current system health.

    GREEN  — All daemons up, MCP responding, disk OK
    YELLOW — 1 service down, or MCP unresponsive, or disk approaching limit
    RED    — 2+ services down, or critical combo (no MCP + no Chrome), or disk critical
    """
    chrome_ok = _is_service_active("chrome-debug")
    n_down = len(down_services)

    if n_down >= 2:
        return "RED"
    if not mcp_ok and not chrome_ok:
        return "RED"
    if disk_warn:
        return "RED"
    if n_down == 1 or not mcp_ok:
        return "YELLOW"
    return "GREEN"


def _write_system_mode(mode: str, details: dict) -> None:
    """Write current system mode to logs/system_mode.json for other services to read."""
    try:
        MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
        MODE_FILE.write_text(json.dumps({
            "mode": mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }, indent=2))
    except Exception as e:
        _log(f"Failed to write system mode: {e}")


def _should_send_heartbeat(state: dict) -> bool:
    """Return True if daily heartbeat is due (once per day at HEARTBEAT_HOUR_MT)."""
    now = datetime.now(MT)
    if now.hour != HEARTBEAT_HOUR_MT:
        return False
    last = state.get("last_heartbeat_date", "")
    today = now.strftime("%Y-%m-%d")
    return last != today


def run_watchdog():
    _log("Watchdog run started")
    state = _load_state()
    now_iso = datetime.now(timezone.utc).isoformat()
    actions = []
    alerts = []
    down_services: list[str] = []   # track for graceful degradation
    mcp_ok = True                   # track for graceful degradation

    # ── Step 0: Network check ──
    if not _check_network():
        if state.get("network_down_since") is None:
            state["network_down_since"] = now_iso
            _log("Network DOWN — entering backoff")
            _write_system_mode("RED", {"reason": "network_down"})
        else:
            _log("Network still down — skipping all checks")
        _save_state(state)
        return

    if state.get("network_down_since"):
        _log("Network recovered")
        actions.append("Network recovered after outage")
        state["network_down_since"] = None

    # ── Step 1: Service health ──
    for svc_name, svc_desc in SERVICES.items():
        if _is_service_active(svc_name):
            continue

        down_services.append(svc_name)
        _log(f"{svc_desc} ({svc_name}) is DOWN")

        # Always reset-failed first so systemd's start-limit-hit doesn't silently
        # eat our restart request (the 18-day-outage root cause).
        _reset_failed_service(svc_name)

        if _is_crash_looping(svc_name, state):
            journal = _get_journal_tail(svc_name)
            msg = (
                f"CRASH LOOP: {svc_desc} restarted >{CRASH_LOOP_THRESHOLD}x in "
                f"{CRASH_LOOP_WINDOW // 60} min. NOT restarting.\n"
                f"Last journal:\n{journal}"
            )
            _log(msg)
            alerts.append(msg)
            enqueue_incident({
                "source": "opscenter_watchdog",
                "event_type": "crash_loop",
                "severity": "critical",
                "service": svc_name,
                "auto_heal_succeeded": False,
                "details": msg,
            })
            continue

        success, output = _restart_service(svc_name)
        state.setdefault("restart_history", {}).setdefault(svc_name, []).append({
            "timestamp": now_iso,
            "reason": "service_dead",
            "success": success,
        })

        if success:
            # Rapid-fail check: a service that dies again within seconds is
            # code-broken (SyntaxError / ImportError), not transiently crashing.
            rapid_timeout = RAPID_FAIL_TIMEOUT.get(svc_name, RAPID_FAIL_DEFAULT)
            time.sleep(rapid_timeout)
            if not _is_service_active(svc_name):
                journal = _get_journal_tail(svc_name)
                msg = (
                    f"CODE BROKEN: {svc_desc} died within {rapid_timeout}s of restart. "
                    f"Likely SyntaxError or ImportError.\n"
                    f"Last journal:\n{journal}"
                )
                _log(msg)
                alerts.append(msg)
                down_services.append(svc_name)  # re-add; healed flag was premature
            else:
                msg = f"AUTO-HEALED: {svc_desc} restarted"
                _log(msg)
                actions.append(msg)
                enqueue_incident({
                    "source": "opscenter_watchdog",
                    "event_type": "auto_healed",
                    "severity": "info",
                    "service": svc_name,
                    "auto_heal_succeeded": True,
                    "details": msg,
                })
        else:
            msg = f"RESTART FAILED: {svc_desc} — {output[:100]}"
            _log(msg)
            alerts.append(msg)

    # ── Step 2: MCP deep check ──
    if _is_service_active("thunderbird-mcp") and not _check_mcp_responding():
        mcp_ok = False
        _log("MCP server alive but not responding to JSON-RPC")

        if not _is_crash_looping("thunderbird-mcp", state):
            success, output = _restart_service("thunderbird-mcp")
            state.setdefault("restart_history", {}).setdefault("thunderbird-mcp", []).append({
                "timestamp": now_iso,
                "reason": "mcp_unresponsive",
                "success": success,
            })
            if success:
                actions.append("MCP server restarted (unresponsive)")
            else:
                alerts.append(f"MCP restart failed: {output[:100]}")
    elif not _is_service_active("thunderbird-mcp"):
        mcp_ok = False

    # ── Step 3: Queue stuck detection ──
    stuck, stuck_tasks = _check_queue_stuck()
    if stuck:
        task_ids = [t.get("task_id", "?") for t in stuck_tasks[:5]]
        msg = f"STUCK QUEUE: {len(stuck_tasks)} task(s) >5 min old: {task_ids}"
        _log(msg)
        alerts.append(msg)

        if _is_service_active("thunderbird-overwatch"):
            _log("Overwatch alive but queue stuck — restarting processor")
            _restart_service("thunderbird-overwatch")
            state.setdefault("restart_history", {}).setdefault("thunderbird-overwatch", []).append({
                "timestamp": now_iso,
                "reason": "queue_stuck",
                "success": True,
            })
            actions.append("Restarted Hale-Loop (stuck queue)")

    # ── Step 4: Disk space check ──
    disk_warn, disk_msg = _check_disk()
    if disk_warn:
        alerts.append(disk_msg)
        _log(f"DISK WARNING: {disk_msg}")

    # ── Step 4b: Compute + publish system mode (graceful degradation) ──
    mode = _compute_system_mode(down_services, mcp_ok, disk_warn)
    prev_mode = state.get("system_mode", "GREEN")
    _write_system_mode(mode, {
        "down_services": down_services,
        "mcp_ok": mcp_ok,
        "disk_warn": disk_warn,
        "alerts": alerts,
    })
    state["system_mode"] = mode

    if mode != prev_mode:
        _log(f"System mode changed: {prev_mode} → {mode}")
        mode_emoji = {"GREEN": "✅", "YELLOW": "⚠️", "RED": "🔴"}.get(mode, "❓")
        if mode == "GREEN":
            actions.append(f"{mode_emoji} System recovered → GREEN")
        elif mode == "YELLOW":
            alerts.insert(0, f"{mode_emoji} System degraded → YELLOW mode. Reduced ops.")
        elif mode == "RED":
            alerts.insert(0, (
                f"{mode_emoji} <b>SYSTEM RED</b> — Multiple failures detected.\n"
                f"Wing in SAFE MODE: expensive AI ops suspended. Recovery in progress."
            ))

    # ── Step 4c: Daily heartbeat (include mode) ──
    if _should_send_heartbeat(state):
        ts = datetime.now(MT).strftime("%Y-%m-%d %H:%M MT")
        mode_emoji = {"GREEN": "✅", "YELLOW": "⚠️", "RED": "🔴"}.get(mode, "❓")
        heartbeat = (
            f"💚 <b>YOGA ALIVE — {ts}</b>\n"
            f"Mode: {mode_emoji} {mode}\n"
            f"{disk_msg}\n"
            f"Services down: {len(down_services)} | MCP: {'OK' if mcp_ok else 'DOWN'}"
        )
        _send_alert(heartbeat)
        state["last_heartbeat_date"] = datetime.now(MT).strftime("%Y-%m-%d")
        _log("Heartbeat sent")

    # ── Step 5: Clean old history (keep 24h) ──
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    for svc in list(state.get("restart_history", {}).keys()):
        state["restart_history"][svc] = [
            r for r in state["restart_history"][svc]
            if r.get("timestamp", "") > cutoff
        ]

    # ── Step 6: Alert Commander ──
    if actions or alerts:
        ts = datetime.now(MT).strftime("%H:%M MT")
        mode_emoji = {"GREEN": "✅", "YELLOW": "⚠️", "RED": "🔴"}.get(mode, "❓")
        lines = [f"<b>WATCHDOG {ts}</b> {mode_emoji} {mode}"]
        if actions:
            lines.append("")
            for a in actions:
                lines.append(f"  {a}")
        if alerts:
            lines.append("")
            lines.append("<b>NEEDS ATTENTION:</b>")
            for a in alerts:
                lines.append(f"  {a}")
        _send_alert("\n".join(lines))

    _save_state(state)
    _log(f"Watchdog complete — mode={mode} {len(actions)} actions, {len(alerts)} alerts")


if __name__ == "__main__":
    run_watchdog()

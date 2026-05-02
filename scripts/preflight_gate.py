#!/usr/bin/env python3
"""
Preflight Gate — Tier 1 Service Health Check
Runs at 05:45 MT daily. Checks client-critical services.
If any are dead, sends Telegram alert to Commander before the morning batch fires.

Zero AI tokens. Pure systemd status + Telegram API.
"""

import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

# ─── Config ──────────────────────────────────────────────────────────────────
BASE = Path("/home/john/Thunderbird")
LOG_DIR = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)

COMMANDER_CHAT_ID = "7554895206"

# Load bot token from env file
def _load_bot_token() -> str:
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    # Fallback: check OpsCenter .env
    ops_env = BASE / "OpsCenter" / ".env"
    if ops_env.exists():
        for line in ops_env.read_text().splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("TELEGRAM_BOT_TOKEN not found in .env files")


# Tier 1: Client-critical — break glass if failed
TIER1 = {
    "hale-draft-engine": "Lifecycle email drafts for clients",
    "hale-touchpoint-proposer": "Touchpoint scheduling (what's due today)",
    "d2m-lifecycle": "Lifecycle state scanner",
    "d2m-correspondence-sync": "Sent email → dossier logging",
    "d2m-fpd-alert": "Final payment date alerts",
    "thunderbird-drive-sync": "Dossier → Google Drive mirror",
}

# Tier 2: Operations — fix within 24h
TIER2 = {
    "hale-brief-generate": "Morning brief auto-generation",
    "d2m-email-intel": "Inbound email intelligence",
    "d2m-booking-monitor": "Booking status change detection",
    "thunderbird-fare-watch": "Fare price monitoring",
    "d2m-mcp": "MCP server (port 8765)",
    "d2m-tunnel": "Cloudflared external tunnel",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "preflight_gate.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("preflight")


def check_service(name: str) -> dict:
    """Check systemd user service status. Returns {name, active, status, detail}."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", f"{name}.service"],
            capture_output=True, text=True, timeout=10,
        )
        is_active = result.stdout.strip()

        # Get last exit code for failed services
        detail = ""
        if is_active == "failed":
            res2 = subprocess.run(
                ["systemctl", "--user", "show", f"{name}.service",
                 "--property=ExecMainStatus,ExecMainStartTimestamp"],
                capture_output=True, text=True, timeout=10,
            )
            detail = res2.stdout.strip().replace("\n", " · ")

        return {
            "name": name,
            "active": is_active in ("active", "inactive"),  # inactive = oneshot completed OK
            "status": is_active,
            "detail": detail,
        }
    except Exception as e:
        return {"name": name, "active": False, "status": "error", "detail": str(e)}


def check_timer_armed(name: str) -> bool:
    """Check if the timer is armed (active/waiting)."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", f"{name}.timer"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def send_telegram(message: str):
    """Send alert to Commander via Telegram."""
    try:
        token = _load_bot_token()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            "chat_id": COMMANDER_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }).encode()
        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        urlopen(req, timeout=15)
        log.info("Telegram alert sent to Commander")
    except Exception as e:
        log.error(f"Telegram send failed: {e}")


def run_preflight():
    """Main preflight check."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    log.info(f"=== PREFLIGHT GATE — {now} ===")

    t1_down = []
    t2_down = []

    # Check Tier 1
    for svc, desc in TIER1.items():
        result = check_service(svc)
        timer_ok = check_timer_armed(svc)

        if result["status"] == "failed":
            t1_down.append((svc, desc, result["detail"]))
            log.error(f"T1 FAILED: {svc} — {desc}")
        elif not timer_ok:
            t1_down.append((svc, desc, "timer not armed"))
            log.warning(f"T1 TIMER DOWN: {svc} — {desc}")
        else:
            log.info(f"T1 OK: {svc}")

    # Check Tier 2
    for svc, desc in TIER2.items():
        result = check_service(svc)
        if result["status"] == "failed":
            t2_down.append((svc, desc, result["detail"]))
            log.warning(f"T2 FAILED: {svc} — {desc}")
        else:
            log.info(f"T2 OK: {svc}")

    # Build alert if anything is down
    if t1_down or t2_down:
        lines = [f"<b>⚠️ PREFLIGHT GATE — {now}</b>", ""]

        if t1_down:
            lines.append("<b>🔴 TIER 1 — CLIENT CRITICAL:</b>")
            for svc, desc, detail in t1_down:
                lines.append(f"  • <b>{svc}</b> — {desc}")

        if t2_down:
            lines.append("")
            lines.append("<b>🟡 TIER 2 — OPERATIONS:</b>")
            for svc, desc, detail in t2_down:
                lines.append(f"  • <b>{svc}</b> — {desc}")

        t1_ok = len(TIER1) - len(t1_down)
        t2_ok = len(TIER2) - len(t2_down)
        total = len(TIER1) + len(TIER2)
        total_ok = t1_ok + t2_ok
        lines.append(f"\n{total_ok}/{total} services healthy.")

        if t1_down:
            lines.append("\n<i>Tier 1 failures affect client deliverables.</i>")

        msg = "\n".join(lines)
        send_telegram(msg)
        log.info(f"Alert sent: {len(t1_down)} T1, {len(t2_down)} T2 failures")
    else:
        log.info("All services healthy. No alert needed.")

    # Write status file for other scripts to read
    status = {
        "timestamp": now,
        "tier1_ok": len(TIER1) - len(t1_down),
        "tier1_total": len(TIER1),
        "tier2_ok": len(TIER2) - len(t2_down),
        "tier2_total": len(TIER2),
        "tier1_failures": [s[0] for s in t1_down],
        "tier2_failures": [s[0] for s in t2_down],
        "all_clear": len(t1_down) == 0 and len(t2_down) == 0,
    }
    (BASE / "config" / "preflight_status.json").write_text(json.dumps(status, indent=2))

    return len(t1_down), len(t2_down)


if __name__ == "__main__":
    t1, t2 = run_preflight()
    if t1 > 0:
        exit(1)  # Signal failure for systemd
    exit(0)

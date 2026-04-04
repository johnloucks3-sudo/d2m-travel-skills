#!/usr/bin/env python3
"""
wing_heartbeat.py — Daily 0600 MT "Wing Alive" push to Commander
=================================================================
Phase 2 Autonomy Build. Fires at 0600 MT via systemd timer.
Sends a morning status push: YOGA alive, service health, next payment, departure countdown.

Uses direct Telegram HTTP (independent of gateway bot).
Token: TELEGRAM_C2_BOT_TOKEN (same as watchdog — D2MC2C bot reaches Commander).
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MT   = timezone(timedelta(hours=-6))   # MDT = UTC-6

# ── Load .env ──────────────────────────────────────────────────────────────────
def _load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

_load_env()

TOKEN      = os.environ.get("TELEGRAM_C2_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID    = os.environ.get("TELEGRAM_COMMANDER_ID", "")
DEPARTURE  = date(2026, 4, 23)   # Silver Nova embark

# ── Payment deadlines (from thunderbird_payment_alerts.py) ────────────────────
DEADLINES = [
    {"client": "Kuklinski (Kyle & Rosalie)", "cruise": "Viking Mars",       "date": "2026-03-31", "amount": "$7,548"},
    {"client": "Kuklinski (Roger & Nick)",   "cruise": "Viking Mars",       "date": "2026-03-31", "amount": "$7,548"},
    {"client": "Morton (Josh & Erica)",      "cruise": "Viking Mars",       "date": "2026-03-31", "amount": "$6,148"},
    {"client": "Furlow (John & Melissa)",    "cruise": "Regent Grandeur",   "date": "2026-04-01", "amount": "$15,486"},
    {"client": "Ely/Darrow (Al & Amy)",      "cruise": "Regent Grandeur",   "date": "2026-04-01", "amount": "$16,640"},
    {"client": "Nichols (Larry & Heidi)",    "cruise": "Regent Grandeur",   "date": "2026-04-01", "amount": "$14,986"},
    {"client": "McLeod (Erik & Melissa)",    "cruise": "Regent Grandeur",   "date": "2026-07-22", "amount": "$12,393"},
    {"client": "Loucks (John & Susan)",      "cruise": "Regent Panama",     "date": "2026-09-30", "amount": "TBD"},
]


def _send_telegram(text: str) -> bool:
    if not TOKEN or not CHAT_ID:
        print("[heartbeat] Telegram creds not set — skipping send", flush=True)
        return False
    try:
        import requests
        resp = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"[heartbeat] Telegram send failed: {e}", flush=True)
        return False


def _count_failed_services() -> tuple[int, list[str]]:
    """Return (count, [names]) of failed user services."""
    try:
        r = subprocess.run(
            ["systemctl", "--user", "list-units", "--type=service", "--state=failed",
             "--no-legend", "--no-pager"],
            capture_output=True, text=True, timeout=10,
        )
        lines = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        names = [l.split()[0].replace(".service", "") for l in lines if ".service" in l]
        return len(names), names
    except Exception:
        return -1, []


def _disk_pct() -> str:
    """Return disk usage percent for / as string like '42%'."""
    try:
        total, used, _ = shutil.disk_usage("/")
        return f"{int(used / total * 100)}%"
    except Exception:
        return "?"


def _next_payment() -> str | None:
    """Return description of nearest future payment deadline."""
    today = date.today()
    future = []
    for d in DEADLINES:
        if d["amount"] in ("TBD", "PAID"):
            continue
        try:
            dd = date.fromisoformat(d["date"])
            days = (dd - today).days
            if days >= 0:
                future.append((days, d))
        except ValueError:
            continue
    if not future:
        return None
    days, d = min(future, key=lambda x: x[0])
    if days == 0:
        return f"TODAY: {d['client']} {d['amount']}"
    elif days == 1:
        return f"TOMORROW: {d['client']} {d['amount']}"
    else:
        return f"{days}d: {d['client']} {d['amount']}"


def _uptime() -> str:
    """System uptime human-readable."""
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        if h >= 24:
            return f"{h // 24}d {h % 24}h"
        return f"{h}h {m}m"
    except Exception:
        return "?"


def main():
    now      = datetime.now(MT)
    today    = date.today()
    days_out = (DEPARTURE - today).days

    failed_ct, failed_names = _count_failed_services()
    disk      = _disk_pct()
    next_pay  = _next_payment()
    uptime    = _uptime()

    # ── Build message ──────────────────────────────────────────────────────────
    ts  = now.strftime("%a %b %-d, %Y — %H:%M MT")

    svc_line = (
        "✅ All services nominal"
        if failed_ct == 0
        else f"⚠️ {failed_ct} service(s) FAILED: {', '.join(failed_names[:3])}"
    )

    pay_line  = f"💳 Next payment: {next_pay}" if next_pay else "💳 No pending payments"

    if days_out > 0:
        dep_line = f"✈️ Silver Nova in <b>{days_out}d</b>"
    elif days_out == 0:
        dep_line = "✈️ <b>EMBARK TODAY</b> — Silver Nova"
    else:
        dep_line = f"🚢 Underway — Day {abs(days_out) + 1}"

    msg = (
        f"🌅 <b>WING ALIVE — {ts}</b>\n\n"
        f"{svc_line}\n"
        f"💾 Disk: {disk} | ⏱ Uptime: {uptime}\n"
        f"{dep_line}\n"
        f"{pay_line}"
    )

    ok = _send_telegram(msg)
    print(f"[heartbeat] {'sent' if ok else 'FAILED'} — {msg[:80]}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

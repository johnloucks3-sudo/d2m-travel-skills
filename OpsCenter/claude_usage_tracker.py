"""
claude_usage_tracker.py — Patched 2026-03-31 v3
- Adds a specific reset-sonnet command for scheduled jobs.
"""
import json, os, sys, time
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Constants and Paths ---
MT = timezone(timedelta(hours=-6))
ROOT = Path(__file__).resolve().parent.parent
OPSCENTER = ROOT / "OpsCenter"
COLLAB = OPSCENTER / "collaboration"
USAGE_STATUS = OPSCENTER / "claude_usage_status.json"
RATE_LIMIT_MD = COLLAB / "rate_limit_status.md"

SESSION_WINDOW_HOURS = 5
MAX_5X_SESSION_LIMIT = 225
MAX_5X_WEEKLY_LIMIT = 1500
SONNET_DAILY_LIMIT = 25

PEAK_HOURS_MT = (6, 12)
PEAK_MULTIPLIER = 1.5

def _now(): return datetime.now(MT)

def _is_peak() -> bool:
    now = _now()
    return now.weekday() < 5 and PEAK_HOURS_MT[0] <= now.hour < PEAK_HOURS_MT[1]

def _default_status():
    now = _now()
    return {
        "session_start": now.isoformat(), "session_messages": 0, "session_limit": MAX_5X_SESSION_LIMIT,
        "weekly_start": now.isoformat(), "weekly_messages": 0, "weekly_limit": MAX_5X_WEEKLY_LIMIT,
        "sonnet_day_start": now.isoformat(), "sonnet_messages_today": 0, "sonnet_daily_limit": SONNET_DAILY_LIMIT,
        "effective_messages": 0, "last_message_at": None, "budget_status": "GREEN",
        "sources": {"desktop": 0, "code": 0, "watcher": 0, "unknown": 0},
        "peak_messages": 0, "offpeak_messages": 0,
    }

def _load_status():
    try: return json.loads(USAGE_STATUS.read_text())
    except Exception: return _default_status()

def _save_status(status):
    USAGE_STATUS.write_text(json.dumps(status, indent=2, default=str))

def _check_resets(status):
    now = _now()
    try:
        day_start = datetime.fromisoformat(status["sonnet_day_start"])
        if now.date() > day_start.date():
            status["sonnet_day_start"] = now.isoformat()
            status["sonnet_messages_today"] = 0
    except Exception: pass
    try:
        weekly_start = datetime.fromisoformat(status["weekly_start"])
        if (now - weekly_start).total_seconds() > 7 * 24 * 3600:
            status["weekly_start"] = now.isoformat()
            status["weekly_messages"] = 0
    except Exception: pass
    try:
        session_start = datetime.fromisoformat(status["session_start"])
        if (now - session_start).total_seconds() > SESSION_WINDOW_HOURS * 3600:
            status["session_start"] = now.isoformat()
            status["session_messages"], status["effective_messages"], status["peak_messages"], status["offpeak_messages"] = 0, 0, 0, 0
            status["sources"] = {"desktop": 0, "code": 0, "watcher": 0, "unknown": 0}
    except Exception: pass
    return status

def _compute_budget_status(status):
    eff_pct = (status.get("effective_messages", 0) / status.get("session_limit", 1)) * 100
    sonnet_pct = (status.get("sonnet_messages_today", 0) / status.get("sonnet_daily_limit", 1)) * 100
    if eff_pct >= 80 or sonnet_pct >= 90: return "RED"
    if eff_pct >= 60 or sonnet_pct >= 70: return "YELLOW"
    return "GREEN"

def log_message(source="unknown", model="sonnet", tokens=0):
    status = _load_status()
    status = _check_resets(status)
    status["session_messages"] += 1
    status["weekly_messages"] += 1
    status["sources"][source] = status["sources"].get(source, 0) + 1
    status["last_message_at"] = _now().isoformat()
    if 'sonnet' in model.lower():
        status["sonnet_messages_today"] = status.get("sonnet_messages_today", 0) + 1
    if _is_peak():
        status["peak_messages"] += 1
        status["effective_messages"] += PEAK_MULTIPLIER
    else:
        status["offpeak_messages"] += 1
        status["effective_messages"] += 1
    status["budget_status"] = _compute_budget_status(status)
    _save_status(status)
    _write_rate_limit_md(status)
    return status

def _write_rate_limit_md(status):
    budget = status["budget_status"]
    color_map = {"GREEN": "🟩", "YELLOW": "🟨", "RED": "🟥"}
    budget_color = color_map.get(budget, "⬜️")
    pct = round(status.get("effective_messages", 0) / status.get("session_limit", 1) * 100, 1)
    sonnet_pct = round(status.get("sonnet_messages_today", 0) / status.get("sonnet_daily_limit", 1) * 100, 1)
    weekly_pct = round(status.get("weekly_messages", 0) / status.get("weekly_limit", 1) * 100, 1)
    sess_meter = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
    sonnet_meter = "█" * int(sonnet_pct / 10) + "░" * (10 - int(sonnet_pct / 10))
    weekly_meter = "█" * int(weekly_pct / 10) + "░" * (10 - int(weekly_pct / 10))
    md = f"""# CLAUDE USAGE STATUS — AUTO-GENERATED
Updated: {_now().strftime("%Y-%m-%dT%H:%M:%S MT")}

## {budget_color} Overall Status: {budget}
### Session
`[{sess_meter}] {pct}%` ({status['session_messages']}/{status['session_limit']} effective)
### Weekly
`[{weekly_meter}] {weekly_pct}%` ({status.get('weekly_messages', 0)}/{status.get('weekly_limit', 1500)})
### Sonnet Daily
`[{sonnet_meter}] {sonnet_pct}%` ({status.get('sonnet_messages_today', 0)}/{status.get('sonnet_daily_limit', 25)})
"""
    RATE_LIMIT_MD.write_text(md)

def get_status():
    status = _load_status()
    status = _check_resets(status)
    status["budget_status"] = _compute_budget_status(status)
    _save_status(status)
    _write_rate_limit_md(status)
    return status

def reset_sonnet():
    """Manually reset the Sonnet daily counter."""
    status = _load_status()
    status["sonnet_day_start"] = _now().isoformat()
    status["sonnet_messages_today"] = 0
    status["budget_status"] = _compute_budget_status(status)
    _save_status(status)
    _write_rate_limit_md(status)
    print("Sonnet daily limit has been reset.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude MAX Usage Tracker")
    sub = parser.add_subparsers(dest="cmd")
    log_p = sub.add_parser("log", help="Log a Claude message")
    log_p.add_argument("--source", default="unknown", choices=["desktop", "code", "watcher", "unknown"])
    log_p.add_argument("--model", default="sonnet")
    log_p.add_argument("--tokens", type=int, default=0)
    sub.add_parser("status", help="Show current usage status")
    sub.add_parser("reset-sonnet", help="Reset Sonnet daily limit")
    args = parser.parse_args()

    if args.cmd == "log":
        log_message(source=args.source, model=args.model, tokens=args.tokens)
    elif args.cmd == "status":
        get_status()
    elif args.cmd == "reset-sonnet":
        reset_sonnet()
    else:
        get_status()
        print("Status updated.")

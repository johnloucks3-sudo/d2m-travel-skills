#!/usr/bin/env python3
"""
continuity_daily_recert.py — X1: Daily Re-Certification Audit
=============================================================
Runs daily via systemd timer. Evaluates 3 continuity thresholds:
  1. failed_unit_count      → target 0, RED >2
  2. heartbeat_ping_miss_24h → target 0, RED >1
  3. scrape_checkpoint_completion_pct → target 100%, RED <80%

Writes results to: OpsCenter/a7_metrics_dashboard.json (under continuity_recert key)
Telegrams Commander on RED breach.

Owner: Sterling A7 · Built 2026-06-10
"""
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

THUNDERBIRD = Path("/home/john/Thunderbird")
METRICS_FILE = THUNDERBIRD / "OpsCenter" / "a7_metrics_dashboard.json"
WATCHDOG_LOG = THUNDERBIRD / "logs" / "coo_watchdog.log"
SCRAPE_DIR = THUNDERBIRD / "validations" / "rssc_scrape"
ENV_FILE = THUNDERBIRD / ".env"

# Thresholds (from ASSESS section of build plan)
THRESHOLD_FAILED_UNITS_RED = 2          # > this = RED
THRESHOLD_HEARTBEAT_MISS_RED = 1        # > this = RED
THRESHOLD_SCRAPE_COMPLETION_RED = 80.0  # < this % = RED

BOOKING_IDS = ["3096289_Ely", "3078056_Nichols", "3071222_Furlow", "2984034_McLeod"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _run(cmd: list) -> tuple:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return -1, str(e)


# ── Metric 1: failed_unit_count ────────────────────────────────────────────────

def count_failed_units() -> dict:
    """Count all currently-failed user-scope systemd units."""
    _, raw = _run(["systemctl", "--user", "list-units", "--state=failed",
                   "--no-legend", "--plain"])
    units = [line.split()[0] for line in raw.splitlines()
             if line.strip() and line.split()[0].endswith(".service")]
    count = len(units)
    status = "GREEN" if count == 0 else ("YELLOW" if count <= THRESHOLD_FAILED_UNITS_RED else "RED")
    return {
        "value": count,
        "status": status,
        "threshold_red": f">{THRESHOLD_FAILED_UNITS_RED}",
        "failed_units": units,
    }


# ── Metric 2: heartbeat_ping_miss_24h ──────────────────────────────────────────

def count_heartbeat_misses() -> dict:
    """
    Count COO watchdog cycles in last 24h where all_clear=False (degraded scans).
    Uses coo_watchdog.log to count 'DEGRADED' scan lines in the past 24h.
    A miss = a cycle where the watchdog reported DEGRADED and could not self-heal
    (i.e., the line contains 'DEGRADED' but no corresponding 'ALL_GREEN' within 2 cycles).
    Simplified metric: count of DEGRADED scan lines in 24h window.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    misses = 0
    last_ts = None

    if not WATCHDOG_LOG.exists():
        return {"value": 0, "status": "UNKNOWN", "note": "watchdog log not found"}

    try:
        lines = WATCHDOG_LOG.read_text().splitlines()
        for line in lines:
            if "SCAN |" not in line:
                continue
            # Parse timestamp from log format: "2026-06-10 22:20:43,740 [INFO] SCAN | ..."
            try:
                ts_str = line.split("[")[0].strip().replace(",", ".")
                ts_str = ts_str[:19]  # "2026-06-10 22:20:43"
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if ts < cutoff:
                continue
            last_ts = ts_str
            if "DEGRADED" in line:
                misses += 1
    except Exception as e:
        return {"value": 0, "status": "UNKNOWN", "note": f"log parse error: {e}"}

    status = "GREEN" if misses == 0 else ("YELLOW" if misses <= THRESHOLD_HEARTBEAT_MISS_RED else "RED")
    return {
        "value": misses,
        "status": status,
        "threshold_red": f">{THRESHOLD_HEARTBEAT_MISS_RED}",
        "last_scan_ts": last_ts,
        "window_hours": 24,
    }


# ── Metric 3: scrape_checkpoint_completion_pct ────────────────────────────────

def scrape_checkpoint_pct() -> dict:
    """
    Check per-booking date-keyed .scrape.done checkpoint files in validations/rssc_scrape/.
    Checkpoints are keyed by YYYYMMDD so stale prior-day files do not report false-green.
    Completion % = bookings with today's .done file / total bookings * 100.
    If no .done files exist (scrape hasn't run today), report as N/A rather than 0%.
    """
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    done_count = 0
    total = len(BOOKING_IDS)
    missing = []

    for b_id in BOOKING_IDS:
        done_file = SCRAPE_DIR / f"{b_id}.{today_str}.scrape.done"
        if done_file.exists():
            done_count += 1
        else:
            missing.append(b_id)

    if done_count == 0:
        # No scrape run yet today — report as N/A (not a failure)
        return {
            "value": None,
            "status": "N/A",
            "note": "No scrape run detected today (no .done files found)",
            "bookings_total": total,
            "bookings_done": 0,
            "missing_bookings": missing,
        }

    pct = (done_count / total) * 100
    status = "GREEN" if pct >= 100 else ("YELLOW" if pct >= THRESHOLD_SCRAPE_COMPLETION_RED else "RED")
    return {
        "value": round(pct, 1),
        "status": status,
        "threshold_red": f"<{THRESHOLD_SCRAPE_COMPLETION_RED}%",
        "bookings_total": total,
        "bookings_done": done_count,
        "missing_bookings": missing,
    }


# ── Alert ──────────────────────────────────────────────────────────────────────

def _send_telegram_alert(message: str) -> None:
    env = _load_env()
    bot_token = env.get("TELEGRAM_C2_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_COMMANDER_ID", "")
    if not bot_token or not chat_id:
        print("WARN: Missing Telegram credentials — alert not sent", file=sys.stderr)
        return
    body = json.dumps({"chat_id": chat_id, "text": message}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                print(f"Telegram error: {result}", file=sys.stderr)
    except Exception as e:
        print(f"Telegram send failed: {e}", file=sys.stderr)


# ── Main audit ─────────────────────────────────────────────────────────────────

def run_recert() -> dict:
    ts = _now_iso()
    print(f"[X1 re-cert] Running at {ts}")

    m1 = count_failed_units()
    m2 = count_heartbeat_misses()
    m3 = scrape_checkpoint_pct()

    red_items = []
    if m1["status"] == "RED":
        red_items.append(f"failed_unit_count={m1['value']} (threshold >{THRESHOLD_FAILED_UNITS_RED})")
    if m2["status"] == "RED":
        red_items.append(f"heartbeat_miss_24h={m2['value']} (threshold >{THRESHOLD_HEARTBEAT_MISS_RED})")
    if m3["status"] == "RED":
        red_items.append(f"scrape_completion={m3['value']}% (threshold <{THRESHOLD_SCRAPE_COMPLETION_RED}%)")

    overall = "GREEN"
    if any(m["status"] == "RED" for m in [m1, m2, m3]):
        overall = "RED"
    elif any(m["status"] == "YELLOW" for m in [m1, m2, m3]):
        overall = "YELLOW"

    result = {
        "timestamp": ts,
        "overall": overall,
        "metrics": {
            "failed_unit_count": m1,
            "heartbeat_ping_miss_24h": m2,
            "scrape_checkpoint_completion_pct": m3,
        },
        "red_items": red_items,
    }

    print(f"[X1 re-cert] Overall: {overall}")
    for k, v in result["metrics"].items():
        print(f"  {k}: {v['value']} ({v['status']})")
    if red_items:
        print(f"[X1 re-cert] RED ALERTS: {red_items}")

    # Update a7_metrics_dashboard.json
    try:
        existing = {}
        if METRICS_FILE.exists():
            existing = json.loads(METRICS_FILE.read_text())
        existing["continuity_recert"] = result
        existing["_last_updated"] = ts
        METRICS_FILE.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
        print(f"[X1 re-cert] Written to {METRICS_FILE}")
    except Exception as e:
        print(f"[X1 re-cert] WARN: could not write metrics file: {e}", file=sys.stderr)

    # Send Telegram alert on RED
    if red_items:
        msg = (
            f"[THUNDERBIRD X1 RE-CERT] CONTINUITY BREACH\n"
            f"Time: {ts}\n"
            + "\n".join(f"  RED: {r}" for r in red_items)
            + "\n\nCheck: journalctl --user -u thunderbird-coo-watchdog"
        )
        _send_telegram_alert(msg)

    return result


if __name__ == "__main__":
    result = run_recert()
    sys.exit(0 if result["overall"] != "RED" else 1)

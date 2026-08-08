#!/usr/bin/env python3
"""
grok_usage_meter.py — daily check of the real SuperGrok weekly usage %,
via bsk (Commander's logged-in browser), not a self-report from Grok
(it has no visibility into its own metering — confirmed 2026-08-03).

Reads grok.com's Settings → Usage panel: weekly SuperGrok % used, reset
date, and extra-credit balance ($). Logs every run; alerts via Telegram
only when usage crosses ALERT_THRESHOLD_PCT — same alert-only philosophy
as zen_usage_guard.py / claude_process_watch.py (see claude-drawdown
skill). Reading Settings does not consume any of the weekly quota itself
— this check is free to run as often as reasonable.

Requires bsk daemon running with grok.com already logged in in the
connected browser. Fails (logs + exits 0) rather than hanging if that
precondition isn't met — there is no headless fallback for this account.
"""
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
LOG_FILE = ROOT / "logs" / "grok_usage_meter.log"
DATA_FILE = ROOT / "data" / "grok_usage.json"
ALERT_THRESHOLD_PCT = 80
TELEGRAM_TOKEN_ENV_FILE = ROOT / ".env.telegram"
TELEGRAM_TOKEN_VAR = "TELEGRAM_D2MC2C_TOKEN"
TELEGRAM_CHAT_ID_VAR = "TELEGRAM_COMMANDER_ID"
TELEGRAM_CHAT_ID_DEFAULT = "7554895206"


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as f:
        f.write(f"{msg}\n")
    print(msg)


def send_telegram(msg: str) -> None:
    try:
        import os
        import urllib.request
        import urllib.parse

        if TELEGRAM_TOKEN_ENV_FILE.exists():
            for line in TELEGRAM_TOKEN_ENV_FILE.read_text().splitlines():
                if line.startswith(f"{TELEGRAM_TOKEN_VAR}="):
                    os.environ[TELEGRAM_TOKEN_VAR] = line.split("=", 1)[1].strip()
        token = os.environ.get(TELEGRAM_TOKEN_VAR, "")
        chat_id = os.environ.get(TELEGRAM_CHAT_ID_VAR, TELEGRAM_CHAT_ID_DEFAULT)
        if not token or not chat_id:
            log("Telegram send skipped — no token/chat_id configured")
            return
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": msg}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        log(f"Telegram send failed (non-fatal): {e!r}")


def run_bsk(*args) -> str:
    result = subprocess.run(["bsk", *args], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"bsk {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def find_ref(snapshot: str, text_match: str) -> str | None:
    for line in snapshot.splitlines():
        if text_match.lower() in line.lower():
            m = re.search(r"@e\d+", line)
            if m:
                return m.group(0)
    return None


def check_usage() -> dict:
    session = run_bsk("session", "start").strip()
    try:
        run_bsk("navigate", "--session", session, "https://grok.com")
        time.sleep(2)
        snap = run_bsk("snapshot", "--session", session)
        profile_btn = find_ref(snap, "pfp")
        if not profile_btn:
            return {"status": "error", "detail": "profile button not found — logged out?"}
        run_bsk("click", "--session", session, profile_btn)
        time.sleep(1)
        snap2 = run_bsk("snapshot", "--session", session)
        settings_item = find_ref(snap2, "Settings")
        if not settings_item:
            return {"status": "error", "detail": "Settings menu item not found"}
        run_bsk("click", "--session", session, settings_item)
        time.sleep(1)
        snap3 = run_bsk("snapshot", "--session", session)
        usage_tab = find_ref(snap3, "Usage")
        if not usage_tab:
            return {"status": "error", "detail": "Usage tab not found"}
        run_bsk("click", "--session", session, usage_tab)
        time.sleep(2)
        final = run_bsk("snapshot", "--session", session)

        pct_match = re.search(r'image "(\d+)%"', final)
        reset_match = re.search(r'StaticText "Resets"\s*\n\s*StaticText "([^"]+)"', final)
        credit_match = re.search(r'image "\$([\d.]+)"', final)

        return {
            "status": "ok",
            "weekly_pct_used": int(pct_match.group(1)) if pct_match else None,
            "resets": reset_match.group(1) if reset_match else None,
            "extra_credits_usd": float(credit_match.group(1)) if credit_match else None,
        }
    finally:
        try:
            run_bsk("session", "stop", session)
        except Exception:
            pass


def main() -> int:
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        result = check_usage()
    except Exception as e:
        log(f"{timestamp} TRANSIENT ERROR (non-fatal, will retry next cycle): {e!r}")
        return 0

    result["timestamp"] = timestamp
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(result, indent=2))

    if result["status"] != "ok":
        log(f"{timestamp} CHECK FAILED: {result.get('detail')}")
        return 0

    pct = result["weekly_pct_used"]
    log(f"{timestamp} Grok weekly usage: {pct}% used, resets {result['resets']}, "
        f"extra credits ${result['extra_credits_usd']:.2f}")

    if pct is not None and pct >= ALERT_THRESHOLD_PCT:
        msg = (f"⚡ Grok weekly SuperGrok usage high: {pct}% used, resets {result['resets']}. "
               f"Extra credits: ${result['extra_credits_usd']:.2f}. Consider spacing out use "
               f"or setting up auto-top-up before hitting the wall.")
        log(f"ALERT: {msg}")
        send_telegram(msg)

    return 0


if __name__ == "__main__":
    sys.exit(main())

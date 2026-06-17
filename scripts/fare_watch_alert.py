#!/usr/bin/env python3
"""
fare_watch_alert.py — MISSION-145 Standalone Fare-Watch Telegram Alert Hook
============================================================================
Loads core/travel/data/fare_watches.json, evaluates each active watch against
its alert_below / alert_above thresholds, and sends concise Telegram alerts to
Commander via the D2MC2C bot.

DEDUP: tracks last-alerted price per watch in logs/fare_watch_alert_state.json.
       Re-alerts only when the current_price_pp has changed from the last-alerted value
       AND still crosses the threshold. Silent if nothing changed.

SAFE: reads fare_watches.json in read-only mode — does NOT modify the fare store.
      The ITA poller (ita_fare_watch_poll.py) and cruise scanner own that file.

Usage:
    # Dry-run (print what WOULD alert, send nothing):
    python3 scripts/fare_watch_alert.py --dry-run

    # Live run (sends alerts for real crossings):
    python3 scripts/fare_watch_alert.py

    # Force-send one watch by id (ignore dedup, bypass threshold check):
    python3 scripts/fare_watch_alert.py --force-id <watch_id>

    # Brief summary (no send, no threshold check, just list watch states):
    python3 scripts/fare_watch_alert.py --brief
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path("/home/john/Thunderbird")
FARE_WATCHES_JSON = ROOT / "core" / "travel" / "data" / "fare_watches.json"
STATE_FILE        = ROOT / "logs" / "fare_watch_alert_state.json"
LOG_FILE          = ROOT / "logs" / "fare_watch_alert.log"

# ---------------------------------------------------------------------------
# Telegram config (read from environment — loaded via EnvironmentFile in systemd)
# ---------------------------------------------------------------------------
BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
COMMANDER_ID = int(os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206"))
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_env_from_file() -> None:
    """Load .env into os.environ if not already set (for CLI runs outside systemd)."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


# ---------------------------------------------------------------------------
# State management (dedup)
# ---------------------------------------------------------------------------
def load_state() -> dict:
    """Returns {watch_id: {"last_alerted_price": float, "last_alerted_ts": str, "direction": str}}"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Telegram send
# ---------------------------------------------------------------------------
def telegram_send(text: str, dry_run: bool = False) -> bool:
    if dry_run:
        _log(f"[DRY-RUN] Would send: {text[:120]}")
        return True
    if not BOT_TOKEN:
        _log("ERROR: no TELEGRAM_BOT_TOKEN in environment — cannot send")
        return False
    payload = json.dumps({
        "chat_id": COMMANDER_ID,
        "text": text,
        "parse_mode": "Markdown"
    }).encode()
    url = TELEGRAM_API.format(token=BOT_TOKEN)
    req = urllib.request.Request(url, data=payload,
                                  headers={"Content-Type": "application/json"},
                                  method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                return True
            _log(f"Telegram API error: {result}")
            return False
    except urllib.error.HTTPError as e:
        _log(f"Telegram HTTP error {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        _log(f"Telegram send error: {e}")
        return False


# ---------------------------------------------------------------------------
# Alert composition
# ---------------------------------------------------------------------------
def format_alert(watch: dict, direction: str) -> str:
    label     = watch.get("label", watch.get("id", "unknown"))
    cur       = watch.get("current_price_pp")
    baseline  = watch.get("baseline_price_pp")
    route     = watch.get("route", "")
    travel_dt = watch.get("travel_date", "")
    pax       = watch.get("passengers", "")
    notes_raw = watch.get("notes", "")
    # Trim notes to first sentence only to keep alert tight
    notes = notes_raw.split(".")[0] if notes_raw else ""

    if direction == "drop":
        ab = watch.get("alert_below")
        delta_pct = round((cur - baseline) / baseline * 100, 1) if baseline else 0
        header = "FARE ALERT -- DROP / BUY SIGNAL"
        threshold_line = f"Alert threshold: below ${ab:,.0f}/pp"
        action_line = "ACTION: Review refare opportunity or book now."
    else:
        ab = watch.get("alert_above")
        delta_pct = round((cur - baseline) / baseline * 100, 1) if baseline else 0
        header = "FARE ALERT -- SPIKE / URGENCY SIGNAL"
        threshold_line = f"Alert threshold: above ${ab:,.0f}/pp"
        action_line = "ACTION: Urgency flag -- lock rate if not yet booked."

    lines = [
        f"*{header}*",
        f"Watch: {label}",
        f"Route: {route}  |  Travel: {travel_dt}  |  Pax: {pax}",
        f"Current: *${cur:,.0f}/pp*  |  Baseline: ${baseline:,.0f}/pp  |  Delta: {delta_pct:+.1f}%",
        threshold_line,
    ]
    if notes:
        lines.append(f"Note: {notes}")
    lines.append(action_line)
    lines.append(f"_Generated by fare_watch_alert.py {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------
def evaluate_watches(watches: dict, state: dict, force_id: str = None) -> list:
    """
    Returns list of (watch_dict, direction, should_send, reason_skipped)
    direction: "drop" | "spike"
    should_send: bool
    reason_skipped: str or None
    """
    results = []
    for wid, w in watches.items():
        if not isinstance(w, dict):
            continue
        if not w.get("active", True):
            continue

        cur      = w.get("current_price_pp")
        ab_low   = w.get("alert_below")
        ab_high  = w.get("alert_above")

        if cur is None:
            continue

        # Determine crossing direction
        direction = None
        if ab_low is not None and cur <= ab_low:
            direction = "drop"
        elif ab_high is not None and cur >= ab_high:
            direction = "spike"

        if direction is None and force_id != wid:
            continue  # no crossing

        if force_id and wid != force_id:
            continue

        # Dedup check
        prev = state.get(wid, {})
        last_price = prev.get("last_alerted_price")
        skip_reason = None

        if force_id == wid:
            skip_reason = None  # always send for forced
        elif last_price is not None and abs(last_price - cur) < 0.01:
            skip_reason = f"dedup: already alerted at ${last_price:,.2f}/pp"

        results.append((w, direction or "forced", not bool(skip_reason), skip_reason))

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Fare watch Telegram alert hook (MISSION-145)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Evaluate and print alerts without sending or updating state")
    ap.add_argument("--force-id", metavar="WATCH_ID",
                    help="Force-alert for a specific watch id, bypassing dedup and threshold")
    ap.add_argument("--brief", action="store_true",
                    help="Print all active watch states (no send)")
    args = ap.parse_args()

    # Load .env for CLI runs (systemd uses EnvironmentFile)
    load_env_from_file()
    # Re-read token after env load
    global BOT_TOKEN, COMMANDER_ID
    BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")
    COMMANDER_ID = int(os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206"))

    # Load fare watches
    if not FARE_WATCHES_JSON.exists():
        _log(f"ERROR: fare_watches.json not found at {FARE_WATCHES_JSON}")
        sys.exit(1)

    try:
        raw = json.loads(FARE_WATCHES_JSON.read_text())
    except Exception as e:
        _log(f"ERROR: failed to parse fare_watches.json: {e}")
        sys.exit(1)

    # Normalise to dict regardless of storage format
    if isinstance(raw, list):
        watches = {w["id"]: w for w in raw if isinstance(w, dict) and "id" in w}
    elif isinstance(raw, dict):
        # May be flat {id: watch} or have a wrapper key
        first_val = next(iter(raw.values()), None) if raw else None
        if isinstance(first_val, dict) and "id" in first_val:
            watches = raw
        else:
            # Look for a wrapper key
            for key in ("watches", "fare_watches"):
                if key in raw and isinstance(raw[key], (list, dict)):
                    inner = raw[key]
                    if isinstance(inner, list):
                        watches = {w["id"]: w for w in inner if isinstance(w, dict) and "id" in w}
                    else:
                        watches = inner
                    break
            else:
                watches = raw
    else:
        _log("ERROR: unexpected fare_watches.json format")
        sys.exit(1)

    active_count = sum(1 for w in watches.values() if isinstance(w, dict) and w.get("active", True))
    _log(f"Loaded {len(watches)} watches ({active_count} active) from fare_watches.json")

    # Brief mode
    if args.brief:
        print(f"\n=== FARE WATCH STATE ({len(watches)} total, {active_count} active) ===")
        state = load_state()
        for wid, w in watches.items():
            if not isinstance(w, dict) or not w.get("active", True):
                continue
            cur  = w.get("current_price_pp", "N/A")
            base = w.get("baseline_price_pp", "N/A")
            ab   = w.get("alert_below", "—")
            aa   = w.get("alert_above", "—")
            prev_price = state.get(wid, {}).get("last_alerted_price")
            alerted_str = f"last-alerted=${prev_price:,.0f}" if prev_price else "never alerted"
            label = w.get("label", wid)[:60]
            crossing = ""
            if isinstance(cur, (int, float)):
                if ab and cur <= ab:
                    crossing = " [DROP CROSSING]"
                elif aa and cur >= aa:
                    crossing = " [SPIKE CROSSING]"
            print(f"  {label}")
            print(f"    cur=${cur}/pp  base=${base}/pp  ab=${ab}  aa={aa}  {alerted_str}{crossing}")
        return

    # Evaluate crossings
    state = load_state()
    evaluations = evaluate_watches(watches, state, force_id=args.force_id)

    if not evaluations:
        _log("No threshold crossings detected. Nothing to alert.")
        return

    sent_count   = 0
    skip_count   = 0
    error_count  = 0

    for w, direction, should_send, skip_reason in evaluations:
        wid = w.get("id", "unknown")
        cur = w.get("current_price_pp")

        if not should_send:
            _log(f"SKIP [{wid}]: {skip_reason}")
            skip_count += 1
            continue

        msg = format_alert(w, direction)

        if args.dry_run:
            _log(f"[DRY-RUN] ALERT [{wid}] direction={direction} current=${cur}/pp")
            print("\n--- ALERT TEXT (DRY-RUN) ---")
            print(msg)
            print("---")
            sent_count += 1
            # Do not update state in dry-run
        else:
            _log(f"SENDING alert [{wid}] direction={direction} current=${cur}/pp")
            ok = telegram_send(msg)
            if ok:
                # Update dedup state
                state[wid] = {
                    "last_alerted_price": cur,
                    "last_alerted_ts": datetime.now(timezone.utc).isoformat(),
                    "direction": direction,
                }
                save_state(state)
                _log(f"SENT [{wid}] — state updated")
                sent_count += 1
            else:
                _log(f"ERROR: failed to send alert for [{wid}]")
                error_count += 1

    _log(f"Run complete: {sent_count} sent, {skip_count} skipped (dedup), {error_count} errors")

    if error_count:
        sys.exit(1)


if __name__ == "__main__":
    main()

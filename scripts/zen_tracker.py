#!/usr/bin/env python3
"""
zen_tracker.py — Empirical Zen Free-Model Usage Tracker
Dreams2Memories Travel, LLC | Thunderbird Wing

Forensic approach: logs every call, learns the unpublished rate limit
by back-calculating from cooldown durations when you hit the wall.

Usage:
  python3 zen_tracker.py --log <model> [--tokens-in N] [--tokens-out N]
  python3 zen_tracker.py --status
  python3 zen_tracker.py --watch            # live tail
  python3 zen_tracker.py --alert N          # exit 1 if N calls before last limit
  python3 zen_tracker.py --check-429        # parse error message, log cooldown
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

LOG_FILE = Path.home() / ".opencode" / "zen_usage.json"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

ZEN_MODELS = [
    "opencode/big-pickle",
    "opencode/deepseek-v4-flash-free",
    "opencode/nemotron-3-super-free",
]

# ── Helpers ────────────────────────────────────────────────────────────────

def _load():
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {"calls": [], "limits": []}
    return {"calls": [], "limits": []}


def _save(data):
    LOG_FILE.write_text(json.dumps(data, indent=2, default=str))


def _now():
    return datetime.now()


def _ts():
    return _now().isoformat()


def _parse_cooldown_from_error(msg):
    """Extract cooldown hours from 'retrying in Xh Ym attempt N'."""
    m = re.search(r"retrying in (\d+)h\s*(\d+)m", msg)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60
    m = re.search(r"retrying in (\d+)h", msg)
    if m:
        return int(m.group(1)) * 3600
    return None


def _detect_limit(limits):
    """From observed cooldowns, back-calculate the actual limit (shared across all free models)."""
    if not limits:
        return None
    recent = [l for l in limits if l["cooldown_seconds"] > 0]
    if not recent:
        return None
    latest = recent[-1]
    calls_before_hit = latest.get("calls_before_hit", 0)
    window_seconds = latest["cooldown_seconds"]
    rate_per_hour = calls_before_hit / (window_seconds / 3600) if window_seconds > 0 else 0
    cooldown_hours = round(window_seconds / 3600, 1)
    estimated_limit = max(calls_before_hit, round(calls_before_hit * (24 / max(cooldown_hours, 0.1))))
    return {
        "last_known_limit": calls_before_hit,
        "extrapolated_24h_limit": estimated_limit,
        "inferred_rate_per_hour": round(rate_per_hour, 1),
        "cooldown_hours": cooldown_hours,
        "observed_at": latest["observed_at"],
    }


def _store_sqlite_snapshot(calls_today, tokens_in_today, tokens_out_today):
    """Write to existing ai_costs.db so cost dashboard still works."""
    try:
        db = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS zen_usage (
                id INTEGER PRIMARY KEY,
                ts TEXT NOT NULL,
                calls_per_hour INTEGER DEFAULT 0,
                tokens_per_hour INTEGER DEFAULT 0,
                calls_per_day INTEGER DEFAULT 0,
                tokens_per_day INTEGER DEFAULT 0,
                UNIQUE(ts)
            )
        """)
        hourly_calls = sum(
            1 for c in calls_today
            if c["timestamp"].startswith(_now().strftime("%Y-%m-%dT%H"))
            if not c.get("error")
        )
        conn.execute("""
            INSERT OR REPLACE INTO zen_usage
            (ts, calls_per_hour, tokens_per_hour, calls_per_day, tokens_per_day)
            VALUES (?, ?, ?, ?, ?)
        """, (_ts(), hourly_calls, tokens_in_today + tokens_out_today,
              len(calls_today), tokens_in_today + tokens_out_today))
        conn.commit()
        conn.close()
    except Exception:
        pass


# ── Commands ───────────────────────────────────────────────────────────────

def cmd_log(model, tokens_in=0, tokens_out=0, error=None, source="manual"):
    data = _load()
    entry = {
        "model": model,
        "timestamp": _ts(),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "error": error,
        "source": source,
    }
    data["calls"].append(entry)
    _save(data)
    if error:
        cooldown = _parse_cooldown_from_error(error)
        if cooldown:
            today_prefix = _now().strftime("%Y-%m-%d")
            calls_today = sum(
                1 for c in data["calls"]
                if c.get("error") is None
                and c["timestamp"].startswith(today_prefix)
            )
            data["limits"].append({
                "model": model,
                "observed_at": _ts(),
                "cooldown_seconds": cooldown,
                "calls_before_hit": calls_today,
                "error_snippet": error[:120],
            })
            _save(data)
            print(f"  ⚠  COOLDOWN: {cooldown//3600}h {(cooldown%3600)//60}m  "
                  f"calls before hit: {calls_today}")
        else:
            print(f"  ⚠  Error logged but couldn't parse cooldown: {error[:100]}")
    else:
        print(f"  ✓  Logged call to {model}")


def cmd_status():
    data = _load()
    calls = data["calls"]
    limits = data["limits"]
    today = _now().strftime("%Y-%m-%d")
    this_hour = _now().strftime("%Y-%m-%dT%H")

    calls_today = [c for c in calls if c["timestamp"].startswith(today)]
    calls_this_hour = [c for c in calls if c["timestamp"].startswith(this_hour)]
    errors_today = [c for c in calls_today if c.get("error")]

    limit_info = _detect_limit(limits)
    limit_line = ""
    if limit_info:
        ok_today = len([c for c in calls_today if not c.get("error")])
        limit_est = limit_info["extrapolated_24h_limit"]
        pct = (ok_today / max(limit_est, 1)) * 100
        remaining = max(0, limit_est - ok_today)
        limit_line = (
            f"  Observed limit:   {limit_info['last_known_limit']} calls before cooldown\n"
            f"  Extrapolated 24h: {limit_est} calls/day\n"
            f"  Used today:       {ok_today} calls ({pct:.0f}%)\n"
            f"  Remaining:        {remaining} calls\n"
            f"  Cooldown if hit:  {limit_info['cooldown_hours']}h\n"
            f"  Inferred rate:    {limit_info['inferred_rate_per_hour']} calls/hr"
        )

    model_breakdown = {}
    for c in calls_today:
        m = c["model"]
        model_breakdown.setdefault(m, {"ok": 0, "err": 0, "t_in": 0, "t_out": 0})
        if c.get("error"):
            model_breakdown[m]["err"] += 1
        else:
            model_breakdown[m]["ok"] += 1
        model_breakdown[m]["t_in"] += c.get("tokens_in", 0)
        model_breakdown[m]["t_out"] += c.get("tokens_out", 0)

    mb_lines = []
    for m in ZEN_MODELS:
        mb = model_breakdown.get(m, {"ok": 0, "err": 0, "t_in": 0, "t_out": 0})
        mb_lines.append(
            f"  {m:<40s} {mb['ok']:>4d} ok  {mb['err']:>3d} err  "
            f"{_fmt_tokens(mb['t_in'])} in  {_fmt_tokens(mb['t_out'])} out"
        )

    last_cooldown = ""
    if limits:
        lc = limits[-1]
        last_cooldown = (
            f"  Last cooldown:  {lc['observed_at']}  "
            f"({lc['cooldown_seconds']//3600}h {(lc['cooldown_seconds']%3600)//60}m)  "
            f"on {lc['model']}"
        )

    total_calls = len(calls)
    total_errors = sum(1 for c in calls if c.get("error"))

    tokens_in_today = sum(c.get("tokens_in", 0) for c in calls_today if not c.get("error"))
    tokens_out_today = sum(c.get("tokens_out", 0) for c in calls_today if not c.get("error"))
    _store_sqlite_snapshot(calls_today, tokens_in_today, tokens_out_today)

    print(f"""
{'='*60}
  ZEN FREE MODEL TRACKER — Empirical
{'='*60}
  Data file:  {LOG_FILE}
  Total logged calls: {total_calls} ({total_errors} errors)
  Since: {calls[0]['timestamp'] if calls else 'N/A'}
  Last:  {calls[-1]['timestamp'] if calls else 'N/A'}

  TODAY ({today}):
  {last_cooldown}
  Calls today:   {len(calls_today)} total  ({len(errors_today)} errors)
  Calls this hour: {len(calls_this_hour)}
  {chr(10).join(mb_lines)}
{'-'*60}
{limit_line}
{'='*60}
""")


def cmd_watch(interval=30):
    """Tail mode — poll and print status every N seconds."""
    print(f"  Watching Zen usage (refresh every {interval}s)...")
    print("  Press Ctrl+C to stop.\n")
    try:
        while True:
            os.system("clear" if os.name == "posix" else "cls")
            cmd_status()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  Stopped.")


def cmd_alert(threshold_pct=80):
    """Exit with code 1 if approaching limit, else 0."""
    data = _load()
    limits = data["limits"]
    calls = data["calls"]
    today = _now().strftime("%Y-%m-%d")
    limit_info = _detect_limit(limits)

    if not limit_info:
        print("  ?  No limit data yet — keep using models, tracker is learning.")
        sys.exit(0)

    calls_today_ok = [c for c in calls if c["timestamp"].startswith(today) and not c.get("error")]
    used = len(calls_today_ok)
    limit_est = limit_info["extrapolated_24h_limit"]
    pct = (used / max(limit_est, 1)) * 100

    if pct >= threshold_pct:
        remaining = max(0, limit_est - used)
        print(f"  ⚠  ALERT: {pct:.0f}% used ({used}/{limit_est}) — "
              f"{remaining} calls remaining before ~{limit_info['cooldown_hours']}h cooldown")
        sys.exit(1)
    else:
        print(f"  ✓  {pct:.0f}% used ({used}/{limit_est}) — below {threshold_pct}% threshold")
        sys.exit(0)


def cmd_check_429():
    """Manually parse an error message passed via stdin or --error."""
    error = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    if not error:
        print("  Provide error text via stdin pipe, or use --log with --error")
        sys.exit(1)
    cooldown = _parse_cooldown_from_error(error)
    if cooldown:
        print(f"  Cooldown detected: {cooldown//3600}h {(cooldown%3600)//60}m")
    else:
        print("  No cooldown pattern found in error")
    return error


def cmd_summarize():
    data = _load()
    limits = data["limits"]
    calls = data["calls"]
    today = _now().strftime("%Y-%m-%d")
    ok_today = [c for c in calls if c["timestamp"].startswith(today) and not c.get("error")]
    used = len(ok_today)
    limit_info = _detect_limit(limits)
    if limit_info:
        limit_est = limit_info["extrapolated_24h_limit"]
        pct = (used / max(limit_est, 1)) * 100
        print(f"ZEN: {pct:.0f}% ({used}/{limit_est})")
    else:
        print(f"ZEN: ? ({used}/?)")


def _fmt_tokens(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Zen free-model usage tracker — learns unpublished rate limits empirically"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--log", metavar="MODEL", help="Log a call to model")
    group.add_argument("--status", action="store_true", help="Dashboard")
    group.add_argument("--watch", action="store_true", help="Live tail mode")
    group.add_argument("--alert", type=float, nargs="?", const=80, metavar="PCT",
                       help="Exit 1 if usage above PCT pct (default: 80)")
    group.add_argument("--check-429", action="store_true",
                       help="Parse a 429 error from stdin and show cooldown")
    group.add_argument("--reset", action="store_true",
                       help="Clear all logged data (for debugging)")
    group.add_argument("--summarize", action="store_true",
                       help="One-line summary for shell/tmux")
    group.add_argument("--hook", metavar="MODEL",
                       help="Log call then exit 1 if above 80pct (for cron/systemd)")

    parser.add_argument("--tokens-in", type=int, default=0)
    parser.add_argument("--tokens-out", type=int, default=0)
    parser.add_argument("--error", help="Error message if call failed")
    parser.add_argument("--source", default="manual",
                        choices=["manual", "cli", "api", "session", "hook"])
    parser.add_argument("--interval", type=int, default=30,
                        help="Refresh interval for --watch (seconds)")

    args = parser.parse_args()

    if args.log:
        cmd_log(args.log, args.tokens_in, args.tokens_out, args.error, args.source)
    elif args.status:
        cmd_status()
    elif args.watch:
        cmd_watch(args.interval)
    elif args.alert is not None:
        cmd_alert(args.alert)
    elif args.check_429:
        cmd_check_429()
    elif args.reset:
        _save({"calls": [], "limits": []})
        print("  ✓  Usage data cleared")
    elif args.summarize:
        cmd_summarize()
    elif args.hook:
        cmd_log(args.hook, args.tokens_in, args.tokens_out, args.error, args.source or "hook")
        cmd_alert(80)


if __name__ == "__main__":
    main()

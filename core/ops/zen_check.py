#!/usr/bin/env python3
"""ZEN Status — multi-model OpenCode usage dashboard.
Reads actual session data from opencode SQLite DB.
Shows all providers: ZEN (DeepSeek), MAX (Claude), Poe, Ollama, OpenRouter, etc.
All times in Denver / Mountain (MDT = UTC-6).
"""
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OPENCODE_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
METRONOME = ROOT / "OpsCenter" / "metronome.py"
RATE_LOG = ROOT / "OpsCenter" / ".deepseek_rate_log"
DENVER_OFFSET = timedelta(hours=-6)

# Known rate limits by model
LIMITS = {
    "deepseek-v4-flash-free": {"name": "ZEN",   "req_hr": 100, "req_day": 500},
}

# Rolling windows in hours
WINDOWS = [("1h", 1), ("24h", 24), ("4d", 96)]

def now_denver():
    return datetime.now(timezone.utc) + DENVER_OFFSET

def fetch(hours_back: float | None = None) -> list[dict]:
    """Query opencode DB for sessions. None = all time."""
    if not OPENCODE_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(OPENCODE_DB))
        conn.row_factory = sqlite3.Row
        where = ""
        params = []
        if hours_back is not None:
            cutoff = (datetime.now(timezone.utc).timestamp() * 1000) - (hours_back * 3600 * 1000)
            where = "WHERE time_created > ?"
            params = [cutoff]
        rows = conn.execute(f"""
            SELECT id, model, cost, tokens_input, tokens_output, tokens_reasoning,
                   tokens_cache_read, tokens_cache_write, time_created
            FROM session
            {where}
            ORDER BY time_created DESC
        """, params).fetchall()
        conn.close()

        results = []
        for r in rows:
            raw = r["model"]
            if isinstance(raw, str):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"id": raw.strip(), "providerID": "unknown"}
            elif isinstance(raw, dict):
                parsed = raw
            else:
                parsed = {"id": "unknown", "providerID": "unknown"}
            mid = parsed.get("id", "unknown") or "(empty)"
            prov = parsed.get("providerID", "unknown") or "-"
            results.append({
                "id": r["id"],
                "model_id": mid,
                "provider": prov,
                "cost": r["cost"] if r["cost"] is not None else 0.0,
                "tokens_input": r["tokens_input"] or 0,
                "tokens_output": r["tokens_output"] or 0,
                "tokens_reasoning": r["tokens_reasoning"] or 0,
                "time_created": r["time_created"],
            })
        return results
    except Exception as e:
        print("  [DB error: " + str(e) + "]")
        return []

def count_zen_api_calls(hours_back: float) -> int:
    if not RATE_LOG.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    count = 0
    with open(RATE_LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ts = datetime.fromisoformat(line)
                if ts >= cutoff:
                    count += 1
            except ValueError:
                continue
    return count

def bar(pct, w=20):
    filled = int(pct / 100 * w) if pct > 0 else 0
    return "█" * min(filled, w) + "░" * max(0, w - min(filled, w))

def print_model_table(sessions, title=""):
    """Group sessions by model and print a table."""
    by_model = {}
    for s in sessions:
        mid = s["model_id"]
        if mid not in by_model:
            by_model[mid] = {"sessions": 0, "cost": 0.0, "in": 0, "out": 0, "reason": 0, "provider": s["provider"]}
        by_model[mid]["sessions"] += 1
        by_model[mid]["cost"] += s["cost"]
        by_model[mid]["in"] += s["tokens_input"]
        by_model[mid]["out"] += s["tokens_output"]
        by_model[mid]["reason"] += s["tokens_reasoning"]

    total_cost = sum(s["cost"] for s in sessions)

    if title:
        print("  " + title)
        print("  {:<28} {:>4} {:>10} {:>10} {:>10} {:>12}".format(
            "Model", "Ses", "Cost", "In", "Out", "Reason"))
    print("  " + "-" * 76)
    for mid in sorted(by_model.keys(), key=lambda m: by_model[m]["cost"], reverse=True):
        m = by_model[mid]
        cost_s = "$" + format(m["cost"], ".4f")
        # Short label
        short = mid
        if len(short) > 27:
            parts = short.split("/")
            short = parts[-1] if len(parts) > 1 else short[-27:]
        print("  {:<28} {:>4} {:>10} {:>10,} {:>10,} {:>12,}".format(
            short, m["sessions"], cost_s,
            m["in"], m["out"], m["reason"]))
    print(f"  {'─' * 76}")
    print(f"  {'TOTAL':<28} {sum(m['sessions'] for m in by_model.values()):>4} {'$' + format(total_cost, '.4f'):>10} {sum(m['in'] for m in by_model.values()):>10,} {sum(m['out'] for m in by_model.values()):>10,} {sum(m['reason'] for m in by_model.values()):>12,}")

def show():
    dn = now_denver()
    print("=" * 78)
    print("  OPENCODE USAGE DASHBOARD  —  " + dn.strftime("%a %b %-d %Y  %H:%M MT"))
    print("=" * 78)

    # ── Rolling windows ──
    for label, window_h in WINDOWS:
        sessions = fetch(window_h)
        if not sessions:
            print(f"\n  [{label}]  no sessions")
            continue

        print(f"\n  ── {label} ({window_h}h rolling)  [{len(sessions)} sessions] ──")
        print_model_table(sessions)

        # ZEN rate limit sub-section within 24h
        if window_h <= 24:
            zen_sessions = [s for s in sessions if s["model_id"] == "deepseek-v4-flash-free"]
            if zen_sessions:
                zen_hr = len([s for s in zen_sessions if s["time_created"] > (datetime.now(timezone.utc).timestamp() * 1000) - 3600 * 1000])
                zen_day = len(zen_sessions) if window_h >= 24 else len([s for s in fetch(24) if s["model_id"] == "deepseek-v4-flash-free"])
                met_hr = count_zen_api_calls(1)
                met_day = count_zen_api_calls(24)
                used_hr = max(zen_hr, met_hr)
                used_day = max(zen_day, met_day)
                lim_hr = LIMITS["deepseek-v4-flash-free"]["req_hr"]
                lim_day = LIMITS["deepseek-v4-flash-free"]["req_day"]
                pct_hr = used_hr / lim_hr * 100 if lim_hr else 0
                pct_day = used_day / lim_day * 100 if lim_day else 0
                print()
                print("  ZEN Rate Limits:")
                status_hr = "GREEN" if pct_hr < 50 else "YELLOW" if pct_hr < 80 else "RED"
                status_day = "GREEN" if pct_day < 50 else "YELLOW" if pct_day < 80 else "RED"
                print(f"    Hourly  [{bar(pct_hr)}]  {used_hr}/{lim_hr}  ({pct_hr:.1f}%)  {status_hr}")
                print(f"    Daily   [{bar(pct_day)}]  {used_day}/{lim_day}  ({pct_day:.1f}%)  {status_day}")

        # For 4d window, also show provider breakdown
        if window_h >= 96:
            by_prov = {}
            for s in sessions:
                prov = s["provider"]
                if prov not in by_prov:
                    by_prov[prov] = {"sessions": 0, "cost": 0.0, "in": 0, "out": 0}
                by_prov[prov]["sessions"] += 1
                by_prov[prov]["cost"] += s["cost"]
                by_prov[prov]["in"] += s["tokens_input"]
                by_prov[prov]["out"] += s["tokens_output"]
            print("\n  By Provider:")
            print("  {:<18} {:>4} {:>12} {:>12} {:>12}".format(
                "Provider", "Ses", "Cost", "In", "Out"))
            print("  " + "-" * 60)
            for prov in sorted(by_prov.keys(), key=lambda p: by_prov[p]["cost"], reverse=True):
                p = by_prov[prov]
                print("  {:<18} {:>4} {:>12} {:>12,} {:>12,}".format(
                    prov, p["sessions"], "$" + format(p["cost"], ".4f"), p["in"], p["out"]))

    # ── All-time model inventory ──
    print()
    print("  ── All-time model inventory ──")
    all_sessions = fetch(None)
    print_model_table(all_sessions)

    # ── Recent sessions (last 24h) ──
    print()
    print("  ── Recent sessions (last 24h, Denver time) ──")
    recent = fetch(24)
    for s in recent[:10]:
        ts_utc = datetime.fromtimestamp(s["time_created"] / 1000, tz=timezone.utc)
        ts_den = ts_utc + DENVER_OFFSET
        mid = s["model_id"]
        short = mid.split("/")[-1] if "/" in mid else mid[:18]
        cost_s = "$" + str(round(s["cost"], 4)) if s["cost"] > 0 else "free"
        in_s = format(s["tokens_input"], ",")
        out_s = format(s["tokens_output"], ",")
        prov = s["provider"]
        print(f"  {ts_den.strftime('%m/%d %H:%M')}  {short:<22} in={in_s:>8}  out={out_s:>6}  {cost_s:>8}  [{prov}]")
    if len(recent) > 10:
        print(f"  ... and {len(recent) - 10} more")

    # ── Zen cache stats ──
    print()
    print("  ── ZEN Cache ──")
    try:
        sys.path.insert(0, str(ROOT))
        from core.ops.zen_cache import ZenCache
        cache = ZenCache()
        st = cache.stats()
        print(f"  Entries: {st['cache_entries']}  Expired: {st['expired_entries']}"
              f"  Hit rate: {st['hit_rate_pct']}%"
              f"  (hits: {st['hits']}  misses: {st['misses']})")
    except Exception as e:
        print("  Cache unavailable: " + str(e))

    # ── Metronome ping ──
    try:
        subprocess.run(
            [sys.executable or "python3", str(METRONOME), "--record-deepseek-call"],
            capture_output=True, timeout=5
        )
    except Exception:
        pass

    print()
    print("=" * 78)
    print("  /zen-status  |  alias: zen")
    print("=" * 78)

if __name__ == "__main__":
    show()

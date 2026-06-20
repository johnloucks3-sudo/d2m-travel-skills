"""Replacement-trigger criteria (Commander directive 2026-06-20).
A CI tool that fails too often or runs too slow must be replaced, not just refreshed.
History entries: {"ts": iso, "ok": bool, "duration_ms": int, "timed_out": bool}.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def needs_replacement(history: list[dict], sla_ms: int, policy: dict,
                      now: datetime | None = None) -> tuple[bool, str]:
    now = now or datetime.now(timezone.utc)
    if not history:
        return (False, "no history")
    ordered = sorted(history, key=lambda h: h["ts"])
    last5 = ordered[-5:]

    # Consecutive failures (trailing)
    consec = 0
    for h in reversed(ordered):
        if not h["ok"]:
            consec += 1
        else:
            break
    if consec >= policy["consecutive_failures_max"]:
        return (True, f"{consec} consecutive failures (max {policy['consecutive_failures_max']})")

    # Consecutive timeouts (trailing)
    consec_to = 0
    for h in reversed(ordered):
        if h.get("timed_out"):
            consec_to += 1
        else:
            break
    if consec_to >= policy["consecutive_timeouts_max"]:
        return (True, f"{consec_to} consecutive timeouts (hung tool)")

    # Rolling failure rate
    cutoff = now - timedelta(days=policy["rolling_window_days"])
    win_failures = sum(1 for h in ordered if _parse(h["ts"]) > cutoff and not h["ok"])
    if win_failures >= policy["failures_in_window_max"]:
        return (True, f"{win_failures} failures in {policy['rolling_window_days']} days "
                      f"(max {policy['failures_in_window_max']})")

    # Latency spike — any single run > factor x SLA
    spike = sla_ms * policy["latency_breach_factor"]
    for h in last5:
        if h["ok"] and h["duration_ms"] > spike:
            return (True, f"latency spike {h['duration_ms']}ms > {spike:.0f}ms "
                          f"({policy['latency_breach_factor']}x SLA)")

    # Sustained latency — N of last 5 over SLA
    over = sum(1 for h in last5 if h["ok"] and h["duration_ms"] > sla_ms)
    if over >= policy["latency_breach_runs_of_last_5"]:
        return (True, f"sustained slowness — {over} of last 5 runs over {sla_ms}ms SLA")

    return (False, "within thresholds")

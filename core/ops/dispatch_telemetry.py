#!/usr/bin/env python3
"""
Dispatch Telemetry — Tracks every model dispatch for cost/usage analysis.

Records:
- Substrate selected (sonnet/opus/haiku/gemini-flash)
- Selection source (Layer 1/4 trigger, default)
- Whether MAX OAuth was used (drives cost calc)
- Whether Layer 3 escalated the response
- Token estimate, duration, est cost vs. would-have-cost-API
- Daily rollup writer

Storage: JSONL append-only at logs/dispatch_telemetry.jsonl
Daily rollup: state/dispatch_daily.json (rewritten each day)
"""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone, date
from typing import Optional

_LOG_PATH = Path("/home/john/Thunderbird/logs/dispatch_telemetry.jsonl")
_ROLLUP_PATH = Path("/home/john/Thunderbird/state/dispatch_daily.json")

# Approx API rates ($/M tokens) for "would-have-cost" math.
# All MAX OAuth calls = $0 marginal (subscription cost).
_API_RATES = {
    "haiku":   {"in": 1.00,  "out": 5.00},
    "sonnet":  {"in": 3.00,  "out": 15.00},
    "opus":    {"in": 15.00, "out": 75.00},
    "gemini-flash": {"in": 0.075, "out": 0.30},
    "deepseek": {"in": 0.27, "out": 0.27},
}


def _hash_request(req: str) -> str:
    return hashlib.sha256(req.encode("utf-8")).hexdigest()[:12]


def _est_tokens(text: str) -> int:
    """Rough char/4 approximation."""
    return max(1, len(text) // 4)


def _estimate_api_cost(substrate: str, in_tokens: int, out_tokens: int) -> float:
    rates = _API_RATES.get(substrate, _API_RATES["sonnet"])
    return (in_tokens * rates["in"] + out_tokens * rates["out"]) / 1_000_000


def log_dispatch(
    request: str,
    response: str,
    substrate: str,
    selection_source: str,
    selection_reason: str,
    executed_via: str,
    escalated: bool,
    duration_s: float,
    supervision: Optional[dict] = None,
) -> dict:
    """Write a single dispatch event. Returns the record for inspection.

    Args:
        executed_via: "max_oauth" if MAX subscription path, "api" if paid API,
                      "fallback_deepseek" if fallback, "test" if mocked.
    """
    in_tokens = _est_tokens(request)
    out_tokens = _est_tokens(response)
    would_cost = _estimate_api_cost(substrate, in_tokens, out_tokens)
    actual_cost = 0.0 if executed_via == "max_oauth" else would_cost

    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "request_hash": _hash_request(request),
        "request_preview": request[:120].replace("\n", " "),
        "substrate": substrate,
        "selection_source": selection_source,
        "selection_reason": selection_reason,
        "executed_via": executed_via,
        "escalated": escalated,
        "supervision_triggers": (supervision or {}).get("matched_triggers", []),
        "tokens_in_est": in_tokens,
        "tokens_out_est": out_tokens,
        "duration_s": round(duration_s, 3),
        "cost_actual_usd": round(actual_cost, 6),
        "cost_would_be_api_usd": round(would_cost, 6),
        "savings_usd": round(would_cost - actual_cost, 6),
    }

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")

    return record


def daily_rollup(target_date: Optional[date] = None) -> dict:
    """Aggregate today's events into a single summary. Writes rollup JSON.

    Uses UTC date for matching since events are stored with UTC timestamps.
    Returns the rollup dict.
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    if not _LOG_PATH.exists():
        return _empty_rollup(target_date)

    events = []
    with open(_LOG_PATH) as f:
        for line in f:
            try:
                ev = json.loads(line)
                ev_date = datetime.fromisoformat(ev["ts"].replace("Z", "+00:00")).date()
                if ev_date == target_date:
                    events.append(ev)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    if not events:
        return _empty_rollup(target_date)

    rollup = {
        "date": target_date.isoformat(),
        "total_dispatches": len(events),
        "by_substrate": _count_field(events, "substrate"),
        "by_source": _count_field(events, "selection_source"),
        "by_executed_via": _count_field(events, "executed_via"),
        "escalations": sum(1 for e in events if e.get("escalated")),
        "max_oauth_pct": round(
            100 * sum(1 for e in events if e.get("executed_via") == "max_oauth") / len(events),
            1,
        ),
        "tokens_in_total_est": sum(e.get("tokens_in_est", 0) for e in events),
        "tokens_out_total_est": sum(e.get("tokens_out_est", 0) for e in events),
        "cost_actual_usd_total": round(sum(e.get("cost_actual_usd", 0) for e in events), 4),
        "cost_would_be_api_total": round(sum(e.get("cost_would_be_api_usd", 0) for e in events), 4),
        "savings_total_usd": round(sum(e.get("savings_usd", 0) for e in events), 4),
        "avg_duration_s": round(
            sum(e.get("duration_s", 0) for e in events) / len(events), 3
        ),
    }

    _ROLLUP_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ROLLUP_PATH.write_text(json.dumps(rollup, indent=2))
    return rollup


def _empty_rollup(d: date) -> dict:
    return {
        "date": d.isoformat(),
        "total_dispatches": 0,
        "by_substrate": {},
        "by_source": {},
        "by_executed_via": {},
        "escalations": 0,
        "max_oauth_pct": 0.0,
        "tokens_in_total_est": 0,
        "tokens_out_total_est": 0,
        "cost_actual_usd_total": 0.0,
        "cost_would_be_api_total": 0.0,
        "savings_total_usd": 0.0,
        "avg_duration_s": 0.0,
    }


def _count_field(events: list, field: str) -> dict:
    counts = {}
    for e in events:
        v = e.get(field, "unknown")
        counts[v] = counts.get(v, 0) + 1
    return counts


def status_report(target_date: Optional[date] = None) -> str:
    """Human-readable status string for CLI / Telegram."""
    r = daily_rollup(target_date)
    if r["total_dispatches"] == 0:
        return f"📊 Dispatch telemetry — {r['date']}: no activity"

    lines = [
        f"📊 DISPATCH TELEMETRY — {r['date']}",
        f"Total dispatches: {r['total_dispatches']}",
        f"MAX OAuth usage: {r['max_oauth_pct']}%",
        f"Layer 3 escalations: {r['escalations']}",
        "",
        "By substrate:",
    ]
    for k, v in sorted(r["by_substrate"].items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("By selection source:")
    for k, v in sorted(r["by_source"].items(), key=lambda x: -x[1]):
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append(f"Tokens (in/out est): {r['tokens_in_total_est']:,} / {r['tokens_out_total_est']:,}")
    lines.append(f"Actual cost today: ${r['cost_actual_usd_total']:.4f}")
    lines.append(f"Would-have-cost API: ${r['cost_would_be_api_total']:.4f}")
    lines.append(f"💰 Savings vs all-API: ${r['savings_total_usd']:.4f}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "rollup":
        print(json.dumps(daily_rollup(), indent=2))
    else:
        print(status_report())

"""
core/ai_infra/seat_budget.py — per-seat budget state (2026-07-16).

Replaces the single-pool, chronically-stale rate_limit_status.md with a
per-seat JSON file. Ground truth: there is no public API for Claude MAX
usage-% — the numbers are manually transcribed off the plan screen, so the
design goal is a ten-second update path (scripts/update_seat_budget.py) plus
an explicit staleness flag so an old number is never silently trusted.

Seats: CC (Claude MAX) · OC (DeepSeek v4 — Zen free/Poe points) · AG (Gemini).
RESERVE (non-MAX Anthropic API key) is tracked but UNFUNDED per Commander.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATE = Path("/home/john/Thunderbird/OpsCenter/collaboration/seat_budget_state.json")
STALE_HOURS = 24
SEATS = ("CC", "OC", "AG", "RESERVE")


def read_state() -> dict:
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def update_seat(seat: str, *, weekly_pct: float | None = None,
                five_hour_pct: float | None = None, note: str = "") -> dict:
    if seat not in SEATS:
        raise ValueError(f"seat must be one of {SEATS}")
    state = read_state()
    entry = state.get(seat, {})
    if weekly_pct is not None:
        entry["weekly_pct"] = weekly_pct
    if five_hour_pct is not None:
        entry["five_hour_pct"] = five_hour_pct
    if note:
        entry["note"] = note
    entry["last_updated"] = datetime.now(timezone.utc).isoformat()
    entry["source"] = "manual (no public usage API)"
    state[seat] = entry
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))
    return entry


def seat_status(seat: str) -> dict:
    """{weekly_pct, five_hour_pct, stale: bool, age_hours} — stale data is
    flagged, never hidden. Missing seat → stale=True, pct=None."""
    entry = read_state().get(seat)
    if not entry or "last_updated" not in entry:
        return {"weekly_pct": None, "five_hour_pct": None, "stale": True, "age_hours": None}
    age = (datetime.now(timezone.utc)
           - datetime.fromisoformat(entry["last_updated"])).total_seconds() / 3600
    return {
        "weekly_pct": entry.get("weekly_pct"),
        "five_hour_pct": entry.get("five_hour_pct"),
        "stale": age > STALE_HOURS,
        "age_hours": round(age, 1),
        "note": entry.get("note", ""),
    }


def blackboard_line() -> str:
    """One line for blackboard_sync: per-seat %, STALE-flagged."""
    parts = []
    for seat in ("CC", "OC", "AG"):
        s = seat_status(seat)
        pct = f"{s['weekly_pct']:.0f}%" if s["weekly_pct"] is not None else "?"
        parts.append(f"{seat}:{pct}" + ("⚠STALE" if s["stale"] else ""))
    return " | ".join(parts)

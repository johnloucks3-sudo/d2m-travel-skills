"""
core/silver/scorecard.py — seat effectiveness scorecard (2026-07-16).

Evidence over assumption: one flat append-only log of real outcomes, two
dimensions per the Commander's ask — task-category fit (who is best at
research/scraping/coding/itineraries/staff work) and working-style traits
(disciplined/fast/deep). Rows come from real events only: certified
delegations (delegation_wiring) and scored insight cards (insight_exchange).
Becomes a routing input for route_task() once enough rows accumulate.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SCORECARD = Path("/home/john/Thunderbird/OpsCenter/collaboration/seat_scorecard.jsonl")

CATEGORIES = ("research", "scraping", "coding", "itineraries", "staff_work",
              "planning", "design", "summarizing", "analysis", "brainstorming",
              "data_pull", "ops", "prediction")


def record(seat: str, *, category: str, outcome: str, task_type: str = "",
           traits_observed: list[str] | None = None, ref: str = "") -> dict:
    """Append one evidence row. outcome: pass|fail|redo|hit|miss."""
    row = {
        "seat": seat, "task_type": task_type, "category": category,
        "traits_observed": traits_observed or [], "outcome": outcome,
        "ref": ref, "date": datetime.now(timezone.utc).isoformat(),
    }
    SCORECARD.parent.mkdir(parents=True, exist_ok=True)
    with SCORECARD.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def summary() -> dict:
    """Per-seat, per-category tallies from real rows."""
    out: dict = defaultdict(lambda: defaultdict(lambda: {"pass": 0, "fail": 0,
                                                         "hit": 0, "miss": 0, "redo": 0}))
    if not SCORECARD.exists():
        return {}
    for line in SCORECARD.read_text().splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        cell = out[r["seat"]][r["category"]]
        cell[r["outcome"]] = cell.get(r["outcome"], 0) + 1
    return {s: dict(c) for s, c in out.items()}

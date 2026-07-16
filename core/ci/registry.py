"""CI registry loader + razor-sharp status computation.
The registry (config/ci_registry.json) is the source of truth AND the policy.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, date
from pathlib import Path

DEFAULT_REGISTRY = Path("/home/john/Thunderbird/config/ci_registry.json")
REQUIRED_FIELDS = ("id", "name", "ci_tool", "health_probe", "currency_window_hours",
                   "reeval_cadence_days", "fallback", "keeper")


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict:
    reg = json.loads(Path(path).read_text())
    for s in reg.get("skills", []):
        missing = [f for f in REQUIRED_FIELDS if f not in s]
        if missing:
            raise ValueError(f"CI registry entry {s.get('id','?')} missing fields: {missing}")
    return reg


def _age_hours(iso: str | None, now: datetime) -> float:
    if not iso:
        return float("inf")
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).total_seconds() / 3600.0


def _age_days(d: str | None, now: datetime) -> float:
    if not d:
        return float("inf")
    y, m, dd = (int(x) for x in d.split("-"))
    return (now.date() - date(y, m, dd)).days


def razor_sharp_status(entry: dict, probe_ok: bool, now: datetime | None = None) -> str:
    """RETIRED (on-demand, not currency-tracked) | RED (probe failed) |
    DULL (currency/re-eval overdue) | RAZOR_SHARP.

    Retired/on-demand designations null their currency_window_hours/reeval_cadence_days
    (they aren't subject to the razor-sharp clock). Guard against None so one such
    entry can't crash the whole fleet sweep (M-636: regent-portal-live nulled its
    windows on retirement and a raw `>=` comparison against None aborted the sweep,
    leaving 46/53 designations stuck at status 'unknown').
    """
    now = now or datetime.now(timezone.utc)
    if entry.get("status") == "retired_on_demand":
        return "RETIRED"
    if not probe_ok:
        return "RED"
    cwh = entry.get("currency_window_hours")
    if cwh is not None and _age_hours(entry.get("last_verified"), now) >= cwh:
        return "DULL"
    rcd = entry.get("reeval_cadence_days")
    if rcd is not None and _age_days(entry.get("last_reeval"), now) >= rcd:
        return "DULL"
    return "RAZOR_SHARP"

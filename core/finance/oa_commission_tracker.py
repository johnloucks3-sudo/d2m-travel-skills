"""Outside Agents received-commission tracker.

Tier is per-host on commission RECEIVED (post-travel payout), trailing 12 months.
OA: 80% base; 90% at $10,000; 95% at $40,000. Source of truth: config/oa_commission_ledger.json.
Harlan owns the numbers. Pages Commander when a threshold is crossed.
"""
from __future__ import annotations
import json
from datetime import date, timedelta
from pathlib import Path

DEFAULT_LEDGER = Path("/home/john/Thunderbird/config/oa_commission_ledger.json")
TIER_90_USD = 10000.0
TIER_95_USD = 40000.0


def _parse(d: str) -> date:
    y, m, dd = (int(x) for x in d.split("-"))
    return date(y, m, dd)


def rolling_received(entries: list[dict], as_of: date) -> float:
    cutoff = as_of - timedelta(days=365)
    return round(sum(
        float(e.get("d2m_received_usd", 0.0))
        for e in entries
        if cutoff < _parse(e["date"]) <= as_of
    ), 2)


def tier_for(rolling_usd: float) -> int:
    if rolling_usd >= TIER_95_USD:
        return 95
    if rolling_usd >= TIER_90_USD:
        return 90
    return 80


class OATracker:
    def __init__(self, ledger_path: Path = DEFAULT_LEDGER):
        self.ledger_path = Path(ledger_path)

    def _load(self) -> dict:
        return json.loads(self.ledger_path.read_text())

    def status(self, as_of: date | None = None) -> dict:
        as_of = as_of or date.today()
        data = self._load()
        entries = data.get("received", [])
        rolling = rolling_received(entries, as_of)
        tier = tier_for(rolling)
        next_threshold = TIER_90_USD if tier == 80 else (TIER_95_USD if tier == 90 else None)
        to_next = round(next_threshold - rolling, 2) if next_threshold else 0.0
        return {
            "host": data.get("host", "Outside Agents, LLC"),
            "as_of": as_of.isoformat(),
            "rolling_received_usd": rolling,
            "current_tier_pct": tier,
            "to_next_tier_usd": to_next,
            "crossed_90": rolling >= TIER_90_USD,
            "crossed_95": rolling >= TIER_95_USD,
        }

    def page_if_crossed(self, as_of: date | None = None) -> str | None:
        s = self.status(as_of)
        if s["crossed_95"]:
            return (f"💰 OA COMMISSION TIER — 95% reached. Trailing-12mo received "
                    f"${s['rolling_received_usd']:,.2f} (host: {s['host']}). Verify OA portal bumped your split.")
        if s["crossed_90"]:
            return (f"💰 OA COMMISSION TIER — 90% reached. Trailing-12mo received "
                    f"${s['rolling_received_usd']:,.2f} (host: {s['host']}). Verify OA portal bumped your split.")
        return None

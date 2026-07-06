"""
D2M Loyalty Tracker
Dreams2Memories Travel, LLC

Tiers repeat clients by confirmed voyage count and generates a discount
code + benefits package per tier.

Tier thresholds (config/loyalty_benefits.json is the source of truth):
  Bronze 1 | Silver 2-3 | Gold 4-5 | Platinum 6+

Voyage count is derived from booking records (KNOWN_BOOKINGS by default) —
NOT from a dossier "embarkation_history" field, which does not exist in any
current dossier. Grouping is by exact client name string (each KNOWN_BOOKINGS
entry already carries the couple's full name); it does not fuzzy-match across
different couples sharing a family surname (e.g. the three Kuklinski-group
bookings are three distinct client identities, not one client with 3 voyages).
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "loyalty_benefits.json"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def load_benefits(config_path: Path = CONFIG_PATH) -> dict:
    return json.loads(config_path.read_text())


def _tier_thresholds(benefits_cfg: dict) -> list[tuple[str, int]]:
    """[(tier, min_voyages), ...] sorted highest threshold first."""
    return sorted(
        ((tier, cfg["min_voyages"]) for tier, cfg in benefits_cfg.items()),
        key=lambda t: -t[1],
    )


def tier_for_voyage_count(count: int, benefits_cfg: dict) -> str:
    if count <= 0:
        return "None"
    for tier, threshold in _tier_thresholds(benefits_cfg):
        if count >= threshold:
            return tier
    return "None"


def client_key(client_name: str) -> str:
    """Case/whitespace-normalized identity key for grouping bookings."""
    return " ".join(client_name.split()).strip().lower()


def count_voyages_per_client(bookings: dict) -> dict:
    """
    bookings: KNOWN_BOOKINGS-shaped dict {booking_key: {"client": str, ...}}
    Returns {display_client_name: voyage_count}, one entry per distinct client identity.
    """
    counts: dict[str, int] = {}
    display_names: dict[str, str] = {}
    for booking in bookings.values():
        key = client_key(booking["client"])
        counts[key] = counts.get(key, 0) + 1
        display_names.setdefault(key, booking["client"])
    return {display_names[key]: n for key, n in counts.items()}


def generate_discount_code(client_name: str, tier: str) -> str:
    """Deterministic code: D2M-<TIER3>-<8-char hash of client+tier>."""
    digest = hashlib.sha256(f"{client_key(client_name)}|{tier}".encode()).hexdigest().upper()
    return f"D2M-{tier[:3].upper()}-{digest[:8]}"


def build_loyalty_record(client_name: str, voyage_count: int, benefits_cfg: dict) -> dict:
    tier = tier_for_voyage_count(voyage_count, benefits_cfg)
    tier_cfg = benefits_cfg.get(tier, {})
    return {
        "client": client_name,
        "voyage_count": voyage_count,
        "tier": tier,
        "discount_pct": tier_cfg.get("discount_pct", 0),
        "onboard_credit_usd": tier_cfg.get("onboard_credit_usd", 0),
        "priority_cabin_selection": tier_cfg.get("priority_cabin_selection", False),
        "concierge_perks": tier_cfg.get("concierge_perks", []),
        "discount_code": generate_discount_code(client_name, tier) if tier != "None" else None,
    }


def build_all_records(bookings: dict, benefits_cfg: dict = None) -> dict:
    benefits_cfg = benefits_cfg or load_benefits()
    counts = count_voyages_per_client(bookings)
    return {
        name: build_loyalty_record(name, count, benefits_cfg)
        for name, count in counts.items()
    }


def run(bookings: dict = None, output_dir: Path = OUTPUT_DIR) -> dict:
    if bookings is None:
        sys.path.insert(0, str(Path(__file__).parent.parent / "scheduling"))
        from thunderbird_anchor_dates import KNOWN_BOOKINGS
        bookings = KNOWN_BOOKINGS

    records = build_all_records(bookings)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"client_loyalty_tier_{datetime.now().strftime('%Y-%m')}.json"
    out_path.write_text(json.dumps(records, indent=2, sort_keys=True))
    return {"output_path": str(out_path), "records": records}


if __name__ == "__main__":
    result = run()
    print(f"Wrote {len(result['records'])} client loyalty records to {result['output_path']}")
    for name, rec in sorted(result["records"].items(), key=lambda kv: -kv[1]["voyage_count"]):
        print(f"  {name}: {rec['voyage_count']} voyage(s) -> {rec['tier']}"
              f"{' (' + rec['discount_code'] + ')' if rec['discount_code'] else ''}")

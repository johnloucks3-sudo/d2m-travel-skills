"""
Allegiant Air CONUS Route Screen — D2M Flight Screening Module
==============================================================

Provides a fast lookup to determine whether Allegiant Air (G4) serves
a given CONUS city-pair, and flags baggage cost implications for
cruise travelers.

Usage:
    from core.travel.allegiant_screen import AllegiantScreen

    screen = AllegiantScreen()
    result = screen.check("COS", "SNA")
    print(result["summary"])

    # With bag weight
    result = screen.check("DEN", "VPS", bag_weight_lb=65)

    # In the fare-watch / flight-price flow:
    note = screen.skill_note("COS", "PIE", bag_weight_lb=60, pax=2)

Data source: /home/john/Thunderbird/data/allegiant_conus_routes.json
Verified: 2026-06-11 | Source: allegiantair.com live pages
"""

import json
from pathlib import Path
from typing import Optional

DATA_FILE = Path(__file__).parent.parent.parent / "data" / "allegiant_conus_routes.json"

# IATA codes for countries outside CONUS — used to skip Allegiant check
_INTL_PREFIXES = set()  # We use a positive check instead: known US airport list
# Airports OUTSIDE the continental US (international + Hawaii/territories).
# Allegiant is CONUS-only, so we skip the check if either endpoint is here.
# Rule: if it's a US state airport on the mainland, it IS potentially CONUS.
# Do NOT include US domestic airports (FLL, MIA, EWR, JFK, LAX, SFO, etc.)
INTL_AIRPORTS = {
    # Europe
    "LIS", "BCN", "FCO", "ATH", "NCE", "BGO", "CDG", "AMS",
    "LHR", "DUB", "ZRH", "VIE", "CPH", "ARN", "OSL", "HEL",
    "PRG", "WAW", "BUD", "SVO", "IST", "KEF",
    # Middle East / Asia / Pacific
    "DXB", "SIN", "HKG", "BKK", "NRT", "KIX", "ICN", "SYD", "MEL",
    # Latin America / Caribbean
    "GRU", "EZE", "SCL", "LIM", "BOG",
    "PTY", "SJO", "MBJ", "NAS", "GCM", "AUA", "CUR",
    "FDF", "PTP", "SXM",
    # US Territories / non-CONUS
    "SJU",  # Puerto Rico
    "STT", "STX",  # USVI
    "HNL", "OGG", "KOA",  # Hawaii — Allegiant does not serve Hawaii from CONUS
    # Note: Alaska airports (ANC, FAI) are also not Allegiant CONUS
    "ANC", "FAI", "JNU",
}

CONUS_STATES = {
    "AL","AZ","AR","CA","CO","CT","DE","FL","GA","ID","IL","IN","IA","KS",
    "KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT",
    "VT","VA","WA","WV","WI","WY","DC",
}


class AllegiantScreen:
    """
    Fast lookup for Allegiant Air CONUS route coverage.

    Designed to be instantiated once per flight-price skill invocation.
    Reads the JSON reference on init; no network calls.
    """

    def __init__(self, data_file: Path = DATA_FILE):
        if not data_file.exists():
            raise FileNotFoundError(
                f"Allegiant route data not found: {data_file}\n"
                f"Run: ls /home/john/Thunderbird/data/allegiant_conus_routes.json"
            )
        with open(data_file) as f:
            self._data = json.load(f)
        self._meta = self._data["_meta"]
        self._bag = self._data["baggage_policy"]
        self._gateways = self._data["gateways"]
        self._logic = self._data["screening_logic"]

    def is_conus_route(self, origin: str, dest: str) -> bool:
        """
        Returns True if BOTH airports are domestic US.
        Conservative: only returns False if either code is in the known
        international set. Unknown codes are treated as potentially domestic.
        """
        return (
            origin.upper() not in INTL_AIRPORTS
            and dest.upper() not in INTL_AIRPORTS
        )

    def check(
        self,
        origin: str,
        dest: str,
        bag_weight_lb: Optional[float] = None,
        pax: int = 2,
        bags_per_pax: int = 1,
    ) -> dict:
        """
        Check Allegiant coverage for a city-pair and return a structured result.

        Args:
            origin:         IATA origin code (e.g. "COS", "DEN")
            dest:           IATA destination code (e.g. "SNA", "VPS")
            bag_weight_lb:  Heaviest checked bag weight in lbs (optional).
                            If provided, calculates overweight surcharges.
            pax:            Number of passengers (for total cost math).
            bags_per_pax:   Checked bags per passenger (default 1).

        Returns dict with keys:
            serves_route:   True / False / None (None = data gap)
            route_note:     Human-readable service status string
            bag_warning:    Bag weight warning string (if bag_weight_lb provided)
            bag_cost_extra_pp: Extra bag cost per person above base (if calculable)
            summary:        One-line skill note combining all findings
            data_gap:       True if origin or dest is not in reference data
            verified_date:  Date of data verification
        """
        o = origin.upper()
        d = dest.upper()

        result = {
            "origin": o,
            "dest": d,
            "serves_route": None,
            "route_note": "",
            "bag_warning": "",
            "bag_cost_extra_pp": 0,
            "summary": "",
            "data_gap": False,
            "verified_date": self._meta["verified_date"],
        }

        # Step 1: Skip if international
        if not self.is_conus_route(o, d):
            result["serves_route"] = False
            result["route_note"] = (
                f"Allegiant check skipped — {o}→{d} is not a CONUS route. "
                f"Allegiant is domestic-only."
            )
            result["summary"] = result["route_note"]
            return result

        # Step 2: Check if origin gateway is in reference
        gw_data = self._gateways.get(o) or self._gateways.get(f"{o}_DFW")
        if gw_data is None:
            result["serves_route"] = None
            result["data_gap"] = True
            result["route_note"] = (
                f"Allegiant: {o} not in D2M verified gateway list (verified "
                f"{self._meta['verified_date']}). "
                f"Check allegiantair.com/route-map for current {o} routes."
            )
        else:
            # Step 3: Check if dest is in routes array
            routes = gw_data.get("routes", [])
            match = next((r for r in routes if r["dest_iata"].upper() == d), None)

            if match:
                seasonal = match.get("seasonal") or "year-round"
                fare = match.get("sample_fare_usd")
                fare_str = f" (sample from ~${fare})" if fare else ""
                result["serves_route"] = True
                result["route_note"] = (
                    f"Allegiant G4 SERVES {o}→{d} ({match['dest_city']}) — "
                    f"nonstop, {seasonal}{fare_str}. "
                    f"Verified {match['verified_date']} via {match['source']}."
                )
            else:
                result["serves_route"] = None
                result["data_gap"] = True
                result["route_note"] = (
                    f"Allegiant {o}→{d}: NOT in D2M verified route list "
                    f"({len(routes)} routes on file for {o} as of "
                    f"{self._meta['verified_date']}). "
                    f"Confirm at allegiantair.com/route-map — absence here does NOT "
                    f"confirm no service."
                )

        # Step 4: Bag weight advisory
        if bag_weight_lb is not None:
            bag_result = self.calc_bag_surcharge(bag_weight_lb, pax, bags_per_pax)
            result["bag_warning"] = bag_result["warning"]
            result["bag_cost_extra_pp"] = bag_result["extra_per_pax_roundtrip"]

        # Step 5: Compose summary
        parts = [result["route_note"]]
        if result["bag_warning"]:
            parts.append(result["bag_warning"])
        if result["serves_route"] is True:
            parts.append(
                "⚠️ Allegiant charges for carry-on bags + has steep airport bag fees — "
                "book bags in advance."
            )
        result["summary"] = " | ".join(parts)

        return result

    def calc_bag_surcharge(
        self,
        bag_weight_lb: float,
        pax: int = 2,
        bags_per_pax: int = 1,
    ) -> dict:
        """
        Calculate Allegiant overweight surcharge for given bag weight.

        Returns:
            warning:                 Human-readable warning string
            overweight:              True if bag exceeds 50 lb limit
            surcharge_per_segment:   Extra charge per bag per segment (USD)
            extra_per_pax_roundtrip: Extra cost per passenger for round trip
            total_extra_all_pax:     Total extra for all pax round trip
        """
        limit = self._bag["standard_checked_limit_lb"]  # 50 lb
        tiers = self._bag["overweight_tiers"]

        if bag_weight_lb <= limit:
            return {
                "warning": (
                    f"Bag weight {bag_weight_lb} lb is within Allegiant's {limit} lb "
                    f"standard limit. No overweight surcharge."
                ),
                "overweight": False,
                "surcharge_per_segment": 0,
                "extra_per_pax_roundtrip": 0,
                "total_extra_all_pax": 0,
            }

        # Find applicable tier
        surcharge = 0
        tier_desc = ""
        for tier in tiers:
            low, high = tier["weight_range_lb"].split("–")
            if float(low) <= bag_weight_lb <= float(high):
                surcharge = tier["surcharge_per_segment_usd"]
                tier_desc = f"{tier['weight_range_lb']} lb = +${surcharge}/segment"
                break
        else:
            # Above highest tier
            surcharge = tiers[-1]["surcharge_per_segment_usd"]
            tier_desc = f">{tiers[-1]['weight_range_lb'].split('–')[0]} lb tier"

        # Round trip = 2 segments
        extra_per_bag_rt = surcharge * 2
        extra_per_pax_rt = extra_per_bag_rt * bags_per_pax
        total_extra = extra_per_pax_rt * pax

        warning = (
            f"⚠️ ALLEGIANT BAG WEIGHT ALERT: {bag_weight_lb} lb bag EXCEEDS "
            f"Allegiant's {limit} lb standard limit. "
            f"Surcharge: +${surcharge}/bag/segment ({tier_desc}). "
            f"Round trip (2 segments): +${extra_per_bag_rt}/bag extra. "
            f"For {pax} pax × {bags_per_pax} bag(s) each: "
            f"+${total_extra} total extra vs. base bag fee. "
            f"Compare to legacy carriers (UA/AA/DL) where bag may be FREE or "
            f"included — Allegiant's total bag cost could be HIGHER despite lower fare."
        )

        return {
            "warning": warning,
            "overweight": True,
            "surcharge_per_segment": surcharge,
            "extra_per_pax_roundtrip": extra_per_pax_rt,
            "total_extra_all_pax": total_extra,
        }

    def skill_note(
        self,
        origin: str,
        dest: str,
        bag_weight_lb: Optional[float] = None,
        pax: int = 2,
    ) -> str:
        """
        One-call method for the flight-price skill.
        Returns a formatted string to append to any CONUS flight quote.

        Usage in flight-price skill:
            from core.travel.allegiant_screen import AllegiantScreen
            note = AllegiantScreen().skill_note("COS", "SNA", bag_weight_lb=65, pax=2)
            # Append note to quote output
        """
        result = self.check(origin, dest, bag_weight_lb=bag_weight_lb, pax=pax)
        return result["summary"]

    def gateway_routes(self, origin: str) -> list:
        """Return all verified routes from a gateway, or empty list if not in file."""
        gw = self._gateways.get(origin.upper(), {})
        return gw.get("routes", [])

    def verified_date(self) -> str:
        return self._meta["verified_date"]


# ---------------------------------------------------------------------------
# CLI: python3 core/travel/allegiant_screen.py COS SNA [bag_weight_lb]
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    screen = AllegiantScreen()

    if len(sys.argv) < 3:
        print("Usage: python3 allegiant_screen.py <ORIGIN> <DEST> [bag_lb]")
        print("\nGateway summaries:")
        for gw_id, gw in screen._gateways.items():
            routes = gw.get("routes", [])
            dests = ", ".join(r["dest_iata"] for r in routes) if routes else "NO DATA"
            print(f"  {gw_id:8s}: {len(routes)} routes → {dests}")
        sys.exit(0)

    origin = sys.argv[1]
    dest = sys.argv[2]
    bag_lb = float(sys.argv[3]) if len(sys.argv) > 3 else None

    result = screen.check(origin, dest, bag_weight_lb=bag_lb)
    print(f"\n{'='*60}")
    print(f"Allegiant Screen: {origin} → {dest}")
    print(f"{'='*60}")
    print(f"Serves route:    {result['serves_route']}")
    print(f"Data gap:        {result['data_gap']}")
    print(f"Route note:      {result['route_note']}")
    if result["bag_warning"]:
        print(f"\nBag warning:     {result['bag_warning']}")
    print(f"\nSummary: {result['summary']}")
    print(f"\nData verified: {result['verified_date']}")

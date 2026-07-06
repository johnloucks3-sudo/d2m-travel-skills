#!/usr/bin/env python3
"""
itinerary_optimizer.py — voyage itinerary optimization suggestion engine.
Dreams2Memories Travel, LLC · Thunderbird Wing

Suggests port/timing optimizations for a voyage itinerary based on:
  - seasonal weather favorability by region/month
  - cruise-industry crowd seasonality by region/month + weekend effect
  - nearby alternate ports (drawn from D2M's own booked-voyage port history —
    the practical stand-in for a live competitor-itinerary feed, which does
    not exist yet; see NEARBY_ALTERNATES)
  - accessibility notes passed in by the caller (optional; there is no live
    accessibility database yet — this is the integration seam for one)

None of the weather/crowd data is a live forecast or a live competitor feed.
Every suggestion is tagged CONFIRMED / INFERRED / UNKNOWN per the Pipeline
Integrity confidence-tagging rule. Callers building client-facing copy from
these suggestions must not present INFERRED reasoning as fact (Negative-Space
Rule) — Reyes (A8) / Dani (A3) own that translation, this module only routes
structured suggestions.

Public API:
    optimize(stops: list[PortStop]) -> list[Suggestion]
    load_voyage_from_mirror(booking_id: str) -> list[PortStop]
    load_voyage_from_public_itinerary_json(path) -> list[PortStop]
    stops_from_generic(records: list[dict]) -> list[PortStop]
    write_suggestions(suggestions, out_path) -> Path

CLI:
    python3 core/voyage/itinerary_optimizer.py --booking-id 3096289
    python3 core/voyage/itinerary_optimizer.py --public-itinerary validations/rssc_scrape/SPL260811A_public_itinerary_ports.json
    python3 core/voyage/itinerary_optimizer.py --itinerary-json my_itinerary.json --out output/suggestions.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MIRROR_FILES = [
    ROOT / "cache/sheets_mirror/daily_itinerary.json",
    ROOT / "cache/sheets_mirror/daily_itinerary_a.json",
    ROOT / "cache/sheets_mirror/daily_itinerary_b.json",
    ROOT / "cache/sheets_mirror/daily_itinerary_bucket.json",
]
PORT_WEATHER_MIRROR = ROOT / "cache/sheets_mirror/port_weather.json"
DEFAULT_OUTPUT = ROOT / "output" / "optimization_suggestions.json"

SEA_KEYWORDS = (
    "at sea", "cruising", "day at sea", "sail the", "date line",
    "baltic sea", "caribbean sea", "pacific ocean", "atlantic ocean",
    "straits of florida", "location",
)

# ── port → climate/crowd region ─────────────────────────────────────────────
# Sourced from the ports that actually appear in D2M's booked-voyage itinerary
# mirrors (cache/sheets_mirror/daily_itinerary*.json) and RSSC public scrapes.
# This is the same real port set scripts/port_city_directory_sync.py builds
# its Port_City_Directory tab from — kept independent here to avoid importing
# a module with live Google Sheets side effects into a pure-logic engine.
PORT_REGION: dict[str, str] = {
    # Northern Europe / Baltic
    "stockholm, sweden": "northern_europe",
    "oslo, norway": "northern_europe",
    "kristiansand, norway": "northern_europe",
    "copenhagen, denmark": "northern_europe",
    "berlin (warnemunde), germany": "northern_europe",
    # Mediterranean
    "athens (piraeus)": "mediterranean",
    "valletta": "mediterranean",
    "naples": "mediterranean",
    "rome (civitavecchia)": "mediterranean",
    "tuscany (livorno)": "mediterranean",
    # East Asia (temperate, monsoon-influenced)
    "yokohama (tokyo), japan": "east_asia_temperate",
    "tokyo (harumi), japan": "east_asia_temperate",
    "tokyo, japan": "east_asia_temperate",
    "aomori, japan": "east_asia_temperate",
    "miyako, iwate, japan": "east_asia_temperate",
    # Pacific Northwest / Alaska
    "seattle (washington), usa": "pacific_northwest",
    "seattle (washington), united states of america": "pacific_northwest",
    "seattle, washington": "pacific_northwest",
    "victoria, canada": "pacific_northwest",
    "juneau (alaska), usa": "alaska",
    "ketchikan, usa": "alaska",
    "kodiak island, alaska, usa": "alaska",
    "sitka (alaska), usa": "alaska",
    "wrangell, usa": "alaska",
    # Tropical Pacific
    "honolulu, hawaii": "tropical_pacific",
    # Mexican Riviera (Pacific coast — distinct from Caribbean)
    "los angeles, california": "mexican_riviera",
    "san diego, california": "mexican_riviera",
    "newport beach, california": "mexican_riviera",
    "acapulco, mexico": "mexican_riviera",
    "cabo san lucas, mexico": "mexican_riviera",
    "cabo san lucas": "mexican_riviera",
    "mazatlan, mexico": "mexican_riviera",
    "mazatlan": "mexican_riviera",
    "puerto vallarta, mexico": "mexican_riviera",
    "puerto vallarta": "mexican_riviera",
    # Caribbean / Panama / Central America / Florida embarkation
    "cozumel, mexico": "caribbean",
    "miami, florida": "caribbean",
    "ft. lauderdale, florida": "caribbean",
    "west palm beach, florida": "caribbean",
    "basseterre, st kitts/nevis": "caribbean",
    "charlotte amalie, st. thomas": "caribbean",
    "roseau, dominica": "caribbean",
    "san juan, puerto rico": "caribbean",
    "puerto plata, dominican republic": "caribbean",
    "george town, grand cayman": "caribbean",
    "tortola, british virgin islands": "caribbean",
    "st. john's, antigua": "caribbean",
    "belize city, belize": "caribbean",
    "roatan, honduras": "caribbean",
    "puerto limon, costa rica": "caribbean",
    "puntarenas, costa rica": "caribbean",
    "puerto quetzal, guatemala": "caribbean",
    "cartagena, colombia": "caribbean",
    "colon, panama": "caribbean",
    "panama city (fuerte amador)": "caribbean",
    "panama canal transit": "caribbean",
    "panama canal": "caribbean",
}

# Keyword fallback when a port isn't in PORT_REGION (new/unseen port names).
_REGION_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("sweden", "northern_europe"), ("norway", "northern_europe"),
    ("denmark", "northern_europe"), ("germany", "northern_europe"),
    ("finland", "northern_europe"), ("estonia", "northern_europe"),
    ("italy", "mediterranean"), ("greece", "mediterranean"),
    ("spain", "mediterranean"), ("croatia", "mediterranean"),
    ("malta", "mediterranean"), ("turkey", "mediterranean"),
    ("japan", "east_asia_temperate"),
    ("alaska", "alaska"),
    ("washington", "pacific_northwest"), ("canada", "pacific_northwest"),
    ("hawaii", "tropical_pacific"),
    ("california", "mexican_riviera"), ("mexico", "mexican_riviera"),
    ("florida", "caribbean"), ("panama", "caribbean"), ("caribbean", "caribbean"),
)

DEFAULT_REGION = "temperate_default"

# ── seasonal favorable-weather probability, by region + month (1-12) ───────
# Heuristic climate normals (INFERRED) — not a live forecast. Replace/augment
# with live per-date records in PORT_WEATHER_MIRROR when that feed goes live.
SEASONAL_WEATHER_PROB: dict[str, dict[int, float]] = {
    "northern_europe": {1: .25, 2: .25, 3: .3, 4: .4, 5: .55, 6: .65,
                        7: .7, 8: .65, 9: .5, 10: .35, 11: .25, 12: .2},
    "mediterranean": {1: .35, 2: .35, 3: .45, 4: .55, 5: .65, 6: .78,
                       7: .85, 8: .82, 9: .7, 10: .55, 11: .4, 12: .35},
    "east_asia_temperate": {1: .4, 2: .4, 3: .55, 4: .7, 5: .7, 6: .4,
                             7: .38, 8: .45, 9: .5, 10: .68, 11: .68, 12: .45},
    "caribbean": {1: .75, 2: .78, 3: .78, 4: .75, 5: .6, 6: .5,
                  7: .5, 8: .48, 9: .42, 10: .45, 11: .55, 12: .72},
    "mexican_riviera": {1: .7, 2: .72, 3: .72, 4: .7, 5: .6, 6: .5,
                        7: .45, 8: .45, 9: .42, 10: .5, 11: .6, 12: .68},
    "pacific_northwest": {1: .25, 2: .3, 3: .35, 4: .4, 5: .5, 6: .6,
                          7: .68, 8: .65, 9: .5, 10: .35, 11: .25, 12: .2},
    "alaska": {1: .15, 2: .15, 3: .2, 4: .3, 5: .45, 6: .55,
               7: .58, 8: .5, 9: .35, 10: .2, 11: .15, 12: .12},
    "tropical_pacific": {m: .68 for m in range(1, 13)},
    "temperate_default": {m: .45 for m in range(1, 13)},
}
WEATHER_ALERT_THRESHOLD = 0.30  # below this, flag + look for an alternative

# ── cruise-industry crowd seasonality, by region + month ───────────────────
# "peak" / "shoulder" / "off" — general published cruise-season patterns
# (INFERRED). Caribbean/Panama peak is northern-hemisphere winter escape
# season; Baltic/Med/Alaska/Japan peaks are northern-hemisphere summer +
# shoulder bloom/foliage windows.
CROWD_CALENDAR: dict[str, dict[int, str]] = {
    "northern_europe": {6: "peak", 7: "peak", 8: "peak", 5: "shoulder", 9: "shoulder"},
    "mediterranean": {7: "peak", 8: "peak", 6: "shoulder", 9: "shoulder", 5: "shoulder", 10: "shoulder"},
    "east_asia_temperate": {4: "peak", 10: "peak", 11: "peak", 3: "shoulder", 5: "shoulder"},
    "caribbean": {12: "peak", 1: "peak", 2: "peak", 3: "peak", 11: "shoulder", 4: "shoulder"},
    "mexican_riviera": {12: "peak", 1: "peak", 2: "peak", 3: "shoulder", 11: "shoulder"},
    "pacific_northwest": {6: "peak", 7: "peak", 8: "peak"},
    "alaska": {6: "peak", 7: "peak", 8: "shoulder", 5: "shoulder"},
    "tropical_pacific": {12: "peak", 1: "peak", 6: "shoulder", 7: "shoulder"},
}


def crowd_level(region: str, month: int) -> str:
    return CROWD_CALENDAR.get(region, {}).get(month, "off")


def weather_probability(region: str, month: int) -> float:
    table = SEASONAL_WEATHER_PROB.get(region, SEASONAL_WEATHER_PROB[DEFAULT_REGION])
    return table.get(month, 0.45)


# ── nearby alternate ports, by region ───────────────────────────────────────
# Built from D2M's own booked-voyage port history (the real, if narrow,
# stand-in for a live competitor-itinerary feed). A port is never offered as
# its own alternative.
NEARBY_ALTERNATES: dict[str, list[str]] = {
    "northern_europe": ["Stockholm, Sweden", "Copenhagen, Denmark", "Oslo, Norway",
                         "Kristiansand, Norway", "Berlin (Warnemunde), Germany"],
    "mediterranean": ["Naples", "Rome (Civitavecchia)", "Valletta", "Tuscany (Livorno)"],
    "caribbean": ["Cozumel, Mexico", "George Town, Grand Cayman", "Roatan, Honduras",
                  "Puerto Limon, Costa Rica"],
    "mexican_riviera": ["Cabo San Lucas", "Puerto Vallarta", "Mazatlan"],
    "east_asia_temperate": ["Yokohama (Tokyo), Japan", "Tokyo, Japan", "Aomori, Japan"],
    "alaska": ["Juneau (Alaska), USA", "Ketchikan, USA", "Sitka (Alaska), USA"],
}


def classify_region(port: str) -> str:
    key = " ".join(port.strip().lower().split())
    if key in PORT_REGION:
        return PORT_REGION[key]
    for kw, region in _REGION_KEYWORDS:
        if kw in key:
            return region
    return DEFAULT_REGION


def is_sea_day(port: str) -> bool:
    p = port.strip().lower()
    if not p:
        return True
    return any(kw in p for kw in SEA_KEYWORDS)


# ── data model ───────────────────────────────────────────────────────────

@dataclass
class PortStop:
    port: str
    call_date: date
    region: str = ""
    booking_id: str = ""
    day_number: str = ""
    arrive: str = ""
    depart: str = ""
    at_sea: bool = False

    def __post_init__(self):
        if not self.region:
            self.region = classify_region(self.port)
        if not self.at_sea:
            self.at_sea = is_sea_day(self.port)


@dataclass
class PortCall:
    """One or more consecutive PortStop days at the same port (an overnight stay)."""
    port: str
    region: str
    dates: list
    booking_id: str = ""


@dataclass
class Suggestion:
    booking_id: str
    port: str
    date: str
    issue: str          # "weather" | "crowd"
    alternative: str
    reasoning: str
    confidence: str     # CONFIRMED | INFERRED | UNKNOWN
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


# ── date parsing ────────────────────────────────────────────────────────

_DATE_FORMATS_WITH_YEAR = (
    "%Y-%m-%d", "%d-%b-%y", "%d-%b-%Y", "%B %d, %Y", "%b %d, %Y", "%b %d, %y",
)
_DATE_FORMATS_NO_YEAR = ("%b %d", "%B %d")


def parse_flexible_date(raw: str, default_year: int | None = None) -> date | None:
    """Parse the mixed date formats found across the voyage mirror/scrape sources."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    for fmt in _DATE_FORMATS_WITH_YEAR:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    if default_year is not None:
        for fmt in _DATE_FORMATS_NO_YEAR:
            try:
                parsed = datetime.strptime(f"{raw} {default_year}", f"{fmt} %Y").date()
                return parsed
            except ValueError:
                continue
    return None


def _infer_default_year(raw_dates: list) -> int | None:
    years = []
    for raw in raw_dates:
        d = parse_flexible_date(raw)
        if d:
            years.append(d.year)
    if not years:
        return None
    return Counter(years).most_common(1)[0][0]


# ── loaders / adapters ──────────────────────────────────────────────────

def stops_from_generic(records: list[dict], booking_id: str = "",
                        fallback_year: int | None = None) -> list[PortStop]:
    """Build PortStops from a generic itinerary schema.

    Accepts any of these key spellings per record: port/city/Port_Location,
    date/Date, arrive/Arrive, depart/Depart, day_number/Day_Number, atSea/at_sea.
    """
    raw_dates = [
        str(r.get("date") or r.get("Date") or "") for r in records
    ]
    default_year = _infer_default_year(raw_dates) or fallback_year

    stops: list[PortStop] = []
    seen: set = set()
    for r in records:
        port = str(r.get("port") or r.get("city") or r.get("Port_Location") or "").strip()
        raw_date = str(r.get("date") or r.get("Date") or "").strip()
        parsed = parse_flexible_date(raw_date, default_year)
        if parsed is None:
            continue
        if not port:
            continue
        dedupe_key = (booking_id, port.lower(), parsed)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        stops.append(PortStop(
            port=port,
            call_date=parsed,
            booking_id=str(r.get("Booking_ID") or booking_id or ""),
            day_number=str(r.get("day_number") or r.get("Day_Number") or ""),
            arrive=str(r.get("arrive") or r.get("Arrive") or ""),
            depart=str(r.get("depart") or r.get("Depart") or ""),
            at_sea=bool(r.get("atSea") or r.get("at_sea") or False),
        ))
    stops.sort(key=lambda s: s.call_date)
    return stops


def load_voyage_from_mirror(booking_id: str) -> list[PortStop]:
    """Pull one voyage's port calls from D2M's own daily-itinerary mirror files."""
    records = []
    for fp in MIRROR_FILES:
        if not fp.exists():
            continue
        try:
            data = json.loads(fp.read_text())
        except Exception:
            continue
        for r in data.get("records", []):
            if str(r.get("Booking_ID", "")).strip() == booking_id:
                records.append(r)
    return stops_from_generic(records, booking_id=booking_id)


_VOYAGE_CODE_DATE_RE = re.compile(r"(\d{2})(\d{2})(\d{2})")


def load_voyage_from_public_itinerary_json(path) -> list[PortStop]:
    """Load the RSSC public-scrape itinerary schema: {day,date,city,country,atSea,arrive,depart}.

    These records carry dates like "Aug 11" with no year. RSSC voyage codes embed
    the sailing date (e.g. SPL260811A -> 26-08-11), so fall back to that when no
    record in the itinerary supplies a full year.
    """
    path = Path(path)
    data = json.loads(path.read_text())
    voyage = data.get("voyage", "")
    records = data.get("itinerary", [])
    default_year = None
    m = _VOYAGE_CODE_DATE_RE.search(voyage)
    if m:
        default_year = 2000 + int(m.group(1))
    return stops_from_generic(records, booking_id=voyage, fallback_year=default_year)


def load_port_weather_overrides() -> dict[tuple, float]:
    """Live per-port/date weather probabilities, if the mirror has been populated.

    Returns {(port_lower, iso_date): probability}. Empty dict when the feed
    (cache/sheets_mirror/port_weather.json) has no records yet — the normal
    case today (see the module docstring).
    """
    if not PORT_WEATHER_MIRROR.exists():
        return {}
    try:
        data = json.loads(PORT_WEATHER_MIRROR.read_text())
    except Exception:
        return {}
    overrides = {}
    for r in data.get("records", []):
        port = str(r.get("port") or r.get("Port") or "").strip().lower()
        d = str(r.get("date") or r.get("Date") or "").strip()
        prob = r.get("good_weather_probability")
        if port and d and prob is not None:
            overrides[(port, d)] = float(prob)
    return overrides


# ── grouping ─────────────────────────────────────────────────────────────

def group_into_port_calls(stops: list[PortStop]) -> list[PortCall]:
    """Group consecutive same-port days into a single call (captures overnights)."""
    calls: list[PortCall] = []
    current: PortCall | None = None
    for stop in sorted(stops, key=lambda s: s.call_date):
        if stop.at_sea:
            current = None
            continue
        same_port = current is not None and current.port.lower() == stop.port.lower()
        adjacent = same_port and (stop.call_date - current.dates[-1]).days <= 1
        if adjacent:
            current.dates.append(stop.call_date)
        else:
            current = PortCall(port=stop.port, region=stop.region,
                                dates=[stop.call_date], booking_id=stop.booking_id)
            calls.append(current)
    return calls


# ── optimization logic ──────────────────────────────────────────────────

def _weekday_alternate_day(call: PortCall) -> date | None:
    """Within a multi-day call, find a weekday (Mon-Thu) day if the call also
    includes a weekend day — the lower-crowd day to route flexible/must-do
    activities to."""
    if len(call.dates) < 2:
        return None
    weekdays = [d for d in call.dates if d.weekday() < 4]   # Mon=0 .. Thu=3
    weekends = [d for d in call.dates if d.weekday() >= 4]  # Fri, Sat, Sun
    if weekdays and weekends:
        return weekdays[0]
    return None


def _best_alternate_port(region: str, exclude_port: str, month: int,
                          want: str) -> str | None:
    """want: 'weather' -> pick the region alternate with the highest weather
    probability for the month; 'crowd' -> pick one whose crowd level for the
    month isn't 'peak'."""
    candidates = [p for p in NEARBY_ALTERNATES.get(region, [])
                  if p.lower() != exclude_port.lower()]
    if not candidates:
        return None
    if want == "weather":
        return max(candidates, key=lambda p: weather_probability(classify_region(p), month))
    for p in candidates:
        if crowd_level(classify_region(p), month) != "peak":
            return p
    return None


def optimize(stops: list[PortStop]) -> list[Suggestion]:
    """Generate optimization suggestions for a voyage's port stops."""
    if not stops:
        return []
    booking_id = stops[0].booking_id
    weather_overrides = load_port_weather_overrides()
    suggestions: list[Suggestion] = []

    for call in group_into_port_calls(stops):
        anchor_date = call.dates[0]
        month = anchor_date.month
        iso = anchor_date.isoformat()

        # ── weather check ──
        override = weather_overrides.get((call.port.lower(), iso))
        if override is not None:
            prob, confidence, source = override, "CONFIRMED", "port_weather live feed"
        else:
            prob = weather_probability(call.region, month)
            confidence, source = "INFERRED", f"seasonal climate normal ({call.region}, month {month})"

        if prob < WEATHER_ALERT_THRESHOLD:
            alt = _best_alternate_port(call.region, call.port, month, "weather")
            if alt:
                alt_prob = weather_probability(classify_region(alt), month)
                suggestions.append(Suggestion(
                    booking_id=booking_id, port=call.port, date=iso, issue="weather",
                    alternative=alt,
                    reasoning=(f"{call.port} carries roughly a {prob:.0%} chance of favorable "
                               f"weather in month {month}; {alt} runs closer to {alt_prob:.0%} "
                               f"for the same window."),
                    confidence=confidence, source=source,
                ))
            else:
                suggestions.append(Suggestion(
                    booking_id=booking_id, port=call.port, date=iso, issue="weather",
                    alternative="none identified — recommend flexible outdoor plan / travel insurance review",
                    reasoning=(f"{call.port} carries roughly a {prob:.0%} chance of favorable "
                               f"weather in month {month}; no region alternate is on file."),
                    confidence=confidence, source=source,
                ))

        # ── crowd check ──
        # The weekend-congestion nudge is orthogonal to whole-season crowd level:
        # a multi-day call spanning a weekend draws heavier local + day-tripper
        # traffic on the weekend day regardless of whether the month overall is
        # peak or just shoulder — so it fires on either. The alternate-port /
        # "none identified" fallbacks are a whole-season concern and stay
        # peak-only.
        level = crowd_level(call.region, month)
        weekday_alt_date = _weekday_alternate_day(call) if level in ("peak", "shoulder") else None
        if weekday_alt_date:
            suggestions.append(Suggestion(
                booking_id=booking_id, port=call.port, date=iso, issue="crowd",
                alternative=f"shift flexible/must-do activities to {weekday_alt_date.isoformat()}",
                reasoning=(f"{call.port} is in {level} cruise season for month {month}; "
                           f"this call spans a weekend day. {weekday_alt_date.strftime('%A')} "
                           f"({weekday_alt_date.isoformat()}) is the weekday day in the same "
                           f"stay and typically sees lower combined ship + local-tourism traffic."),
                confidence="INFERRED",
                source=f"cruise-industry seasonal crowd pattern ({call.region}, month {month})",
            ))
        elif level == "peak":
            alt = _best_alternate_port(call.region, call.port, month, "crowd")
            if alt:
                suggestions.append(Suggestion(
                    booking_id=booking_id, port=call.port, date=iso, issue="crowd",
                    alternative=alt,
                    reasoning=(f"{call.port} is in peak cruise season for month {month}. "
                               f"{alt} is a region port not flagged peak for the same window."),
                    confidence="INFERRED",
                    source=f"cruise-industry seasonal crowd pattern ({call.region}, month {month})",
                ))
            else:
                suggestions.append(Suggestion(
                    booking_id=booking_id, port=call.port, date=iso, issue="crowd",
                    alternative="none identified — recommend earliest-morning or last-departure excursion slots",
                    reasoning=(f"{call.port} is in peak cruise season for month {month}; "
                               f"the whole region runs peak in this window, so no region "
                               f"alternate is off-peak either."),
                    confidence="INFERRED",
                    source=f"cruise-industry seasonal crowd pattern ({call.region}, month {month})",
                ))

    return suggestions


def check_accessibility(stops: list[PortStop], client_notes: str = "") -> list[Suggestion]:
    """Optional accessibility pass. There is no live accessibility database yet —
    this is the integration seam for one (Reyes/A8 domain). Returns UNKNOWN-tagged
    suggestions only when the caller supplies notes; otherwise returns nothing
    rather than fabricating a concern (Negative-Space Rule)."""
    if not client_notes:
        return []
    notes_lower = client_notes.lower()
    mobility_flag = any(kw in notes_lower for kw in ("wheelchair", "mobility", "walker", "cane"))
    if not mobility_flag:
        return []
    booking_id = stops[0].booking_id if stops else ""
    out = []
    for call in group_into_port_calls(stops):
        out.append(Suggestion(
            booking_id=booking_id, port=call.port, date=call.dates[0].isoformat(),
            issue="accessibility",
            alternative="route to Reyes (A8) for tender/accessibility confirmation before booking excursions",
            reasoning="Client notes flag a mobility consideration; port-level tender/accessibility "
                      "status is not in a live database yet and must be confirmed by hand.",
            confidence="UNKNOWN",
            source="client notes (caller-supplied) — no accessibility database wired in",
        ))
    return out


# ── output ───────────────────────────────────────────────────────────────

def write_suggestions(suggestions: list[Suggestion], out_path=DEFAULT_OUTPUT) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suggestion_count": len(suggestions),
        "suggestions": [s.to_dict() for s in suggestions],
    }
    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Voyage itinerary optimization suggestions")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--booking-id", help="Booking ID to pull from cache/sheets_mirror")
    group.add_argument("--public-itinerary", help="Path to an RSSC-style public itinerary JSON")
    group.add_argument("--itinerary-json", help="Path to a generic {records:[...]} or [...] itinerary JSON")
    parser.add_argument("--client-notes", default="", help="Optional free-text accessibility notes")
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    if args.booking_id:
        stops = load_voyage_from_mirror(args.booking_id)
    elif args.public_itinerary:
        stops = load_voyage_from_public_itinerary_json(args.public_itinerary)
    else:
        raw = json.loads(Path(args.itinerary_json).read_text())
        records = raw.get("records", raw) if isinstance(raw, dict) else raw
        stops = stops_from_generic(records)

    suggestions = optimize(stops)
    suggestions += check_accessibility(stops, args.client_notes)
    out = write_suggestions(suggestions, args.out)
    print(f"{len(stops)} port stop(s) analyzed. Wrote {len(suggestions)} suggestion(s) to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
CI TRINITY — Leg 1: Cruise Link Resolver
Maps (cruise_line, ship_name, departure_date) → external booking/itinerary URL

Supports 6 priority luxury lines: Regent, Silversea, Viking, Crystal, Atlas, Explora.
Primary source: CruiseMapper (universal ship-level pages).
Tier 2: line-specific search/deep links where patterns exist.

Usage:
    from link_resolver import resolve_sailing, resolve_ship_url
    
    url = resolve_sailing("Silversea Cruises", "Silver Nova", "2026-08-15")
    # → "https://www.cruisemapper.com/ships/silver-nova?date=2026-08-15"
    
    url = resolve_ship_url("Regent Seven Seas Cruises", "Seven Seas Explorer")
    # → "https://www.cruisemapper.com/ships/seven-seas-explorer"
"""

import re
from datetime import datetime
from typing import Optional

# ── Ship slug maps ──────────────────────────────────────────────────────────
# CruiseMapper uses lowercase-hyphenated ship names.
# Most are auto-derivable from the name, but some need manual overrides.

SHIP_SLUG_OVERRIDES: dict[str, str] = {
    # Atlas
    "World Traveller": "world-traveller",
    "World Navigator": "world-navigator",
    "World Voyager": "world-voyager",
    # Crystal
    "Crystal Serenity": "crystal-serenity",
    "Crystal Symphony": "crystal-symphony",
    "Crystal Endeavor": "crystal-endeavor",
    "Crystal Esprit": "crystal-esprit",
    "National Geographic Islander 2": "national-geographic-islander",
    "SS Elisabeth": "ss-elisabeth",
    "SS Victoria": "ss-victoria",
    "Scenic Eclipse": "scenic-eclipse",
    # Explora
    "EXPLORA I": "explora-i",
    "EXPLORA II": "explora-ii",
    "EXPLORA III": "explora-iii",
    "EXPLORA IV": "explora-iv",
    "EXPLORA V": "explora-v",
    "MSC Explora 1": "explora-i",
    "MSC Explora 2": "explora-ii",
    "MSC Explora 3": "explora-iii",
    "MSC Explora 4": "explora-iv",
    "MSC Explora 5": "explora-v",
    # Regent
    "Seven Seas Explorer": "seven-seas-explorer",
    "Seven Seas Grandeur": "seven-seas-grandeur",
    "Seven Seas Splendor": "seven-seas-splendor",
    "Seven Seas Voyager": "seven-seas-voyager",
    "Seven Seas Mariner": "seven-seas-mariner",
    "Seven Seas Navigator": "seven-seas-navigator",
    "Seven Seas Prestige": "seven-seas-prestige",
    "Regent Seven": "seven-seas-splendor",  # likely alias
    # Silversea
    "Silver Nova": "silver-nova",
    "Silver Ray": "silver-ray",
    "Silver Muse": "silver-muse",
    "Silver Moon": "silver-moon",
    "Silver Dawn": "silver-dawn",
    "Silver Spirit": "silver-spirit",
    "Silver Shadow": "silver-shadow",
    "Silver Whisper": "silver-whisper",
    "Silver Cloud": "silver-cloud",
    "Silver Wind": "silver-wind",
    "Silver Wind Expedition": "silver-wind",
    "Silver Origin": "silver-origin",
    "Silver Endeavour": "silver-endeavour",
    "ms La Belle des Oceans": "silver-nova",  # SG/agency forwarder name
    "ms La Belle de l'Adriatique": "silver-moon",  # ditto
    # Viking (Ocean)
    "Viking Star": "viking-star",
    "Viking Sea": "viking-sea",
    "Viking Sky": "viking-sky",
    "Viking Sun": "viking-sun",
    "Viking Orion": "viking-orion",
    "Viking Jupiter": "viking-jupiter",
    "Viking Venus": "viking-venus",
    "Viking Mars": "viking-mars",
    "Viking Neptune": "viking-neptune",
    "Viking Saturn": "viking-saturn",
    "Viking Vela": "viking-vela",
    "Viking Mira": "viking-mira",
    "Viking Libra": "viking-libra",
    "Viking Astrea": "viking-astrea",
    "Viking Vesta": "viking-vesta",
    "Viking Octantis": "viking-octantis",
    "Viking Polaris": "viking-polaris",
}

# ── Cruise line → URL builder pattern ──────────────────────────────────────

def _slugify(name: str) -> str:
    """Convert ship name to CruiseMapper slug."""
    name = name.strip()
    # Check overrides first
    if name in SHIP_SLUG_OVERRIDES:
        return SHIP_SLUG_OVERRIDES[name]
    # Auto-slugify: lowercase, replace spaces/special chars with hyphens
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def resolve_ship_url(line: str, ship: str) -> str:
    """
    Return the best known URL for a cruise ship's itinerary/overview page.
    
    Primary: CruiseMapper ship profile.
    Fallback: Google search URL.
    """
    slug = _slugify(ship)
    # CruiseMapper — reliable for all ships
    cm_url = f"https://www.cruisemapper.com/ships/{slug}"
    return cm_url


def resolve_sailing(
    line: str,
    ship: str,
    departure: Optional[str] = None,
    voyage_code: Optional[str] = None,
    destination: Optional[str] = None,
    from_port: Optional[str] = None,
    nights: Optional[int] = None,
) -> dict:
    """
    Resolve the best external URL for a specific sailing.

    Returns dict with:
        - url:         The recommended URL (str)
        - label:       Human-readable link text (str)
        - source:      Source of the URL ('cruisemapper', 'deep_link', 'search')
        - ship_url:    CruiseMapper ship profile URL
        - line_url:    Cruise line homepage
    """
    slug = _slugify(ship)
    cm_ship_url = f"https://www.cruisemapper.com/ships/{slug}"

    # Build date anchor for CruiseMapper
    date_fragment = ""
    if departure:
        try:
            dt = datetime.strptime(departure[:10], "%Y-%m-%d")
            date_fragment = f"?date={dt.strftime('%Y-%m-%d')}"
        except ValueError:
            pass

    # CruiseMapper as universal fallback
    cm_sailing_url = cm_ship_url + date_fragment

    # Try line-specific deep link
    deep_link = _try_deep_link(line, ship, departure, voyage_code)

    result = {
        "url": deep_link["url"] if deep_link else cm_sailing_url,
        "label": deep_link["label"] if deep_link else f"View on CruiseMapper",
        "source": deep_link["source"] if deep_link else "cruisemapper",
        "ship_url": cm_ship_url,
        "line_url": LINE_HOMEPAGES.get(_normalize_line(line), ""),
    }

    if deep_link:
        result["alt_url"] = cm_sailing_url
        result["alt_label"] = f"CruiseMapper: {ship}"

    return result


def resolve_all_sailings(records: list[dict]) -> list[dict]:
    """
    Batch-resolve URLs for a list of sailing records (mutates in place).
    Expects each record to have keys: 'line', 'ship', 'departure'.
    Adds keys: 'booking_url', 'booking_label', 'booking_source', 'ship_url', 'line_url'
    """
    for r in records:
        resolved = resolve_sailing(
            line=r.get("line", ""),
            ship=r.get("ship", ""),
            departure=r.get("departure"),
            voyage_code=r.get("voyage_code"),
            destination=r.get("destination"),
            from_port=r.get("from_port"),
            nights=r.get("nights"),
        )
        r["booking_url"] = resolved["url"]
        r["booking_label"] = resolved["label"]
        r["booking_source"] = resolved["source"]
        r["ship_url"] = resolved["ship_url"]
        r["line_url"] = resolved["line_url"]
    return records


# ── Line-specific deep links ────────────────────────────────────────────────

LINE_HOMEPAGES: dict[str, str] = {
    "regent seven seas cruises": "https://www.rssc.com",
    "silversea cruises":        "https://www.silversea.com",
    "viking":                   "https://www.vikingcruises.com",
    "crystal cruises":          "https://www.crystalcruises.com",
    "atlas ocean voyages":      "https://www.atlasoceanvoyages.com",
    "explora journeys":         "https://www.explorajourneys.com",
    "seabourn":                 "https://www.seabourn.com",
    "oceania cruises":          "https://www.oceaniacruises.com",
    "cunard":                   "https://www.cunard.com",
    "ponant":                   "https://www.ponant.com",
    "windstar cruises":         "https://www.windstarcruises.com",
    "azamara":                  "https://www.azamara.com",
    "ambassador cruise line":   "https://www.ambassadorcruiseline.com",
    "aurora expeditions":       "https://www.auroraexpeditions.com.au",
    "celestyal cruises":        "https://www.celestyal.com",
    "emerald cruises":          "https://www.emeraldcruises.com",
    "fred. olsen cruise lines": "https://www.fredolsencruises.com",
    "hapag-lloyd cruises":      "https://www.hl-cruises.com",
    "hurtigruten":              "https://www.hurtigruten.com",
    "lindblad expeditions":     "https://www.expeditions.com",
    "paul gauguin cruises":     "https://www.pgcruises.com",
    "quark expeditions":        "https://www.quarkexpeditions.com",
    "ritz-carlton yacht collection": "https://www.ritzcarltonyachtcollection.com",
    "saga cruises":             "https://www.saga.co.uk",
    "scenic":                   "https://www.scenic.com",
    "seadream yacht club":      "https://www.seadream.com",
    "star clippers":            "https://www.starclippers.com",
    "hx expeditions":           "https://www.hx.com",
    "explora journeys":         "https://www.explorajourneys.com",
}


def _normalize_line(line: str) -> str:
    """Normalize cruise line name to lowercase for lookup."""
    return line.strip().lower()


def _try_deep_link(line: str, ship: str, departure: Optional[str], voyage_code: Optional[str]) -> Optional[dict]:
    """
    Attempt to build a line-specific deep link.
    Returns dict with {url, label, source} or None if no pattern matches.
    """
    nline = _normalize_line(line)
    slug = _slugify(ship)
    year = departure[:4] if departure and len(departure) >= 4 else ""

    # ── Regent Seven Seas ───────────────────────────────────────────────────
    if "regent" in nline:
        # RSSC uses: https://www.rssc.com/ships/{ship-name}/deals?date=YYYY-MM-DD
        if departure and year:
            return {
                "url": f"https://www.rssc.com/ships/{slug}/deals?date={departure[:10]}",
                "label": f"Regent: {departure[:10]}",
                "source": "deep_link",
            }
        return {
            "url": f"https://www.rssc.com/ships/{slug}",
            "label": "Regent: View Ship & Sailings",
            "source": "deep_link",
        }

    # ── Silversea ───────────────────────────────────────────────────────────
    if "silversea" in nline:
        # Silversea needs voyage code: https://www.silversea.com/voyages/{voyage_code}.html
        if voyage_code:
            vc = voyage_code.strip()
            return {
                "url": f"https://www.silversea.com/voyages/{vc}.html",
                "label": f"Silversea: Voyage {vc}",
                "source": "deep_link",
            }
        # Fallback: ship page
        return {
            "url": f"https://www.silversea.com/ships/{slug}.html",
            "label": "Silversea: View Ship",
            "source": "deep_link",
        }

    # ── Viking ──────────────────────────────────────────────────────────────
    if "viking" in nline:
        # Viking uses: https://www.vikingcruises.com/oceans/ships/{ship-slug}.html
        return {
            "url": f"https://www.vikingcruises.com/oceans/ships/{slug}.html",
            "label": "Viking: View Ship & Itineraries",
            "source": "deep_link",
        }

    # ── Crystal ─────────────────────────────────────────────────────────────
    if "crystal" in nline:
        return {
            "url": f"https://www.crystalcruises.com/ships/{slug}",
            "label": "Crystal: View Ship",
            "source": "deep_link",
        }

    # ── Atlas Ocean ─────────────────────────────────────────────────────────
    if "atlas" in nline:
        return {
            "url": f"https://www.atlasoceanvoyages.com/ships/{slug}",
            "label": "Atlas: View Ship & Voyages",
            "source": "deep_link",
        }

    # ── Explora Journeys ────────────────────────────────────────────────────
    if "explora" in nline:
        return {
            "url": f"https://www.explorajourneys.com/ships/{slug}",
            "label": "Explora: View Ship",
            "source": "deep_link",
        }

    return None


# ── CLI entry point ─────────────────────────────────────────────────────────

def main():
    import sys
    args = sys.argv[1:]
    if not args:
        print("link_resolver.py <line> <ship> [departure]")
        print()
        print("Examples:")
        print("  python3 scripts/link_resolver.py 'Silversea Cruises' 'Silver Nova' 2026-08-15")
        print("  python3 scripts/link_resolver.py 'Regent Seven Seas Cruises' 'Seven Seas Explorer'")
        print("  python3 scripts/link_resolver.py --list-ships")
        return

    if args[0] == "--list-ships":
        print("Known ship slugs:")
        for name in sorted(SHIP_SLUG_OVERRIDES.keys()):
            print(f"  {name:40s} → {SHIP_SLUG_OVERRIDES[name]}")
        return

    line = args[0]
    ship = args[1]
    departure = args[2] if len(args) > 2 else None
    result = resolve_sailing(line, ship, departure)
    print(f"  URL:    {result['url']}")
    print(f"  Label:  {result['label']}")
    print(f"  Source: {result['source']}")
    if result.get("alt_url"):
        print(f"  Alt:    {result['alt_url']}")
    print(f"  Ship:   {result['ship_url']}")
    print(f"  Line:   {result['line_url']}")


if __name__ == "__main__":
    main()

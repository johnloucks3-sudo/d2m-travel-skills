#!/usr/bin/env python3
"""
VTG Intel Splitter — reads vtg_structured_*.txt, writes per-line JSON files.

Outputs (date-stamped to today):
  intel/regent_vtg_YYYYMMDD.json
  intel/silversea_vtg_YYYYMMDD.json
  intel/atlas_vtg_YYYYMMDD.json

Run manually after a new VTG email blast is parsed, or via ExecStartPre in cruise-db-refresh.service.
"""
import json, re, sys
from datetime import datetime
from pathlib import Path

ROOT     = Path("/home/john/Thunderbird")
INTEL    = ROOT / "intel"
TODAY    = datetime.now().strftime("%Y%m%d")

# Target lines and their output file stems
TARGET_LINES = {
    "Regent Seven Seas Cruises": "regent",
    "Silversea Cruises":         "silversea",
    "Atlas Ocean Voyages":       "atlas",
}

LINE_CANONICAL = {
    "Regent":              "Regent Seven Seas Cruises",
    "Silversea":           "Silversea Cruises",
    "Atlas Ocean Voyages": "Atlas Ocean Voyages",
    "Atlas":               "Atlas Ocean Voyages",
}

REGION_MAP = [
    ("Mediterranean",  ["mediterranean","athens","piraeus","rome","civitavecchia","barcelona",
                        "lisbon","valletta","venice","istanbul","dubrovnik","marseille",
                        "palma","naples","sicily","malaga","santorini","mykonos","split",
                        "monte carlo","monaco","nice","cannes","genoa","florence","tunisia"]),
    ("Caribbean",      ["caribbean","miami","san juan","barbados","st thomas","st maarten",
                        "aruba","curacao","grenada","antigua","martinique","guadeloupe",
                        "nassau","havana","montego bay","ocho rios","bridgetown"]),
    ("Northern Europe",["norway","bergen","fjord","helsinki","stockholm","copenhagen",
                        "amsterdam","hamburg","tallinn","riga","vilnius","gdansk",
                        "kiel","warnemunde","bremerhaven","southampton","dover","edinburgh"]),
    ("Alaska",         ["alaska","juneau","ketchikan","sitka","glacier bay","skagway","seward","anchorage"]),
    ("South America",  ["buenos aires","rio de janeiro","montevideo","valparaiso","ushuaia",
                        "cartagena","lima","callao","amazon","brazil","argentina","chile","peru"]),
    ("Asia Pacific",   ["tokyo","osaka","hong kong","singapore","shanghai","beijing","taipei",
                        "seoul","busan","sydney","melbourne","auckland","bali","phuket",
                        "vietnam","cambodia","indonesia","japan","china","south korea"]),
    ("Middle East",    ["dubai","abu dhabi","muscat","doha","bahrain","oman","uae","egypt",
                        "petra","jordan","israel","tel aviv","haifa","aqaba","suez"]),
    ("Indian Ocean",   ["maldives","mauritius","seychelles","reunion","madagascar","zanzibar",
                        "mumbai","colombo","sri lanka","india"]),
]

def infer_region(route: str) -> str:
    r = route.lower()
    for region, kws in REGION_MAP:
        if any(k in r for k in kws):
            return region
    return "World"


def parse_vtg_file(path: Path) -> list[dict]:
    line_names = ["Regent", "Silversea", "Explora Journeys", "Atlas Ocean Voyages",
                  "Atlas", "Paul Gauguin", "Ponant"]
    ln_pat = '|'.join(re.escape(l) for l in line_names)
    row_re = re.compile(
        r'^#(\d+)\s+(\d+)\s+(.+?)\s+(' + ln_pat + r')\s*/\s*(.+?)\s+'
        r'(?:5\.5|6)\s+\$([0-9,]+)\s+\$([0-9,]+)\s+(\d+)%\s+(.+)$'
    )
    scraped = TODAY
    # Try to read scraped date from file header
    with open(path) as f:
        for raw in f:
            m = re.search(r'(\d{4}-\d{2}-\d{2})', raw)
            if m:
                scraped = m.group(1).replace("-", "")
                break

    deals = []
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or not line.startswith('#') or not line[1:2].isdigit():
                continue
            m = row_re.match(line)
            if not m:
                continue
            fdeal, nights, before, ln, ship, orig, disc, pct, status = m.groups()
            canonical = LINE_CANONICAL.get(ln, ln)
            # Only keep target lines
            if canonical not in TARGET_LINES:
                continue
            dm = re.match(r'^(\w{3}\s+\d+(?:,\s*\d{4})?)\s*(.*)', before.strip())
            date_str = dm.group(1) if dm else ''
            route    = dm.group(2).strip() if dm else before.strip()
            yr_m = re.search(r'(\d{4})', date_str)
            year = int(yr_m.group(1)) if yr_m else 2026
            try:
                clean = re.sub(r',\s*\d{4}', '', date_str).strip()
                d = datetime.strptime(f"{clean} {year}", "%b %d %Y")
                iso_date = d.strftime("%Y-%m-%d")
            except Exception:
                iso_date = ''
            source_key = TARGET_LINES[canonical] + "_vtg"
            deals.append({
                "line":       canonical,
                "ship":       ship.strip(),
                "departure":  iso_date,
                "date_str":   date_str,
                "nights":     int(nights),
                "from_port":  route[:40],
                "to_port":    "",
                "route":      route,
                "region":     infer_region(route),
                "price_disc": int(disc.replace(",", "")),
                "price_orig": int(orig.replace(",", "")),
                "discount":   int(pct),
                "suite":      "Suite" in status,
                "vtg_fd":     fdeal,
                "sources":    [source_key],
                "scraped":    scraped[:4] + "-" + scraped[4:6] + "-" + scraped[6:] if len(scraped) == 8 else scraped,
            })
    return deals


def find_latest_vtg_file() -> Path | None:
    candidates = sorted(INTEL.glob("vtg_structured_*.txt"), reverse=True)
    return candidates[0] if candidates else None


def main():
    vtg_file = find_latest_vtg_file()
    if not vtg_file:
        print("ERROR: No vtg_structured_*.txt found in intel/", file=sys.stderr)
        sys.exit(1)

    print(f"Reading {vtg_file.name}…")
    all_deals = parse_vtg_file(vtg_file)
    print(f"  {len(all_deals)} target-line records parsed")

    by_line = {}
    for d in all_deals:
        by_line.setdefault(d["line"], []).append(d)

    for canonical, stem in TARGET_LINES.items():
        records = by_line.get(canonical, [])
        out_path = INTEL / f"{stem}_vtg_{TODAY}.json"
        out_path.write_text(json.dumps(records, indent=2))
        print(f"  → {out_path.name}  ({len(records)} records)")

    print("Done.")


if __name__ == "__main__":
    main()

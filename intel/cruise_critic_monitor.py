#!/usr/bin/env python3
"""
Cruise Critic & voyage feedback monitor — MISSION-372
Scrapes recent reviews/intel for D2M's 3 active ships using Serper API.
Run weekly (or on-demand before client touchpoints).

Ships monitored:
  - Regent Seven Seas Grandeur (Aug 2026, Dec 2026 departures)
  - Silversea Silver Muse (Jun 2026 departure — McLeod)
  - Viking Ocean Viking Mars (Dec 2026 departure — Kuklinski)
"""

import os
import json
import datetime
import urllib.request
import urllib.parse

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "cruise_intel")

SHIPS = [
    {"name": "Regent Seven Seas Grandeur", "query": "Regent Seven Seas Grandeur review 2026 passenger experience"},
    {"name": "Silversea Silver Muse", "query": "Silversea Silver Muse review 2026 Mediterranean passenger"},
    {"name": "Viking Mars", "query": "Viking Ocean Viking Mars review 2026 Baltic passenger experience"},
]


def serper_search(query: str, num: int = 5) -> list[dict]:
    if not SERPER_API_KEY:
        print("[WARN] SERPER_API_KEY not set — skipping search")
        return []
    payload = json.dumps({"q": query, "num": num}).encode()
    req = urllib.request.Request(
        "https://google.serper.dev/search",
        data=payload,
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data.get("organic", [])


def run_sweep():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    results = {}

    for ship in SHIPS:
        print(f"Searching: {ship['name']}...")
        hits = serper_search(ship["query"])
        results[ship["name"]] = [
            {"title": h.get("title"), "snippet": h.get("snippet"), "link": h.get("link")}
            for h in hits
        ]
        print(f"  {len(hits)} results")

    out_file = os.path.join(OUTPUT_DIR, f"cruise_feedback_{date_str}.json")
    with open(out_file, "w") as f:
        json.dump({"date": date_str, "ships": results}, f, indent=2)

    print(f"\nSaved: {out_file}")

    # Print brief summary
    print("\n=== CRUISE INTEL BRIEF ===")
    for ship_name, hits in results.items():
        print(f"\n{ship_name}:")
        for h in hits[:3]:
            print(f"  - {h['title']}")
            if h['snippet']:
                print(f"    {h['snippet'][:120]}...")

    return out_file


if __name__ == "__main__":
    run_sweep()

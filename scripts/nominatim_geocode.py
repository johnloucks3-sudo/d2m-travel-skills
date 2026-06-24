#!/usr/bin/env python3
"""
OSM Nominatim geocoder — $0 fallback for port/city distance calculations.
Use instead of Google Maps API for non-embed geocoding (avoids cost per-call).
MISSION-389: Port Maps — Mapbox vs Google vs OSM

Usage:
  python3 nominatim_geocode.py "Civitavecchia, Italy"
  python3 nominatim_geocode.py "Nassau, Bahamas" --distance "Miami, FL"
"""

import sys
import math
import time
import argparse
import urllib.request
import urllib.parse
import json

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "D2M-Thunderbird/1.0 (johnloucks3@gmail.com)"


def geocode(place: str) -> dict | None:
    params = urllib.parse.urlencode({"q": place, "format": "json", "limit": 1})
    req = urllib.request.Request(
        f"{NOMINATIM_URL}?{params}",
        headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        results = json.loads(resp.read())
    if not results:
        return None
    r = results[0]
    return {"lat": float(r["lat"]), "lon": float(r["lon"]), "display": r["display_name"]}


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def port_to_city_distances(port: str, cities: list[str]) -> list[dict]:
    port_geo = geocode(port)
    if not port_geo:
        return []
    results = []
    for city in cities:
        time.sleep(1)  # Nominatim rate limit: 1 req/sec
        city_geo = geocode(city)
        if city_geo:
            km = haversine_km(port_geo["lat"], port_geo["lon"], city_geo["lat"], city_geo["lon"])
            results.append({"city": city, "km": round(km, 1), "miles": round(km * 0.621371, 1)})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OSM Nominatim geocoder for D2M port logistics")
    parser.add_argument("place", help="Place to geocode")
    parser.add_argument("--distance", help="Calculate distance to this second place")
    args = parser.parse_args()

    geo = geocode(args.place)
    if not geo:
        print(f"Not found: {args.place}")
        sys.exit(1)
    print(f"Location: {geo['display']}")
    print(f"Coords: {geo['lat']}, {geo['lon']}")

    if args.distance:
        time.sleep(1)
        geo2 = geocode(args.distance)
        if geo2:
            km = haversine_km(geo["lat"], geo["lon"], geo2["lat"], geo2["lon"])
            print(f"Distance to {args.distance}: {km:.1f} km / {km*0.621371:.1f} miles")

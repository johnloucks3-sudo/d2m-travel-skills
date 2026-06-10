
import json
import requests

FACTBOOK_RAW_BASE = "https://raw.githubusercontent.com/factbook/factbook.json/master"

FACTBOOK_COUNTRY_MAP: dict[str, tuple[str, str]] = {
    "norway": ("europe", "no"),
    "sweden": ("europe", "sw"),
    "denmark": ("europe", "da"),
    "japan": ("east-n-southeast-asia", "ja"),
    "greece": ("europe", "gr"),
    "united states": ("north-america", "us"),
    "iceland": ("europe", "ic"),
    "finland": ("europe", "fi"),
}

def _fetch_factbook(country_key: str) -> dict:
    key = country_key.lower().strip()
    if key not in FACTBOOK_COUNTRY_MAP:
        raise ValueError(f"Country '{country_key}' not in factbook map. Available: {', '.join(sorted(FACTBOOK_COUNTRY_MAP.keys()))}")

    region, code = FACTBOOK_COUNTRY_MAP[key]
    url = f"{FACTBOOK_RAW_BASE}/{region}/{code}.json"

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()

def _safe_text(obj, *keys, default="Not available") -> str:
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, {})
    if isinstance(current, dict):
        return current.get("text", default)
    if isinstance(current, str):
        return current
    return default

def _format_country_briefing(data: dict, country_name: str) -> dict:
    intro = data.get("Introduction", {})
    geo = data.get("Geography", {})
    people = data.get("People and Society", {})
    economy = data.get("Economy", {})
    transport = data.get("Transportation", {})
    govt = data.get("Government", {})

    location = _safe_text(geo, "Location")
    climate = _safe_text(geo, "Climate")
    terrain = _safe_text(geo, "Terrain")
    area_total = _safe_text(geo, "Area", "total")
    coastline = _safe_text(geo, "Coastline")
    natural_resources = _safe_text(geo, "Natural resources")

    population = _safe_text(people, "Population", "total")
    languages = _safe_text(people, "Languages", "Languages")
    religions = _safe_text(people, "Religions")

    currency = _safe_text(economy, "Currency")
    exchange_rates = _safe_text(economy, "Exchange rates")
    gdp_per_capita = _safe_text(economy, "Real GDP per capita")
    economy_overview = _safe_text(economy, "Economic overview")

    capital = _safe_text(govt, "Capital", "name")
    country_name_official = _safe_text(govt, "Country name", "conventional long form")

    ports_raw = _safe_text(transport, "Major seaports")
    airports = _safe_text(transport, "Airports")

    background = _safe_text(intro, "Background")

    return {
        "country": country_name.title(),
        "official_name": country_name_official,
        "capital": capital,
        "background_summary": background[:600] + "..." if len(background) > 600 else background,
        "geography": {
            "location": location,
            "area_total": area_total,
            "coastline": coastline,
            "terrain": terrain,
        },
        "climate": climate,
        "people": {
            "population": population,
            "languages": languages,
            "religions": religions,
        },
        "economy": {
            "overview": economy_overview[:400] + "..." if len(economy_overview) > 400 else economy_overview,
            "currency": currency,
            "exchange_rates": exchange_rates,
            "gdp_per_capita": gdp_per_capita,
        },
        "transportation": {
            "major_ports": ports_raw,
            "airports": airports,
        },
        "natural_resources": natural_resources,
    }

if __name__ == "__main__":
    client_destinations = ["Norway", "Iceland", "Denmark", "Finland", "Japan", "United States", "Greece"]
    all_briefings = []

    for dest in client_destinations:
        country_for_lookup = "united states" if dest.lower() == "hawaii" else dest
        try:
            data = _fetch_factbook(country_for_lookup)
            briefing = _format_country_briefing(data, country_for_lookup)
            if dest.lower() == "hawaii":
                briefing["note"] = "Intelligence for Hawaii is based on United States data."
            all_briefings.append({"destination": dest, "intelligence": briefing, "status": "success"})
        except ValueError as e:
            all_briefings.append({"destination": dest, "status": "error", "message": str(e)})
        except requests.HTTPError as e:
            all_briefings.append({"destination": dest, "status": "error", "message": f"HTTP Error: {e.response.status_code} - {e.response.text}"})
        except Exception as e:
            all_briefings.append({"destination": dest, "status": "error", "message": str(e)})

    print(json.dumps(all_briefings, indent=2))

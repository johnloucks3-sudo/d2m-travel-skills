"""
Dreams2Memories World Factbook Intelligence MCP Module
======================================================

Country and port city intelligence for client pre-trip briefings:
- Fetch country data from the CIA World Factbook (via factbook.json GitHub repo)
- Format clean client-readable briefings: geography, climate, currency, ports, travel notes
- No API credentials required — uses raw GitHub content

Data source: https://github.com/factbook/factbook.json
Integrates with: travel_mcp_server.py
Dependencies: requests
"""

import json
import logging
import requests
from typing import Optional
from pathlib import Path

from pydantic import Field
from mcp.server.fastmcp import FastMCP

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = logging.getLogger(__name__)

FACTBOOK_RAW_BASE = "https://raw.githubusercontent.com/factbook/factbook.json/master"

# Country code map: country name -> (region_folder, country_code)
# Based on factbook.json repository structure
FACTBOOK_COUNTRY_MAP: dict[str, tuple[str, str]] = {
    "norway": ("europe", "no"),
    "sweden": ("europe", "sw"),
    "denmark": ("europe", "da"),
    "japan": ("east-n-southeast-asia", "ja"),
    "panama": ("central-america-n-caribbean", "pm"),
    "greece": ("europe", "gr"),
    "italy": ("europe", "it"),
    "spain": ("europe", "sp"),
    "croatia": ("europe", "hr"),
    "montenegro": ("europe", "mj"),
    "malta": ("europe", "mt"),
    "united states": ("north-america", "us"),
    "alaska": ("north-america", "us"),
    "iceland": ("europe", "ic"),
    "finland": ("europe", "fi"),
    "germany": ("europe", "gm"),
    "france": ("europe", "fr"),
    "portugal": ("europe", "po"),
    "netherlands": ("europe", "nl"),
    "bahamas": ("central-america-n-caribbean", "bf"),
    "mexico": ("north-america", "mx"),
    # Additional entries for common D2M destinations
    "united kingdom": ("europe", "uk"),
    "ireland": ("europe", "ei"),
    "australia": ("australia-oceania", "as"),
    "new zealand": ("australia-oceania", "nz"),
    "canada": ("north-america", "ca"),
    "argentina": ("south-america", "ar"),
    "brazil": ("south-america", "br"),
    "peru": ("south-america", "pe"),
    "chile": ("south-america", "ci"),
    "costa rica": ("central-america-n-caribbean", "cs"),
    "turkey": ("middle-east", "tu"),
    "israel": ("middle-east", "is"),
    "egypt": ("africa", "eg"),
    "morocco": ("africa", "mo"),
    "south africa": ("africa", "sf"),
    "kenya": ("africa", "ke"),
    "india": ("south-asia", "in"),
    "thailand": ("east-n-southeast-asia", "th"),
    "vietnam": ("east-n-southeast-asia", "vm"),
    "indonesia": ("east-n-southeast-asia", "id"),
    "singapore": ("east-n-southeast-asia", "sn"),
    "china": ("east-n-southeast-asia", "ch"),
    "south korea": ("east-n-southeast-asia", "ks"),
    "hong kong": ("east-n-southeast-asia", "hk"),
    "taiwan": ("east-n-southeast-asia", "tw"),
    "russia": ("europe", "rs"),
    "ukraine": ("europe", "up"),
    "poland": ("europe", "pl"),
    "czech republic": ("europe", "ez"),
    "austria": ("europe", "au"),
    "switzerland": ("europe", "sz"),
    "belgium": ("europe", "be"),
    "luxembourg": ("europe", "lu"),
    "monaco": ("europe", "mn"),
}

# Port city to country mapping for convenience
PORT_CITY_COUNTRY_MAP: dict[str, str] = {
    "piraeus": "greece",
    "athens": "greece",
    "mykonos": "greece",
    "santorini": "greece",
    "corfu": "greece",
    "dubrovnik": "croatia",
    "split": "croatia",
    "kotor": "montenegro",
    "barcelona": "spain",
    "valencia": "spain",
    "palma": "spain",
    "mallorca": "spain",
    "rome": "italy",
    "civitavecchia": "italy",
    "naples": "italy",
    "venice": "italy",
    "genoa": "italy",
    "palermo": "italy",
    "lisbon": "portugal",
    "marseille": "france",
    "nice": "france",
    "monte carlo": "monaco",
    "valletta": "malta",
    "istanbul": "turkey",
    "oslo": "norway",
    "bergen": "norway",
    "flam": "norway",
    "geiranger": "norway",
    "stockholm": "sweden",
    "copenhagen": "denmark",
    "helsinki": "finland",
    "reykjavik": "iceland",
    "amsterdam": "netherlands",
    "southampton": "united kingdom",
    "dover": "united kingdom",
    "edinburgh": "united kingdom",
    "dublin": "ireland",
    "miami": "united states",
    "ft. lauderdale": "united states",
    "fort lauderdale": "united states",
    "los angeles": "united states",
    "seattle": "united states",
    "new york": "united states",
    "honolulu": "united states",
    "anchorage": "alaska",
    "juneau": "alaska",
    "ketchikan": "alaska",
    "skagway": "alaska",
    "seward": "alaska",
    "colon": "panama",
    "balboa": "panama",
    "tokyo": "japan",
    "yokohama": "japan",
    "osaka": "japan",
    "kyoto": "japan",
    "nassau": "bahamas",
    "cozumel": "mexico",
    "cancun": "mexico",
}


# ============================================================================
# DATA EXTRACTION HELPERS
# ============================================================================

def _fetch_factbook(country_key: str) -> dict:
    """Fetch factbook JSON for a country by its map key."""
    key = country_key.lower().strip()
    if key not in FACTBOOK_COUNTRY_MAP:
        raise ValueError(
            f"Country '{country_key}' not in factbook map. "
            f"Available: {', '.join(sorted(FACTBOOK_COUNTRY_MAP.keys()))}"
        )

    region, code = FACTBOOK_COUNTRY_MAP[key]
    url = f"{FACTBOOK_RAW_BASE}/{region}/{code}.json"

    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _safe_text(obj, *keys, default="Not available") -> str:
    """Safely extract nested text from factbook JSON."""
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
    """Extract and format key factbook fields into a client briefing structure."""

    intro = data.get("Introduction", {})
    geo = data.get("Geography", {})
    people = data.get("People and Society", {})
    economy = data.get("Economy", {})
    transport = data.get("Transportation", {})
    govt = data.get("Government", {})

    # Geography & Climate
    location = _safe_text(geo, "Location")
    climate = _safe_text(geo, "Climate")
    terrain = _safe_text(geo, "Terrain")
    area_total = _safe_text(geo, "Area", "total")
    coastline = _safe_text(geo, "Coastline")
    natural_resources = _safe_text(geo, "Natural resources")

    # People & Language
    population = _safe_text(people, "Population", "total")
    languages = _safe_text(people, "Languages", "Languages")
    religions = _safe_text(people, "Religions")

    # Economy & Currency
    currency = _safe_text(economy, "Currency")
    exchange_rates = _safe_text(economy, "Exchange rates")
    gdp_per_capita = _safe_text(economy, "Real GDP per capita")
    economy_overview = _safe_text(economy, "Economic overview")

    # Government
    capital = _safe_text(govt, "Capital", "name")
    country_name_official = _safe_text(govt, "Country name", "conventional long form")

    # Transportation / Ports
    ports_raw = _safe_text(transport, "Major seaports")
    airports = _safe_text(transport, "Airports")

    # Background
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


def _format_port_city_briefing(port_city: str, country_data: dict, country: str) -> dict:
    """Build a port-city-specific briefing from country factbook data."""
    base = _format_country_briefing(country_data, country)

    # Add port city context
    base["port_city"] = port_city.title()
    base["d2m_travel_notes"] = _build_travel_notes(port_city.lower(), country.lower(), base)

    return base


def _build_travel_notes(port_city: str, country: str, briefing: dict) -> list:
    """Build practical travel notes for a D2M client pre-trip briefing."""
    notes = []

    currency = briefing.get("economy", {}).get("currency", "")
    if currency and currency != "Not available":
        notes.append(f"Currency: {currency}")

    languages = briefing.get("people", {}).get("languages", "")
    if languages and languages != "Not available":
        notes.append(f"Language(s): {languages[:150]}")

    climate = briefing.get("climate", "")
    if climate and climate != "Not available":
        notes.append(f"Climate: {climate[:200]}")

    ports = briefing.get("transportation", {}).get("major_ports", "")
    if ports and ports != "Not available":
        notes.append(f"Major ports: {ports[:200]}")

    capital = briefing.get("capital", "")
    if capital and capital != "Not available":
        notes.append(f"Capital city: {capital}")

    if country == "greece":
        notes.append("Tipping: 5-10% in restaurants. Taxis: round up fare.")
        notes.append("Dress code: Cover shoulders/knees at religious sites.")
    elif country == "italy":
        notes.append("Tipping: Not mandatory, but 1-2€ appreciated at cafes.")
        notes.append("Dress code: Cover shoulders at churches and cathedrals.")
    elif country == "japan":
        notes.append("Tipping: NOT customary — can be considered rude.")
        notes.append("Customs: Remove shoes when entering traditional establishments.")
    elif country in ("norway", "sweden", "denmark", "finland", "iceland"):
        notes.append("Safety: Extremely safe, low crime. Credit cards universally accepted.")
        notes.append("Daylight: Midnight sun in summer — bring a sleep mask.")

    return notes


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

def register_worldfactbook_tools(mcp: FastMCP):
    """Register World Factbook intelligence tools with the MCP server."""

    @mcp.tool(
        name="get_country_intel",
        annotations={"title": "Get CIA World Factbook Country Intelligence", "readOnlyHint": True},
    )
    async def get_country_intel(
        country: str = Field(..., description=(
            "Country name (e.g., 'Norway', 'Japan', 'Greece'). "
            "Supported: " + ", ".join(sorted(FACTBOOK_COUNTRY_MAP.keys()))
        )),
    ) -> str:
        """Fetch country intelligence from the CIA World Factbook (factbook.json GitHub repo).

        Returns a structured briefing with:
        - Geography (location, terrain, coastline, area)
        - Climate summary
        - Population, languages, religion
        - Economy overview, currency, GDP per capita
        - Major ports and airports
        - Travel notes for D2M clients

        No API key required. Ideal for client pre-trip briefing packets.
        """
        try:
            data = _fetch_factbook(country)
        except ValueError as e:
            return json.dumps({
                "status": "country_not_found",
                "country": country,
                "message": str(e),
                "supported_countries": sorted(FACTBOOK_COUNTRY_MAP.keys()),
            })
        except requests.HTTPError as e:
            return json.dumps({
                "status": "error",
                "country": country,
                "message": f"Failed to fetch factbook data: {e}",
                "http_status": e.response.status_code if e.response else None,
            })
        except Exception as e:
            logger.error("World Factbook fetch error for %s: %s", country, e)
            return json.dumps({"status": "error", "country": country, "message": str(e)})

        briefing = _format_country_briefing(data, country)
        return json.dumps({
            "status": "success",
            "source": "CIA World Factbook via factbook.json",
            **briefing,
        }, indent=2)

    @mcp.tool(
        name="get_port_city_intel",
        annotations={"title": "Get Port City Intelligence for Client Briefings", "readOnlyHint": True},
    )
    async def get_port_city_intel(
        port_city: str = Field(..., description=(
            "Port city name (e.g., 'Santorini', 'Bergen', 'Dubrovnik', 'Yokohama'). "
            "Can also use country capital or major city."
        )),
        country: str = Field("", description=(
            "Country override (optional — auto-detected for known port cities). "
            "Use if port city is not auto-mapped."
        )),
    ) -> str:
        """Get destination-specific intelligence for a cruise port or travel city.

        Combines CIA World Factbook country data with port-city-specific travel notes,
        formatted as a client-ready pre-trip briefing. Ideal for Dani's port briefing
        emails, dossier destination sections, and client proposal inserts.

        Covers: geography, climate, currency, local language, major ports, dress codes,
        tipping customs, and D2M-curated travel tips.

        Auto-detects country from 50+ known port cities. Override with `country` param
        if needed.
        """
        port_lower = port_city.lower().strip()
        country_key = country.lower().strip() if country else PORT_CITY_COUNTRY_MAP.get(port_lower, "")

        if not country_key:
            # Try partial match
            for city_key, ctry in PORT_CITY_COUNTRY_MAP.items():
                if port_lower in city_key or city_key in port_lower:
                    country_key = ctry
                    break

        if not country_key:
            return json.dumps({
                "status": "country_not_found",
                "port_city": port_city,
                "message": (
                    f"Could not auto-detect country for '{port_city}'. "
                    "Please provide the `country` parameter explicitly."
                ),
                "known_port_cities": sorted(PORT_CITY_COUNTRY_MAP.keys()),
                "supported_countries": sorted(FACTBOOK_COUNTRY_MAP.keys()),
            })

        try:
            data = _fetch_factbook(country_key)
        except ValueError as e:
            return json.dumps({
                "status": "country_not_in_factbook",
                "port_city": port_city,
                "country_detected": country_key,
                "message": str(e),
                "supported_countries": sorted(FACTBOOK_COUNTRY_MAP.keys()),
            })
        except requests.HTTPError as e:
            return json.dumps({
                "status": "error",
                "port_city": port_city,
                "message": f"Failed to fetch factbook data: {e}",
                "http_status": e.response.status_code if e.response else None,
            })
        except Exception as e:
            logger.error("World Factbook port city error for %s/%s: %s", port_city, country_key, e)
            return json.dumps({"status": "error", "port_city": port_city, "message": str(e)})

        briefing = _format_port_city_briefing(port_city, data, country_key)
        return json.dumps({
            "status": "success",
            "source": "CIA World Factbook via factbook.json",
            "country_key_used": country_key,
            **briefing,
        }, indent=2)

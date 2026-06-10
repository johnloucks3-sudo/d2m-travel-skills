"""
Dreams2Memories Google Maps MCP Module
=======================================

Extends the travel MCP server with Google Maps API operations:
- Geocode addresses to lat/lng coordinates
- Calculate distance and duration between locations
- Generate static map URLs for embedding in itineraries
- Search for places (restaurants, landmarks, etc.)
- Get detailed place information including hours and reviews

Auth: Google Maps API key from GOOGLE_MAPS_API_KEY env var or .env file.
No OAuth required — uses API key authentication.

Integrates with: travel_mcp_server.py
Dependencies: requests, python-dotenv
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from pydantic import Field
from mcp.server.fastmcp import FastMCP

# Configuration
THUNDERBIRD_DIR = Path.home() / "Thunderbird"
ENV_FILE = THUNDERBIRD_DIR / ".env"

logger = logging.getLogger(__name__)

# Cache for API key
_maps_api_key = None


def _get_maps_api_key() -> Optional[str]:
    """Load the Google Maps API key from environment or .env file.

    Checks GOOGLE_MAPS_API_KEY environment variable first, then
    falls back to reading from Thunderbird's .env file.
    Returns None if no key is configured.
    """
    global _maps_api_key
    if _maps_api_key is not None:
        return _maps_api_key

    # Try environment variable first
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if key:
        _maps_api_key = key
        return key

    # Try .env file
    if ENV_FILE.exists():
        try:
            load_dotenv(ENV_FILE)
            key = os.environ.get("GOOGLE_MAPS_API_KEY")
            if key:
                _maps_api_key = key
                return key
        except Exception as e:
            logger.warning(f"Failed to load .env file: {e}")

    logger.warning("Google Maps API key not configured. Maps tools will return errors.")
    _maps_api_key = ""
    return None


def _check_key() -> Optional[str]:
    """Return the API key or None if not configured."""
    key = _get_maps_api_key()
    if not key:
        return None
    return key


def _maps_error_response(message: str, detail: Optional[str] = None) -> str:
    """Build a standard error response JSON string."""
    resp = {"error": message}
    if detail:
        resp["detail"] = detail
    return json.dumps(resp, indent=2)


def _fetch_google_api(url: str, params: dict) -> dict:
    """Make a request to a Google Maps API endpoint and return parsed JSON.

    Handles HTTP errors and unexpected exceptions uniformly.
    The API key is injected into params by the caller.
    """
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Google returns 200 with error status in the body
        if data.get("status") == "REQUEST_DENIED":
            error_msg = data.get("error_message", "Request denied")
            logger.error(f"Google Maps API rejected request: {error_msg}")
            return {"error": error_msg, "google_status": "REQUEST_DENIED"}

        if data.get("status") == "INVALID_REQUEST":
            error_msg = data.get("error_message", "Invalid request")
            logger.error(f"Google Maps API invalid request: {error_msg}")
            return {"error": error_msg, "google_status": "INVALID_REQUEST"}

        if data.get("status") == "OVER_QUERY_LIMIT":
            error_msg = data.get("error_message", "Over query limit")
            logger.error(f"Google Maps API query limit exceeded: {error_msg}")
            return {"error": error_msg, "google_status": "OVER_QUERY_LIMIT"}

        if data.get("status") == "ZERO_RESULTS":
            return {"error": "No results found", "google_status": "ZERO_RESULTS"}

        return data

    except requests.exceptions.Timeout:
        logger.error("Google Maps API request timed out")
        return {"error": "Request timed out"}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Google Maps API connection error: {e}")
        return {"error": f"Connection failed: {e}"}
    except requests.exceptions.HTTPError as e:
        logger.error(f"Google Maps API HTTP error: {e}")
        return {"error": f"HTTP {e.response.status_code}: {e.response.reason}"}
    except json.JSONDecodeError as e:
        logger.error(f"Google Maps API response parse error: {e}")
        return {"error": f"Failed to parse API response: {e}"}
    except Exception as e:
        logger.error(f"Google Maps API unexpected error: {e}")
        return {"error": str(e)}


def register_maps_mcp_tools(mcp: FastMCP):
    """Register all Google Maps tools with the MCP server.

    If the Google Maps API key is not configured, registers fallback tools
    that return a clear error message.
    """
    api_key = _check_key()
    key_available = api_key is not None

    if not key_available:
        logger.warning(
            "GOOGLE_MAPS_API_KEY not found — registering fallback maps tools"
        )

    # ─── Tool 1: Geocode ─────────────────────────────────────────────────

    @mcp.tool(
        name="maps_geocode",
        annotations={
            "title": "Geocode Address to Coordinates",
            "readOnlyHint": True,
        },
    )
    async def maps_geocode(
        address: str = Field(
            ..., description="Address to geocode (e.g. '1600 Amphitheatre Parkway, Mountain View, CA')"
        ),
    ) -> str:
        """Geocode an address to latitude/longitude coordinates using Google Geocoding API.

        Returns formatted address, lat, lng, and place_id.
        """
        if not key_available:
            return _maps_error_response("Google Maps API key not configured")

        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {"address": address, "key": api_key}
            data = _fetch_google_api(url, params)

            if "error" in data:
                return json.dumps(data, indent=2)

            results = data.get("results", [])
            if not results:
                return json.dumps(
                    {"error": "No results found for address", "google_status": "ZERO_RESULTS"},
                    indent=2,
                )

            result = results[0]
            geometry = result["geometry"]["location"]
            return json.dumps(
                {
                    "status": "success",
                    "formatted_address": result.get("formatted_address", ""),
                    "lat": geometry["lat"],
                    "lng": geometry["lng"],
                    "place_id": result.get("place_id", ""),
                    "types": result.get("types", []),
                    "address_components": result.get("address_components", []),
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Maps geocode error: {e}")
            return _maps_error_response(str(e))

    # ─── Tool 2: Distance Matrix ─────────────────────────────────────────

    @mcp.tool(
        name="maps_distance_matrix",
        annotations={
            "title": "Calculate Distances Between Locations",
            "readOnlyHint": True,
        },
    )
    async def maps_distance_matrix(
        origins_json: str = Field(
            ...,
            description='JSON array of origin addresses, e.g. ["Denver, CO", "Colorado Springs, CO"]',
        ),
        destinations_json: str = Field(
            ...,
            description='JSON array of destination addresses, e.g. ["Los Angeles, CA", "San Diego, CA"]',
        ),
        mode: str = Field(
            "driving",
            description="Travel mode: 'driving', 'walking', 'bicycling', or 'transit'",
        ),
    ) -> str:
        """Calculate distance and duration between origins and destinations.

        Supports multiple travel modes. Returns distance (km/miles) and
        duration for each origin-destination pair.
        """
        if not key_available:
            return _maps_error_response("Google Maps API key not configured")

        try:
            # Parse JSON arrays
            try:
                origins = json.loads(origins_json)
                destinations = json.loads(destinations_json)
            except json.JSONDecodeError as e:
                return _maps_error_response(f"Invalid JSON: {e}")

            if not isinstance(origins, list) or not origins:
                return _maps_error_response("origins_json must be a non-empty JSON array")
            if not isinstance(destinations, list) or not destinations:
                return _maps_error_response("destinations_json must be a non-empty JSON array")

            valid_modes = {"driving", "walking", "bicycling", "transit"}
            if mode not in valid_modes:
                return _maps_error_response(
                    f"Invalid mode '{mode}'. Must be one of: {', '.join(sorted(valid_modes))}"
                )

            url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                "origins": "|".join(origins),
                "destinations": "|".join(destinations),
                "mode": mode,
                "key": api_key,
            }

            data = _fetch_google_api(url, params)
            if "error" in data:
                return json.dumps(data, indent=2)

            rows = data.get("rows", [])
            results = []
            for i, row in enumerate(rows):
                origin = origins[i] if i < len(origins) else f"origin_{i}"
                elements = row.get("elements", [])
                for j, element in enumerate(elements):
                    destination = destinations[j] if j < len(destinations) else f"dest_{j}"
                    pair = {
                        "origin": origin,
                        "destination": destination,
                    }
                    if element.get("status") == "OK":
                        pair["distance"] = {
                            "text": element["distance"]["text"],
                            "value_meters": element["distance"]["value"],
                        }
                        pair["duration"] = {
                            "text": element["duration"]["text"],
                            "value_seconds": element["duration"]["value"],
                        }
                        pair["status"] = "OK"
                    else:
                        pair["status"] = element.get("status", "UNKNOWN")
                    results.append(pair)

            return json.dumps(
                {
                    "status": "success",
                    "mode": mode,
                    "origin_addresses": data.get("origin_addresses", origins),
                    "destination_addresses": data.get("destination_addresses", destinations),
                    "results": results,
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Maps distance matrix error: {e}")
            return _maps_error_response(str(e))

    # ─── Tool 3: Static Map URL ──────────────────────────────────────────

    @mcp.tool(
        name="maps_static_map_url",
        annotations={
            "title": "Generate Google Static Map URL",
            "readOnlyHint": True,
        },
    )
    async def maps_static_map_url(
        center: str = Field(
            "",
            description="Center of the map: address or 'lat,lng' (e.g. 'Denver, CO' or '39.7392,-104.9903'). Required if markers_json is empty.",
        ),
        markers_json: str = Field(
            "",
            description='JSON array of marker locations, e.g. ["Denver, CO", "39.7392,-104.9903"]. If provided without center, map auto-centers on markers.',
        ),
        zoom: int = Field(
            10,
            description="Map zoom level (0=world, 21=building). Default 10.",
            ge=0,
            le=21,
        ),
        size: str = Field(
            "600x400",
            description="Image dimensions in pixels, e.g. '600x400' or '800x600'. Max 640x640 free tier.",
        ),
        maptype: str = Field(
            "roadmap",
            description="Map type: 'roadmap', 'satellite', 'terrain', or 'hybrid'",
        ),
    ) -> str:
        """Generate a Google Static Maps URL for embedding in itineraries and web pages.

        Returns the URL string (not the image binary). The client can use this URL
        directly in <img> tags or download it separately.
        """
        if not key_available:
            return _maps_error_response("Google Maps API key not configured")

        try:
            valid_types = {"roadmap", "satellite", "terrain", "hybrid"}
            if maptype not in valid_types:
                return _maps_error_response(
                    f"Invalid maptype '{maptype}'. Must be one of: {', '.join(sorted(valid_types))}"
                )

            # Parse markers
            markers_param = None
            if markers_json:
                try:
                    markers = json.loads(markers_json)
                except json.JSONDecodeError as e:
                    return _maps_error_response(f"Invalid markers_json: {e}")

                if not isinstance(markers, list):
                    return _maps_error_response("markers_json must be a JSON array")

                # Encode markers as pipe-separated locations
                marker_locations = "|".join(
                    m.strip() for m in markers if isinstance(m, str) and m.strip()
                )
                if marker_locations:
                    markers_param = f"size:mid|{marker_locations}"

            # Build URL
            base = "https://maps.googleapis.com/maps/api/staticmap"
            params = {
                "size": size,
                "maptype": maptype,
                "key": api_key,
            }

            if markers_param:
                params["markers"] = markers_param

            if center:
                params["center"] = center
                params["zoom"] = str(zoom)
            elif not markers_param:
                return _maps_error_response(
                    "Either 'center' or 'markers_json' is required"
                )
            # If markers are set but no center, auto-center (no zoom control without center)

            # Build query string manually to handle special chars
            from urllib.parse import urlencode, quote

            query_parts = []
            for k, v in params.items():
                if k == "markers":
                    # markers need special encoding — pipe-separated values
                    query_parts.append(f"markers={quote(v)}")
                else:
                    query_parts.append(f"{k}={quote(str(v))}")

            url = f"{base}?{'&'.join(query_parts)}"

            return json.dumps(
                {
                    "status": "success",
                    "url": url,
                    "size": size,
                    "maptype": maptype,
                    "zoom": zoom if center else None,
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Maps static map URL error: {e}")
            return _maps_error_response(str(e))

    # ─── Tool 4: Places Search ───────────────────────────────────────────

    @mcp.tool(
        name="maps_places_search",
        annotations={
            "title": "Search Places Near Location",
            "readOnlyHint": True,
        },
    )
    async def maps_places_search(
        query: str = Field(
            ...,
            description="Search query (e.g. 'restaurants near Eiffel Tower', 'museums in Rome')",
        ),
        location: str = Field(
            "",
            description="Optional bias location as 'lat,lng' (e.g. '48.8584,2.2945'). Improves relevance.",
        ),
        radius: int = Field(
            5000,
            description="Search radius in meters (default 5000, max 50000). Only used when location is provided.",
            ge=1,
            le=50000,
        ),
    ) -> str:
        """Search for places using Google Places API Text Search.

        Returns place name, formatted address, rating, types, and place_id
        for each result. Useful for finding restaurants, hotels, landmarks,
        and services near a client's destination.
        """
        if not key_available:
            return _maps_error_response("Google Maps API key not configured")

        try:
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {"query": query, "key": api_key}

            if location:
                params["location"] = location
                params["radius"] = str(radius)

            data = _fetch_google_api(url, params)
            if "error" in data:
                return json.dumps(data, indent=2)

            places = []
            for result in data.get("results", []):
                geometry = result.get("geometry", {})
                loc = geometry.get("location", {}) if geometry else {}
                places.append(
                    {
                        "name": result.get("name", ""),
                        "formatted_address": result.get("formatted_address", ""),
                        "rating": result.get("rating"),
                        "user_ratings_total": result.get("user_ratings_total", 0),
                        "types": result.get("types", []),
                        "place_id": result.get("place_id", ""),
                        "lat": loc.get("lat"),
                        "lng": loc.get("lng"),
                        "price_level": result.get("price_level"),
                        "opening_hours": result.get("opening_hours", {}),
                        "photos": [
                            {"photo_reference": p.get("photo_reference"), "height": p.get("height"), "width": p.get("width")}
                            for p in result.get("photos", [])
                        ],
                    }
                )

            return json.dumps(
                {
                    "status": "success",
                    "query": query,
                    "count": len(places),
                    "places": places,
                },
                indent=2,
            )

        except Exception as e:
            logger.error(f"Maps places search error: {e}")
            return _maps_error_response(str(e))

    # ─── Tool 5: Place Details ───────────────────────────────────────────

    @mcp.tool(
        name="maps_place_details",
        annotations={
            "title": "Get Detailed Place Information",
            "readOnlyHint": True,
        },
    )
    async def maps_place_details(
        place_id: str = Field(
            ...,
            description="Google Place ID (from maps_places_search or maps_geocode results)",
        ),
    ) -> str:
        """Get comprehensive details for a specific place.

        Returns full address, phone number, website URL, opening hours,
        Google reviews, price level, and more. Ideal for building client
        briefing materials and itinerary recommendations.
        """
        if not key_available:
            return _maps_error_response("Google Maps API key not configured")

        try:
            url = "https://maps.googleapis.com/maps/api/place/details/json"
            params = {
                "place_id": place_id,
                "fields": [
                    "name",
                    "formatted_address",
                    "formatted_phone_number",
                    "international_phone_number",
                    "website",
                    "url",
                    "rating",
                    "user_ratings_total",
                    "price_level",
                    "types",
                    "opening_hours",
                    "reviews",
                    "photos",
                    "geometry",
                    "address_components",
                    "adr_address",
                    "business_status",
                    "icon",
                    "icon_background_color",
                    "icon_mask_base_uri",
                    "plus_code",
                    "utc_offset",
                    "vicinity",
                    "wheelchair_accessible_entrance",
                    "current_opening_hours",
                ],
                "key": api_key,
            }

            data = _fetch_google_api(url, params)
            if "error" in data:
                return json.dumps(data, indent=2)

            result = data.get("result", {})
            if not result:
                return json.dumps(
                    {"error": "No place found for the given place_id"},
                    indent=2,
                )

            # Structure the response
            geometry = result.get("geometry", {})
            loc = geometry.get("location", {}) if geometry else {}
            opening_hours = result.get("opening_hours", {})
            current_hours = result.get("current_opening_hours", {})
            reviews_raw = result.get("reviews", [])

            # Limit reviews to most recent 5
            reviews = []
            for r in reviews_raw[:5]:
                reviews.append(
                    {
                        "author_name": r.get("author_name", ""),
                        "rating": r.get("rating"),
                        "text": r.get("text", ""),
                        "time": r.get("relative_time_description", ""),
                    }
                )

            detail = {
                "name": result.get("name", ""),
                "formatted_address": result.get("formatted_address", ""),
                "adr_address": result.get("adr_address", ""),
                "phone": {
                    "formatted": result.get("formatted_phone_number", ""),
                    "international": result.get("international_phone_number", ""),
                },
                "website": result.get("website"),
                "google_maps_url": result.get("url"),
                "rating": result.get("rating"),
                "user_ratings_total": result.get("user_ratings_total", 0),
                "price_level": result.get("price_level"),
                "types": result.get("types", []),
                "business_status": result.get("business_status"),
                "lat": loc.get("lat"),
                "lng": loc.get("lng"),
                "utc_offset_minutes": result.get("utc_offset"),
                "plus_code": result.get("plus_code"),
                "vicinity": result.get("vicinity"),
                "wheelchair_accessible": result.get("wheelchair_accessible_entrance", False),
                "opening_hours": {
                    "open_now": opening_hours.get("open_now"),
                    "periods": opening_hours.get("periods", []),
                    "weekday_text": opening_hours.get("weekday_text", []),
                },
                "current_opening_hours": {
                    "open_now": current_hours.get("open_now"),
                    "periods": current_hours.get("periods", []),
                    "weekday_text": current_hours.get("weekday_text", []),
                } if current_hours else None,
                "reviews": reviews,
                "place_id": place_id,
            }

            return json.dumps(
                {"status": "success", "place": detail},
                indent=2,
            )

        except Exception as e:
            logger.error(f"Maps place details error: {e}")
            return _maps_error_response(str(e))

    logger.info("Google Maps tools registered successfully")


if __name__ == "__main__":
    # Quick test — requires GOOGLE_MAPS_API_KEY to be set
    import sys

    key = _get_maps_api_key()
    if not key:
        print("GOOGLE_MAPS_API_KEY not configured.")
        print("Set the environment variable or add it to:")
        print(f"  {ENV_FILE}")
        sys.exit(1)

    print(f"Google Maps API key found: {key[:6]}...{key[-4:]}")
    print()

    # Test geocode
    print("=== Testing maps_geocode ===")
    import asyncio

    async def test():
        # We can't easily call the registered tools directly since they
        # need an MCP server, so we test the underlying API

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": "Denver, CO", "key": key}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data["status"] == "OK":
            loc = data["results"][0]["geometry"]["location"]
            print(f"  Denver, CO → {loc['lat']}, {loc['lng']}")
        else:
            print(f"  FAILED: {data.get('status')}")

        # Test places search
        print()
        print("=== Testing maps_places_search ===")
        url2 = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params2 = {"query": "restaurants near Eiffel Tower", "key": key}
        resp2 = requests.get(url2, params=params2, timeout=10)
        data2 = resp2.json()
        if data2.get("results"):
            print(f"  Found {len(data2['results'])} results")
            for p in data2["results"][:3]:
                print(f"  - {p.get('name')} ({p.get('rating', 'N/A')}★)")
        else:
            print(f"  FAILED: {data2.get('status')}")

        print()
        print("Done. Module ready for MCP registration.")

    asyncio.run(test())

"""
Dreams2Memories Hotel Search MCP Module
========================================

Hotel availability search via Hotelbeds/Bedsonline APITude:
- Search hotels by destination, geolocation, or hotel codes
- Check/verify rates before booking
- Retrieve hotel content details (descriptions, images, facilities)
- Visual browser search on Bedsonline portal (Playwright Stealth)

Integrates with: travel_mcp_server.py
Dependencies: requests, playwright, playwright-stealth
API Docs: https://developer.hotelbeds.com/documentation/hotels/booking-api/
"""

import json
import logging
import hashlib
import time
import base64
import requests
import asyncio
from typing import Optional, List
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML as WeasyHTML
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = logging.getLogger(__name__)


class HotelbedsConfig:
    """Hotelbeds APITude configuration.

    Get your API key and secret from https://developer.hotelbeds.com/
    or from your Bedsonline partner account.
    """

    API_KEY = ""       # Set your Hotelbeds API key
    API_SECRET = ""    # Set your Hotelbeds API secret

    # Switch to "https://api.hotelbeds.com" for production
    BASE_URL = "https://api.test.hotelbeds.com"

    BOOKING_API = "/hotel-api/1.0"
    CONTENT_API = "/hotel-content-api/1.0"

    # Bedsonline portal
    PORTAL_LOGIN_URL = "https://app.bedsonline.com/auth/login"
    PORTAL_SEARCH_URL = "https://app.bedsonline.com/accommodation"


SCREENSHOTS_DIR = Path.home() / "Thunderbird" / "screenshots"


def _load_credentials() -> tuple[str, str]:
    """Load API credentials from config or .env-style file."""
    if HotelbedsConfig.API_KEY and HotelbedsConfig.API_SECRET:
        return HotelbedsConfig.API_KEY, HotelbedsConfig.API_SECRET

    # Try loading from a credentials file
    cred_file = Path.home() / "Thunderbird" / "hotelbeds_credentials.json"
    if cred_file.exists():
        with open(cred_file) as f:
            creds = json.load(f)
        HotelbedsConfig.API_KEY = creds.get("api_key", "")
        HotelbedsConfig.API_SECRET = creds.get("api_secret", "")
        if creds.get("base_url"):
            HotelbedsConfig.BASE_URL = creds["base_url"]
        return HotelbedsConfig.API_KEY, HotelbedsConfig.API_SECRET

    raise ValueError(
        "Hotelbeds credentials not configured. "
        "Create ~/Thunderbird/hotelbeds_credentials.json with "
        '{"api_key": "YOUR_KEY", "api_secret": "YOUR_SECRET"}'
    )


def _auth_headers() -> dict:
    """Generate Hotelbeds authentication headers with SHA-256 signature."""
    api_key, api_secret = _load_credentials()
    timestamp = str(int(time.time()))
    sig_raw = api_key + api_secret + timestamp
    signature = hashlib.sha256(sig_raw.encode("utf-8")).hexdigest()
    return {
        "Api-key": api_key,
        "X-Signature": signature,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _api_url(path: str) -> str:
    """Build full API URL."""
    return f"{HotelbedsConfig.BASE_URL}{HotelbedsConfig.BOOKING_API}{path}"


def _content_url(path: str) -> str:
    """Build full Content API URL."""
    return f"{HotelbedsConfig.BASE_URL}{HotelbedsConfig.CONTENT_API}{path}"


# ============================================================================
# RESPONSE FORMATTING HELPERS
# ============================================================================

def _format_hotel_results(data: dict) -> dict:
    """Extract the key fields from an availability response into a concise summary."""
    hotels_container = data.get("hotels", {})
    raw_hotels = hotels_container.get("hotels", [])

    summary = {
        "check_in": hotels_container.get("checkIn"),
        "check_out": hotels_container.get("checkOut"),
        "total_hotels": hotels_container.get("total", len(raw_hotels)),
        "hotels": [],
    }

    for h in raw_hotels:
        rooms_summary = []
        for room in h.get("rooms", []):
            for rate in room.get("rates", []):
                rooms_summary.append({
                    "room_name": room.get("name"),
                    "room_code": room.get("code"),
                    "rate_key": rate.get("rateKey"),
                    "rate_type": rate.get("rateType"),
                    "board": rate.get("boardName", rate.get("boardCode")),
                    "net_price": rate.get("net"),
                    "currency": h.get("currency"),
                    "payment_type": rate.get("paymentType"),
                    "allotment": rate.get("allotment"),
                    "cancellation_policies": rate.get("cancellationPolicies"),
                })

        summary["hotels"].append({
            "code": h.get("code"),
            "name": h.get("name"),
            "category": h.get("categoryName"),
            "destination": h.get("destinationName"),
            "zone": h.get("zoneName"),
            "min_rate": h.get("minRate"),
            "max_rate": h.get("maxRate"),
            "currency": h.get("currency"),
            "latitude": h.get("latitude"),
            "longitude": h.get("longitude"),
            "rooms": rooms_summary,
        })

    return summary


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

def register_hotel_search_tools(mcp: FastMCP):
    """Register hotel search tools with the MCP server."""

    @mcp.tool(
        name="search_hotels",
        annotations={"title": "Search Hotel Availability (Hotelbeds)", "readOnlyHint": True},
    )
    async def search_hotels(
        check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)"),
        check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)"),
        adults: int = Field(2, description="Number of adults per room"),
        rooms: int = Field(1, description="Number of rooms"),
        children: int = Field(0, description="Number of children per room"),
        children_ages: Optional[str] = Field(
            None, description="Comma-separated children ages, e.g. '5,8'"
        ),
        destination: Optional[str] = Field(
            None,
            description="Hotelbeds destination code (e.g. 'PMI' for Palma, 'LON' for London). "
            "Use this OR latitude/longitude, not both.",
        ),
        latitude: Optional[float] = Field(None, description="Latitude for geo search"),
        longitude: Optional[float] = Field(None, description="Longitude for geo search"),
        radius: int = Field(20, description="Search radius in km (for geo search)"),
        hotel_codes: Optional[str] = Field(
            None, description="Comma-separated Hotelbeds hotel codes (max 2000)"
        ),
        min_category: Optional[int] = Field(None, description="Minimum star rating (1-5)"),
        max_category: Optional[int] = Field(None, description="Maximum star rating (1-5)"),
        min_rate: Optional[float] = Field(None, description="Minimum price filter"),
        max_rate: Optional[float] = Field(None, description="Maximum price filter"),
        board_codes: Optional[str] = Field(
            None,
            description="Comma-separated board/meal codes: RO (room only), BB (bed & breakfast), "
            "HB (half board), FB (full board), AI (all inclusive)",
        ),
        max_hotels: int = Field(50, description="Max hotels to return (1-2000)"),
        max_rates_per_room: int = Field(3, description="Max rate options per room type"),
    ) -> str:
        """Search for available hotels via the Hotelbeds/Bedsonline API.

        Provide location using ONE of: destination code, lat/lon coordinates, or hotel codes.
        Returns hotel names, room types, prices, board plans, and cancellation policies.
        """
        try:
            # Build occupancies
            occupancy = {"rooms": rooms, "adults": adults, "children": children}
            if children > 0 and children_ages:
                ages = [int(a.strip()) for a in children_ages.split(",")]
                occupancy["paxes"] = [{"type": "CH", "age": age} for age in ages]

            payload: dict = {
                "stay": {"checkIn": check_in, "checkOut": check_out},
                "occupancies": [occupancy],
                "filter": {
                    "maxHotels": min(max_hotels, 2000),
                    "maxRatesPerRoom": max_rates_per_room,
                },
            }

            # Location — exactly one method required
            if destination:
                payload["destination"] = {"code": destination}
            elif latitude is not None and longitude is not None:
                payload["geolocation"] = {
                    "latitude": latitude,
                    "longitude": longitude,
                    "radius": radius,
                    "unit": "km",
                }
            elif hotel_codes:
                codes = [int(c.strip()) for c in hotel_codes.split(",")]
                payload["hotels"] = {"hotel": codes}
            else:
                return json.dumps(
                    {"error": "Provide destination, lat/lon, or hotel_codes"}, indent=2
                )

            # Optional filters
            if min_category:
                payload["filter"]["minCategory"] = min_category
            if max_category:
                payload["filter"]["maxCategory"] = max_category
            if min_rate:
                payload["filter"]["minRate"] = min_rate
            if max_rate:
                payload["filter"]["maxRate"] = max_rate
            if board_codes:
                payload["boards"] = {
                    "board": [b.strip() for b in board_codes.split(",")]
                }

            logger.info(f"Hotelbeds availability search: {check_in} to {check_out}")
            resp = requests.post(
                _api_url("/hotels"),
                headers=_auth_headers(),
                json=payload,
                timeout=30,
            )

            if resp.status_code != 200:
                return json.dumps(
                    {
                        "error": f"Hotelbeds API error {resp.status_code}",
                        "detail": resp.text[:1000],
                    },
                    indent=2,
                )

            result = _format_hotel_results(resp.json())
            return json.dumps(result, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e), "type": "config_error"}, indent=2)
        except requests.RequestException as e:
            logger.error(f"Hotelbeds request failed: {e}")
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"Hotel search error: {e}")
            return json.dumps({"error": str(e), "type": "search_error"}, indent=2)

    @mcp.tool(
        name="check_hotel_rates",
        annotations={"title": "Verify Hotel Rate (Hotelbeds)", "readOnlyHint": True},
    )
    async def check_hotel_rates(
        rate_keys: str = Field(
            ...,
            description="Comma-separated rateKey values from search_hotels results "
            "(required when rateType was 'RECHECK'). Max 10 keys.",
        ),
    ) -> str:
        """Re-verify hotel rate pricing and availability.

        Required before booking when a rate's rateType is 'RECHECK'.
        If rateType was 'BOOKABLE', you can skip this and book directly.
        Returns updated pricing, cancellation policies, and confirmed availability.
        """
        try:
            keys = [k.strip() for k in rate_keys.split(",")]
            if len(keys) > 10:
                return json.dumps(
                    {"error": "Maximum 10 rate keys per checkrates call"}, indent=2
                )

            payload = {"rooms": [{"rateKey": key} for key in keys]}

            logger.info(f"Hotelbeds checkrates for {len(keys)} rate(s)")
            resp = requests.post(
                _api_url("/checkrates"),
                headers=_auth_headers(),
                json=payload,
                timeout=30,
            )

            if resp.status_code != 200:
                return json.dumps(
                    {
                        "error": f"Hotelbeds API error {resp.status_code}",
                        "detail": resp.text[:1000],
                    },
                    indent=2,
                )

            data = resp.json()
            hotel = data.get("hotel", {})
            rooms_detail = []
            for room in hotel.get("rooms", []):
                for rate in room.get("rates", []):
                    rooms_detail.append({
                        "room_name": room.get("name"),
                        "rate_key": rate.get("rateKey"),
                        "rate_type": rate.get("rateType"),
                        "net_price": rate.get("net"),
                        "board": rate.get("boardName", rate.get("boardCode")),
                        "payment_type": rate.get("paymentType"),
                        "cancellation_policies": rate.get("cancellationPolicies"),
                    })

            return json.dumps(
                {
                    "hotel_code": hotel.get("code"),
                    "hotel_name": hotel.get("name"),
                    "check_in": hotel.get("checkIn"),
                    "check_out": hotel.get("checkOut"),
                    "currency": hotel.get("currency"),
                    "rooms": rooms_detail,
                },
                indent=2,
            )

        except ValueError as e:
            return json.dumps({"error": str(e), "type": "config_error"}, indent=2)
        except requests.RequestException as e:
            logger.error(f"Hotelbeds checkrates failed: {e}")
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"Checkrates error: {e}")
            return json.dumps({"error": str(e), "type": "checkrates_error"}, indent=2)

    @mcp.tool(
        name="get_hotel_details",
        annotations={"title": "Get Hotel Details (Hotelbeds)", "readOnlyHint": True},
    )
    async def get_hotel_details(
        hotel_codes: str = Field(
            ..., description="Comma-separated Hotelbeds hotel codes to look up"
        ),
    ) -> str:
        """Retrieve static hotel content: description, images, facilities, address, coordinates.

        Use this to get detailed information about specific hotels found via search_hotels.
        Data comes from the Hotelbeds Content API (updated weekly).
        """
        try:
            codes = [c.strip() for c in hotel_codes.split(",")]
            codes_param = ",".join(codes)

            logger.info(f"Hotelbeds content lookup for hotel(s): {codes_param}")
            resp = requests.get(
                _content_url(f"/hotels?codes={codes_param}&language=ENG&useSecondaryLanguage=true"),
                headers=_auth_headers(),
                timeout=30,
            )

            if resp.status_code != 200:
                return json.dumps(
                    {
                        "error": f"Hotelbeds Content API error {resp.status_code}",
                        "detail": resp.text[:1000],
                    },
                    indent=2,
                )

            data = resp.json()
            raw_hotels = data.get("hotels", [])
            details = []
            for h in raw_hotels:
                images = []
                for img in (h.get("images") or [])[:5]:
                    images.append({
                        "type": img.get("imageTypeCode"),
                        "path": img.get("path"),
                        "order": img.get("order"),
                    })

                facilities = []
                for fac in (h.get("facilities") or [])[:20]:
                    facilities.append({
                        "code": fac.get("facilityCode"),
                        "group": fac.get("facilityGroupCode"),
                        "description": fac.get("description", {}).get("content"),
                    })

                details.append({
                    "code": h.get("code"),
                    "name": h.get("name", {}).get("content"),
                    "description": h.get("description", {}).get("content", "")[:500],
                    "category": h.get("categoryCode"),
                    "address": h.get("address", {}).get("content"),
                    "city": h.get("city", {}).get("content"),
                    "country": h.get("countryCode"),
                    "latitude": h.get("coordinates", {}).get("latitude"),
                    "longitude": h.get("coordinates", {}).get("longitude"),
                    "email": h.get("email"),
                    "phone": h.get("phones", [{}])[0].get("phoneNumber") if h.get("phones") else None,
                    "web": h.get("web"),
                    "images": images,
                    "facilities": facilities,
                })

            return json.dumps({"total": len(details), "hotels": details}, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e), "type": "config_error"}, indent=2)
        except requests.RequestException as e:
            logger.error(f"Hotelbeds content request failed: {e}")
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"Hotel details error: {e}")
            return json.dumps({"error": str(e), "type": "content_error"}, indent=2)

    # ====================================================================
    # BEDSONLINE PORTAL BROWSER TOOLS (Playwright Stealth)
    # ====================================================================

    @mcp.tool(
        name="bedsonline_browse_search",
        annotations={"title": "Browse Bedsonline Hotel Search (Visual)", "readOnlyHint": True},
    )
    async def bedsonline_browse_search(
        username: Optional[str] = Field(None, description="Bedsonline login email (reads from credentials file if omitted)"),
        password: Optional[str] = Field(None, description="Bedsonline login password (reads from credentials file if omitted)"),
        destination: str = Field(..., description="Destination city or hotel name to type into search"),
        check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)"),
        check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)"),
        rooms: int = Field(1, description="Number of rooms"),
        adults: int = Field(2, description="Adults per room"),
        screenshot_steps: bool = Field(True, description="Take screenshots at each step for review"),
    ) -> str:
        """Log into the Bedsonline portal and perform a visual hotel search.

        Opens the Bedsonline web app in a stealth browser, logs in with your
        credentials, fills in the search form, and returns results with screenshots.
        Use this when you want to see the portal UI or when the API doesn't
        cover what you need (e.g. special promotions, visual comparison).
        """
        try:
            # Load portal credentials
            cred_file = Path.home() / "Thunderbird" / "hotelbeds_credentials.json"
            if (not username or not password) and cred_file.exists():
                with open(cred_file) as f:
                    creds = json.load(f)
                username = username or creds.get("portal_username", "")
                password = password or creds.get("portal_password", "")

            if not username or not password:
                return json.dumps({
                    "error": "Portal credentials required. Add portal_username and "
                    "portal_password to ~/Thunderbird/hotelbeds_credentials.json"
                }, indent=2)

            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            screenshots = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            async with Stealth().use_async(async_playwright()) as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()

                # Step 1: Navigate to login
                logger.info("Bedsonline portal: navigating to login")
                await page.goto(HotelbedsConfig.PORTAL_LOGIN_URL, wait_until="networkidle", timeout=45000)
                await page.wait_for_timeout(2000)

                if screenshot_steps:
                    path = SCREENSHOTS_DIR / f"bedsonline_01_login_{timestamp}.png"
                    await page.screenshot(path=str(path), full_page=False)
                    screenshots.append({"step": "login_page", "path": str(path)})

                # Step 2: Fill login form
                logger.info("Bedsonline portal: logging in")
                # Try common login form selectors
                email_selectors = [
                    'input[type="email"]', 'input[name="email"]',
                    'input[name="username"]', 'input#email', 'input#username',
                    'input[placeholder*="mail"]', 'input[placeholder*="user"]',
                ]
                password_selectors = [
                    'input[type="password"]', 'input[name="password"]',
                    'input#password',
                ]

                email_filled = False
                for sel in email_selectors:
                    try:
                        if await page.locator(sel).count() > 0:
                            await page.fill(sel, username)
                            email_filled = True
                            break
                    except Exception:
                        continue

                password_filled = False
                for sel in password_selectors:
                    try:
                        if await page.locator(sel).count() > 0:
                            await page.fill(sel, password)
                            password_filled = True
                            break
                    except Exception:
                        continue

                if not email_filled or not password_filled:
                    if screenshot_steps:
                        path = SCREENSHOTS_DIR / f"bedsonline_login_fail_{timestamp}.png"
                        await page.screenshot(path=str(path), full_page=False)
                        screenshots.append({"step": "login_form_not_found", "path": str(path)})
                    await browser.close()
                    return json.dumps({
                        "error": "Could not find login form fields",
                        "screenshots": screenshots,
                        "page_text": (await page.evaluate("document.body.innerText"))[:2000],
                    }, indent=2)

                # Click login/submit button
                submit_selectors = [
                    'button[type="submit"]', 'input[type="submit"]',
                    'button:has-text("Log in")', 'button:has-text("Login")',
                    'button:has-text("Sign in")', 'button:has-text("Submit")',
                ]
                for sel in submit_selectors:
                    try:
                        if await page.locator(sel).count() > 0:
                            await page.click(sel, timeout=5000)
                            break
                    except Exception:
                        continue

                await page.wait_for_timeout(5000)

                if screenshot_steps:
                    path = SCREENSHOTS_DIR / f"bedsonline_02_after_login_{timestamp}.png"
                    await page.screenshot(path=str(path), full_page=False)
                    screenshots.append({"step": "after_login", "path": str(path)})

                # Step 3: Navigate to accommodation search
                logger.info("Bedsonline portal: navigating to hotel search")
                current_url = page.url
                if "accommodation" not in current_url:
                    await page.goto(HotelbedsConfig.PORTAL_SEARCH_URL, wait_until="networkidle", timeout=45000)
                    await page.wait_for_timeout(3000)

                if screenshot_steps:
                    path = SCREENSHOTS_DIR / f"bedsonline_03_search_page_{timestamp}.png"
                    await page.screenshot(path=str(path), full_page=False)
                    screenshots.append({"step": "search_page", "path": str(path)})

                # Step 4: Fill search form
                logger.info(f"Bedsonline portal: searching for '{destination}'")

                # Try to find and fill the destination field
                dest_selectors = [
                    'input[placeholder*="estination"]',
                    'input[placeholder*="hotel"]',
                    'input[placeholder*="city"]',
                    'input[aria-label*="estination"]',
                    'input[aria-label*="search"]',
                    'input[name*="destination"]',
                    'input[name*="search"]',
                    'input[data-testid*="destination"]',
                    'input[class*="search"]',
                    'input[class*="destination"]',
                ]

                dest_filled = False
                for sel in dest_selectors:
                    try:
                        loc = page.locator(sel)
                        if await loc.count() > 0:
                            await loc.first.click()
                            await page.wait_for_timeout(500)
                            await loc.first.fill(destination)
                            await page.wait_for_timeout(2000)
                            # Try to click first autocomplete suggestion
                            suggestion_selectors = [
                                'li[class*="suggestion"]', 'div[class*="suggestion"]',
                                'li[class*="result"]', 'div[class*="result"]',
                                'li[class*="option"]', 'div[class*="option"]',
                                '[role="option"]', '[role="listbox"] li',
                                'ul[class*="dropdown"] li', 'div[class*="dropdown"] li',
                            ]
                            for sug_sel in suggestion_selectors:
                                try:
                                    sug = page.locator(sug_sel)
                                    if await sug.count() > 0:
                                        await sug.first.click()
                                        break
                                except Exception:
                                    continue
                            dest_filled = True
                            break
                    except Exception:
                        continue

                await page.wait_for_timeout(1000)

                # Try to fill date fields
                date_selectors = [
                    'input[name*="checkin"]', 'input[name*="check_in"]',
                    'input[name*="checkIn"]', 'input[placeholder*="Check-in"]',
                    'input[data-testid*="checkin"]', 'input[aria-label*="Check-in"]',
                ]
                for sel in date_selectors:
                    try:
                        loc = page.locator(sel)
                        if await loc.count() > 0:
                            await loc.first.fill(check_in)
                            break
                    except Exception:
                        continue

                date_out_selectors = [
                    'input[name*="checkout"]', 'input[name*="check_out"]',
                    'input[name*="checkOut"]', 'input[placeholder*="Check-out"]',
                    'input[data-testid*="checkout"]', 'input[aria-label*="Check-out"]',
                ]
                for sel in date_out_selectors:
                    try:
                        loc = page.locator(sel)
                        if await loc.count() > 0:
                            await loc.first.fill(check_out)
                            break
                    except Exception:
                        continue

                if screenshot_steps:
                    path = SCREENSHOTS_DIR / f"bedsonline_04_form_filled_{timestamp}.png"
                    await page.screenshot(path=str(path), full_page=False)
                    screenshots.append({"step": "form_filled", "path": str(path)})

                # Step 5: Click search button
                search_selectors = [
                    'button:has-text("Search")', 'button:has-text("search")',
                    'button[type="submit"]', 'button[class*="search"]',
                    'button[data-testid*="search"]', 'a:has-text("Search")',
                ]
                for sel in search_selectors:
                    try:
                        loc = page.locator(sel)
                        if await loc.count() > 0:
                            await loc.first.click()
                            break
                    except Exception:
                        continue

                # Wait for results to load
                logger.info("Bedsonline portal: waiting for results")
                await page.wait_for_timeout(8000)

                # Scroll to load more results
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

                if screenshot_steps:
                    path = SCREENSHOTS_DIR / f"bedsonline_05_results_{timestamp}.png"
                    await page.screenshot(path=str(path), full_page=True)
                    screenshots.append({"step": "search_results", "path": str(path)})

                # Extract page content
                page_text = await page.evaluate("document.body.innerText")
                page_title = await page.title()
                final_url = page.url

                await browser.close()

                return json.dumps({
                    "status": "success",
                    "destination": destination,
                    "check_in": check_in,
                    "check_out": check_out,
                    "destination_found": dest_filled,
                    "page_title": page_title,
                    "final_url": final_url,
                    "screenshots": screenshots,
                    "results_text": page_text[:8000],
                }, indent=2)

        except Exception as e:
            logger.error(f"Bedsonline browser search error: {e}")
            return json.dumps({"error": str(e), "type": "browser_error"}, indent=2)

    @mcp.tool(
        name="bedsonline_browse_interact",
        annotations={"title": "Interact with Bedsonline Portal", "readOnlyHint": True},
    )
    async def bedsonline_browse_interact(
        url: str = Field(
            "https://app.bedsonline.com/accommodation",
            description="Bedsonline page URL to interact with",
        ),
        actions: str = Field(
            "[]",
            description='JSON array of actions: '
            '[{"action":"click","selector":"button.filter"}, '
            '{"action":"type","selector":"input.search","text":"Paris"}, '
            '{"action":"scroll","direction":"down"}, '
            '{"action":"wait","seconds":3}, '
            '{"action":"screenshot","name":"step1"}]',
        ),
        username: Optional[str] = Field(None, description="Bedsonline login email (if login needed)"),
        password: Optional[str] = Field(None, description="Bedsonline login password (if login needed)"),
        login_first: bool = Field(False, description="Log in before performing actions"),
        screenshot: bool = Field(True, description="Take a final screenshot"),
        max_length: int = Field(30000, description="Max chars of page text to return (Claude 1M context is GA)"),
    ) -> str:
        """Interact with any Bedsonline portal page using click/type/scroll actions.

        Use this for:
        - Applying filters on search results
        - Clicking into hotel details
        - Navigating between pages
        - Comparing rates visually
        - Any portal interaction the API doesn't cover
        """
        try:
            action_list = json.loads(actions)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON in actions parameter"})

        try:
            # Load portal credentials if login needed
            if login_first:
                cred_file = Path.home() / "Thunderbird" / "hotelbeds_credentials.json"
                if (not username or not password) and cred_file.exists():
                    with open(cred_file) as f:
                        creds = json.load(f)
                    username = username or creds.get("portal_username", "")
                    password = password or creds.get("portal_password", "")

            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            async with Stealth().use_async(async_playwright()) as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()

                # Login flow if requested
                if login_first and username and password:
                    await page.goto(HotelbedsConfig.PORTAL_LOGIN_URL, wait_until="networkidle", timeout=45000)
                    await page.wait_for_timeout(2000)

                    for sel in ['input[type="email"]', 'input[name="email"]', 'input[name="username"]']:
                        try:
                            if await page.locator(sel).count() > 0:
                                await page.fill(sel, username)
                                break
                        except Exception:
                            continue

                    for sel in ['input[type="password"]', 'input[name="password"]']:
                        try:
                            if await page.locator(sel).count() > 0:
                                await page.fill(sel, password)
                                break
                        except Exception:
                            continue

                    for sel in ['button[type="submit"]', 'button:has-text("Log in")', 'button:has-text("Sign in")']:
                        try:
                            if await page.locator(sel).count() > 0:
                                await page.click(sel, timeout=5000)
                                break
                        except Exception:
                            continue

                    await page.wait_for_timeout(5000)

                # Navigate to target URL
                await page.goto(url, wait_until="networkidle", timeout=45000)
                await page.wait_for_timeout(3000)

                # Execute actions
                action_results = []
                for i, act in enumerate(action_list):
                    action_type = act.get("action", "")
                    try:
                        if action_type == "click":
                            await page.click(act["selector"], timeout=10000)
                            action_results.append({"step": i + 1, "action": "click", "selector": act["selector"], "status": "ok"})

                        elif action_type == "type":
                            await page.fill(act["selector"], act["text"])
                            action_results.append({"step": i + 1, "action": "type", "status": "ok"})

                        elif action_type == "scroll":
                            direction = act.get("direction", "down")
                            if direction == "down":
                                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            elif direction == "up":
                                await page.evaluate("window.scrollTo(0, 0)")
                            else:
                                pixels = int(act.get("pixels", 500))
                                await page.evaluate(f"window.scrollBy(0, {pixels})")
                            action_results.append({"step": i + 1, "action": "scroll", "status": "ok"})

                        elif action_type == "wait":
                            secs = min(act.get("seconds", 2), 15)
                            await page.wait_for_timeout(secs * 1000)
                            action_results.append({"step": i + 1, "action": "wait", "status": "ok"})

                        elif action_type == "screenshot":
                            name = act.get("name", f"step_{i + 1}")
                            path = SCREENSHOTS_DIR / f"bedsonline_{name}_{timestamp}.png"
                            await page.screenshot(path=str(path), full_page=act.get("full_page", False))
                            action_results.append({"step": i + 1, "action": "screenshot", "path": str(path), "status": "ok"})

                        elif action_type == "select":
                            await page.select_option(act["selector"], act["value"])
                            action_results.append({"step": i + 1, "action": "select", "status": "ok"})

                        elif action_type == "hover":
                            await page.hover(act["selector"], timeout=10000)
                            action_results.append({"step": i + 1, "action": "hover", "status": "ok"})

                        else:
                            action_results.append({"step": i + 1, "action": action_type, "status": "unknown_action"})

                    except Exception as e:
                        action_results.append({"step": i + 1, "action": action_type, "status": "error", "error": str(e)})

                # Collect final state
                page_text = await page.evaluate("document.body.innerText")
                result = {
                    "status": "success",
                    "url": page.url,
                    "title": await page.title(),
                    "actions": action_results,
                    "text": page_text[:max_length],
                }

                if screenshot:
                    path = SCREENSHOTS_DIR / f"bedsonline_final_{timestamp}.png"
                    await page.screenshot(path=str(path), full_page=False)
                    result["screenshot"] = str(path)

                await browser.close()
                return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Bedsonline interact error: {e}")
            return json.dumps({"error": str(e), "type": "browser_error"}, indent=2)

    # ====================================================================
    # HOTEL COMPARISON + QUOTE TOOLS
    # ====================================================================

    EUR_TO_USD = 1.09
    STANDARD_MARKUP = 0.25
    PREMIUM_MARKUP = 0.22
    THUNDERBIRD_DIR = Path.home() / "Thunderbird"

    def _fmt_usd(amount) -> str:
        try:
            return f"${float(amount):,.2f}"
        except (ValueError, TypeError):
            return str(amount)

    @mcp.tool(
        name="compare_hotels",
        annotations={"title": "Compare Hotels Side-by-Side", "readOnlyHint": True},
    )
    async def compare_hotels(
        hotels_json: str = Field(
            ...,
            description="JSON array of 2-3 hotel objects to compare. Each needs: "
            "name (str), category (str like '5 STARS'), zone (str), "
            "min_rate (str/number in EUR or USD), currency (str), "
            "rooms (array of {room_name, board, net_price, currency, cancellation_policies}). "
            "Use results from search_hotels or get_hotel_details.",
        ),
        markup: float = Field(0.25, description="Markup rate (0.25 = 25% standard, 0.22 = 22% premium)"),
        nights: int = Field(1, description="Number of nights (for per-night price calculation)"),
    ) -> str:
        """Compare 2-3 hotels side-by-side with pricing and cancellation summary.

        Takes hotel objects from search_hotels results and creates a structured
        comparison with net prices, client prices (with markup), per-night rates,
        cancellation policies, and a value recommendation.
        """
        try:
            hotels = json.loads(hotels_json)
            if not isinstance(hotels, list) or len(hotels) < 2:
                return json.dumps({"error": "Provide 2-3 hotels to compare"}, indent=2)
            hotels = hotels[:3]

            comparison = []
            best_price = float("inf")
            best_idx = 0

            for i, hotel in enumerate(hotels):
                currency = hotel.get("currency", "EUR")
                min_rate = float(hotel.get("min_rate", 0))

                # Convert to USD
                usd_net = min_rate * EUR_TO_USD if currency.upper() == "EUR" else min_rate
                client_total = usd_net * (1 + markup)
                per_night_net = usd_net / max(nights, 1)
                per_night_client = client_total / max(nights, 1)

                if client_total < best_price:
                    best_price = client_total
                    best_idx = i

                # Best room option
                rooms = hotel.get("rooms", [])
                best_room = rooms[0] if rooms else {}
                room_name = best_room.get("room_name", "Standard")
                board = best_room.get("board", "Room Only")

                # Cancellation summary
                cancel_policies = best_room.get("cancellation_policies", [])
                cancel_summary = "Non-refundable"
                if cancel_policies:
                    first = cancel_policies[0]
                    cancel_date = first.get("from", "")[:10]
                    cancel_amount = first.get("amount", "")
                    if len(cancel_policies) > 1:
                        cancel_summary = f"Partial penalty from {cancel_date}, full penalty later"
                    else:
                        cancel_summary = f"Full penalty from {cancel_date}"

                comparison.append({
                    "option": i + 1,
                    "name": hotel.get("name", f"Hotel {i+1}"),
                    "category": hotel.get("category", "N/A"),
                    "zone": hotel.get("zone", "N/A"),
                    "room": room_name,
                    "board": board,
                    "total_options": len(rooms),
                    "net_total": _fmt_usd(usd_net),
                    "client_total": _fmt_usd(client_total),
                    "per_night_net": _fmt_usd(per_night_net),
                    "per_night_client": _fmt_usd(per_night_client),
                    "nights": nights,
                    "markup": f"{markup * 100:.0f}%",
                    "cancellation": cancel_summary,
                    "is_best_value": False,
                    "client_raw": round(client_total, 2),
                })

            comparison[best_idx]["is_best_value"] = True

            return json.dumps({
                "comparison": comparison,
                "total_hotels": len(comparison),
                "best_value": comparison[best_idx]["name"],
                "nights": nights,
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except Exception as e:
            logger.error(f"Hotel comparison error: {e}")
            return json.dumps({"error": str(e), "type": "compare_error"}, indent=2)

    @mcp.tool(
        name="render_hotel_quote_pdf",
        annotations={"title": "Render Hotel Quote PDF (D2M Branded)", "readOnlyHint": False},
    )
    async def render_hotel_quote_pdf(
        client_name: str = Field(..., description="Client name for the quote"),
        destination: str = Field(..., description="Destination city/region (e.g. 'Kyoto, Japan')"),
        check_in: str = Field(..., description="Check-in date (human-readable, e.g. 'April 1, 2026')"),
        check_out: str = Field(..., description="Check-out date (human-readable)"),
        nights: int = Field(1, description="Number of nights"),
        travelers: str = Field("2", description="Number of travelers"),
        hotels_json: str = Field(
            ...,
            description="JSON array of hotel comparison objects. Each: "
            "option (int), name (str), category (str), zone (str), room (str), "
            "board (str), client_total (str like '$1,234.00'), per_night_client (str), "
            "cancellation (str), is_best_value (bool)",
        ),
        recommendation: Optional[str] = Field(None, description="Recommendation text"),
        notes: Optional[str] = Field(None, description="Important notes for the client"),
        output_filename: Optional[str] = Field(None, description="Output PDF filename"),
    ) -> str:
        """Render a branded D2M hotel quote PDF with comparison table.

        Generates a professional PDF with hotel option cards, pricing comparison,
        cancellation policies, and D2M branding. Returns the path to the generated PDF.
        """
        try:
            hotels = json.loads(hotels_json)

            if not output_filename:
                safe_client = client_name.replace(" ", "_")
                safe_dest = destination.split(",")[0].replace(" ", "_")
                month_year = datetime.now().strftime("%b%Y")
                output_filename = f"{safe_client}_{safe_dest}_Hotels_{month_year}.pdf"

            output_dir = THUNDERBIRD_DIR / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = output_dir / output_filename
            html_path = output_dir / output_filename.replace(".pdf", ".html")

            # Build inline HTML (self-contained, same brand as flight template)
            rows_html = ""
            for h in hotels:
                pick_class = ' style="background:#f5e9c8;border-left:4px solid #c9a84c;"' if h.get("is_best_value") else ""
                pick_badge = ' <span style="background:#c9a84c;color:#0d1b2e;font-size:0.7em;font-weight:700;padding:2px 8px;border-radius:10px;">BEST VALUE</span>' if h.get("is_best_value") else ""
                rows_html += f"""
                <tr{pick_class}>
                    <td style="padding:12px 15px;border-bottom:1px solid #e9ecef;font-weight:600;">Option {h.get('option','')}{pick_badge}</td>
                    <td style="padding:12px 15px;border-bottom:1px solid #e9ecef;">{h.get('name','')}</td>
                    <td style="padding:12px 15px;border-bottom:1px solid #e9ecef;">{h.get('category','')}</td>
                    <td style="padding:12px 15px;border-bottom:1px solid #e9ecef;">{h.get('room','')}<br><span style="font-size:0.8em;color:#8a9ab5;">{h.get('board','')}</span></td>
                    <td style="padding:12px 15px;border-bottom:1px solid #e9ecef;">{h.get('per_night_client','')}</td>
                    <td style="padding:12px 15px;border-bottom:1px solid #e9ecef;font-weight:700;color:#0d1b2e;">{h.get('client_total','')}</td>
                    <td style="padding:12px 15px;border-bottom:1px solid #e9ecef;font-size:0.85em;">{h.get('cancellation','')}</td>
                </tr>"""

            rec_html = ""
            if recommendation:
                rec_html = f"""
                <div style="margin:30px 40px;padding:25px;background:linear-gradient(135deg,#0d1b2e,#1e3358);color:#ffffff;border-radius:8px;border-left:5px solid #c9a84c;">
                    <h3 style="color:#e8c97a;margin:0 0 10px;font-size:1.1em;">Our Recommendation</h3>
                    <p style="margin:0;font-size:0.95em;line-height:1.6;">{recommendation}</p>
                </div>"""

            notes_text = notes or "Rates subject to availability and may change. Cancellation policies apply as noted. All prices include taxes and fees."

            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{client_name} — Hotel Options | Dreams2Memories Travel</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif; line-height:1.5; color:#0d1b2e; background:#f4f6f9; }}
        .container {{ max-width:900px; margin:0 auto; background:#ffffff; box-shadow:0 0 30px rgba(0,0,0,0.08); }}
        @media print {{ body {{ background:white; }} .container {{ box-shadow:none; max-width:100%; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div style="background:linear-gradient(135deg,#0d1b2e,#152540);color:#ffffff;padding:60px 50px;text-align:center;border-bottom:4px solid #c9a84c;">
            <h1 style="font-size:2.2em;font-weight:300;margin-bottom:8px;">Hotel Options for {client_name}</h1>
            <div style="font-size:1.6em;color:#e8c97a;margin:15px 0;font-weight:600;">{destination}</div>
            <div style="margin-top:20px;font-size:0.95em;color:#8a9ab5;border-top:1px solid rgba(255,255,255,0.15);padding-top:15px;">
                <span style="margin:0 15px;">{check_in} — {check_out}</span>
                <span style="margin:0 15px;">{nights} night{'s' if nights != 1 else ''}</span>
                <span style="margin:0 15px;">{travelers} traveler{'s' if travelers != '1' else ''}</span>
                <span style="margin:0 15px;">Prepared {datetime.now().strftime('%B %d, %Y')}</span>
            </div>
        </div>

        <h2 style="font-size:1.4em;color:#0d1b2e;padding:30px 40px 15px;border-bottom:2px solid #c9a84c;margin:0 40px;">Your Options</h2>
        <div style="padding:30px 40px;">
            <table style="width:100%;border-collapse:collapse;font-size:0.88em;">
                <thead>
                    <tr style="background:#0d1b2e;color:#ffffff;">
                        <th style="padding:12px 15px;text-align:left;font-size:0.85em;text-transform:uppercase;">Option</th>
                        <th style="padding:12px 15px;text-align:left;font-size:0.85em;text-transform:uppercase;">Hotel</th>
                        <th style="padding:12px 15px;text-align:left;font-size:0.85em;text-transform:uppercase;">Rating</th>
                        <th style="padding:12px 15px;text-align:left;font-size:0.85em;text-transform:uppercase;">Room / Board</th>
                        <th style="padding:12px 15px;text-align:left;font-size:0.85em;text-transform:uppercase;">Per Night</th>
                        <th style="padding:12px 15px;text-align:left;font-size:0.85em;text-transform:uppercase;">Total</th>
                        <th style="padding:12px 15px;text-align:left;font-size:0.85em;text-transform:uppercase;">Cancellation</th>
                    </tr>
                </thead>
                <tbody>{rows_html}
                </tbody>
            </table>
        </div>

        {rec_html}

        <div style="padding:20px 40px 30px;font-size:0.85em;color:#7f8c8d;">
            <p><strong>Important:</strong> {notes_text}</p>
        </div>

        <div style="background:#0d1b2e;color:#ffffff;padding:40px 50px;text-align:center;border-top:4px solid #c9a84c;">
            <h3 style="color:#e8c97a;margin-bottom:10px;">Ready to Book?</h3>
            <p><strong>Dreams2Memories Travel, LLC</strong></p>
            <p style="font-size:0.95em;color:#8a9ab5;margin-top:5px;">
                <a href="mailto:johnloucks3@gmail.com" style="color:#c9a84c;text-decoration:none;">johnloucks3@gmail.com</a> | (719) 291-0742
            </p>
        </div>
    </div>
</body>
</html>"""

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            WeasyHTML(string=html_content, base_url=str(THUNDERBIRD_DIR)).write_pdf(str(pdf_path))

            logger.info(f"Hotel quote PDF rendered: {pdf_path}")
            return json.dumps({
                "status": "success",
                "pdf_path": str(pdf_path),
                "html_path": str(html_path),
                "client_name": client_name,
                "destination": destination,
                "hotels_count": len(hotels),
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except Exception as e:
            logger.error(f"Hotel quote PDF render error: {e}")
            return json.dumps({"error": str(e), "type": "render_error"}, indent=2)

    @mcp.tool(
        name="email_hotel_quote",
        annotations={"title": "Email Hotel Quote to Client", "readOnlyHint": False},
    )
    async def email_hotel_quote(
        to_email: str = Field(..., description="Client email address"),
        client_name: str = Field(..., description="Client name for greeting"),
        destination: str = Field(..., description="Destination (e.g. 'Kyoto, Japan')"),
        check_in: str = Field(..., description="Check-in date (human-readable)"),
        check_out: str = Field(..., description="Check-out date (human-readable)"),
        summary_json: str = Field(
            ...,
            description="JSON array of hotel summary objects for email body. Each: "
            "option (int), name (str), category (str), room (str), board (str), "
            "per_night_client (str), client_total (str), cancellation (str)",
        ),
        recommendation: Optional[str] = Field(None, description="Brief recommendation text"),
        pdf_path: Optional[str] = Field(
            None,
            description="Path to hotel quote PDF to attach. Use render_hotel_quote_pdf first.",
        ),
        subject: Optional[str] = Field(None, description="Custom email subject"),
    ) -> str:
        """Create a Gmail draft with hotel quote summary and optional PDF attachment.

        Generates a branded HTML email with hotel comparison table and attaches
        the PDF if provided. Creates a draft (does NOT send — you review first).
        """
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            summary = json.loads(summary_json)

            if not subject:
                subject = f"Your Hotel Options: {destination}"

            rows_html = ""
            for h in summary:
                rows_html += f"""
                <tr>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;font-weight:600;">Option {h.get('option','')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{h.get('name','')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{h.get('category','')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{h.get('room','')}<br><small style="color:#8a9ab5;">{h.get('board','')}</small></td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{h.get('per_night_client','')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;font-weight:700;color:#0d1b2e;">{h.get('client_total','')}</td>
                </tr>"""

            rec_html = ""
            if recommendation:
                rec_html = f"""
                <div style="margin:25px 0;padding:20px;background:#0d1b2e;color:#ffffff;border-radius:6px;border-left:4px solid #c9a84c;">
                    <strong style="color:#e8c97a;">Our Recommendation:</strong><br>
                    <span style="font-size:0.95em;line-height:1.6;">{recommendation}</span>
                </div>"""

            attachment_note = ""
            if pdf_path:
                attachment_note = "<p style='font-size:0.9em;color:#8a9ab5;margin-top:15px;'>See the attached PDF for the full detailed comparison.</p>"

            html_body = f"""
            <div style="font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;max-width:700px;margin:0 auto;color:#2c3e50;">
                <div style="background:linear-gradient(135deg,#0d1b2e,#152540);color:#ffffff;padding:35px 30px;text-align:center;border-bottom:3px solid #c9a84c;">
                    <h2 style="margin:0 0 5px;font-weight:300;font-size:1.6em;">Hotel Options</h2>
                    <div style="color:#e8c97a;font-size:1.2em;font-weight:600;">{destination}</div>
                    <div style="color:#8a9ab5;margin-top:10px;font-size:0.9em;">{check_in} — {check_out}</div>
                </div>

                <div style="padding:25px 30px;">
                    <p>Hi {client_name},</p>
                    <p style="margin:15px 0;">I've curated some wonderful hotel options for your stay. Here's a quick overview — let me know which one catches your eye or if you'd like to explore more.</p>

                    <table style="width:100%;border-collapse:collapse;font-size:0.85em;margin:20px 0;">
                        <thead>
                            <tr style="background:#0d1b2e;color:#ffffff;">
                                <th style="padding:10px 12px;text-align:left;">Option</th>
                                <th style="padding:10px 12px;text-align:left;">Hotel</th>
                                <th style="padding:10px 12px;text-align:left;">Rating</th>
                                <th style="padding:10px 12px;text-align:left;">Room</th>
                                <th style="padding:10px 12px;text-align:left;">Per Night</th>
                                <th style="padding:10px 12px;text-align:left;">Total</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}
                        </tbody>
                    </table>

                    {rec_html}
                    {attachment_note}

                    <p style="margin-top:25px;">Warmly,<br><strong>John Loucks</strong><br>Dreams2Memories Travel, LLC<br>
                    <a href="mailto:johnloucks3@gmail.com" style="color:#c9a84c;">johnloucks3@gmail.com</a> | (719) 291-0742</p>
                </div>

                <div style="background:#0d1b2e;color:#8a9ab5;padding:20px;text-align:center;font-size:0.8em;border-top:3px solid #c9a84c;">
                    Dreams2Memories Travel, LLC | Monument, CO
                </div>
            </div>"""

            # Create Gmail draft
            creds_path = THUNDERBIRD_DIR / "credentials.json"
            if not creds_path.exists():
                return json.dumps({
                    "error": "Google service account credentials not found",
                }, indent=2)

            scopes = ["https://www.googleapis.com/auth/gmail.modify"]
            credentials = service_account.Credentials.from_service_account_file(
                str(creds_path), scopes=scopes
            )
            delegated = credentials.with_subject("d2mconcierge@gmail.com")
            gmail_service = build("gmail", "v1", credentials=delegated)

            msg = MIMEMultipart()
            msg["to"] = to_email
            msg["from"] = "d2mconcierge@gmail.com"
            msg["subject"] = subject
            msg.attach(MIMEText(html_body, "html"))

            if pdf_path and Path(pdf_path).exists():
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                pdf_attachment = MIMEApplication(pdf_data, _subtype="pdf")
                pdf_attachment.add_header(
                    "Content-Disposition", "attachment",
                    filename=Path(pdf_path).name,
                )
                msg.attach(pdf_attachment)

            raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
            draft = gmail_service.users().drafts().create(
                userId="me",
                body={"message": {"raw": raw_msg}},
            ).execute()

            draft_id = draft.get("id", "unknown")
            logger.info(f"Hotel quote Gmail draft created: {draft_id}")

            return json.dumps({
                "status": "draft_created",
                "draft_id": draft_id,
                "to": to_email,
                "subject": subject,
                "has_pdf_attachment": bool(pdf_path and Path(pdf_path).exists()),
                "message": "Gmail draft ready for review. Open Gmail to review and send.",
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except Exception as e:
            logger.error(f"Email hotel quote error: {e}")
            return json.dumps({"error": str(e), "type": "email_error"}, indent=2)

    logger.info("Hotel search tools registered (Hotelbeds/Bedsonline)")


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def test_status():
        """Quick connectivity test against the Hotelbeds status endpoint."""
        try:
            resp = requests.get(
                _api_url("/status"),
                headers=_auth_headers(),
                timeout=10,
            )
            print(f"Status: {resp.status_code}")
            print(json.dumps(resp.json(), indent=2))
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(test_status())

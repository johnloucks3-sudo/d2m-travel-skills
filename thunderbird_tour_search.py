"""
Dreams2Memories Tour & Activity Search MCP Module
==================================================

Tour/activity search, comparison, and quote generation:
- Amadeus Tours & Activities API (by destination + coordinates)
- Musement API (free, global catalog)
- Agent portal browser scraping (ProjectExpedition, TAAP, Viator TA)
- Consumer price scraping (Expedia, public Viator)
- Content scraping (Fodor's, Rick Steves recommendations)
- Side-by-side comparison with net+commission pricing
- Branded PDF quote generation with D2M logo and slogan
- Gmail draft with quote attachment

Integrates with: travel_mcp_server.py
Dependencies: requests, playwright, playwright-stealth, jinja2, weasyprint
"""

import json
import logging
import time
import base64
import requests
import asyncio
from typing import Optional
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from weasyprint import HTML as WeasyHTML
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
SCREENSHOTS_DIR = THUNDERBIRD_DIR / "screenshots"
OUTPUT_DIR = THUNDERBIRD_DIR / "output"

# Branding assets
LOGO_FILE = THUNDERBIRD_DIR / "Agency_Logo.png"
HEADSHOT_FILE = THUNDERBIRD_DIR / "John_Headshot.jpg"
SLOGAN = "D2M Travel, Curating the experience of a lifetime"

# Pricing
EUR_TO_USD = 1.09
STANDARD_MARKUP = 0.25
PREMIUM_MARKUP = 0.22


# ============================================================================
# AMADEUS AUTH (reuses credentials from flight module)
# ============================================================================

class AmadeusToursConfig:
    CLIENT_ID = ""
    CLIENT_SECRET = ""
    BASE_URL = "https://test.api.amadeus.com"
    _token = None
    _token_expires = 0


def _load_amadeus_credentials():
    """Load Amadeus API credentials from config file."""
    if AmadeusToursConfig.CLIENT_ID and AmadeusToursConfig.CLIENT_SECRET:
        return AmadeusToursConfig.CLIENT_ID, AmadeusToursConfig.CLIENT_SECRET

    cred_file = THUNDERBIRD_DIR / "amadeus_credentials.json"
    if cred_file.exists():
        with open(cred_file, encoding="utf-8") as f:
            creds = json.load(f)
        AmadeusToursConfig.CLIENT_ID = creds.get("client_id", "")
        AmadeusToursConfig.CLIENT_SECRET = creds.get("client_secret", "")
        if creds.get("base_url"):
            AmadeusToursConfig.BASE_URL = creds["base_url"]
        return AmadeusToursConfig.CLIENT_ID, AmadeusToursConfig.CLIENT_SECRET

    raise ValueError(
        "Amadeus credentials not configured. "
        "Create ~/Thunderbird/amadeus_credentials.json"
    )


def _get_amadeus_token() -> str:
    """Get OAuth2 access token, refreshing if expired."""
    now = time.time()
    if AmadeusToursConfig._token and now < AmadeusToursConfig._token_expires - 60:
        return AmadeusToursConfig._token

    client_id, client_secret = _load_amadeus_credentials()
    resp = requests.post(
        f"{AmadeusToursConfig.BASE_URL}/v1/security/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    AmadeusToursConfig._token = data["access_token"]
    AmadeusToursConfig._token_expires = now + data.get("expires_in", 1799)
    return AmadeusToursConfig._token


def _amadeus_headers() -> dict:
    token = _get_amadeus_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


# ============================================================================
# CURRENCY / PRICING HELPERS
# ============================================================================

def fmt_usd(amount) -> str:
    """Format a numeric amount as USD string."""
    try:
        val = float(amount)
        return f"${val:,.2f}"
    except (ValueError, TypeError):
        return str(amount)


def _apply_markup(net_amount: float, currency: str = "USD", markup: float = STANDARD_MARKUP) -> dict:
    """Convert to USD if needed and apply D2M markup."""
    usd_net = net_amount
    if currency.upper() == "EUR":
        usd_net = net_amount * EUR_TO_USD

    client_price = usd_net * (1 + markup)
    return {
        "net_usd": fmt_usd(usd_net),
        "markup_pct": f"{markup * 100:.0f}%",
        "client_price_usd": fmt_usd(client_price),
        "net_raw": round(usd_net, 2),
        "client_raw": round(client_price, 2),
    }


# ============================================================================
# RESPONSE FORMATTING
# ============================================================================

def _format_amadeus_activities(data: dict) -> list:
    """Format Amadeus Tours & Activities API response."""
    raw = data.get("data", [])
    activities = []
    for act in raw:
        price = act.get("price", {})
        currency = price.get("currencyCode", "USD")
        amount = float(price.get("amount", 0))
        pricing = _apply_markup(amount, currency)

        activities.append({
            "source": "amadeus",
            "id": act.get("id"),
            "name": act.get("name"),
            "short_description": act.get("shortDescription", "")[:300],
            "type": act.get("type"),
            "rating": act.get("rating"),
            "booking_link": act.get("bookingLink"),
            "pictures": [(p if isinstance(p, str) else p.get("url", "")) for p in (act.get("pictures") or [])[:3]],
            "duration": act.get("minimumDuration"),
            "price": {
                "amount": amount,
                "currency": currency,
                **pricing,
            },
            "geo": {
                "latitude": act.get("geoCode", {}).get("latitude"),
                "longitude": act.get("geoCode", {}).get("longitude"),
            },
        })
    return activities


def _format_musement_activities(data: list) -> list:
    """Format Musement API response."""
    activities = []
    for act in data:
        price_obj = act.get("retail_price", {})
        currency = price_obj.get("currency", "EUR")
        amount = float(price_obj.get("value", 0))
        pricing = _apply_markup(amount, currency)

        activities.append({
            "source": "musement",
            "id": str(act.get("uuid", act.get("id", ""))),
            "name": act.get("title", ""),
            "short_description": act.get("description", "")[:300],
            "type": act.get("typologies", [{}])[0].get("name", "Activity") if act.get("typologies") else "Activity",
            "rating": act.get("reviews_avg"),
            "reviews_count": act.get("reviews_number"),
            "booking_link": act.get("url"),
            "pictures": [img.get("url") for img in (act.get("cover_image_url") and [{"url": act["cover_image_url"]}] or [])],
            "duration": act.get("duration_range", {}).get("max"),
            "price": {
                "amount": amount,
                "currency": currency,
                **pricing,
            },
            "city": act.get("city", {}).get("name"),
            "country": act.get("city", {}).get("country", {}).get("name"),
        })
    return activities


def _format_comparison(tours: list) -> list:
    """Build side-by-side comparison rows from formatted tour results."""
    rows = []
    for i, tour in enumerate(tours):
        price = tour.get("price", {})
        rows.append({
            "option": i + 1,
            "name": tour.get("name", "Unknown"),
            "source": tour.get("source", ""),
            "type": tour.get("type", ""),
            "duration": tour.get("duration", "N/A"),
            "rating": tour.get("rating", "N/A"),
            "net_price": price.get("net_usd", "N/A"),
            "client_price": price.get("client_price_usd", "N/A"),
            "client_raw": price.get("client_raw", 0),
            "consumer_price": tour.get("consumer_price", "N/A"),
            "savings": tour.get("savings", ""),
        })
    return rows


# ============================================================================
# BRANDING HELPERS
# ============================================================================

def _logo_base64() -> str:
    """Load D2M logo as base64 data URI."""
    if LOGO_FILE.exists():
        data = LOGO_FILE.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        suffix = LOGO_FILE.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        return f"data:{mime};base64,{b64}"
    return ""


def _headshot_base64() -> str:
    """Load John's headshot as base64 data URI."""
    if HEADSHOT_FILE.exists():
        data = HEADSHOT_FILE.read_bytes()
        b64 = base64.b64encode(data).decode("utf-8")
        suffix = HEADSHOT_FILE.suffix.lower()
        mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"
        return f"data:{mime};base64,{b64}"
    return ""


# ============================================================================
# PDF TEMPLATE
# ============================================================================

def _render_tour_quote_html(context: dict) -> str:
    """Render the tour quote HTML from inline template with D2M branding."""
    logo_uri = _logo_base64()
    headshot_uri = _headshot_base64()

    logo_img = f'<img src="{logo_uri}" style="max-height:60px;margin-bottom:8px;" alt="D2M Travel">' if logo_uri else '<div style="font-size:1.5em;font-weight:700;color:#e8c97a;">D2M Travel</div>'
    headshot_img = f'<img src="{headshot_uri}" style="width:60px;height:60px;border-radius:50%;border:2px solid #c9a84c;object-fit:cover;" alt="John Loucks">' if headshot_uri else ""

    # Build tour option cards
    tour_cards = ""
    for tour in context.get("tours", []):
        pictures_html = ""
        pics = tour.get("pictures", [])
        if pics and pics[0]:
            pictures_html = f'<img src="{pics[0]}" style="width:100%;height:180px;object-fit:cover;border-radius:6px 6px 0 0;" alt="{tour.get("name","")}">'

        rating_html = ""
        if tour.get("rating"):
            rating_html = f'<span style="color:#c9a84c;font-weight:600;">★ {tour["rating"]}</span>'

        badges = ""
        for badge in tour.get("badges", []):
            badges += f'<span style="display:inline-block;background:#c9a84c;color:#0d1b2e;padding:2px 8px;border-radius:3px;font-size:0.75em;font-weight:600;margin-right:5px;">{badge}</span>'

        price = tour.get("price", {})
        consumer = tour.get("consumer_price", "")
        savings_html = ""
        if consumer and tour.get("savings"):
            savings_html = f'''
            <div style="margin-top:5px;font-size:0.8em;">
                <span style="text-decoration:line-through;color:#8a9ab5;">Consumer: {consumer}</span>
                <span style="color:#4CAF50;font-weight:600;margin-left:8px;">You save {tour["savings"]}</span>
            </div>'''

        tour_cards += f'''
        <div style="background:#152540;border:1px solid #1e3358;border-radius:6px;margin-bottom:20px;overflow:hidden;">
            {pictures_html}
            <div style="padding:20px;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div style="flex:1;">
                        <h3 style="margin:0 0 8px;color:#e8c97a;font-size:1.1em;">{tour.get("name","")}</h3>
                        <div style="font-size:0.85em;color:#8a9ab5;margin-bottom:5px;">
                            {tour.get("type","")} · {tour.get("duration","N/A")} · {tour.get("source","").title()}
                        </div>
                        {rating_html}
                        <div style="margin-top:5px;">{badges}</div>
                    </div>
                    <div style="text-align:right;min-width:120px;">
                        <div style="font-size:1.4em;font-weight:700;color:#e8c97a;">{price.get("client_price_usd","")}</div>
                        <div style="font-size:0.75em;color:#8a9ab5;">per person</div>
                        {savings_html}
                    </div>
                </div>
                <p style="font-size:0.85em;color:#ccc;margin:12px 0 0;line-height:1.5;">{tour.get("short_description","")}</p>
            </div>
        </div>'''

    # Build comparison table
    comp_html = ""
    comparison = context.get("comparison", [])
    if comparison:
        comp_rows = ""
        for row in comparison:
            pick_style = "background:#1e3358;border-left:3px solid #c9a84c;" if row.get("is_pick") else ""
            comp_rows += f'''
            <tr style="{pick_style}">
                <td style="padding:10px 12px;border-bottom:1px solid #1e3358;font-weight:600;color:#e8c97a;">Option {row.get("option","")}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #1e3358;">{row.get("name","")[:40]}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #1e3358;">{row.get("source","")}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #1e3358;">{row.get("duration","")}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #1e3358;">{row.get("rating","")}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #1e3358;font-weight:700;color:#e8c97a;">{row.get("client_price","")}</td>
            </tr>'''

        comp_html = f'''
        <div style="margin:30px 0;">
            <h2 style="color:#e8c97a;border-bottom:2px solid #c9a84c;padding-bottom:8px;font-size:1.1em;">Side-by-Side Comparison</h2>
            <table style="width:100%;border-collapse:collapse;font-size:0.85em;color:#ccc;">
                <thead>
                    <tr style="background:#0d1b2e;">
                        <th style="padding:10px 12px;text-align:left;color:#c9a84c;">Option</th>
                        <th style="padding:10px 12px;text-align:left;color:#c9a84c;">Tour/Activity</th>
                        <th style="padding:10px 12px;text-align:left;color:#c9a84c;">Source</th>
                        <th style="padding:10px 12px;text-align:left;color:#c9a84c;">Duration</th>
                        <th style="padding:10px 12px;text-align:left;color:#c9a84c;">Rating</th>
                        <th style="padding:10px 12px;text-align:left;color:#c9a84c;">Price/pp</th>
                    </tr>
                </thead>
                <tbody>{comp_rows}</tbody>
            </table>
        </div>'''

    # Recommendation
    rec_html = ""
    if context.get("recommendation"):
        rec_html = f'''
        <div style="margin:25px 0;padding:20px;background:#0d1b2e;border-left:4px solid #c9a84c;border-radius:0 6px 6px 0;">
            <strong style="color:#e8c97a;">Our Recommendation</strong>
            <p style="margin:8px 0 0;color:#ccc;line-height:1.6;">{context["recommendation"]}</p>
        </div>'''

    notes_html = ""
    if context.get("notes"):
        notes_html = f'<p style="font-size:0.8em;color:#8a9ab5;margin-top:20px;font-style:italic;">{context["notes"]}</p>'

    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Tour Quote — {context.get("client_name","")}</title></head>
<body style="margin:0;padding:0;background:#0a1628;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;color:#ccc;">
    <!-- Header -->
    <div style="background:linear-gradient(135deg,#0d1b2e,#152540);padding:35px 40px;text-align:center;border-bottom:3px solid #c9a84c;">
        {logo_img}
        <h1 style="margin:10px 0 5px;color:#ffffff;font-weight:300;font-size:1.6em;">Tours & Activities</h1>
        <div style="color:#e8c97a;font-size:1.2em;font-weight:600;">{context.get("destination","")}</div>
        <div style="color:#8a9ab5;margin-top:8px;font-size:0.9em;">
            Prepared for <strong style="color:#fff;">{context.get("client_name","")}</strong> ·
            {context.get("travel_dates","")} · {context.get("travelers","2")} travelers
        </div>
        <div style="color:#8a9ab5;margin-top:5px;font-size:0.8em;">{context.get("prepared_date","")}</div>
    </div>

    <!-- Tour Cards -->
    <div style="padding:30px 40px;">
        {tour_cards}
        {comp_html}
        {rec_html}
        {notes_html}
    </div>

    <!-- Footer -->
    <div style="background:#0d1b2e;padding:25px 40px;border-top:3px solid #c9a84c;text-align:center;">
        <div style="display:inline-flex;align-items:center;gap:15px;margin-bottom:10px;">
            {headshot_img}
            <div style="text-align:left;">
                <div style="color:#ffffff;font-weight:600;">John Loucks</div>
                <div style="color:#8a9ab5;font-size:0.85em;">johnloucks3@gmail.com · (719) 291-0742</div>
            </div>
        </div>
        <div style="color:#c9a84c;font-size:0.9em;font-style:italic;margin-top:10px;">{SLOGAN}</div>
        <div style="color:#8a9ab5;font-size:0.75em;margin-top:8px;">Dreams2Memories Travel, LLC · Monument, CO</div>
    </div>
</body>
</html>'''
    return html


# ============================================================================
# TOOL REGISTRATION
# ============================================================================

def register_tour_search_tools(mcp: FastMCP):
    """Register tour/activity search tools with the MCP server."""

    # ================================================================
    # TIER 1: API-POWERED SEARCH
    # ================================================================

    @mcp.tool(
        name="search_tours",
        annotations={"title": "Search Tours & Activities (Amadeus)", "readOnlyHint": True},
    )
    async def search_tours(
        latitude: float = Field(..., description="Latitude of the destination (e.g. 48.8566 for Paris)"),
        longitude: float = Field(..., description="Longitude of the destination (e.g. 2.3522 for Paris)"),
        radius: int = Field(20, description="Search radius in km (1-100)"),
        max_results: int = Field(20, description="Max activities to return (1-50)"),
    ) -> str:
        """Search for tours and activities near a destination via Amadeus API.

        Returns tours/activities with pricing, ratings, descriptions, and photos.
        Prices include both net cost and client price with D2M markup.
        Use search_airports or a geocoding service to get coordinates.
        """
        try:
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "radius": min(radius, 100),
            }

            logger.info(f"Amadeus tours search: lat={latitude}, lon={longitude}, r={radius}km")
            resp = requests.get(
                f"{AmadeusToursConfig.BASE_URL}/v1/shopping/activities",
                headers=_amadeus_headers(),
                params=params,
                timeout=30,
            )

            if resp.status_code != 200:
                error_detail = resp.text[:1000]
                try:
                    errors = resp.json().get("errors", [])
                    if errors:
                        error_detail = "; ".join(e.get("detail", e.get("title", "")) for e in errors)
                except Exception:
                    pass
                return json.dumps({"error": f"Amadeus API error {resp.status_code}", "detail": error_detail}, indent=2)

            activities = _format_amadeus_activities(resp.json())[:max_results]
            return json.dumps({
                "status": "success",
                "source": "amadeus",
                "total": len(activities),
                "activities": activities,
            }, indent=2)

        except ValueError as e:
            return json.dumps({"error": str(e), "type": "config_error"}, indent=2)
        except requests.RequestException as e:
            logger.error(f"Amadeus tours request failed: {e}")
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"Tour search error: {e}")
            return json.dumps({"error": str(e), "type": "search_error"}, indent=2)

    @mcp.tool(
        name="search_tours_musement",
        annotations={"title": "Search Tours & Activities (Musement)", "readOnlyHint": True},
    )
    async def search_tours_musement(
        city: str = Field(..., description="City name (e.g. 'Paris', 'Rome', 'Tokyo')"),
        category: Optional[str] = Field(None, description="Category filter: 'tours', 'museums', 'food', 'outdoor', 'nightlife', 'shows'"),
        max_results: int = Field(20, description="Max activities to return (1-50)"),
    ) -> str:
        """Search for tours and activities via the Musement API.

        Free API with good European and global coverage.
        Returns activities with pricing, ratings, descriptions.
        Prices include net cost and D2M markup.
        """
        try:
            # Musement requires partner header — use stealth browser as fallback
            logger.info(f"Musement search: city={city}")

            search_term = f"{city} tours"
            if category:
                search_term += f" {category}"

            async with Stealth().use_async(async_playwright()) as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                )
                page = await context.new_page()

                url = f"https://www.musement.com/us/search/?q={city.replace(' ', '+')}"
                await page.goto(url, wait_until="networkidle", timeout=45000)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)

                content = await page.evaluate("document.body.innerText")
                page_url = page.url
                await browser.close()

            return json.dumps({
                "status": "success",
                "source": "musement",
                "city": city,
                "search_url": page_url,
                "note": "Musement API requires partner registration. Results scraped from public site.",
                "content_snippet": content[:6000],
            }, indent=2)

        except requests.RequestException as e:
            logger.error(f"Musement request failed: {e}")
            return json.dumps({"error": str(e), "type": "request_error"}, indent=2)
        except Exception as e:
            logger.error(f"Musement search error: {e}")
            return json.dumps({"error": str(e), "type": "search_error"}, indent=2)

    # ================================================================
    # TIER 1B: AGENT PORTAL BROWSER (with login pause)
    # ================================================================

    @mcp.tool(
        name="browse_tour_portal",
        annotations={"title": "Browse Tour Agent Portal (with Login Pause)", "readOnlyHint": True},
    )
    async def browse_tour_portal(
        portal: str = Field(
            ...,
            description="Portal to open: 'projectexpedition', 'taap' (Expedia TA), 'viator_ta', or a custom URL",
        ),
        search_query: Optional[str] = Field(None, description="Tour/activity to search for after login"),
        destination: Optional[str] = Field(None, description="Destination to search"),
        login_timeout: int = Field(600, description="Max seconds to wait for login (default 600 / 10 min). Close browser to abort."),
        screenshot_steps: bool = Field(True, description="Take screenshots at each step"),
    ) -> str:
        """Open a tour agent portal in a visible browser for manual login, then scrape results.

        Launches a VISIBLE browser window. You log in manually while the tool waits.
        Once logged in (page URL changes from login page), the tool proceeds to search
        and capture results with screenshots.

        Portals: ProjectExpedition, TAAP (Expedia TA portal), Viator TA site.
        """
        try:
            portal_urls = {
                "projectexpedition": "https://www.projectexpedition.com/login",
                "taap": "https://www.expediataap.com/",
                "viator_ta": "https://traveladvisor.viator.com/login",
            }

            start_url = portal_urls.get(portal.lower(), portal)

            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            screenshots = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            portal_name = portal.lower().replace(" ", "_")

            async with Stealth().use_async(async_playwright()) as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
                page = await context.new_page()

                # Navigate to login page
                logger.info(f"Opening portal: {start_url}")
                await page.goto(start_url, wait_until="networkidle", timeout=45000)
                login_url = page.url

                if screenshot_steps:
                    path = SCREENSHOTS_DIR / f"{portal_name}_01_login_{timestamp}.png"
                    await page.screenshot(path=str(path), full_page=False)
                    screenshots.append({"step": "login_page", "path": str(path)})

                # Wait for manual login — poll for URL change OR DOM auth signals
                logger.info(f"Waiting up to {login_timeout}s for manual login...")
                elapsed = 0
                poll_interval = 3
                logged_in = False

                # Capture initial page state for comparison
                initial_body = await page.evaluate("document.body.innerText")
                has_sign_in_initially = any(
                    kw in initial_body.lower()
                    for kw in ["sign in", "log in", "register | sign in"]
                )

                while elapsed < login_timeout:
                    await page.wait_for_timeout(poll_interval * 1000)
                    elapsed += poll_interval

                    # Check if user closed the browser window
                    if page.is_closed():
                        return json.dumps({
                            "status": "manually_closed",
                            "message": "Browser was closed by user before login was detected.",
                            "screenshots": screenshots,
                        }, indent=2)

                    current_url = page.url

                    # Strategy 1: URL changed away from login page
                    if current_url != login_url and "login" not in current_url.lower() and "partners" not in current_url.lower():
                        logged_in = True
                        logger.info(f"Login detected via URL change: {current_url}")
                        break

                    # Strategy 2: DOM auth signals — "Sign In" disappeared or user element appeared
                    try:
                        current_body = await page.evaluate("document.body.innerText")
                        body_lower = current_body.lower()

                        # Check if sign-in prompts vanished
                        sign_in_gone = has_sign_in_initially and not any(
                            kw in body_lower
                            for kw in ["sign in", "log in", "register | sign in"]
                        )

                        # Check if authenticated elements appeared
                        auth_signals = any(
                            kw in body_lower
                            for kw in [
                                "my bookings", "my account", "dashboard",
                                "welcome", "sign out", "log out", "logout",
                                "my referral", "my wishlist", "commission",
                            ]
                        )

                        if sign_in_gone or auth_signals:
                            logged_in = True
                            logger.info(f"Login detected via DOM change (sign_in_gone={sign_in_gone}, auth_signals={auth_signals})")
                            break
                    except Exception:
                        pass  # Page may be navigating, retry next poll

                    if elapsed % 15 == 0:
                        logger.info(f"Still waiting for login... {elapsed}s / {login_timeout}s")

                if not logged_in:
                    if screenshot_steps:
                        try:
                            path = SCREENSHOTS_DIR / f"{portal_name}_timeout_{timestamp}.png"
                            await page.screenshot(path=str(path), full_page=False)
                            screenshots.append({"step": "login_timeout", "path": str(path)})
                        except Exception:
                            pass
                    return json.dumps({
                        "status": "login_timeout",
                        "message": f"Login not detected within {login_timeout}s. Browser left open — close it manually.",
                        "screenshots": screenshots,
                    }, indent=2)

                if screenshot_steps:
                    path = SCREENSHOTS_DIR / f"{portal_name}_02_logged_in_{timestamp}.png"
                    await page.screenshot(path=str(path), full_page=False)
                    screenshots.append({"step": "logged_in", "path": str(path)})

                # Search if query provided
                if search_query or destination:
                    query = search_query or destination
                    logger.info(f"Searching portal for: {query}")

                    # Try common search field selectors
                    search_selectors = [
                        'input[placeholder*="earch"]',
                        'input[placeholder*="estination"]',
                        'input[placeholder*="tour"]',
                        'input[placeholder*="activity"]',
                        'input[type="search"]',
                        'input[name="search"]',
                        'input[name="query"]',
                        'input[name="q"]',
                    ]

                    search_filled = False
                    for sel in search_selectors:
                        try:
                            if await page.locator(sel).count() > 0:
                                await page.fill(sel, query)
                                await page.press(sel, "Enter")
                                search_filled = True
                                break
                        except Exception:
                            continue

                    if search_filled:
                        await page.wait_for_timeout(5000)
                        if screenshot_steps:
                            path = SCREENSHOTS_DIR / f"{portal_name}_03_results_{timestamp}.png"
                            await page.screenshot(path=str(path), full_page=True)
                            screenshots.append({"step": "search_results", "path": str(path)})

                # Capture page content
                content = await page.evaluate("document.body.innerText")
                await browser.close()

                return json.dumps({
                    "status": "success",
                    "portal": portal,
                    "logged_in": True,
                    "searched": bool(search_query or destination),
                    "screenshots": screenshots,
                    "page_content": content[:8000],
                }, indent=2)

        except Exception as e:
            if "Target closed" in str(e) or "Browser closed" in str(e):
                return json.dumps({
                    "status": "manually_closed",
                    "message": "Browser was closed by user.",
                    "screenshots": screenshots if 'screenshots' in dir() else [],
                }, indent=2)
            logger.error(f"Portal browse error: {e}")
            return json.dumps({"error": str(e), "type": "browser_error"}, indent=2)

    # ================================================================
    # TIER 1C: CONSUMER PRICE SCRAPING
    # ================================================================

    @mcp.tool(
        name="scrape_consumer_tour_prices",
        annotations={"title": "Scrape Consumer Tour Prices (Expedia/Viator)", "readOnlyHint": True},
    )
    async def scrape_consumer_tour_prices(
        destination: str = Field(..., description="Destination city or region"),
        tour_name: Optional[str] = Field(None, description="Specific tour/activity name to search"),
        site: str = Field("expedia", description="Site to scrape: 'expedia', 'viator', 'both'"),
        screenshot: bool = Field(True, description="Take a screenshot of results"),
    ) -> str:
        """Scrape consumer-facing tour prices from Expedia or Viator.

        Use this to compare agent net prices against what consumers see.
        Returns tour names, prices, and ratings from public listings.
        """
        try:
            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            search_term = tour_name or f"tours in {destination}"
            results = {}

            sites_to_scrape = []
            if site in ("expedia", "both"):
                sites_to_scrape.append(("expedia", f"https://www.expedia.com/things-to-do/search?location={destination.replace(' ', '%20')}&query={search_term.replace(' ', '%20')}"))
            if site in ("viator", "both"):
                sites_to_scrape.append(("viator", f"https://www.viator.com/searchResults/all?text={search_term.replace(' ', '%20')}"))

            async with Stealth().use_async(async_playwright()) as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )

                for site_name, url in sites_to_scrape:
                    page = await context.new_page()
                    logger.info(f"Scraping {site_name}: {url}")

                    try:
                        await page.goto(url, wait_until="networkidle", timeout=45000)
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(3000)

                        if screenshot:
                            path = SCREENSHOTS_DIR / f"consumer_{site_name}_{timestamp}.png"
                            await page.screenshot(path=str(path), full_page=False)
                            results[f"{site_name}_screenshot"] = str(path)

                        content = await page.evaluate("document.body.innerText")
                        results[site_name] = {
                            "url": url,
                            "content_snippet": content[:6000],
                        }
                    except Exception as e:
                        results[site_name] = {"error": str(e)}
                    finally:
                        await page.close()

                await browser.close()

            return json.dumps({
                "status": "success",
                "destination": destination,
                "search_term": search_term,
                "results": results,
            }, indent=2)

        except Exception as e:
            logger.error(f"Consumer scrape error: {e}")
            return json.dumps({"error": str(e), "type": "scraping_error"}, indent=2)

    @mcp.tool(
        name="scrape_tour_content",
        annotations={"title": "Scrape Tour Recommendations (Fodor's/Rick Steves)", "readOnlyHint": True},
    )
    async def scrape_tour_content(
        destination: str = Field(..., description="Destination city or region"),
        source: str = Field("both", description="Content source: 'fodors', 'ricksteves', or 'both'"),
        screenshot: bool = Field(True, description="Take a screenshot of results"),
    ) -> str:
        """Scrape expert tour recommendations from Fodor's and Rick Steves.

        Returns curated tour/activity recommendations from trusted travel authorities.
        Useful for validating tour quality and discovering hidden gems.
        """
        try:
            SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results = {}

            sites = []
            dest_slug = destination.lower().replace(" ", "-").replace(",", "")
            if source in ("fodors", "both"):
                sites.append(("fodors", f"https://www.fodors.com/world-regions/search?query={destination.replace(' ', '+')}+things+to+do"))
            if source in ("ricksteves", "both"):
                sites.append(("ricksteves", f"https://www.ricksteves.com/search?q={destination.replace(' ', '+')}+tours+activities"))

            async with Stealth().use_async(async_playwright()) as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                )

                for site_name, url in sites:
                    page = await context.new_page()
                    logger.info(f"Scraping {site_name}: {url}")

                    try:
                        await page.goto(url, wait_until="networkidle", timeout=45000)
                        await page.wait_for_timeout(2000)

                        if screenshot:
                            path = SCREENSHOTS_DIR / f"content_{site_name}_{timestamp}.png"
                            await page.screenshot(path=str(path), full_page=False)
                            results[f"{site_name}_screenshot"] = str(path)

                        content = await page.evaluate("document.body.innerText")
                        results[site_name] = {
                            "url": url,
                            "content_snippet": content[:6000],
                        }
                    except Exception as e:
                        results[site_name] = {"error": str(e)}
                    finally:
                        await page.close()

                await browser.close()

            return json.dumps({
                "status": "success",
                "destination": destination,
                "results": results,
            }, indent=2)

        except Exception as e:
            logger.error(f"Content scrape error: {e}")
            return json.dumps({"error": str(e), "type": "scraping_error"}, indent=2)

    # ================================================================
    # TIER 2: COMPARISON
    # ================================================================

    @mcp.tool(
        name="compare_tours",
        annotations={"title": "Compare Tours Side-by-Side", "readOnlyHint": True},
    )
    async def compare_tours(
        tours_json: str = Field(
            ...,
            description="JSON array of tour objects to compare. Each must have: "
            "name, source, type, duration, rating, price (with client_price_usd, client_raw). "
            "Optionally include consumer_price for savings calculation. 2-10 tours.",
        ),
    ) -> str:
        """Compare 2-10 tours side-by-side with pricing analysis.

        Pass tour objects from search_tours or search_tours_musement results.
        Optionally include consumer_price from scrape_consumer_tour_prices
        to show client savings vs. booking direct.
        Returns comparison table with best value and highest rated badges.
        """
        try:
            tours = json.loads(tours_json)
            if not isinstance(tours, list) or len(tours) < 2:
                return json.dumps({"error": "Provide an array of 2-10 tour objects to compare"}, indent=2)

            tours = tours[:10]

            # Calculate savings if consumer prices provided
            for tour in tours:
                consumer = tour.get("consumer_price")
                if consumer:
                    try:
                        consumer_val = float(str(consumer).replace("$", "").replace(",", ""))
                        client_val = tour.get("price", {}).get("client_raw", 0)
                        if consumer_val > client_val and client_val > 0:
                            saving = consumer_val - client_val
                            tour["savings"] = fmt_usd(saving)
                    except (ValueError, TypeError):
                        pass

            comparison = _format_comparison(tours)

            # Find best value and highest rated
            best_price_idx = 0
            best_price = float("inf")
            best_rating_idx = 0
            best_rating = 0

            for i, row in enumerate(comparison):
                price_val = row.get("client_raw", float("inf"))
                if price_val < best_price and price_val > 0:
                    best_price = price_val
                    best_price_idx = i

                rating_val = row.get("rating", 0)
                try:
                    rating_num = float(rating_val) if rating_val != "N/A" else 0
                except (ValueError, TypeError):
                    rating_num = 0
                if rating_num > best_rating:
                    best_rating = rating_num
                    best_rating_idx = i

            for i, row in enumerate(comparison):
                row["badges"] = []
                if i == best_price_idx:
                    row["badges"].append("BEST VALUE")
                if i == best_rating_idx:
                    row["badges"].append("HIGHEST RATED")

            return json.dumps({
                "comparison": comparison,
                "total_options": len(comparison),
                "recommendation": {
                    "best_value": comparison[best_price_idx]["option"],
                    "highest_rated": comparison[best_rating_idx]["option"],
                },
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except Exception as e:
            logger.error(f"Tour comparison error: {e}")
            return json.dumps({"error": str(e), "type": "compare_error"}, indent=2)

    # ================================================================
    # TIER 3: PDF QUOTE + EMAIL
    # ================================================================

    @mcp.tool(
        name="render_tour_quote_pdf",
        annotations={"title": "Render Tour Quote PDF (D2M Branded)", "readOnlyHint": False},
    )
    async def render_tour_quote_pdf(
        client_name: str = Field(..., description="Client name for the quote"),
        destination: str = Field(..., description="Destination city/region"),
        travel_dates: str = Field(..., description="Travel dates (human-readable, e.g. 'June 15-22, 2026')"),
        travelers: str = Field("2", description="Number of travelers"),
        tours_json: str = Field(
            ...,
            description="JSON array of tour objects for the quote. Each: "
            "name, source, type, duration, rating, price (with client_price_usd), "
            "short_description, pictures (array of URLs), badges (array of strings). "
            "Optionally: consumer_price, savings.",
        ),
        comparison_json: Optional[str] = Field(
            None,
            description="JSON array of comparison row objects. Each: "
            "option, name, source, duration, rating, client_price, is_pick (bool)",
        ),
        recommendation: Optional[str] = Field(None, description="Recommendation text for the client"),
        notes: Optional[str] = Field(None, description="Important notes or disclaimers"),
        output_filename: Optional[str] = Field(None, description="Output PDF filename"),
    ) -> str:
        """Render a branded D2M tour quote PDF with logo, headshot, and slogan.

        Generates a professional PDF with tour option cards, comparison table,
        recommendation, and full D2M branding.
        """
        try:
            tours = json.loads(tours_json)
            comparison = json.loads(comparison_json) if comparison_json else None

            if not output_filename:
                safe_client = client_name.replace(" ", "_")
                safe_dest = destination.replace(" ", "_").replace(",", "")
                month_year = datetime.now().strftime("%b%Y")
                output_filename = f"{safe_client}_Tours_{safe_dest}_{month_year}.pdf"

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            pdf_path = OUTPUT_DIR / output_filename
            html_path = OUTPUT_DIR / output_filename.replace(".pdf", ".html")

            context = {
                "client_name": client_name,
                "destination": destination,
                "travel_dates": travel_dates,
                "travelers": travelers,
                "prepared_date": datetime.now().strftime("%B %d, %Y"),
                "tours": tours,
                "comparison": comparison,
                "recommendation": recommendation,
                "notes": notes or "Prices valid for 48 hours. Availability subject to change. All prices per person unless noted.",
            }

            html_content = _render_tour_quote_html(context)

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            WeasyHTML(string=html_content, base_url=str(THUNDERBIRD_DIR)).write_pdf(str(pdf_path))

            logger.info(f"Tour quote PDF rendered: {pdf_path}")
            return json.dumps({
                "status": "success",
                "pdf_path": str(pdf_path),
                "html_path": str(html_path),
                "client_name": client_name,
                "destination": destination,
                "tours_count": len(tours),
                "has_logo": LOGO_FILE.exists(),
                "has_headshot": HEADSHOT_FILE.exists(),
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except Exception as e:
            logger.error(f"Tour quote PDF error: {e}")
            return json.dumps({"error": str(e), "type": "render_error"}, indent=2)

    @mcp.tool(
        name="email_tour_quote",
        annotations={"title": "Email Tour Quote to Client", "readOnlyHint": False},
    )
    async def email_tour_quote(
        to_email: str = Field(..., description="Client email address"),
        client_name: str = Field(..., description="Client name for greeting"),
        destination: str = Field(..., description="Destination city/region"),
        travel_dates: str = Field(..., description="Travel dates (human-readable)"),
        summary_json: str = Field(
            ...,
            description="JSON array of tour summary objects for email body. Each: "
            "option (int), name (str), duration (str), rating, client_price (str)",
        ),
        recommendation: Optional[str] = Field(None, description="Brief recommendation text"),
        pdf_path: Optional[str] = Field(None, description="Path to tour quote PDF to attach"),
        subject: Optional[str] = Field(None, description="Custom email subject"),
    ) -> str:
        """Create a Gmail draft with tour quote and optional PDF attachment.

        Uses OAuth Gmail (thunderbird_gmail). Creates a draft — does NOT send.
        John reviews and sends manually.
        """
        try:
            from thunderbird_gmail import _get_gmail_service, USER_EMAIL

            summary = json.loads(summary_json)

            if not subject:
                subject = f"Tour & Activity Options: {destination}"

            # Build summary rows
            rows_html = ""
            for opt in summary:
                rating_text = f"★ {opt['rating']}" if opt.get("rating") and opt["rating"] != "N/A" else ""
                rows_html += f"""
                <tr>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;font-weight:600;">Option {opt.get('option','')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{opt.get('name','')[:45]}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{opt.get('duration','')}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;">{rating_text}</td>
                    <td style="padding:10px 12px;border-bottom:1px solid #e9ecef;font-weight:700;color:#0d1b2e;">{opt.get('client_price','')}</td>
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
                attachment_note = "<p style='font-size:0.9em;color:#8a9ab5;margin-top:15px;'>See the attached PDF for full details with photos and pricing.</p>"

            html_body = f"""
            <div style="font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;max-width:700px;margin:0 auto;color:#2c3e50;">
                <div style="background:linear-gradient(135deg,#0d1b2e,#152540);color:#ffffff;padding:35px 30px;text-align:center;border-bottom:3px solid #c9a84c;">
                    <h2 style="margin:0 0 5px;font-weight:300;font-size:1.6em;">Tours & Activities</h2>
                    <div style="color:#e8c97a;font-size:1.2em;font-weight:600;">{destination}</div>
                    <div style="color:#8a9ab5;margin-top:10px;font-size:0.9em;">{travel_dates}</div>
                </div>

                <div style="padding:25px 30px;">
                    <p>Hi {client_name},</p>
                    <p style="margin:15px 0;">I've curated some wonderful tour and activity options for your trip to {destination}. Each one has been hand-picked to make your experience unforgettable.</p>

                    <table style="width:100%;border-collapse:collapse;font-size:0.85em;margin:20px 0;">
                        <thead>
                            <tr style="background:#0d1b2e;color:#ffffff;">
                                <th style="padding:10px 12px;text-align:left;">Option</th>
                                <th style="padding:10px 12px;text-align:left;">Tour/Activity</th>
                                <th style="padding:10px 12px;text-align:left;">Duration</th>
                                <th style="padding:10px 12px;text-align:left;">Rating</th>
                                <th style="padding:10px 12px;text-align:left;">Price/pp</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>

                    {rec_html}
                    {attachment_note}

                    <p style="margin-top:25px;">Warmly,<br><strong>John Loucks</strong><br>Dreams2Memories Travel, LLC<br>
                    <a href="mailto:johnloucks3@gmail.com" style="color:#c9a84c;">johnloucks3@gmail.com</a> | (719) 291-0742</p>
                    <p style="font-size:0.85em;color:#8a9ab5;font-style:italic;">{SLOGAN}</p>
                </div>

                <div style="background:#0d1b2e;color:#8a9ab5;padding:20px;text-align:center;font-size:0.8em;border-top:3px solid #c9a84c;">
                    Dreams2Memories Travel, LLC · Monument, CO
                </div>
            </div>"""

            # Create Gmail draft via OAuth
            service = _get_gmail_service()

            msg = MIMEMultipart()
            msg["to"] = to_email
            msg["from"] = USER_EMAIL
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
            draft = service.users().drafts().create(
                userId="me",
                body={"message": {"raw": raw_msg}},
            ).execute()

            return json.dumps({
                "status": "draft_created",
                "draft_id": draft.get("id"),
                "to": to_email,
                "subject": subject,
                "has_pdf_attachment": bool(pdf_path and Path(pdf_path).exists()),
                "message": "Gmail draft ready for review. Open Gmail to review and send.",
            }, indent=2)

        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON: {str(e)}"}, indent=2)
        except RuntimeError as e:
            return json.dumps({"error": str(e), "type": "auth_error"}, indent=2)
        except Exception as e:
            logger.error(f"Email tour quote error: {e}")
            return json.dumps({"error": str(e), "type": "email_error"}, indent=2)

    logger.info("Tour search tools registered (Amadeus + Musement + Browser)")

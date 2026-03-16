"""
Dreams2Memories Outside Agents Portal Module
=============================================

Connects to Outside Agents (MAGOA) portals:
- MAGtap (tap.myagentgenie.com) — agent community, training, resources
- Odysseus (book.myagentgenie.com) — booking system (cruise, hotel, fast sell)
- TESS (crm.myagentgenie.com) — trips/travel management, CRM, commissions

Auth Strategy: "Team Login" via Chrome CDP
  1. Launch Chrome with --remote-debugging-port=9222
  2. John logs into portals in regular Chrome (handles 2FA, Cloudflare, fingerprinting)
  3. Playwright connects via CDP to John's live Chrome
  4. Automation works in the same tabs — identical fingerprint, cookies, everything

Why CDP: These sites use Cloudflare Bot Management + ClientJS fingerprinting.
Playwright's own browser gets 403'd. CDP rides the real Chrome — undetectable.

Purpose-built tools:
  oa_scrape_bookings    — Odysseus report view → structured JSON → optional Sheets sync
  oa_scrape_commissions — TESS commission report → structured JSON
  oa_send_invoice       — TESS invoice template automation (test or client send)
  oa_activate_portal    — Send Client Portal Activation email
  oa_portal_monitor     — Diff-check client portal activity → Telegram alerts

Integrates with: travel_mcp_server.py
Dependencies: playwright, requests (for Telegram), google-api-python-client (for Sheets)
"""

import json
import logging
import asyncio
import os
import requests as _requests
from pathlib import Path
from datetime import datetime
from typing import Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, Page, BrowserContext, Browser

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
SCREENSHOTS_DIR = THUNDERBIRD_DIR / "screenshots"
OA_STATE_DIR = THUNDERBIRD_DIR / "oa_state"
CDP_URL = "http://127.0.0.1:9222"

# Google Sheets config
SHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
CREDENTIALS_FILE = THUNDERBIRD_DIR / "credentials.json"

# TESS navigation URLs
TESS_BASE = "https://crm.myagentgenie.com/app/views"
TESS_TRIPS = f"{TESS_BASE}/trip-management/trips"
TESS_CLIENTS = f"{TESS_BASE}/client-management/clients"
TESS_COMMISSIONS = f"{TESS_BASE}/commissions"
TESS_DASHBOARD = f"{TESS_BASE}/dashboard"

# Odysseus navigation URLs
ODY_BASE = "https://book.myagentgenie.com/admin"
ODY_BOOKINGS = f"{ODY_BASE}/bookings/report.aspx"


def _notify_commander(message: str):
    """Send a Telegram notification to the Commander."""
    try:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        commander_id = os.environ.get("TELEGRAM_COMMANDER_ID", "")
        if not bot_token or not commander_id:
            logger.warning("Telegram env vars not set — skipping notification")
            return
        _requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": commander_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")


def _load_state(name: str) -> dict:
    """Load a JSON state file from oa_state/. Returns {} if missing."""
    OA_STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = OA_STATE_DIR / f"{name}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(name: str, data: dict):
    """Save a JSON state file to oa_state/."""
    OA_STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = OA_STATE_DIR / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

# Portal definitions
PORTALS = {
    "magtap": {
        "name": "MAGtap",
        "login_url": "https://tap.myagentgenie.com/wp-login.php",
        "home_url": "https://tap.myagentgenie.com/",
        "domain": "tap.myagentgenie.com",
        "auth_signals": ["mysite", "magsos", "magcrm", "maglms", "profile", "log out"],
    },
    "odysseus": {
        "name": "Odysseus",
        "login_url": "https://book.myagentgenie.com/admin/login.aspx",
        "home_url": "https://book.myagentgenie.com/admin/",
        "domain": "book.myagentgenie.com",
        "auth_signals": ["fast sell", "bookings", "search bookings", "customers", "book cruise"],
    },
    "tess": {
        "name": "TESS (Travel eSolutions)",
        "login_url": "https://crm.myagentgenie.com/app/maglogin",
        "home_url": "https://crm.myagentgenie.com/app/views/dashboard",
        "domain": "crm.myagentgenie.com",
        "auth_signals": ["dashboard", "trip management", "commission", "client management"],
    },
}

# Cached CDP connection
_cdp_browser: Browser | None = None
_cdp_playwright = None


async def _connect_cdp() -> tuple[Browser, BrowserContext]:
    """Connect to Chrome via CDP. Returns (browser, default_context)."""
    global _cdp_browser, _cdp_playwright

    # Check if existing connection is alive
    if _cdp_browser is not None:
        try:
            _ = _cdp_browser.contexts
            return _cdp_browser, _cdp_browser.contexts[0]
        except Exception:
            _cdp_browser = None

    # New connection
    if _cdp_playwright is None:
        _cdp_playwright = await async_playwright().start()

    _cdp_browser = await _cdp_playwright.chromium.connect_over_cdp(CDP_URL)
    ctx = _cdp_browser.contexts[0] if _cdp_browser.contexts else await _cdp_browser.new_context()
    return _cdp_browser, ctx


async def _find_portal_tab(ctx: BrowserContext, portal_key: str) -> Page | None:
    """Find an existing tab for a portal by domain match."""
    domain = PORTALS[portal_key]["domain"]
    for page in ctx.pages:
        try:
            if domain in page.url:
                return page
        except Exception:
            continue
    return None


def _screenshot_path(portal_key: str, label: str = "") -> Path:
    """Generate a screenshot path."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{label}" if label else ""
    return SCREENSHOTS_DIR / f"{portal_key}{suffix}_{timestamp}.png"


def register_outside_agents_tools(mcp: FastMCP):
    """Register Outside Agents portal tools with the MCP server."""

    @mcp.tool(
        name="oa_connect",
        annotations={"title": "Outside Agents — Connect to Chrome", "readOnlyHint": True},
    )
    async def oa_connect() -> str:
        """Connect to Chrome via CDP and report which portals are accessible.

        Prerequisites:
          1. Chrome must be running with --remote-debugging-port=9222
          2. John must be logged into portals in Chrome

        Launch Chrome with:
          google-chrome-stable --remote-debugging-port=9222 \\
            --user-data-dir=$HOME/.config/google-chrome-debug
        """
        try:
            browser, ctx = await _connect_cdp()
        except Exception as e:
            return json.dumps({
                "error": "Cannot connect to Chrome CDP",
                "detail": str(e),
                "fix": "Launch Chrome with: google-chrome-stable --remote-debugging-port=9222 --user-data-dir=$HOME/.config/google-chrome-debug",
            }, indent=2)

        tabs = []
        portal_status = {}
        for page in ctx.pages:
            try:
                url = page.url
                tabs.append(url)
            except Exception:
                continue

        for key, portal in PORTALS.items():
            tab = await _find_portal_tab(ctx, key)
            if tab:
                try:
                    body = (await tab.inner_text("body")).lower()
                    authenticated = any(s in body for s in portal["auth_signals"])
                    portal_status[key] = {
                        "name": portal["name"],
                        "tab_found": True,
                        "authenticated": authenticated,
                        "url": tab.url,
                    }
                except Exception:
                    portal_status[key] = {"name": portal["name"], "tab_found": True, "authenticated": False, "error": "Could not read tab"}
            else:
                portal_status[key] = {"name": portal["name"], "tab_found": False, "authenticated": False}

        return json.dumps({
            "status": "connected",
            "chrome_tabs": len(tabs),
            "portals": portal_status,
        }, indent=2)

    @mcp.tool(
        name="oa_browse",
        annotations={"title": "Outside Agents — Browse Portal Page", "readOnlyHint": True},
    )
    async def oa_browse(
        portal: str = "magtap",
        path: str = "",
        extract: str = "text",
        screenshot: bool = True,
        max_length: int = 30000,
    ) -> str:
        """Navigate to a page in a portal and extract content.

        John must be logged in to the portal in Chrome first.
        Uses CDP to ride the existing Chrome session.

        Args:
            portal: Portal name — 'magtap', 'odysseus', or 'tess'
            path: URL path (e.g., '/bookings/search.aspx') or full URL.
                  Empty = use current tab or go to portal home.
            extract: What to extract — 'text', 'html', 'links', 'tables', or 'all'
            screenshot: Take a screenshot
            max_length: Max chars to return
        """
        portal_key = portal.lower().strip()
        if portal_key not in PORTALS:
            return json.dumps({"error": f"Unknown portal: {portal}. Options: {list(PORTALS.keys())}"})

        portal_def = PORTALS[portal_key]

        try:
            browser, ctx = await _connect_cdp()
        except Exception as e:
            return json.dumps({"error": "Chrome CDP not connected", "detail": str(e)})

        # Find or create portal tab
        page = await _find_portal_tab(ctx, portal_key)
        if not page:
            page = await ctx.new_page()
            target = path if path.startswith("http") else portal_def["home_url"]
            await page.goto(target, wait_until="networkidle", timeout=30000)
        elif path:
            if path.startswith("http"):
                target = path
            else:
                base = portal_def["home_url"] or portal_def["login_url"].rsplit("/", 1)[0]
                target = base.rstrip("/") + "/" + path.lstrip("/")
            await page.goto(target, wait_until="networkidle", timeout=30000)

        await page.wait_for_timeout(2000)

        result = {
            "status": "success",
            "portal": portal_key,
            "url": page.url,
            "title": await page.title(),
        }

        if extract in ("text", "all"):
            text = await page.evaluate("document.body.innerText")
            result["text"] = text[:max_length]
            if len(text) > max_length:
                result["truncated"] = True
                result["total_chars"] = len(text)

        if extract in ("html", "all"):
            html = await page.content()
            result["html"] = html[:max_length]

        if extract in ("links", "all"):
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    text: a.innerText.trim().substring(0, 100),
                    href: a.href
                })).filter(l => l.text && l.href.startsWith('http'))
            """)
            result["links"] = links[:200]

        if extract in ("tables", "all"):
            tables = await page.evaluate("""
                () => Array.from(document.querySelectorAll('table')).slice(0, 10).map((t, i) => ({
                    index: i,
                    rows: Array.from(t.querySelectorAll('tr')).slice(0, 50).map(row =>
                        Array.from(row.querySelectorAll('td, th')).map(c => c.innerText.trim().substring(0, 200))
                    )
                }))
            """)
            result["tables"] = tables

        if screenshot:
            path_s = _screenshot_path(portal_key, "browse")
            await page.screenshot(path=str(path_s))
            result["screenshot"] = str(path_s)

        return json.dumps(result, indent=2)

    @mcp.tool(
        name="oa_action",
        annotations={"title": "Outside Agents — Interact with Portal", "readOnlyHint": False},
    )
    async def oa_action(
        portal: str = "magtap",
        actions: str = "[]",
        screenshot: bool = True,
        max_length: int = 30000,
    ) -> str:
        """Perform actions on a portal page in Chrome via CDP.

        Args:
            portal: Portal name
            actions: JSON array of actions:
                [
                    {"action": "goto", "url": "/bookings/search.aspx"},
                    {"action": "click", "selector": "button.search"},
                    {"action": "type", "selector": "input#search", "text": "Loucks"},
                    {"action": "select", "selector": "select#status", "value": "confirmed"},
                    {"action": "scroll", "direction": "down"},
                    {"action": "wait", "seconds": 3},
                    {"action": "screenshot", "name": "results"},
                    {"action": "extract_text"},
                    {"action": "extract_table", "selector": "table.bookings"}
                ]
            screenshot: Take a final screenshot
            max_length: Max chars to return
        """
        portal_key = portal.lower().strip()
        if portal_key not in PORTALS:
            return json.dumps({"error": f"Unknown portal: {portal}"})

        portal_def = PORTALS[portal_key]

        try:
            action_list = json.loads(actions)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON in actions"})

        try:
            browser, ctx = await _connect_cdp()
        except Exception as e:
            return json.dumps({"error": "Chrome CDP not connected", "detail": str(e)})

        page = await _find_portal_tab(ctx, portal_key)
        if not page:
            return json.dumps({"error": f"No {portal_def['name']} tab open in Chrome. Navigate there first."})

        step_results = []
        for i, act in enumerate(action_list):
            action_type = act.get("action", "")
            step = {"step": i + 1, "action": action_type}

            try:
                if action_type == "goto":
                    url = act["url"]
                    if not url.startswith("http"):
                        base = portal_def["home_url"] or portal_def["login_url"].rsplit("/", 1)[0]
                        url = base.rstrip("/") + "/" + url.lstrip("/")
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    step["status"] = "ok"
                    step["url"] = page.url

                elif action_type == "click":
                    await page.click(act["selector"], timeout=10000)
                    await page.wait_for_timeout(1000)
                    step["status"] = "ok"

                elif action_type == "type":
                    await page.fill(act["selector"], act["text"])
                    step["status"] = "ok"

                elif action_type == "select":
                    await page.select_option(act["selector"], act["value"])
                    step["status"] = "ok"

                elif action_type == "scroll":
                    direction = act.get("direction", "down")
                    if direction == "down":
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    else:
                        await page.evaluate("window.scrollTo(0, 0)")
                    step["status"] = "ok"

                elif action_type == "wait":
                    secs = min(act.get("seconds", 2), 15)
                    await page.wait_for_timeout(secs * 1000)
                    step["status"] = "ok"

                elif action_type == "screenshot":
                    name = act.get("name", f"step_{i+1}")
                    path_s = _screenshot_path(portal_key, name)
                    await page.screenshot(path=str(path_s))
                    step["status"] = "ok"
                    step["path"] = str(path_s)

                elif action_type == "extract_text":
                    text = await page.evaluate("document.body.innerText")
                    step["status"] = "ok"
                    step["text"] = text[:max_length]

                elif action_type == "extract_table":
                    selector = act.get("selector", "table")
                    table_data = await page.evaluate(f"""
                        () => {{
                            const t = document.querySelector('{selector}');
                            if (!t) return null;
                            return Array.from(t.querySelectorAll('tr')).slice(0, 100).map(row =>
                                Array.from(row.querySelectorAll('td, th')).map(c => c.innerText.trim().substring(0, 200))
                            );
                        }}
                    """)
                    step["status"] = "ok"
                    step["table"] = table_data

                else:
                    step["status"] = "unknown_action"

            except Exception as e:
                step["status"] = "error"
                step["error"] = str(e)

            step_results.append(step)

        result = {
            "status": "success",
            "portal": portal_key,
            "url": page.url,
            "title": await page.title(),
            "actions": step_results,
        }

        if screenshot:
            path_s = _screenshot_path(portal_key, "final")
            await page.screenshot(path=str(path_s))
            result["screenshot"] = str(path_s)

        return json.dumps(result, indent=2)

    @mcp.tool(
        name="oa_status",
        annotations={"title": "Outside Agents — Connection Status", "readOnlyHint": True},
    )
    async def oa_status() -> str:
        """Check Chrome CDP connection and portal tab status."""
        try:
            browser, ctx = await _connect_cdp()
        except Exception as e:
            return json.dumps({
                "connected": False,
                "error": str(e),
                "fix": "Launch Chrome with: google-chrome-stable --remote-debugging-port=9222 --user-data-dir=$HOME/.config/google-chrome-debug",
            }, indent=2)

        portals = {}
        for key, portal in PORTALS.items():
            tab = await _find_portal_tab(ctx, key)
            if tab:
                try:
                    body = (await tab.inner_text("body")).lower()[:500]
                    authenticated = any(s in body for s in portal["auth_signals"])
                    portals[key] = {"name": portal["name"], "open": True, "authenticated": authenticated, "url": tab.url}
                except Exception:
                    portals[key] = {"name": portal["name"], "open": True, "authenticated": False}
            else:
                portals[key] = {"name": portal["name"], "open": False, "authenticated": False}

        return json.dumps({
            "connected": True,
            "chrome_tabs": len(ctx.pages),
            "portals": portals,
        }, indent=2)

    # ==================================================================
    # PURPOSE-BUILT TOOLS — Booking Scraper, Commissions, Invoice,
    # Portal Activation, Portal Monitor
    # ==================================================================

    @mcp.tool(
        name="oa_scrape_bookings",
        annotations={"title": "Outside Agents — Scrape Odysseus Bookings", "readOnlyHint": True},
    )
    async def oa_scrape_bookings(
        sync_to_sheets: bool = Field(False, description="Also push extracted bookings to Google Sheets Booking Master"),
        screenshot: bool = Field(True, description="Take a screenshot of the report view"),
    ) -> str:
        """Scrape the Odysseus Report View for all bookings and return structured JSON.

        Navigates to Odysseus > Bookings > Report View, extracts the booking table
        with all available fields (confirmation, client, supplier, dates, costs,
        commissions, status, etc.). Optionally syncs to Google Sheets.

        Prerequisites: Chrome CDP running, John logged into Odysseus.
        """
        try:
            browser, ctx = await _connect_cdp()
        except Exception as e:
            return json.dumps({"error": "Chrome CDP not connected", "detail": str(e)})

        page = await _find_portal_tab(ctx, "odysseus")
        if not page:
            page = await ctx.new_page()

        try:
            await page.goto(ODY_BOOKINGS, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # Extract the report table — headers + rows
            table_data = await page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    // Find the largest table (the report view)
                    let best = null;
                    let bestRows = 0;
                    for (const t of tables) {
                        const rows = t.querySelectorAll('tr').length;
                        if (rows > bestRows) { bestRows = rows; best = t; }
                    }
                    if (!best) return null;

                    const rows = Array.from(best.querySelectorAll('tr'));
                    if (rows.length === 0) return null;

                    // First row = headers
                    const headers = Array.from(rows[0].querySelectorAll('th, td'))
                        .map(c => c.innerText.trim());

                    // Data rows
                    const data = rows.slice(1).map(row =>
                        Array.from(row.querySelectorAll('td'))
                            .map(c => c.innerText.trim())
                    );

                    return { headers, data };
                }
            """)

            if not table_data or not table_data.get("data"):
                # Fallback: try extracting all visible text
                text = await page.evaluate("document.body.innerText")
                result = {
                    "status": "partial",
                    "message": "No booking table found — returning page text",
                    "url": page.url,
                    "text": text[:10000],
                }
                if screenshot:
                    sp = _screenshot_path("odysseus", "bookings")
                    await page.screenshot(path=str(sp))
                    result["screenshot"] = str(sp)
                return json.dumps(result, indent=2)

            headers = table_data["headers"]
            bookings = []
            for row in table_data["data"]:
                booking = {}
                for i, val in enumerate(row):
                    if i < len(headers) and headers[i]:
                        booking[headers[i]] = val
                if booking:
                    bookings.append(booking)

            result = {
                "status": "success",
                "source": "odysseus_report_view",
                "url": page.url,
                "booking_count": len(bookings),
                "columns": headers,
                "bookings": bookings,
                "scraped_at": datetime.now().isoformat(),
            }

            if screenshot:
                sp = _screenshot_path("odysseus", "bookings")
                await page.screenshot(path=str(sp))
                result["screenshot"] = str(sp)

            # Save state for diff monitoring
            _save_state("bookings_latest", {
                "bookings": bookings,
                "scraped_at": datetime.now().isoformat(),
            })

            # Optional Sheets sync
            if sync_to_sheets and bookings:
                sheets_result = _sync_bookings_to_sheets(bookings, headers)
                result["sheets_sync"] = sheets_result

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            logger.error(f"Booking scrape error: {e}")
            return json.dumps({"error": str(e), "type": "scrape_error"})

    @mcp.tool(
        name="oa_scrape_commissions",
        annotations={"title": "Outside Agents — Scrape TESS Commissions", "readOnlyHint": True},
    )
    async def oa_scrape_commissions(
        screenshot: bool = Field(True, description="Take a screenshot of the commission page"),
    ) -> str:
        """Scrape the TESS commission report and return structured JSON.

        Navigates to TESS > Commissions, extracts commission data including
        booking references, amounts, status (pending/paid), and dates.

        Prerequisites: Chrome CDP running, John logged into TESS.
        """
        try:
            browser, ctx = await _connect_cdp()
        except Exception as e:
            return json.dumps({"error": "Chrome CDP not connected", "detail": str(e)})

        page = await _find_portal_tab(ctx, "tess")
        if not page:
            page = await ctx.new_page()

        try:
            await page.goto(TESS_COMMISSIONS, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # Extract commission table
            table_data = await page.evaluate("""
                () => {
                    const tables = document.querySelectorAll('table');
                    let best = null;
                    let bestRows = 0;
                    for (const t of tables) {
                        const rows = t.querySelectorAll('tr').length;
                        if (rows > bestRows) { bestRows = rows; best = t; }
                    }
                    if (!best) return null;

                    const rows = Array.from(best.querySelectorAll('tr'));
                    if (rows.length === 0) return null;

                    const headers = Array.from(rows[0].querySelectorAll('th, td'))
                        .map(c => c.innerText.trim());
                    const data = rows.slice(1).map(row =>
                        Array.from(row.querySelectorAll('td'))
                            .map(c => c.innerText.trim())
                    );
                    return { headers, data };
                }
            """)

            # Also extract any summary/totals text on the page
            summary_text = await page.evaluate("""
                () => {
                    // Look for summary cards, total boxes, or header stats
                    const candidates = document.querySelectorAll(
                        '.summary, .totals, .commission-summary, .card, .stat, .widget, [class*="total"], [class*="summary"]'
                    );
                    return Array.from(candidates).map(el => el.innerText.trim()).filter(t => t.length > 0).slice(0, 10);
                }
            """)

            commissions = []
            headers = []
            if table_data and table_data.get("data"):
                headers = table_data["headers"]
                for row in table_data["data"]:
                    record = {}
                    for i, val in enumerate(row):
                        if i < len(headers) and headers[i]:
                            record[headers[i]] = val
                    if record:
                        commissions.append(record)

            # Fallback to full text if no table
            if not commissions:
                text = await page.evaluate("document.body.innerText")
                result = {
                    "status": "partial",
                    "message": "No commission table found — returning page text and summaries",
                    "url": page.url,
                    "summary_widgets": summary_text,
                    "text": text[:10000],
                }
            else:
                # Save for monitoring
                _save_state("commissions_latest", {
                    "commissions": commissions,
                    "scraped_at": datetime.now().isoformat(),
                })

                result = {
                    "status": "success",
                    "source": "tess_commissions",
                    "url": page.url,
                    "commission_count": len(commissions),
                    "columns": headers,
                    "commissions": commissions,
                    "summary_widgets": summary_text,
                    "scraped_at": datetime.now().isoformat(),
                }

            if screenshot:
                sp = _screenshot_path("tess", "commissions")
                await page.screenshot(path=str(sp))
                result["screenshot"] = str(sp)

            return json.dumps(result, indent=2, default=str)

        except Exception as e:
            logger.error(f"Commission scrape error: {e}")
            return json.dumps({"error": str(e), "type": "scrape_error"})

    @mcp.tool(
        name="oa_send_invoice",
        annotations={"title": "Outside Agents — Send Invoice from TESS", "readOnlyHint": False},
    )
    async def oa_send_invoice(
        trip_name: str = Field(..., description="Trip name or ID to find in TESS Trip Management"),
        client_name: str = Field(..., description="Client name to select in the invoice recipient dropdown"),
        template: str = Field("MAG Invoice Detail", description="Invoice template: 'MAG Invoice', 'MAG Invoice 2018', or 'MAG Invoice Detail'"),
        test_only: bool = Field(True, description="True = send test invoice to YOUR email first. False = send to client (use with caution)."),
        export_pdf: bool = Field(False, description="Also export invoice as PDF"),
    ) -> str:
        """Automate sending an invoice from TESS.

        Navigates to Trip Management > [trip] > COMMUNICATION tab,
        selects the invoice template, selects the client, and either
        sends a test invoice (to John) or sends to the client.

        SAFETY: test_only=True by default — sends to your email, not the client.

        Prerequisites: Chrome CDP running, John logged into TESS.
        Trip must have active bookings and travelers.
        """
        try:
            browser, ctx = await _connect_cdp()
        except Exception as e:
            return json.dumps({"error": "Chrome CDP not connected", "detail": str(e)})

        page = await _find_portal_tab(ctx, "tess")
        if not page:
            page = await ctx.new_page()

        try:
            # Step 1: Navigate to Trip Management > Trips
            await page.goto(TESS_TRIPS, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            # Step 2: Search/click the trip
            # Try to find a search input and type the trip name
            search_filled = False
            for selector in ["input[placeholder*='search' i]", "input[placeholder*='trip' i]",
                             "input[type='search']", "input.search", "#search"]:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        await el.fill(trip_name)
                        await page.wait_for_timeout(1500)
                        search_filled = True
                        break
                except Exception:
                    continue

            # Click the trip link that matches
            trip_clicked = False
            try:
                links = await page.query_selector_all("a, tr, .trip-row, [class*='trip']")
                for link in links:
                    text = (await link.inner_text()).strip()
                    if trip_name.lower() in text.lower():
                        await link.click()
                        await page.wait_for_timeout(2000)
                        trip_clicked = True
                        break
            except Exception:
                pass

            if not trip_clicked:
                sp = _screenshot_path("tess", "invoice_trip_not_found")
                await page.screenshot(path=str(sp))
                return json.dumps({
                    "error": f"Could not find trip '{trip_name}' in TESS",
                    "screenshot": str(sp),
                    "suggestion": "Check the trip name matches exactly what appears in TESS Trip Management",
                }, indent=2)

            # Step 3: Click COMMUNICATION tab
            comm_clicked = False
            for selector in ["[data-tab*='communication' i]", "a:has-text('Communication')",
                             "a:has-text('COMMUNICATION')", ".tab:has-text('Communication')",
                             "li:has-text('Communication')"]:
                try:
                    await page.click(selector, timeout=5000)
                    await page.wait_for_timeout(2000)
                    comm_clicked = True
                    break
                except Exception:
                    continue

            if not comm_clicked:
                # Try clicking by text content
                try:
                    await page.evaluate("""
                        () => {
                            const els = document.querySelectorAll('a, button, li, div, span');
                            for (const el of els) {
                                if (el.innerText.trim().toUpperCase() === 'COMMUNICATION') {
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    await page.wait_for_timeout(2000)
                    comm_clicked = True
                except Exception:
                    pass

            if not comm_clicked:
                sp = _screenshot_path("tess", "invoice_no_comm_tab")
                await page.screenshot(path=str(sp))
                return json.dumps({
                    "error": "Could not find COMMUNICATION tab on trip page",
                    "screenshot": str(sp),
                }, indent=2)

            # Step 4: Select invoice template
            template_selected = False
            try:
                await page.evaluate(f"""
                    () => {{
                        const items = document.querySelectorAll('a, li, div, span, td');
                        for (const el of items) {{
                            const txt = el.innerText.trim();
                            if (txt === '{template}' || txt.includes('{template}')) {{
                                el.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}
                """)
                await page.wait_for_timeout(2000)
                template_selected = True
            except Exception as e:
                logger.warning(f"Template selection failed: {e}")

            if not template_selected:
                sp = _screenshot_path("tess", "invoice_no_template")
                await page.screenshot(path=str(sp))
                return json.dumps({
                    "error": f"Could not select template '{template}'",
                    "screenshot": str(sp),
                }, indent=2)

            # Step 5: Select client from dropdown
            client_selected = False
            try:
                # Look for client dropdown
                for sel in ["select[name*='client' i]", "select[id*='client' i]",
                            "select.client", "#clientSelect", "select"]:
                    try:
                        options = await page.evaluate(f"""
                            () => {{
                                const select = document.querySelector("{sel}");
                                if (!select) return null;
                                const opts = Array.from(select.options);
                                const match = opts.find(o =>
                                    o.text.toLowerCase().includes("{client_name.lower()}")
                                );
                                if (match) {{
                                    select.value = match.value;
                                    select.dispatchEvent(new Event('change', {{bubbles: true}}));
                                    return match.text;
                                }}
                                return null;
                            }}
                        """)
                        if options:
                            client_selected = True
                            break
                    except Exception:
                        continue
            except Exception:
                pass

            if not client_selected:
                sp = _screenshot_path("tess", "invoice_no_client")
                await page.screenshot(path=str(sp))
                return json.dumps({
                    "error": f"Could not select client '{client_name}' from dropdown",
                    "screenshot": str(sp),
                }, indent=2)

            await page.wait_for_timeout(2000)

            # Step 6: Click the appropriate send button
            actions_taken = []

            if export_pdf:
                try:
                    await page.evaluate("""
                        () => {
                            const btns = document.querySelectorAll('button, a, input[type="button"]');
                            for (const b of btns) {
                                if (b.innerText && b.innerText.toLowerCase().includes('export to pdf')) {
                                    b.click();
                                    return true;
                                }
                            }
                            return false;
                        }
                    """)
                    await page.wait_for_timeout(2000)
                    actions_taken.append("pdf_exported")
                except Exception:
                    actions_taken.append("pdf_export_failed")

            if test_only:
                button_text = "email test invoice"
            else:
                button_text = "email invoice"

            try:
                await page.evaluate(f"""
                    () => {{
                        const btns = document.querySelectorAll('button, a, input[type="button"]');
                        for (const b of btns) {{
                            if (b.innerText && b.innerText.toLowerCase().includes('{button_text}')) {{
                                b.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}
                """)
                await page.wait_for_timeout(3000)
                actions_taken.append("test_invoice_sent" if test_only else "invoice_sent_to_client")
            except Exception as e:
                actions_taken.append(f"send_failed: {e}")

            sp = _screenshot_path("tess", "invoice_result")
            await page.screenshot(path=str(sp))

            return json.dumps({
                "status": "success",
                "trip": trip_name,
                "client": client_name,
                "template": template,
                "test_only": test_only,
                "actions": actions_taken,
                "screenshot": str(sp),
                "url": page.url,
            }, indent=2)

        except Exception as e:
            logger.error(f"Invoice automation error: {e}")
            sp = _screenshot_path("tess", "invoice_error")
            try:
                await page.screenshot(path=str(sp))
            except Exception:
                sp = None
            return json.dumps({
                "error": str(e),
                "type": "invoice_error",
                "screenshot": str(sp) if sp else None,
            }, indent=2)

    @mcp.tool(
        name="oa_activate_portal",
        annotations={"title": "Outside Agents — Activate Client Portal", "readOnlyHint": False},
    )
    async def oa_activate_portal(
        trip_name: str = Field(..., description="Trip name to find in TESS Trip Management"),
        client_name: str = Field(..., description="Client name to send the portal activation email to"),
    ) -> str:
        """Send the Client Portal Activation email from TESS.

        Navigates to the trip's COMMUNICATION tab, selects the
        'Client Portal Activation' template, selects the client,
        and sends the activation email.

        Once activated, the client can:
        - View trip details, itineraries, bookings
        - Add credit card information securely
        - Upload documents and complete tasks

        Prerequisites: Chrome CDP running, John logged into TESS.
        """
        try:
            browser, ctx = await _connect_cdp()
        except Exception as e:
            return json.dumps({"error": "Chrome CDP not connected", "detail": str(e)})

        page = await _find_portal_tab(ctx, "tess")
        if not page:
            page = await ctx.new_page()

        try:
            # Navigate to Trip Management
            await page.goto(TESS_TRIPS, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            # Search and click the trip
            trip_clicked = False
            for selector in ["input[placeholder*='search' i]", "input[type='search']", "input.search"]:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        await el.fill(trip_name)
                        await page.wait_for_timeout(1500)
                        break
                except Exception:
                    continue

            try:
                links = await page.query_selector_all("a, tr, .trip-row, [class*='trip']")
                for link in links:
                    text = (await link.inner_text()).strip()
                    if trip_name.lower() in text.lower():
                        await link.click()
                        await page.wait_for_timeout(2000)
                        trip_clicked = True
                        break
            except Exception:
                pass

            if not trip_clicked:
                sp = _screenshot_path("tess", "portal_trip_not_found")
                await page.screenshot(path=str(sp))
                return json.dumps({
                    "error": f"Could not find trip '{trip_name}'",
                    "screenshot": str(sp),
                }, indent=2)

            # Click COMMUNICATION tab
            comm_clicked = False
            try:
                await page.evaluate("""
                    () => {
                        const els = document.querySelectorAll('a, button, li, div, span');
                        for (const el of els) {
                            if (el.innerText.trim().toUpperCase() === 'COMMUNICATION') {
                                el.click();
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                await page.wait_for_timeout(2000)
                comm_clicked = True
            except Exception:
                pass

            if not comm_clicked:
                sp = _screenshot_path("tess", "portal_no_comm_tab")
                await page.screenshot(path=str(sp))
                return json.dumps({"error": "Could not find COMMUNICATION tab", "screenshot": str(sp)}, indent=2)

            # Select "Client Portal Activation" template
            template_selected = False
            try:
                await page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('a, li, div, span, td');
                        for (const el of items) {
                            const txt = el.innerText.trim();
                            if (txt.includes('Client Portal Activation') || txt.includes('Portal Activation')) {
                                el.click();
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                await page.wait_for_timeout(2000)
                template_selected = True
            except Exception:
                pass

            if not template_selected:
                sp = _screenshot_path("tess", "portal_no_template")
                await page.screenshot(path=str(sp))
                return json.dumps({
                    "error": "Could not find 'Client Portal Activation' template",
                    "screenshot": str(sp),
                }, indent=2)

            # Select client
            client_selected = False
            try:
                for sel in ["select[name*='client' i]", "select[id*='client' i]", "select"]:
                    result_val = await page.evaluate(f"""
                        () => {{
                            const select = document.querySelector("{sel}");
                            if (!select) return null;
                            const opts = Array.from(select.options);
                            const match = opts.find(o =>
                                o.text.toLowerCase().includes("{client_name.lower()}")
                            );
                            if (match) {{
                                select.value = match.value;
                                select.dispatchEvent(new Event('change', {{bubbles: true}}));
                                return match.text;
                            }}
                            return null;
                        }}
                    """)
                    if result_val:
                        client_selected = True
                        break
            except Exception:
                pass

            if not client_selected:
                sp = _screenshot_path("tess", "portal_no_client")
                await page.screenshot(path=str(sp))
                return json.dumps({
                    "error": f"Could not select client '{client_name}'",
                    "screenshot": str(sp),
                }, indent=2)

            await page.wait_for_timeout(1500)

            # Click send button
            sent = False
            try:
                await page.evaluate("""
                    () => {
                        const btns = document.querySelectorAll('button, a, input[type="button"]');
                        for (const b of btns) {
                            const txt = (b.innerText || '').toLowerCase();
                            if (txt.includes('email client portal') || txt.includes('send activation')
                                || txt.includes('activate') || txt.includes('send email')) {
                                b.click();
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                await page.wait_for_timeout(3000)
                sent = True
            except Exception:
                pass

            sp = _screenshot_path("tess", "portal_activation_result")
            await page.screenshot(path=str(sp))

            if sent:
                _notify_commander(
                    f"🔑 *Client Portal Activation sent*\n"
                    f"Trip: {trip_name}\nClient: {client_name}\n"
                    f"Client will receive email with ACTIVATE NOW button."
                )

            return json.dumps({
                "status": "success" if sent else "uncertain",
                "action": "portal_activation_sent" if sent else "send_button_not_confirmed",
                "trip": trip_name,
                "client": client_name,
                "screenshot": str(sp),
                "url": page.url,
                "note": "Client will receive email with ACTIVATE NOW button. "
                        "They register via Passkey or One-Time Code, then can add credit cards, "
                        "upload documents, and complete tasks.",
            }, indent=2)

        except Exception as e:
            logger.error(f"Portal activation error: {e}")
            return json.dumps({"error": str(e), "type": "portal_error"}, indent=2)

    @mcp.tool(
        name="oa_portal_monitor",
        annotations={"title": "Outside Agents — Monitor Portal for Changes", "readOnlyHint": True},
    )
    async def oa_portal_monitor(
        check_bookings: bool = Field(True, description="Check Odysseus for booking changes"),
        check_commissions: bool = Field(True, description="Check TESS for commission changes"),
        check_client_activity: bool = Field(True, description="Check TESS for client portal activity (credit cards, documents, tasks)"),
        notify: bool = Field(True, description="Send Telegram notification if changes detected"),
    ) -> str:
        """Monitor OA portals for changes since last check.

        Compares current portal state against saved state from last scrape.
        Detects: new/changed bookings, commission updates, client portal
        activity (new credit cards, documents uploaded, tasks completed).

        Sends Telegram alerts to the Commander when changes are found.

        Prerequisites: Chrome CDP running, John logged into portals.
        Best used on a cron schedule (e.g., every 30 minutes).
        """
        try:
            browser, ctx = await _connect_cdp()
        except Exception as e:
            return json.dumps({"error": "Chrome CDP not connected", "detail": str(e)})

        changes = []
        results = {"status": "success", "checked_at": datetime.now().isoformat(), "changes": []}

        # --- Check Bookings ---
        if check_bookings:
            try:
                page = await _find_portal_tab(ctx, "odysseus")
                if not page:
                    page = await ctx.new_page()

                await page.goto(ODY_BOOKINGS, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)

                current_text = await page.evaluate("document.body.innerText")
                previous = _load_state("bookings_monitor")

                if previous.get("text_hash"):
                    import hashlib
                    current_hash = hashlib.md5(current_text.encode()).hexdigest()
                    if current_hash != previous["text_hash"]:
                        changes.append({
                            "type": "bookings_changed",
                            "detail": "Odysseus booking data has changed since last check",
                        })

                _save_state("bookings_monitor", {
                    "text_hash": hashlib.md5(current_text.encode()).hexdigest() if 'hashlib' in dir() else "",
                    "checked_at": datetime.now().isoformat(),
                    "text_preview": current_text[:500],
                })

            except Exception as e:
                results["booking_check_error"] = str(e)

        # --- Check Commissions ---
        if check_commissions:
            try:
                page = await _find_portal_tab(ctx, "tess")
                if not page:
                    page = await ctx.new_page()

                await page.goto(TESS_COMMISSIONS, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)

                current_text = await page.evaluate("document.body.innerText")
                previous = _load_state("commissions_monitor")

                import hashlib
                current_hash = hashlib.md5(current_text.encode()).hexdigest()
                if previous.get("text_hash") and current_hash != previous["text_hash"]:
                    changes.append({
                        "type": "commissions_changed",
                        "detail": "TESS commission data has changed since last check",
                    })

                _save_state("commissions_monitor", {
                    "text_hash": current_hash,
                    "checked_at": datetime.now().isoformat(),
                    "text_preview": current_text[:500],
                })

            except Exception as e:
                results["commission_check_error"] = str(e)

        # --- Check Client Portal Activity ---
        if check_client_activity:
            try:
                page = await _find_portal_tab(ctx, "tess")
                if not page:
                    page = await ctx.new_page()

                # Navigate to Client Management
                await page.goto(TESS_CLIENTS, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)

                # Extract client list with visible status indicators
                client_data = await page.evaluate("""
                    () => {
                        const rows = document.querySelectorAll('tr, .client-row, [class*="client"]');
                        const clients = [];
                        for (const row of rows) {
                            const text = row.innerText.trim();
                            if (text.length > 5 && text.length < 500) {
                                clients.push(text.replace(/\\n/g, ' | '));
                            }
                        }
                        return clients.slice(0, 50);
                    }
                """)

                previous = _load_state("clients_monitor")
                import hashlib
                current_hash = hashlib.md5(json.dumps(client_data).encode()).hexdigest()

                if previous.get("data_hash") and current_hash != previous["data_hash"]:
                    # Find what changed
                    old_set = set(previous.get("clients", []))
                    new_set = set(client_data)
                    added = new_set - old_set
                    removed = old_set - new_set

                    change_detail = "Client data changed."
                    if added:
                        change_detail += f" New/modified entries: {len(added)}."
                    if removed:
                        change_detail += f" Removed entries: {len(removed)}."

                    changes.append({
                        "type": "client_activity",
                        "detail": change_detail,
                        "new_entries": list(added)[:10],
                    })

                _save_state("clients_monitor", {
                    "data_hash": current_hash,
                    "clients": client_data,
                    "checked_at": datetime.now().isoformat(),
                })

            except Exception as e:
                results["client_check_error"] = str(e)

        results["changes"] = changes
        results["change_count"] = len(changes)

        # Send Telegram notification if changes found
        if notify and changes:
            lines = ["🔔 *OA Portal Changes Detected*\n"]
            for c in changes:
                lines.append(f"• *{c['type']}*: {c['detail']}")
            lines.append(f"\n_Checked at {datetime.now().strftime('%H:%M %b %d')}_")
            _notify_commander("\n".join(lines))
            results["notification_sent"] = True

        if not changes:
            results["message"] = "No changes detected since last check"

        return json.dumps(results, indent=2, default=str)

    logger.info("Outside Agents portal tools registered (oa_connect, oa_browse, oa_action, oa_status, "
                "oa_scrape_bookings, oa_scrape_commissions, oa_send_invoice, oa_activate_portal, oa_portal_monitor)")


# ============================================================================
# Sheets Sync Helper (used by oa_scrape_bookings)
# ============================================================================

def _sync_bookings_to_sheets(bookings: list[dict], headers: list[str]) -> dict:
    """Push scraped Odysseus bookings to Google Sheets Booking Master.

    Maps Odysseus report fields to the Booking Master column structure.
    Appends new rows; does not overwrite existing data.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        if not CREDENTIALS_FILE.exists():
            return {"error": f"Credentials not found: {CREDENTIALS_FILE}"}

        creds = service_account.Credentials.from_service_account_file(
            str(CREDENTIALS_FILE),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        service = build("sheets", "v4", credentials=creds)

        # Field mapping: Odysseus header → Booking Master column index
        # Based on the 49-column structure in thunderbird_v3.py
        field_map = {
            "Agency Conf#": 3,       # D: Confirmation Number
            "Customer": 2,           # C: Client Name
            "FirstName": 2,
            "LastName": 2,
            "Email": 4,              # E: Email
            "Supplier": 11,          # L: Supplier
            "Conf#": 12,             # M: Supplier Confirmation
            "Status": 13,            # N: Status
            "Total": 14,             # O: Total Cost
            "From DateTime": 7,      # H: Start Date
            "To DateTime": 8,        # I: End Date
            "Pax": 21,              # V: Travelers
            "Cruise Commission": None,  # Tracked separately
        }

        rows_added = 0
        for booking in bookings:
            row = [""] * 49
            row[1] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Timestamp

            for field, value in booking.items():
                col_idx = field_map.get(field)
                if col_idx is not None and value:
                    # Handle client name concatenation
                    if field in ("FirstName", "LastName", "Customer"):
                        existing = row[2]
                        row[2] = f"{existing} {value}".strip() if existing else value
                    else:
                        row[col_idx] = value

            # Only add if we have at least a confirmation number or client name
            if row[2] or row[3]:
                service.spreadsheets().values().append(
                    spreadsheetId=SHEET_ID,
                    range="'Booking Master'!A:A",
                    valueInputOption="USER_ENTERED",
                    body={"values": [row]},
                ).execute()
                rows_added += 1

        return {"status": "success", "rows_added": rows_added}

    except Exception as e:
        logger.error(f"Sheets sync error: {e}")
        return {"error": str(e)}

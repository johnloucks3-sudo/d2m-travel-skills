"""
Dreams2Memories Browser MCP Module
===================================

General-purpose web browsing via Playwright Stealth:
- Browse any URL and extract page content
- Take screenshots
- Click elements and fill forms
- Extract links, tables, and structured data
- Persistent login profiles for agent portals (Bedsonline, Viking TA, etc.)

Login Handoff:
  1. browse_login("bedsonline", "https://www.bedsonline.com/login")
     -> Opens visible browser, Yoda logs in manually
  2. browse_url("https://www.bedsonline.com/search", profile="bedsonline")
     -> Reuses saved cookies — no re-login needed

Integrates with: travel_mcp_server.py
Dependencies: playwright, playwright-stealth
"""

import json
import logging
import asyncio
import base64
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

DOWNLOADS_DIR = Path.home() / "Downloads"
SCREENSHOTS_DIR = Path.home() / "Thunderbird" / "screenshots"
PROFILES_DIR = Path.home() / "Thunderbird" / "browser_profiles"


async def _launch_context(p, headless: bool = True, profile: str = None):
    """Launch a browser context, optionally with a persistent profile.

    If profile is set, uses a persistent context with saved cookies/storage.
    Otherwise creates a fresh ephemeral context.
    """
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    if profile:
        profile_dir = PROFILES_DIR / profile
        profile_dir.mkdir(parents=True, exist_ok=True)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            viewport={"width": 1920, "height": 1080},
            user_agent=user_agent,
        )
        return context, None  # persistent context IS the browser
    else:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
        )
        return context, browser


async def browse_url(
    url: str,
    extract: str = "text",
    wait_seconds: int = 3,
    screenshot: bool = False,
    scroll: bool = True,
    max_length: int = 30000,
    profile: str = "",
) -> str:
    """Browse any URL with stealth browser. Returns page text, HTML, links, or screenshot.

    Module-level function — importable by other Thunderbird modules.

    Args:
        url: The URL to browse
        extract: What to extract - 'text', 'html', 'links', 'tables', or 'all'
        wait_seconds: Seconds to wait after page load (1-15)
        screenshot: Also save a screenshot to ~/Thunderbird/screenshots/
        scroll: Scroll to bottom to trigger lazy-loading
        max_length: Max chars of content to return
        profile: Optional saved login profile name (from browse_login) to reuse cookies
    """
    wait_seconds = max(1, min(wait_seconds, 15))
    logger.info(f"Browsing: {url} (extract={extract}, profile={profile or 'none'})")

    try:
        async with Stealth().use_async(async_playwright()) as p:
            context, browser = await _launch_context(
                p, headless=True, profile=profile if profile else None
            )
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(wait_seconds * 1000)

            if scroll:
                await page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
                await page.wait_for_timeout(2000)

            result = {"status": "success", "url": url, "title": await page.title()}

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
                result["link_count"] = len(links)

            if extract in ("tables", "all"):
                tables = await page.evaluate("""
                    () => Array.from(document.querySelectorAll('table')).slice(0, 5).map((table, idx) => {
                        const rows = Array.from(table.querySelectorAll('tr')).slice(0, 50);
                        return {
                            index: idx,
                            row_count: table.querySelectorAll('tr').length,
                            data: rows.map(row =>
                                Array.from(row.querySelectorAll('td, th')).map(cell => cell.innerText.trim().substring(0, 200))
                            )
                        };
                    })
                """)
                result["tables"] = tables

            if screenshot:
                SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                domain = url.split("//")[-1].split("/")[0].replace(".", "_")
                screenshot_path = SCREENSHOTS_DIR / f"{domain}_{timestamp}.png"
                await page.screenshot(path=str(screenshot_path), full_page=False)
                result["screenshot"] = str(screenshot_path)

            await context.close()
            if browser:
                await browser.close()
            return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Browse error: {e}")
        return json.dumps({"error": str(e), "type": "browser_error"})


def register_browser_tools(mcp: FastMCP):
    """Register general-purpose browser tools with the MCP server."""

    @mcp.tool(
        name="browse_login",
        annotations={"title": "Login Handoff — Open Visible Browser", "readOnlyHint": False},
    )
    async def browse_login(
        profile_name: str,
        url: str,
        wait_for_close: bool = True,
    ) -> str:
        """Open a visible browser window for manual login. Cookies are saved to a persistent profile.

        After login, close the browser window. The session is saved and can be reused
        by browse_url and browse_and_click with profile=profile_name.

        Args:
            profile_name: Name for this login profile (e.g., 'bedsonline', 'viking_ta', 'regent')
            url: Login page URL
            wait_for_close: Wait for user to close the browser window (default True)
        """
        logger.info(f"Login handoff: {profile_name} -> {url}")

        try:
            async with Stealth().use_async(async_playwright()) as p:
                context, _ = await _launch_context(p, headless=False, profile=profile_name)
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                if wait_for_close:
                    # Wait for user to close the browser window
                    try:
                        await page.wait_for_event("close", timeout=300000)  # 5 min max
                    except Exception:
                        pass

                # Take a screenshot before closing
                SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = SCREENSHOTS_DIR / f"login_{profile_name}_{timestamp}.png"
                try:
                    await page.screenshot(path=str(screenshot_path), full_page=False)
                except Exception:
                    screenshot_path = None

                await context.close()

                return json.dumps({
                    "status": "success",
                    "profile": profile_name,
                    "profile_dir": str(PROFILES_DIR / profile_name),
                    "url": url,
                    "screenshot": str(screenshot_path) if screenshot_path else None,
                    "note": f"Session saved. Use profile='{profile_name}' in browse_url/browse_and_click to reuse.",
                }, indent=2)

        except Exception as e:
            logger.error(f"Login handoff error: {e}")
            return json.dumps({"error": str(e), "type": "login_error"})

    @mcp.tool(
        name="browse_list_profiles",
        annotations={"title": "List Saved Browser Profiles", "readOnlyHint": True},
    )
    async def browse_list_profiles() -> str:
        """List all saved browser login profiles."""
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        profiles = []
        for d in sorted(PROFILES_DIR.iterdir()):
            if d.is_dir():
                profiles.append({
                    "name": d.name,
                    "path": str(d),
                })
        return json.dumps({"status": "success", "profiles": profiles, "count": len(profiles)}, indent=2)

    @mcp.tool(
        name="browse_url",
        annotations={"title": "Browse URL (Stealth)", "readOnlyHint": True},
    )
    async def _browse_url_tool(
        url: str,
        extract: str = "text",
        wait_seconds: int = 3,
        screenshot: bool = False,
        scroll: bool = True,
        max_length: int = 30000,
        profile: str = "",
    ) -> str:
        """Browse any URL with stealth browser. Returns page text, HTML, links, or screenshot.

        Args:
            url: The URL to browse
            extract: What to extract - 'text', 'html', 'links', 'tables', or 'all'
            wait_seconds: Seconds to wait after page load (1-15)
            screenshot: Also save a screenshot to ~/Thunderbird/screenshots/
            scroll: Scroll to bottom to trigger lazy-loading
            max_length: Max chars of content to return (default 30K, Claude 1M context is GA)
            profile: Optional saved login profile name (from browse_login) to reuse cookies
        """
        return await browse_url(
            url=url,
            extract=extract,
            wait_seconds=wait_seconds,
            screenshot=screenshot,
            scroll=scroll,
            max_length=max_length,
            profile=profile,
        )

    @mcp.tool(
        name="browse_and_click",
        annotations={"title": "Browse and Interact", "readOnlyHint": True},
    )
    async def browse_and_click(
        url: str,
        actions: str = "[]",
        wait_seconds: int = 3,
        screenshot: bool = True,
        max_length: int = 30000,
        profile: str = "",
    ) -> str:
        """Browse a URL and perform a sequence of click/type/scroll actions.

        Args:
            url: The URL to browse
            actions: JSON array of actions, e.g.:
                [
                    {"action": "click", "selector": "button.search"},
                    {"action": "type", "selector": "input#search", "text": "luxury cruise"},
                    {"action": "scroll", "direction": "down"},
                    {"action": "wait", "seconds": 2},
                    {"action": "screenshot", "name": "after_search"}
                ]
            wait_seconds: Seconds to wait after page load
            screenshot: Take a final screenshot
            max_length: Max chars of content to return
            profile: Optional saved login profile name to reuse cookies
        """
        wait_seconds = max(1, min(wait_seconds, 15))
        logger.info(f"Interactive browse: {url} (profile={profile or 'none'})")

        try:
            action_list = json.loads(actions)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON in actions parameter"})

        try:
            async with Stealth().use_async(async_playwright()) as p:
                context, browser = await _launch_context(
                    p, headless=True, profile=profile if profile else None
                )
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(wait_seconds * 1000)

                action_results = []
                SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

                for i, act in enumerate(action_list):
                    action_type = act.get("action", "")
                    try:
                        if action_type == "click":
                            await page.click(act["selector"], timeout=10000)
                            action_results.append({"step": i + 1, "action": "click", "status": "ok"})

                        elif action_type == "type":
                            await page.fill(act["selector"], act["text"])
                            action_results.append({"step": i + 1, "action": "type", "status": "ok"})

                        elif action_type == "scroll":
                            direction = act.get("direction", "down")
                            if direction == "down":
                                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            else:
                                await page.evaluate("window.scrollTo(0, 0)")
                            action_results.append({"step": i + 1, "action": "scroll", "status": "ok"})

                        elif action_type == "wait":
                            secs = min(act.get("seconds", 2), 10)
                            await page.wait_for_timeout(secs * 1000)
                            action_results.append({"step": i + 1, "action": "wait", "status": "ok"})

                        elif action_type == "screenshot":
                            name = act.get("name", f"step_{i+1}")
                            path = SCREENSHOTS_DIR / f"{name}_{datetime.now().strftime('%H%M%S')}.png"
                            await page.screenshot(path=str(path), full_page=False)
                            action_results.append({"step": i + 1, "action": "screenshot", "path": str(path), "status": "ok"})

                        else:
                            action_results.append({"step": i + 1, "action": action_type, "status": "unknown_action"})

                    except Exception as e:
                        action_results.append({"step": i + 1, "action": action_type, "status": "error", "error": str(e)})

                text = await page.evaluate("document.body.innerText")
                result = {
                    "status": "success",
                    "url": url,
                    "title": await page.title(),
                    "actions": action_results,
                    "text": text[:max_length],
                }

                if screenshot:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    domain = url.split("//")[-1].split("/")[0].replace(".", "_")
                    screenshot_path = SCREENSHOTS_DIR / f"{domain}_final_{timestamp}.png"
                    await page.screenshot(path=str(screenshot_path), full_page=False)
                    result["screenshot"] = str(screenshot_path)

                await context.close()
                if browser:
                    await browser.close()
                return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Interactive browse error: {e}")
            return json.dumps({"error": str(e), "type": "browser_error"})

    logger.info("Browser tools registered successfully")

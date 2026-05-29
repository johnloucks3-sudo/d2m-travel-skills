#!/usr/bin/env python3
"""
MISSION-061 — invisible_playwright POC
ELON/A12 — Centrav + Cruise Line Pricing

Attempts invisible_playwright (patched Firefox, C++-level stealth),
falls back to standard Playwright + playwright-stealth.

Credentials are loaded from environment or a JSON config file so the
script is production-ready without hardcoded secrets.

Usage:
    # With invisible_playwright (install first):
    pip install git+https://github.com/feder-cr/invisible_playwright.git
    python -m invisible_playwright fetch

    export CENTRAV_USER=your_username
    export CENTRAV_PASS=your_password
    export CENTRAV_AGENCY_ID=your_agency_id

    python mission-061-invisible-playwright-poc.py

    # Or pass a config file:
    python mission-061-invisible-playwright-poc.py --config /path/to/config.json
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("mission-061")

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"

CENTRAV_URL = "https://www.centrav.com"
CENTRAV_LOGIN_URL = "https://agent.centrav.com/login"
PRINCESS_URL = "https://www.princess.com/cruise-search/"
CONFIG_KEYS = ["centrav_user", "centrav_pass", "centrav_agency_id"]


def load_config(config_path: str | None) -> dict:
    config = {}
    if config_path:
        path = Path(config_path)
        if not path.exists():
            log.error("Config file not found: %s", config_path)
            sys.exit(1)
        with open(path) as f:
            config = json.load(f)
    for key in CONFIG_KEYS:
        env_key = key.upper()
        if env_key in os.environ:
            config[key] = os.environ[env_key]
    missing = [k for k in CONFIG_KEYS if k not in config]
    if missing:
        log.warning("Missing config keys (will skip login): %s", missing)
    return config


def get_browser_impl():
    """Try invisible_playwright first, fall back to standard Playwright + stealth."""
    try:
        from invisible_playwright import InvisiblePlaywright
        log.info("Using invisible_playwright (patched Firefox, C++-level stealth)")
        return "invisible", InvisiblePlaywright
    except ImportError:
        log.info("invisible_playwright not installed, falling back to standard Playwright")
        return "standard", None


async def run_invisible(config: dict):
    from invisible_playwright import InvisiblePlaywright

    proxy = None
    if config.get("proxy_server"):
        proxy = {
            "server": config["proxy_server"],
            "username": config.get("proxy_user", ""),
            "password": config.get("proxy_pass", ""),
        }

    async with InvisiblePlaywright(proxy=proxy) as browser:
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=None,  # invisible_playwright manages its own UA
        )
        page = await context.new_page()
        await run_tasks(page, config)


def run_invisible_sync(config: dict):
    from invisible_playwright import InvisiblePlaywright

    proxy = None
    if config.get("proxy_server"):
        proxy = {
            "server": config["proxy_server"],
            "username": config.get("proxy_user", ""),
            "password": config.get("proxy_pass", ""),
        }

    with InvisiblePlaywright(proxy=proxy) as browser:
        page = browser.new_page()
        run_tasks_sync(page, config)


def run_standard_sync(config: dict):
    from playwright.sync_api import sync_playwright
    import playwright_stealth

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        playwright_stealth.stealth(page)
        log.info("Applied playwright-stealth evasions")
        run_tasks_sync(page, config)
        browser.close()


async def run_tasks(page, config: dict):
    """Async task runner — navigates to both targets."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        log.info("Navigating to Centrav: %s", CENTRAV_LOGIN_URL)
        await page.goto(CENTRAV_LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        centrav_path = SCREENSHOT_DIR / f"centrav_login_{ts}.png"
        await page.screenshot(path=str(centrav_path), full_page=True)
        log.info("Centrav screenshot saved: %s", centrav_path)
        log.info("Page title: %s", await page.title())
    except Exception as e:
        log.error("Centrav navigation failed: %s", e)

    try:
        log.info("Navigating to Princess: %s", PRINCESS_URL)
        await page.goto(PRINCESS_URL, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        princess_path = SCREENSHOT_DIR / f"princess_cruises_{ts}.png"
        await page.screenshot(path=str(princess_path), full_page=True)
        log.info("Princess screenshot saved: %s", princess_path)
        log.info("Page title: %s", await page.title())
    except Exception as e:
        log.error("Princess navigation failed: %s", e)


def run_tasks_sync(page, config: dict):
    """Sync task runner — navigates to both targets."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        log.info("Navigating to Centrav: %s", CENTRAV_LOGIN_URL)
        page.goto(CENTRAV_LOGIN_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        centrav_path = SCREENSHOT_DIR / f"centrav_login_{ts}.png"
        page.screenshot(path=str(centrav_path), full_page=True)
        log.info("Centrav screenshot saved: %s", centrav_path)
        log.info("Page title: %s", page.title())
    except Exception as e:
        log.error("Centrav navigation failed: %s", e)

    try:
        log.info("Navigating to Princess: %s", PRINCESS_URL)
        page.goto(PRINCESS_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        princess_path = SCREENSHOT_DIR / f"princess_cruises_{ts}.png"
        page.screenshot(path=str(princess_path), full_page=True)
        log.info("Princess screenshot saved: %s", princess_path)
        log.info("Page title: %s", page.title())
    except Exception as e:
        log.error("Princess navigation failed: %s", e)


def main():
    parser = argparse.ArgumentParser(
        description="MISSION-061: invisible_playwright POC — Centrav + Cruise Line Pricing"
    )
    parser.add_argument("--config", help="Path to JSON config file with centrav credentials")
    parser.add_argument(
        "--impl",
        choices=["invisible", "standard", "auto"],
        default="auto",
        help="Which browser implementation to use",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    impl_choice, impl_cls = get_browser_impl()

    if args.impl == "invisible":
        impl_choice = "invisible"
    elif args.impl == "standard":
        impl_choice = "standard"

    if impl_choice == "invisible":
        log.info("Launching invisible_playwright (sync mode)")
        run_invisible_sync(config)
    else:
        log.info("Launching standard Playwright + playwright-stealth")
        run_standard_sync(config)

    log.info("MISSION-061 complete — screenshots in %s", SCREENSHOT_DIR)


if __name__ == "__main__":
    main()

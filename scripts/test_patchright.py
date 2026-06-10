#!/usr/bin/env python3
"""Test patchright: stealth Chromium launch, navigate to rssc.com, screenshot."""
from patchright.sync_api import sync_playwright
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "output"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto("https://www.rssc.com", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    page.screenshot(path=str(OUT / "rssc_home_chromium.png"), full_page=True, timeout=60000)
    title = page.title()
    browser.close()

print(f"CHROMIUM OK — title: {title}")
print(f"Screenshot: {OUT / 'rssc_home_chromium.png'}")
sys.exit(0)

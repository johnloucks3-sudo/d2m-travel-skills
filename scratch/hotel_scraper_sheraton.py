#!/usr/bin/env python3
"""
Sheraton Desert Villas Scottsdale - Playwright headless rate scraper
Feb 1 - March 31, 2027 | 7-day rolling windows | Military/Senior/Loyalty rates
"""

import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime, timedelta
from pathlib import Path

class SheratonScraper:
    def __init__(self):
        self.results = {
            "marriott": [],
            "hilton": [],
            "roomres": [],
            "summary": {}
        }
        self.output_dir = Path("/home/john/Thunderbird/output")
        self.output_dir.mkdir(exist_ok=True)
        
    async def run(self):
        async with async_playwright() as p:
            # Launch non-headless so user can RoboForm
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()
            
            print("\n🦅 SHERATON DESERT VILLAS SCOTTSDALE RATE SCRAPER")
            print("=" * 60)
            print("Property: Sheraton Desert Villas Scottsdale")
            print("Dates: Feb 1 - March 31, 2027 (59 rolling 7-day windows)")
            print("Guests: 2 | Rooms: 1 or 2 king beds")
            print("=" * 60)
            
            # Step 1: Marriott Bonvoy
            print("\n📍 STEP 1: MARRIOTT BONVOY")
            print("Navigating to Marriott search page...")
            await page.goto("https://www.marriott.com/hotels/travel/phxsv-sheraton-desert-villas-scottsdale/")
            print("✅ Marriott page loaded. Please log in via RoboForm.")
            print("⏳ Waiting for your login... (press Enter when logged in)")
            input()
            
            # Step 2: Hilton Honors
            print("\n📍 STEP 2: HILTON HONORS")
            print("Navigating to Hilton search page...")
            await page.goto("https://www.hilton.com")
            print("✅ Hilton page loaded. Please log in via RoboForm.")
            print("⏳ Waiting for your login... (press Enter when logged in)")
            input()
            
            # Step 3: room-res.com
            print("\n📍 STEP 3: ROOM-RES.COM")
            print("Navigating to room-res.com...")
            await page.goto("https://www.room-res.com")
            print("✅ room-res.com page loaded. Please log in via RoboForm.")
            print("⏳ Waiting for your login... (press Enter when logged in)")
            input()
            
            print("\n✅ All logins complete. Starting automated window cycling...")
            
            await browser.close()
            print("\n🦅 Browser session closed. Ready for next phase.")

if __name__ == "__main__":
    scraper = SheratonScraper()
    asyncio.run(scraper.run())

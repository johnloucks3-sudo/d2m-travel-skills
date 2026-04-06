#!/usr/bin/env python3
"""
Cruise Website HTML Inspector
==============================

This tool helps you find the correct CSS selectors for scraping.
It will save the HTML from cruise line search pages so you can inspect them.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def inspect_regent():
    """Inspect Regent Seven Seas cruise search page"""
    url = "https://www.rssc.com/find-a-cruise"
    
    print("🔍 Inspecting Regent Seven Seas...")
    print(f"URL: {url}\n")
    
    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=False)  # headless=False so you can see
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            print("📡 Loading page...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            print("⏳ Waiting 5 seconds for dynamic content...")
            await page.wait_for_timeout(5000)
            
            # Scroll to load lazy content
            print("📜 Scrolling to load content...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)
            
            # Get full HTML
            html = await page.content()
            
            # Save to file
            output_file = Path("regent_html_inspection.html")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f"\n✅ HTML saved to: {output_file}")
            print("\nNow:")
            print("1. Open regent_html_inspection.html in a text editor")
            print("2. Search for words like 'Mediterranean', 'Venice', 'Barcelona'")
            print("3. Look at the HTML structure around those words")
            print("4. Find the CSS class or ID of the voyage card container")
            print("\nExample - you might see something like:")
            print('  <div class="voyage-result-card">')
            print('    <h3>Mediterranean Discovery</h3>')
            print('    <p>Departs: June 15, 2025</p>')
            print('  </div>')
            print("\nThen the selector would be: .voyage-result-card")
            
            print("\n⏸️  Browser will stay open for 30 seconds so you can inspect...")
            print("   (Use browser DevTools: Right-click → Inspect)")
            await page.wait_for_timeout(30000)
            
            await browser.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def inspect_silversea():
    """Inspect Silversea cruise search page"""
    url = "https://www.silversea.com/find-a-cruise.html"
    
    print("\n\n🔍 Inspecting Silversea...")
    print(f"URL: {url}\n")
    
    try:
        async with Stealth().use_async(async_playwright()) as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            print("📡 Loading page...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            print("⏳ Waiting 5 seconds for dynamic content...")
            await page.wait_for_timeout(5000)
            
            # Scroll
            print("📜 Scrolling to load content...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)
            
            # Get full HTML
            html = await page.content()
            
            # Save to file
            output_file = Path("silversea_html_inspection.html")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            print(f"\n✅ HTML saved to: {output_file}")
            print("\nFollow same steps as with Regent to find the selectors")
            
            print("\n⏸️  Browser will stay open for 30 seconds...")
            await page.wait_for_timeout(30000)
            
            await browser.close()
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    print("="*70)
    print("CRUISE WEBSITE HTML INSPECTOR")
    print("="*70)
    print("\nThis tool will:")
    print("1. Open each cruise line website in a browser")
    print("2. Save the HTML to a file for inspection")
    print("3. Keep browser open so you can use DevTools\n")
    
    choice = input("Inspect [1] Regent, [2] Silversea, or [3] Both? (1/2/3): ").strip()
    
    if choice in ['1', '3']:
        await inspect_regent()
    
    if choice in ['2', '3']:
        await inspect_silversea()
    
    print("\n" + "="*70)
    print("✅ INSPECTION COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Open the HTML files and find the voyage card selectors")
    print("2. Update thunderbird_ship_intel.py with the correct selectors")
    print("3. Run the sweep again")

if __name__ == "__main__":
    asyncio.run(main())

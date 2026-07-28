import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto("https://www.rssc.com/agent/dashboard/#myBookings")
        await page.wait_for_timeout(5000)
        print("URL:", page.url)
        print("Title:", await page.title())
        text = await page.evaluate("document.body.innerText")
        print("Logged in:", "sign in" not in text.lower())

asyncio.run(run())

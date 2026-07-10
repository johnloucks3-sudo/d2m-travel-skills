"""Ancestry authenticated search — Stoycos genealogy (Commander's account).
Single clean login attempt (password via argv) to avoid tripping Cloudflare,
then runs record searches. Reuses persistent profile cookies once logged in.

Usage: ancestry_stoycos_search.py [password] [--search-only]
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")
from core.ai_infra.xvfb_driver import XvfbDriver

OUT = Path("/home/john/Thunderbird/output/stoycos_search")
OUT.mkdir(parents=True, exist_ok=True)
PROFILE = "/home/john/Thunderbird/state/firefox_ancestry"

EMAIL = "yodainva@gmail.com"
PASSWORD = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "Boss5277"
SEARCH_ONLY = "--search-only" in sys.argv

SIGNIN = "https://www.ancestry.com/account/signin"

SEARCHES = [
    ("william_stoycos",
     "https://www.ancestry.com/search/?name=William+Vasili_Stoycos&birth=1890&birth_x=5-0-0"),
    ("william_stoikos",
     "https://www.ancestry.com/search/?name=Vasilios_Stoikos&birth=1890"),
    ("evanthia_stoycos",
     "https://www.ancestry.com/search/?name=Evanthia_Stoycos&birth=1895"),
    ("evanthia_hadjistavrou",
     "https://www.ancestry.com/search/?name=Evanthia_Hadjistavrou&birth=1895&birth_x=5-0-0"),
    ("stoycos_surname",
     "https://www.ancestry.com/search/?name=_Stoycos"),
]


async def logged_in(page):
    return await page.evaluate("""() => {
        const u = window.location.href;
        if (u.includes('signin') || u.includes('/account/signin')) return false;
        const b = document.body ? document.body.innerText.toLowerCase() : '';
        return b.includes('sign out') || b.includes('my trees') ||
               b.includes('recent') || document.querySelector('[href*="signout"]') != null;
    }""")


async def try_login(page):
    print(f"\n=== LOGIN attempt: {EMAIL} / {PASSWORD[:4]}... ===", flush=True)
    await page.goto(SIGNIN, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(4000)

    # detect Cloudflare wall
    cf = await page.evaluate("""() => {
        const b = document.body ? document.body.innerText.toLowerCase() : '';
        return document.querySelector('[name=cf-turnstile-response]') != null ||
               b.includes('verify you are human') || b.includes('checking your browser');
    }""")
    if cf:
        print("  CLOUDFLARE TURNSTILE present — waiting 12s for auto-pass...", flush=True)
        await page.wait_for_timeout(12000)
        await page.screenshot(path=str(OUT / "cloudflare_wall.png"))

    if not await page.query_selector("#username"):
        print("  no username field (blocked). screenshot saved.", flush=True)
        await page.screenshot(path=str(OUT / "login_blocked.png"))
        body = await page.evaluate("() => document.body ? document.body.innerText.slice(0,500) : ''")
        print(f"  PAGE: {body[:400]}", flush=True)
        return False

    await page.fill("#username", EMAIL)
    await page.wait_for_timeout(800)
    await page.fill("#password", PASSWORD)
    await page.wait_for_timeout(800)

    # submit via Enter in password field (Ancestry submits on Enter)
    await page.focus("#password")
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(8000)
    await page.screenshot(path=str(OUT / "after_submit.png"))

    if await logged_in(page):
        print("  LOGIN SUCCESS", flush=True)
        return True

    # capture any error / state
    state = await page.evaluate("""() => {
        const err = document.querySelector('[class*=error],[class*=alert],[role=alert]');
        return {
            url: window.location.href,
            err: err ? err.innerText.slice(0,200) : '',
            body: document.body ? document.body.innerText.slice(0,400) : ''
        };
    }""")
    print(f"  NOT logged in. url={state['url']}", flush=True)
    print(f"  ERROR MSG: {state['err']!r}", flush=True)
    print(f"  BODY: {state['body'][:300]}", flush=True)
    return False


async def run_search(page, label, url):
    print(f"\n### SEARCH: {label}", flush=True)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path=str(OUT / f"search_{label}.png"), full_page=True)
        text = await page.evaluate("""() => {
            const r = document.querySelector('#searchResults, .searchResults, [class*=result]');
            return (r ? r.innerText : document.body.innerText).slice(0, 6000);
        }""")
        (OUT / f"search_{label}.txt").write_text(text)
        print(f"  saved {len(text)} chars", flush=True)
        print("  --- SNIPPET ---", flush=True)
        print(text[:2500], flush=True)
        print("  --- END ---", flush=True)
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)


async def main():
    async with XvfbDriver(display_num=88, profile_dir=PROFILE) as d:
        page = d.page
        page.set_default_timeout(45000)

        ok = SEARCH_ONLY
        if SEARCH_ONLY:
            # verify cookie-based session
            await page.goto("https://www.ancestry.com/", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(4000)
            ok = await logged_in(page)
            print(f"cookie session logged_in={ok}", flush=True)

        if not ok:
            ok = await try_login(page)

        if not ok:
            print("\n!!! LOGIN FAILED. Aborting search.", flush=True)
            return

        for label, url in SEARCHES:
            await run_search(page, label, url)
        await d.save_cookies(Path(PROFILE) / "cookies.json")
        print("\nDONE. Cookies saved.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

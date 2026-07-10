"""Ancestry authenticated search via InvisiblePlaywright (stealth Firefox).
Ephemeral (no persistent profile — faster launch), re-login each run.
Usage: ancestry_stoycos_stealth.py [password]
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")
from invisible_playwright import InvisiblePlaywright

OUT = Path("/home/john/Thunderbird/output/stoycos_search")
OUT.mkdir(parents=True, exist_ok=True)

EMAIL = "yodainva@gmail.com"
PASSWORD = sys.argv[1] if len(sys.argv) > 1 else "Boss5277"
SIGNIN = "https://www.ancestry.com/account/signin"

SEARCHES = [
    ("william_stoycos",
     "https://www.ancestry.com/search/?name=William+Vasili_Stoycos&birth=1890&birth_x=5-0-0"),
    ("william_dayton",
     "https://www.ancestry.com/search/?name=William_Stoycos&residence=_Dayton-Ohio-USA&birth=1890&birth_x=10-0-0"),
    ("evanthia_stoycos",
     "https://www.ancestry.com/search/?name=Evanthia_Stoycos&birth=1895&birth_x=5-0-0"),
    ("evanthia_hadjistavrou",
     "https://www.ancestry.com/search/?name=Evanthia_Hadjistavrou&birth=1895&birth_x=5-0-0"),
    ("stoycos_surname",
     "https://www.ancestry.com/search/?name=_Stoycos"),
    ("stoycos_dayton_all",
     "https://www.ancestry.com/search/?name=_Stoycos&residence=_Dayton-Ohio-USA"),
    ("stoycos_census_1930",
     "https://www.ancestry.com/search/collections/6224/?name=_Stoycos&residence=_Ohio-USA"),
    ("stoycos_census_1940",
     "https://www.ancestry.com/search/collections/2442/?name=_Stoycos&residence=_Ohio-USA"),
]


def txt(page, n=500):
    return page.evaluate("() => document.body ? document.body.innerText : ''")[:n]


def logged_in(page):
    return page.evaluate("""() => {
        const u = window.location.href;
        if (u.includes('signin') || u.includes('/account/signin')) return false;
        const b = document.body ? document.body.innerText.toLowerCase() : '';
        // logged-in nav chrome
        if (b.includes('sign out') || b.includes('my trees') ||
            document.querySelector('[href*="signout"]') != null) return true;
        const hasNav = ['trees','memories','messages','hints'].filter(k => b.includes(k)).length;
        return hasNav >= 3 && !b.includes('email or username');
    }""")


def main():
    print("Launching InvisiblePlaywright (ephemeral stealth)...", flush=True)
    with InvisiblePlaywright(
        headless=True, humanize=True, prep_recaptcha=False,
        locale="en-US", timezone="America/Denver",
    ) as browser:
        print("Browser launched.", flush=True)
        page = browser.new_page()

        print(f"\n=== LOGIN {EMAIL} / {PASSWORD[:4]}... ===", flush=True)
        page.goto(SIGNIN, timeout=45000, wait_until="domcontentloaded")
        time.sleep(6)
        body = txt(page, 400).lower()
        print(f"  landing body: {body[:200]!r}", flush=True)
        if any(x in body for x in ("browser validation", "verify you are human", "error 54", "checking")):
            print("  BOT WALL — waiting 18s for stealth auto-pass...", flush=True)
            time.sleep(18)
            page.goto(SIGNIN, timeout=45000, wait_until="domcontentloaded")
            time.sleep(6)
        if not page.query_selector("#username"):
            page.screenshot(path=str(OUT / "stealth_blocked.png"))
            print(f"  BLOCKED. page: {txt(page, 400)!r}", flush=True)
            return
        page.fill("#username", EMAIL)
        time.sleep(1)
        page.fill("#password", PASSWORD)
        time.sleep(1)
        page.focus("#password")
        page.keyboard.press("Enter")
        time.sleep(10)
        page.screenshot(path=str(OUT / "stealth_after_submit.png"))
        if not logged_in(page):
            state = page.evaluate("""() => {
                const e = document.querySelector('[class*=error],[role=alert]');
                return {u: location.href, e: e?e.innerText.slice(0,200):'', b: document.body.innerText.slice(0,400)};
            }""")
            print(f"  NOT logged in. url={state['u']}", flush=True)
            print(f"  ERR: {state['e']!r}", flush=True)
            print(f"  BODY: {state['b'][:300]}", flush=True)
            return
        print("  LOGIN SUCCESS", flush=True)

        for label, url in SEARCHES:
            print(f"\n### SEARCH: {label}", flush=True)
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
                time.sleep(5)
                page.screenshot(path=str(OUT / f"stealth_search_{label}.png"), full_page=True)
                t = page.evaluate("""() => {
                    const r = document.querySelector('#searchResults, .searchResults, [class*=result]');
                    return (r ? r.innerText : document.body.innerText).slice(0, 6000);
                }""")
                (OUT / f"search_{label}.txt").write_text(t)
                print(f"  saved {len(t)} chars", flush=True)
                print("  --- SNIPPET ---", flush=True)
                print(t[:2500], flush=True)
                print("  --- END ---", flush=True)
            except Exception as e:
                print(f"  ERROR: {e}", flush=True)
        print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()

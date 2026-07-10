"""Ellis Island / Statue of Liberty Foundation passenger search via stealth browser.
Free, no login. Searches surname variants for the Stoycos immigrant couple.
"""
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")
from invisible_playwright import InvisiblePlaywright

OUT = Path("/home/john/Thunderbird/output/stoycos_search")
OUT.mkdir(parents=True, exist_ok=True)

# surname variants + a couple of first-name-targeted queries
QUERIES = [
    ("Stoycos", ""),
    ("Stoikos", ""),
    ("Stoykos", ""),
    ("Stoicos", ""),
    ("Hadjistavrou", ""),
    ("Hatzistavrou", ""),
]

SEARCH_PAGES = [
    "https://heritage.statueofliberty.org/passenger",
    "https://www.libertyellisfoundation.org/passenger",
]


def txt(page, n=600):
    return page.evaluate("() => document.body ? document.body.innerText : ''")[:n]


def dump_inputs(page):
    return page.evaluate("""() => Array.from(document.querySelectorAll('input,button,select')).map(e => ({
        tag:e.tagName, type:e.type||'', id:e.id||'', name:e.name||'',
        ph:e.placeholder||'', txt:(e.innerText||e.value||'').slice(0,25)
    })).slice(0,40)""")


def main():
    print("Launching stealth for Ellis Island...", flush=True)
    with InvisiblePlaywright(headless=True, humanize=True, locale="en-US",
                             timezone="America/Denver") as browser:
        page = browser.new_page()
        # find a working search page
        search_url = None
        for u in SEARCH_PAGES:
            try:
                page.goto(u, timeout=45000, wait_until="domcontentloaded")
                time.sleep(6)
                body = txt(page, 300).lower()
                print(f"\nPAGE {u}\n  body: {body[:180]!r}", flush=True)
                page.screenshot(path=str(OUT / f"ellis_landing_{SEARCH_PAGES.index(u)}.png"))
                if "passenger" in body or page.query_selector("input"):
                    search_url = u
                    print("  FORM FIELDS:", json.dumps(dump_inputs(page))[:700], flush=True)
                    break
            except Exception as e:
                print(f"  ERR {u}: {e}", flush=True)
        if not search_url:
            print("No Ellis Island search page reachable.", flush=True)
            return

        for last, first in QUERIES:
            print(f"\n### ELLIS SEARCH last={last} first={first!r}", flush=True)
            try:
                page.goto(search_url, timeout=45000, wait_until="domcontentloaded")
                time.sleep(4)
                # fill last name
                filled = False
                for sel in ["input[name*=last i]", "input[id*=last i]", "input[placeholder*=last i]",
                            "#lastName", "input[name=lastName]"]:
                    try:
                        if page.query_selector(sel):
                            page.fill(sel, last)
                            filled = True
                            break
                    except Exception:
                        continue
                if first:
                    for sel in ["input[name*=first i]", "input[id*=first i]", "#firstName"]:
                        try:
                            if page.query_selector(sel):
                                page.fill(sel, first); break
                        except Exception:
                            continue
                if not filled:
                    print("  could not find last-name field", flush=True)
                    print("  INPUTS:", json.dumps(dump_inputs(page))[:600], flush=True)
                    continue
                # submit
                clicked = False
                for sel in ["button[type=submit]", "button:has-text('Search')", "input[type=submit]",
                            "a:has-text('Search')"]:
                    try:
                        el = page.query_selector(sel)
                        if el:
                            el.click(); clicked = True; break
                    except Exception:
                        continue
                if not clicked:
                    page.keyboard.press("Enter")
                time.sleep(7)
                page.screenshot(path=str(OUT / f"ellis_{last}.png"), full_page=True)
                t = page.evaluate("() => document.body ? document.body.innerText : ''")[:5000]
                (OUT / f"ellis_{last}.txt").write_text(t)
                print(f"  saved {len(t)} chars, url={page.url}", flush=True)
                print("  --- SNIPPET ---", flush=True)
                print(t[:2000], flush=True)
                print("  --- END ---", flush=True)
            except Exception as e:
                print(f"  ERROR: {e}", flush=True)
        print("\nDONE.", flush=True)


if __name__ == "__main__":
    main()

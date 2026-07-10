"""Drill the William Stoycos 1924 Ellis Island record — capture Quick View detail."""
import sys, time
from pathlib import Path
sys.path.insert(0, "/home/john/Thunderbird")
from invisible_playwright import InvisiblePlaywright

OUT = Path("/home/john/Thunderbird/output/stoycos_search")
URL = "https://heritage.statueofliberty.org/passenger"


def main():
    with InvisiblePlaywright(headless=True, humanize=True, locale="en-US",
                             timezone="America/Denver") as browser:
        page = browser.new_page()
        page.goto(URL, timeout=45000, wait_until="domcontentloaded")
        time.sleep(6)
        # fill last name Stoycos
        for sel in ["input[name*=last i]", "input[id*=last i]", "input[placeholder*=last i]", "#lastName"]:
            if page.query_selector(sel):
                page.fill(sel, "Stoycos"); break
        for sel in ["input[name*=first i]", "input[id*=first i]", "#firstName"]:
            if page.query_selector(sel):
                page.fill(sel, "William"); break
        for sel in ["button[type=submit]", "button:has-text('Search')", "input[type=submit]"]:
            el = page.query_selector(sel)
            if el:
                el.click(); break
        else:
            page.keyboard.press("Enter")
        time.sleep(8)
        page.screenshot(path=str(OUT / "william_results.png"), full_page=True)
        # click first Quick View
        qv = page.query_selector("a:has-text('Quick View'), button:has-text('Quick View')")
        if qv:
            qv.click()
            time.sleep(6)
            page.screenshot(path=str(OUT / "william_quickview.png"), full_page=True)
            detail = page.evaluate("""() => {
                const m = document.querySelector('[role=dialog],[class*=modal],[class*=Modal],[class*=quickview i],[class*=detail i]');
                return (m ? m.innerText : document.body.innerText).slice(0, 4000);
            }""")
            (OUT / "william_quickview.txt").write_text(detail)
            print("=== WILLIAM STOYCOS QUICK VIEW ===", flush=True)
            print(detail[:3000], flush=True)
        else:
            print("No Quick View link found.", flush=True)
            print(page.evaluate("() => document.body.innerText")[:2000], flush=True)


if __name__ == "__main__":
    main()

"""
RoomRes API request-shape capture tool (one-off, for connector dev).

Seeds the captured browser session (localStorage incl JWT + cookies) into a
headless Chromium, navigates the load-triggered hotelPageUrl (fires
/hotel/details/rooms + /content) and, if possible, a search-results URL
(fires /hotel/search). Logs every request to the RoomRes API hosts with
method, URL, headers, postData, and response body, and writes a JSON fixture.

Run:  /home/john/Thunderbird/.venv/bin/python core/travel/_roomres_capture.py
Output: core/travel/_roomres_capture_fixture.json
"""
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

SESSION = Path("/home/john/Downloads/roomres_session.json")
OUT = Path(__file__).parent / "_roomres_capture_fixture.json"

API_HOST_HINTS = ("api.roomresservices.com", "execute-api", "rrwebapi")


def load_session():
    d = json.loads(SESSION.read_text())
    ls = d["ls"]
    cookies_raw = d["cookies"]
    return ls, cookies_raw


def parse_cookie_header(cookies_raw, domain=".room-res.com"):
    out = []
    for part in cookies_raw.split("; "):
        if "=" not in part:
            continue
        name, _, val = part.partition("=")
        out.append({
            "name": name.strip(),
            "value": val.strip(),
            "domain": domain,
            "path": "/",
        })
    return out


def main():
    ls, cookies_raw = load_session()
    captured = []

    init_js = "() => {\n" + "\n".join(
        f"  try {{ localStorage.setItem({json.dumps(k)}, {json.dumps(v)}); }} catch(e) {{}}"
        for k, v in ls.items()
    ) + "\n}"
    init_script = f"({init_js})()"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        # cookies for both room-res.com and api host
        cookies = parse_cookie_header(cookies_raw, ".room-res.com")
        try:
            ctx.add_cookies(cookies)
        except Exception as e:
            print("cookie add warn:", e, file=sys.stderr)
        ctx.add_init_script(init_script)

        page = ctx.new_page()

        pending = {}

        def on_request(req):
            if any(h in req.url for h in API_HOST_HINTS):
                pending[req] = {
                    "method": req.method,
                    "url": req.url,
                    "headers": dict(req.headers),
                    "postData": req.post_data,
                }

        def on_response(resp):
            req = resp.request
            if req in pending:
                rec = pending.pop(req)
                rec["status"] = resp.status
                try:
                    rec["responseSample"] = resp.text()[:2000]
                except Exception:
                    rec["responseSample"] = None
                captured.append(rec)

        page.on("request", on_request)
        page.on("response", on_response)

        urls = []
        hp = ls.get("hotelPageUrl")
        if hp:
            urls.append(("hotelpage", hp))
        # search results URL (React route) — try to fire /hotel/search
        urls.append((
            "search",
            "https://room-res.com/hotellist?destination=Venice%2C+Italy"
            "&dateFrom=02-May-2027&dateTo=05-May-2027&rooms=2",
        ))

        for label, url in urls:
            print(f"--- navigating [{label}] {url[:90]} ---")
            try:
                page.goto(url, wait_until="networkidle", timeout=45000)
            except Exception as e:
                print(f"goto warn [{label}]:", e, file=sys.stderr)
            page.wait_for_timeout(6000)

        browser.close()

    OUT.write_text(json.dumps(captured, indent=2))
    print(f"\nCaptured {len(captured)} API calls -> {OUT}")
    for c in captured:
        print(f"  {c['method']} {c['url'][:100]}  [{c.get('status')}]")


if __name__ == "__main__":
    main()

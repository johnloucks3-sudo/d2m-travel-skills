"""
RoomRes search+autocomplete capture (phase 2).
Seeds session, opens homepage, types destination to fire autocomplete,
captures the autocomplete + search request/response shapes.
"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION = Path("/home/john/Downloads/roomres_session.json")
OUT = Path(__file__).parent / "_roomres_capture2_fixture.json"
API_HINTS = ("api.roomresservices.com", "execute-api", "rrwebapi")


def main():
    d = json.loads(SESSION.read_text())
    ls = d["ls"]
    cookies_raw = d["cookies"]

    init_js = "() => {\n" + "\n".join(
        f"  try {{ localStorage.setItem({json.dumps(k)}, {json.dumps(v)}); }} catch(e){{}}"
        for k, v in ls.items()
    ) + "\n}"
    init_script = f"({init_js})()"

    cookies = []
    for part in cookies_raw.split("; "):
        if "=" in part:
            n, _, v = part.partition("=")
            cookies.append({"name": n.strip(), "value": v.strip(),
                            "domain": ".room-res.com", "path": "/"})

    captured = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
        try:
            ctx.add_cookies(cookies)
        except Exception as e:
            print("cookie warn:", e, file=sys.stderr)
        ctx.add_init_script(init_script)
        page = ctx.new_page()
        pending = {}

        def on_req(r):
            if any(h in r.url for h in API_HINTS) and (
                "autocomplete" in r.url.lower() or "search" in r.url.lower()
                or "/hotel/" in r.url.lower()):
                pending[r] = {"method": r.method, "url": r.url,
                              "postData": r.post_data}

        def on_resp(resp):
            rq = resp.request
            if rq in pending:
                rec = pending.pop(rq)
                rec["status"] = resp.status
                try:
                    rec["responseSample"] = resp.text()[:1500]
                except Exception:
                    rec["responseSample"] = None
                captured.append(rec)

        page.on("request", on_req)
        page.on("response", on_resp)

        page.goto("https://room-res.com/", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(3000)

        # find a destination/search input and type into it
        typed = False
        selectors = [
            "input[placeholder*='destination' i]",
            "input[placeholder*='where' i]",
            "input[placeholder*='hotel' i]",
            "input[placeholder*='city' i]",
            "input[type='text']",
            "input[type='search']",
        ]
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    el.type("Venice", delay=180)
                    typed = True
                    print(f"typed into {sel}")
                    break
            except Exception:
                continue
        if not typed:
            # dump visible inputs for diagnosis
            inputs = page.eval_on_selector_all(
                "input",
                "els => els.map(e=>({ph:e.placeholder,type:e.type,name:e.name,vis:e.offsetParent!==null}))")
            print("INPUTS:", json.dumps(inputs)[:1500])
        page.wait_for_timeout(5000)

        # try clicking first autocomplete suggestion
        for sug in ["text=Venice, Veneto", "text=Venice", "[role=option]", "li"]:
            try:
                opt = page.query_selector(sug)
                if opt and opt.is_visible():
                    opt.click()
                    print(f"clicked suggestion {sug}")
                    break
            except Exception:
                continue
        page.wait_for_timeout(5000)
        b.close()

    OUT.write_text(json.dumps(captured, indent=2))
    print(f"\nCaptured {len(captured)} -> {OUT}")
    for c in captured:
        print(f"  {c['method']} {c['url'][:95]} [{c.get('status')}]")


if __name__ == "__main__":
    main()

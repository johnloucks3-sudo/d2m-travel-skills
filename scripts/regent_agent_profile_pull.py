#!/usr/bin/env python3
"""
regent_agent_profile_pull.py — Map how DEEP the Regent agent-side view goes.

Given a booked-cruise agent URL, loads OA agent cookies, harvests every agent-portal
link, then follows the profile / preferences / guest-detail / saved-voyages /
online-check-in pages and dumps what each exposes. Answers: beyond booking data,
can the agent see suite/dining/drink preferences, saved voyages, personal info?

Usage:
  python3 scripts/regent_agent_profile_pull.py \
    --url "https://www.rssc.com/agent/myaccount/bookedcruise.aspx?<ENCID>" \
    --cookies creds/regent_cookies.json --out validations/mcleod_agent_profile

Akamai-tolerant (Firefox + live cookies), same pattern as regent_booking_capture.py.
"""
import argparse
import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright


def load_cookies(path):
    raw = json.loads(Path(path).read_text())
    out = []
    for c in raw:
        if "rssc.com" not in c.get("domain", ""):
            continue
        nc = {k: v for k, v in c.items() if k != "sameSite"}
        if c.get("sameSite") in ("Strict", "Lax", "None"):
            nc["sameSite"] = c["sameSite"]
        out.append(nc)
    return out


# link text/href keywords that likely lead to deeper client data
FOLLOW = ["profile", "preference", "guest", "saved", "checkin", "check-in",
          "suite-detail", "itinerary", "traveldoc", "document", "loyalty", "society"]


async def dump_page(page, tag, out):
    txt = await page.evaluate("() => document.body ? document.body.innerText : ''")
    (out / f"{tag}.txt").write_text(txt, encoding="utf-8")
    return txt


def interesting(text):
    """What personal/preference signals appear in a page's text?"""
    sig = {}
    for kw in ["dietary", "diet", "allerg", "beverage", "drink", "wine", "bed config",
               "pillow", "celebration", "occasion", "anniversary", "birthday",
               "passport", "date of birth", "dob", "email", "phone", "address",
               "emergency", "frequent flyer", "known traveler", "tsa", "mobility",
               "wheelchair", "dining time", "seating", "suite preference",
               "saved", "society", "loyalty", "reward night", "tier"]:
        n = len(re.findall(kw, text, re.I))
        if n:
            m = re.search(kw, text, re.I)
            ex = text[m.start():m.start() + 55].replace("\n", " ")
            sig[kw] = (n, ex)
    return sig


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--cookies", default="creds/regent_cookies.json")
    ap.add_argument("--out", default="validations/regent_agent_profile")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        b = await pw.firefox.launch(headless=True)
        ctx = await b.new_context(viewport={"width": 1440, "height": 900})
        await ctx.add_cookies(load_cookies(a.cookies))
        page = await ctx.new_page()
        await page.goto(a.url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3500)
        if "login" in page.url.lower() or "access denied" in (await page.title()).lower():
            print(f"AUTH FAIL — bounced to {page.url[:80]}. Refresh agent cookies.")
            await b.close()
            return

        # harvest all agent-portal links
        links = await page.evaluate(
            """() => [...document.querySelectorAll('a[href]')].map(a => ({t:(a.innerText||'').trim().slice(0,40), h:a.href}))""")
        agent_links = [l for l in links if "rssc.com" in l["h"]]
        uniq = list({l["h"]: l for l in agent_links}.values())
        (out / "all_links.json").write_text(json.dumps(uniq, indent=1))
        follow = [l for l in uniq if any(k in (l["t"] + l["h"]).lower() for k in FOLLOW)]
        print(f"booking page: {len(uniq)} agent links, {len(follow)} candidate deep-links\n")

        report = {"booking_url": a.url, "pages": {}}
        # the booking page itself
        bt = await dump_page(page, "00_booking", out)
        report["pages"]["00_booking"] = interesting(bt)

        # follow candidate deep-links
        for i, l in enumerate(follow, 1):
            tag = f"{i:02d}_" + re.sub(r"[^a-z0-9]+", "-", (l["t"] or "link").lower())[:24]
            try:
                await page.goto(l["h"], wait_until="domcontentloaded", timeout=40000)
                await page.wait_for_timeout(3000)
                if "login" in page.url.lower():
                    report["pages"][tag] = {"_bounced_to_login": True}
                    continue
                t = await dump_page(page, tag, out)
                report["pages"][tag] = {"url": l["h"], "label": l["t"], "signals": interesting(t)}
            except Exception as e:
                report["pages"][tag] = {"_error": str(e)[:80]}
        (out / "_depth_report.json").write_text(json.dumps(report, indent=2))

        # print summary
        print("=== AGENT-VIEW DEPTH ===")
        for tag, info in report["pages"].items():
            sig = info.get("signals", info) if isinstance(info, dict) else {}
            keys = [k for k in sig if k not in ("url", "label")] if isinstance(sig, dict) else []
            lbl = info.get("label", "") if isinstance(info, dict) else ""
            print(f"  {tag} {('['+lbl+']') if lbl else ''}: {', '.join(keys) if keys else '(no personal/pref signals)'}")
        await b.close()


if __name__ == "__main__":
    asyncio.run(main())

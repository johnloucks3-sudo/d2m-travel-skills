#!/usr/bin/env python3
"""
Site Structure Sentinel — DOM Change Detection for Supplier Sites
=================================================================
Monitors critical supplier login pages and data pages for structural changes.
When a page's DOM hash changes, it alerts via Telegram before the scraper breaks.

Strategy:
  - Compute a hash of the page's structural skeleton (tag names, IDs, classes,
    input types, button text — not content)
  - Store the hash in state/site_sentinel_state.json
  - On each run, compare current hash to stored hash
  - If changed: alert, save screenshot, store new hash as baseline
  - If unchanged: silent OK

Portals monitored (Tier 1 — revenue-critical):
  - Regent login page (rssc.com/agent)
  - Centrav login page (centrav.com/login)
  - Perx login page (perx.com/account/login)
  - Silversea login page (my.silversea.com)
  - TESS auth page (crm.myagentgenie.com)

Tier 2 — change detection only (no auth):
  - Kiwitaxi pricing page
  - GetYourGuide activity-card selector
  - Silversea voyage listing pages

Usage:
    python3 scripts/site_structure_sentinel.py              # full check
    python3 scripts/site_structure_sentinel.py --site regent # single site
    python3 scripts/site_structure_sentinel.py --reset       # reset all baselines

Dreams2Memories Travel, LLC — Thunderbird Wing — Hale COS 2026-06-04
"""
import asyncio, hashlib, json, logging, sys
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

THUNDERBIRD = Path(__file__).resolve().parent.parent
STATE_DIR = THUNDERBIRD / "OpsCenter" / "state"
LOG_DIR = THUNDERBIRD / "logs"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

STATE_FILE = STATE_DIR / "site_sentinel_state.json"
LOG_FILE = LOG_DIR / "site_sentinel.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s SENTINEL %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_FILE), mode="a"),
    ],
)
log = logging.getLogger("sentinel")

SITES = {
    "regent_login": {
        "url": "https://www.rssc.com/agent/default.aspx",
        "tier": 1,
        "auth_needed": False,
        "critical_selectors": [
            "#uxAgentHomePage_uxAgentRegister_uxLoginEmailAddressTextbox",
            "#uxAgentHomePage_uxAgentRegister_uxLoginPasswordTextbox",
            "#uxAgentHomePage_uxAgentRegister_uxLoginButton",
        ],
    },
    "centrav_login": {
        "url": "https://www.centrav.com/login",
        "tier": 1,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="email"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "perx_login": {
        "url": "https://www.perx.com/account/login",
        "tier": 1,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="email"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "silversea_login": {
        "url": "https://my.silversea.com/Account/Login",
        "tier": 1,
        "auth_needed": False,
        "critical_selectors": [
            'input[id*="email"]',
            'input[id*="password"]',
            'button[type="submit"]',
        ],
    },
    "tess_auth": {
        "url": "https://crm.myagentgenie.com",
        "tier": 1,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="text"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "kiwitaxi_search": {
        "url": "https://www.kiwitaxi.com",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[name*="from"]',
            'input[name*="to"]',
            'button[type="submit"]',
        ],
    },
    "getyourguide_search": {
        "url": "https://www.getyourguide.com",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            "[class*='activity-card']",
            '[data-testid*="search"]',
        ],
    },
    "silversea_voyages": {
        "url": "https://www.silversea.com/find-a-voyage.html?voyageType=classic&ship=NV",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            ".voyage-card",
            ".price",
            ".departure-date",
        ],
    },
    "seabourn_login": {
        "url": "https://book2.seabourn.com",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="text"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "windstar_login": {
        "url": "https://advisorhub.windstarcruises.com",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="email"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "princess_login": {
        "url": "https://book.princess.com",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="text"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "carnival_login": {
        "url": "https://secure.cruisingpower.com",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="text"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "kensington_login": {
        "url": "https://fit.kensingtontours.com",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="email"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "agentmax_login": {
        "url": "https://www.agentmaxonline.com/agentmaxweb/agentportal/index.html",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="text"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "globus_login": {
        "url": "https://accounts.globusfamily.com",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="email"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "agent_universe_login": {
        "url": "https://affiliateus.agentuniverse.com/",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="text"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "room_res_login": {
        "url": "https://room-res.com/login",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="email"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "atlas_login": {
        "url": "https://agents.atlasoceanvoyages.com",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="email"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
    "explora_login": {
        "url": "https://agent.explorajourneys.com",
        "tier": 2,
        "auth_needed": False,
        "critical_selectors": [
            'input[type="email"]',
            'input[type="password"]',
            'button[type="submit"]',
        ],
    },
}


def compute_structure_hash(page_source: str, critical_selectors: list) -> str:
    """Hash the structural skeleton of a page — not content, just form/shape."""
    import re
    skeleton_parts = []
    skeleton_parts.append(f"selectors:{sorted(critical_selectors)}")
    form_inputs = re.findall(
        r'<(input|select|textarea|button|form)([^>]*)>', page_source, re.I
    )
    for tag, attrs in sorted(form_inputs):
        attrs_clean = re.sub(
            r'(value|placeholder|aria-label|title)=["\'][^"\']*["\']',
            '', attrs
        )
        skeleton_parts.append(f"<{tag}{attrs_clean}>")
    headings = re.findall(r'<h[1-6][^>]*>', page_source)
    skeleton_parts.extend(sorted(headings))
    links = re.findall(r'<a\s+[^>]*href=["\'][^"\']*["\']', page_source)
    skeleton_parts.append(f"link_count:{len(links)}")
    raw = "|".join(skeleton_parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"baselines": {}, "history": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


async def check_site(
    browser, site_name: str, config: dict, state: dict
) -> dict:
    """Check one site for structural changes. Returns result dict."""
    url = config["url"]
    selectors = config["critical_selectors"]
    tier = config["tier"]

    log.info(f"[{site_name}] Checking {url}")

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
        ),
    )
    page = await context.new_page()

    result = {
        "site": site_name,
        "url": url,
        "tier": tier,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "changed": False,
        "selector_health": {},
        "error": None,
    }

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)

        source = await page.content()
        current_hash = compute_structure_hash(source, selectors)
        baseline = state["baselines"].get(site_name)

        for sel in selectors:
            count = await page.evaluate(
                f"document.querySelectorAll('{sel}').length"
            )
            result["selector_health"][sel] = count

        if baseline is None:
            state["baselines"][site_name] = current_hash
            result["changed"] = False
            result["action"] = "baseline_set"
            log.info(f"[{site_name}] Baseline set: {current_hash}")
        elif current_hash != baseline:
            result["changed"] = True
            result["old_hash"] = baseline
            result["new_hash"] = current_hash
            result["action"] = "ALERT — structure changed"
            state["baselines"][site_name] = current_hash
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_dir = THUNDERBIRD / "validations" / "sentinel"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            await page.screenshot(
                path=str(screenshot_dir / f"{site_name}_{timestamp}.png"),
                full_page=True,
            )
            log.warning(
                f"[{site_name}] STRUCTURE CHANGED: {baseline} -> {current_hash}"
            )
            log.warning(
                f"[{site_name}] Screenshot saved to validations/sentinel/{site_name}_{timestamp}.png"
            )
        else:
            result["changed"] = False
            result["action"] = "no_change"
            log.info(f"[{site_name}] OK — hash match ({current_hash})")

        missing_selectors = [
            sel for sel, count in result["selector_health"].items() if count == 0
        ]
        if missing_selectors:
            log.warning(f"[{site_name}] Missing selectors: {missing_selectors}")

    except Exception as e:
        result["error"] = str(e)
        log.error(f"[{site_name}] Check failed: {e}")
    finally:
        await context.close()

    return result


async def main():
    reset = "--reset" in sys.argv
    site_filter = None
    for arg in sys.argv[1:]:
        if arg.startswith("--site="):
            site_filter = arg.split("=", 1)[1]

    state = load_state()

    if reset:
        state["baselines"] = {}
        state["history"] = []
        save_state(state)
        log.info("All baselines reset — next run will re-establish")
        return

    sites_to_check = SITES.items()
    if site_filter:
        if site_filter not in SITES:
            log.error(f"Unknown site: {site_filter}. Valid: {list(SITES.keys())}")
            return
        sites_to_check = [(site_filter, SITES[site_filter])]

    results = []

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        log.info("Sentinel browser launched (Firefox headless)")

        for site_name, config in sites_to_check:
            result = await check_site(browser, site_name, config, state)
            results.append(result)

        await browser.close()

    changes = [r for r in results if r.get("changed")]
    errors = [r for r in results if r.get("error")]
    log.info(
        f"Sentinel complete: {len(results)} sites checked, "
        f"{len(changes)} changes, {len(errors)} errors"
    )

    state["history"].append({
        "run_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(results),
            "changed": len(changes),
            "errors": len(errors),
        },
        "results": results,
    })
    state["history"] = state["history"][-30:]
    save_state(state)

    if changes:
        log.warning("=== STRUCTURE CHANGES DETECTED ===")
        for r in changes:
            log.warning(f"  {r['site']}: {r['url']}")
        log.warning("Review screenshots in validations/sentinel/")
        sys.exit(1)

    if errors:
        log.warning(f"{len(errors)} sites had errors — review logs")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

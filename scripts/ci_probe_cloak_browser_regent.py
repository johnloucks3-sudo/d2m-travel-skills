#!/usr/bin/env python3
"""
CI EFFICACY PROBE — CloakBrowser Tier 3 (Regent rssc.com Akamai wall)
=====================================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

CloakBrowser is smart_fetch's Tier 3 stealth-fetch escalation. Its reason to exist
is defeating the Akamai edge wall on rssc.com (Regent Seven Seas) where a plain HTTP
fetch is 403-walled. This probe is EFFICACY-based (not presence): it actually drives
smart_fetch against the live rssc.com public domain and asserts CloakBrowser cleared
the wall and returned real content.

SCOPE NOTE: this verifies the public-site EDGE wall is defeated. The authenticated
Regent B2B booking portal (login + reCAPTCHA, MISSION-214) is a separate CI entry
(`regent-portal-live`) and is NOT what this probe measures.

Checks:
  1. tools/cloak/cloak_fetch.mjs exists and node is resolvable
  2. cloakbrowser npm package is installed under tools/cloak/node_modules
  3. smart_fetch.fetch("https://www.rssc.com") returns via Tier 3 with content > threshold

Exit 0 = RAZOR_SHARP. Exit 1 = RED.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
CLOAK_MJS = ROOT / "tools" / "cloak" / "cloak_fetch.mjs"
CLOAK_PKG = ROOT / "tools" / "cloak" / "node_modules" / "cloakbrowser"
TEST_URL = "https://www.rssc.com"
MIN_CONTENT_BYTES = 2000  # a real render is tens of KB; a wall page / empty body is tiny


def fail(msg: str) -> "NoReturn":
    print(f"RED cloak-browser-regent: {msg}")
    sys.exit(1)


def main() -> None:
    # 1. Tier 3 fetcher + node present
    if not CLOAK_MJS.exists():
        fail(f"cloak fetcher missing: {CLOAK_MJS}")
    node = shutil.which("node") or next(
        (p for p in ("/usr/bin/node", "/usr/local/bin/node",
                     str(Path.home() / ".local/bin/node")) if Path(p).exists()),
        None,
    )
    if not node:
        fail("node runtime not found on PATH or known locations")

    # 2. cloakbrowser installed
    if not CLOAK_PKG.exists():
        fail(f"cloakbrowser npm package missing: {CLOAK_PKG} (run: cd tools/cloak && npm install)")

    # 3. Efficacy: live Tier 3 fetch clears the Regent Akamai wall
    sys.path.insert(0, str(ROOT))
    try:
        from core.web.smart_fetch import fetch
    except Exception as e:  # noqa: BLE001
        fail(f"cannot import smart_fetch: {e}")

    try:
        r = fetch(TEST_URL, output="markdown", timeout=60)
    except Exception as e:  # noqa: BLE001
        fail(f"smart_fetch raised on {TEST_URL}: {e}")

    if r.get("walled"):
        fail(f"{TEST_URL} still WALLED after all tiers — CloakBrowser did not clear Akamai")
    if r.get("tier_used") != 3:
        fail(f"{TEST_URL} served by tier {r.get('tier_used')}, expected Tier 3 (CloakBrowser)")
    n = len(r.get("content") or "")
    if n < MIN_CONTENT_BYTES:
        fail(f"{TEST_URL} Tier 3 returned only {n} bytes (< {MIN_CONTENT_BYTES}) — likely a wall/empty page")

    print(f"GREEN cloak-browser-regent: Tier 3 cleared {TEST_URL} "
          f"(status={r.get('status')}, {n} bytes)")
    sys.exit(0)


if __name__ == "__main__":
    main()

"""
RoboForm Vault Extractor — extracts portal credentials once vault is accessible.

Three modes:
  1. --browser   : Launch Chrome with RoboForm extension, navigate to start page, export
  2. --accept    : Accept the pending share for d2mconcierge@gmail.com
  3. --portal    : Check config/portal_creds.json and update from extracted data

The share link (from d2mconcierge inbox, 2026-05-25):
  https://online.roboform.com/login?authReturnUrl=acceptshare&acceptshare=AQAUABAAzIkuAdoz...

Usage:
  python3 scripts/roboform_extract.py --accept    # opens browser to accept share
  python3 scripts/roboform_extract.py --browser   # extracts from running RoboForm session
  python3 scripts/roboform_extract.py --status    # shows current vault status
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

THUNDERBIRD = Path(__file__).resolve().parents[1]
PORTAL_CREDS = THUNDERBIRD / "config" / "portal_creds.json"

# The accept link from the d2mconcierge Gmail inbox (email from 2026-05-25)
SHARE_ACCEPT_URL = (
    "https://online.roboform.com/login"
    "?authReturnUrl=acceptshare"
    "&acceptshare=AQAUABAAzIkuAdozMyEl8G92ZXQGqpbbTVL2LMQ0n32gGCSaral1qOKHgXeVqODv_xk_"
    "DJAtxPLcECk2SYEodmgQoH8xu2L8oZitgARHoinfrMmVah96GInU_qFB3Cxm0inTnTQqSq36vcostZJlyTT"
    "N1Gv2VwY3N5zXERaAK7RR-yOH4CtgBk8k97bpu0rg_5A"
)

CHROME_DEBUG_PROFILE = Path.home() / ".config" / "google-chrome-debug"
RF_EXTENSION_ID = "pnlccmojcmeohlpggmfnbbiapkmbliob"


def cmd_status():
    """Report RoboForm vault status."""
    # Check extension LevelDB for account info
    from pathlib import Path
    import subprocess, re

    ldb = CHROME_DEBUG_PROFILE / "Default" / "Local Extension Settings" / RF_EXTENSION_ID / "000003.log"
    if not ldb.exists():
        print("❌ RoboForm extension LevelDB not found")
        return

    output = subprocess.run(["strings", str(ldb)], capture_output=True, text=True).stdout

    email_m = re.search(r'"email"\s*"([^"]+)"', output)
    acct_m = re.search(r'"accountId"\s*"([^"]+)"', output)
    token_m = re.search(r'"loginToken"\s*"([^"]{20,})"', output)

    print("=== RoboForm Status ===")
    print(f"Account: {email_m.group(1) if email_m else 'unknown'}")
    print(f"Account ID: {acct_m.group(1) if acct_m else 'unknown'}")
    print(f"Token: {'PRESENT' if token_m else 'MISSING'}")

    # Check blob files (vault data)
    blob_dir = (
        CHROME_DEBUG_PROFILE / "Default" / "IndexedDB"
        / f"chrome-extension_{RF_EXTENSION_ID}_0.indexeddb.blob" / "1" / "00"
    )
    blobs = list(blob_dir.glob("*")) if blob_dir.exists() else []
    total_kb = sum(f.stat().st_size for f in blobs) / 1024
    print(f"Vault blobs: {len(blobs)} files ({total_kb:.1f} KB) — ENCRYPTED")
    print()
    print("=== Share Acceptance ===")
    print("Share URL: PRESENT (from d2mconcierge inbox, 2026-05-25)")
    print("Status: PENDING — must be accepted by Commander in browser")
    print()
    print("=== What Commander needs to do ===")
    print("1. Open Chrome and go to d2mconcierge@gmail.com")
    print("2. Create RoboForm account at https://www.roboform.com/download (use d2mconcierge@gmail.com)")
    print("3. Navigate to the accept link (run: python3 scripts/roboform_extract.py --show-link)")
    print("4. Log in and accept the share")
    print("5. The shared folder 'John Loucks (HALE)' will then be available")


def cmd_show_link():
    print("=== RoboForm Share Accept Link ===")
    print()
    print("Share this link with Commander to accept the RoboForm folder share.")
    print("Must be opened in a browser where d2mconcierge@gmail.com is logged in.")
    print()
    print(SHARE_ACCEPT_URL)
    print()
    print("After accepting, run: python3 scripts/roboform_extract.py --browser")


def cmd_accept():
    """Open the accept link in a visible browser window."""
    print("Opening share accept link in browser...")
    print(f"URL: {SHARE_ACCEPT_URL[:80]}...")
    print()
    print("Instructions:")
    print("1. Log in with d2mconcierge@gmail.com")
    print("2. If no account: click 'Sign Up Here' first")
    print("3. Accept the share")
    print("4. Run: python3 scripts/roboform_extract.py --browser to extract passwords")

    try:
        subprocess.Popen(
            ["google-chrome", "--new-window", SHARE_ACCEPT_URL],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        print()
        print("✓ Browser launched")
    except FileNotFoundError:
        print("Chrome not found — copy the URL above and open it manually")


def cmd_browser():
    """
    Launch Chrome with the RoboForm extension and extract visible passwords.
    This works when the vault is unlocked (auto-unlock or master password entered).
    """
    print("Attempting to extract RoboForm passwords via browser...")
    print("Note: This requires the vault to be unlocked.")
    print()

    ext_dir = CHROME_DEBUG_PROFILE / "Default" / "Extensions" / RF_EXTENSION_ID
    ext_versions = list(ext_dir.glob("*")) if ext_dir.exists() else []
    if not ext_versions:
        print("❌ RoboForm extension not found at", ext_dir)
        return

    ext_path = sorted(ext_versions)[-1]
    print(f"Extension: {ext_path.name}")

    try:
        import asyncio
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ playwright not installed")
        return

    async def extract():
        async with async_playwright() as pw:
            # Launch with RoboForm extension loaded
            ctx = await pw.chromium.launch_persistent_context(
                user_data_dir=str(CHROME_DEBUG_PROFILE),
                channel="chrome",
                headless=False,  # Need visible browser for vault access
                args=[
                    f"--load-extension={ext_path}",
                    f"--disable-extensions-except={ext_path}",
                ],
            )

            page = await ctx.new_page()
            print("Navigating to RoboForm start page...")
            try:
                await page.goto(
                    f"chrome-extension://{RF_EXTENSION_ID}/start.html",
                    wait_until="networkidle",
                    timeout=20_000
                )
                await page.wait_for_timeout(3000)

                url = page.url
                body = await page.inner_text("body")
                print(f"URL: {url}")
                print(f"Body preview: {body[:300]}")

                # Try to find login entries
                login_items = await page.query_selector_all(
                    "[class*='login-item'], [class*='item-row'], [data-type='login']"
                )
                print(f"Login items found: {len(login_items)}")

                for item in login_items[:20]:
                    text = await item.inner_text()
                    print(f"  Item: {text[:100]}")

            except Exception as e:
                print(f"Error: {e}")
            finally:
                input("\nPress Enter to close browser...")
                await ctx.close()

    asyncio.run(extract())


def main():
    parser = argparse.ArgumentParser(description="RoboForm vault extractor")
    parser.add_argument("--status", action="store_true", help="Show vault status")
    parser.add_argument("--show-link", action="store_true", help="Print the share accept link")
    parser.add_argument("--accept", action="store_true", help="Open share accept link in browser")
    parser.add_argument("--browser", action="store_true", help="Extract via browser")
    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.show_link:
        cmd_show_link()
    elif args.accept:
        cmd_accept()
    elif args.browser:
        cmd_browser()
    else:
        cmd_status()


if __name__ == "__main__":
    main()

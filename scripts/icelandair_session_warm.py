#!/usr/bin/env python3
"""
icelandair_session_warm.py — Warm-ping keepalive for the authenticated
Icelandair session captured 2026-07-10 (Saga member fares / login-gated
content). Mirrors scripts/centrav_session_warm.py's safety contract.

WHY: The captured session's real constraint isn't the login token (iceAuth
lasts ~14 days, myiceAuth ~400 days) — it's Cloudflare's own __cf_bm cookie,
which had ~23 minutes left at capture time and needs periodic activity to
keep rolling forward. Login itself is a human-only gate (password reset,
Cloudflare Turnstile) — this script NEVER attempts to re-authenticate or
solve a challenge. It only keeps an already-good session warm.

SAFE BY DESIGN (mirrors centrav_session_warm.py's contract exactly):
  - Verifies an authenticated marker FIRST (no "Sign up"/"Log in" prompt,
    no Cloudflare challenge title) before doing anything else.
  - Dead session / challenge hit / any error -> SKIP. icelandair_cookies.json
    is left UNTOUCHED. Escalates to Sterling; never attempts to defeat the
    wall itself.
  - Only on a CONFIRMED-authenticated re-check does it re-extract cookies
    and overwrite the saved file (picking up cf_bm/cf_clearance's renewed
    values, which is the entire point of the ping).

Exit codes:
  0  authenticated — session warmed + cookies re-saved
  2  not authenticated / challenged — needs manual re-login (dead session)
  3  skipped — infra error (Xvfb/Chrome failed to start); file untouched

Usage:
  .venv/bin/python3 scripts/icelandair_session_warm.py
  .venv/bin/python3 scripts/icelandair_session_warm.py --check   # report only, never write
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import websocket

ROOT = Path("/home/john/Thunderbird")
COOKIE_FILE = ROOT / "creds" / "icelandair_cookies.json"
WARM_URL = "https://www.icelandair.com/en-us/"
CHROME_BIN = "/opt/google/chrome/chrome"
DISPLAY_NUM = 90  # dedicated, distinct from the :99 already in use elsewhere
DEBUG_PORT = 9291  # dedicated, distinct from the manual 9222 session
STARTUP_SETTLE_SECONDS = 5
NAV_SETTLE_SECONDS = 6

logging.basicConfig(
    filename=ROOT / "logs" / "icelandair_session_warm.log",
    level=logging.INFO,
    format="%(asctime)s [icelandair-warm] %(message)s",
)
logger = logging.getLogger("icelandair_session_warm")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    logger.info(msg)


def _start_xvfb() -> subprocess.Popen:
    proc = subprocess.Popen(
        ["Xvfb", f":{DISPLAY_NUM}", "-screen", "0", "1280x900x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(2)
    return proc


def _start_chrome(profile_dir: Path) -> subprocess.Popen:
    env = {"DISPLAY": f":{DISPLAY_NUM}"}
    import os
    full_env = dict(os.environ)
    full_env.update(env)
    proc = subprocess.Popen(
        [
            CHROME_BIN,
            f"--remote-debugging-port={DEBUG_PORT}",
            "--remote-debugging-address=127.0.0.1",
            "--remote-allow-origins=*",
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
        ],
        env=full_env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(STARTUP_SETTLE_SECONDS)
    return proc


def _cdp_new_tab(url: str) -> Optional[dict]:
    import urllib.request
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{DEBUG_PORT}/json/new?{url}", method="PUT"
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        log(f"cdp_new_tab failed: {e}")
        return None


def _cdp_close_tab(target_id: str) -> None:
    import urllib.request
    try:
        urllib.request.urlopen(
            f"http://127.0.0.1:{DEBUG_PORT}/json/close/{target_id}", timeout=5
        )
    except Exception:
        pass


def _ws_call(ws: websocket.WebSocket, msg_id: int, method: str, params: Optional[dict] = None,
             timeout: int = 15) -> dict:
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    ws.settimeout(timeout)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        raw = ws.recv()
        try:
            parsed = json.loads(raw)
        except Exception:
            continue
        if parsed.get("id") == msg_id:
            return parsed
    raise TimeoutError(f"no response for {method} within {timeout}s")


def _inject_cookies(ws: websocket.WebSocket, cookies: list[dict]) -> None:
    cdp_cookies = []
    for c in cookies:
        cc = {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/")}
        if c.get("secure"):
            cc["secure"] = True
        if c.get("httpOnly"):
            cc["httpOnly"] = True
        if c.get("expires"):
            cc["expires"] = c["expires"]
        if c.get("sameSite"):
            cc["sameSite"] = c["sameSite"]
        cdp_cookies.append(cc)
    result = _ws_call(ws, 1, "Network.setCookies", {"cookies": cdp_cookies})
    if "error" in result:
        raise RuntimeError(f"Network.setCookies failed: {result['error']}")


def _check_authenticated(ws: websocket.WebSocket) -> bool:
    """Mirrors the visual proof from the manual capture: an authenticated
    session shows an account avatar, not a Log in/Sign up prompt, and never
    hit a Cloudflare challenge page."""
    # "Log in" text is the reliable negative signal (confirmed 2026-07-10 live):
    # "Sign up" persists regardless of auth state (newsletter/loyalty CTA
    # elsewhere on the page), so it is NOT used as a marker.
    expr = (
        "JSON.stringify({"
        "title: document.title,"
        "hasLogin: /\\bLog in\\b/i.test(document.body.innerText),"
        "hasChallenge: /just a moment/i.test(document.title)"
        "})"
    )
    result = _ws_call(ws, 2, "Runtime.evaluate", {"expression": expr, "returnByValue": True})
    if "error" in result:
        return False
    value = json.loads(result["result"]["result"]["value"])
    log(f"auth check: {value}")
    if value["hasChallenge"]:
        return False
    if value["hasLogin"]:
        return False
    return True


def _extract_icelandair_cookies(ws: websocket.WebSocket) -> list[dict]:
    result = _ws_call(ws, 3, "Network.getAllCookies", {})
    if "error" in result:
        raise RuntimeError(f"Network.getAllCookies failed: {result['error']}")
    cookies = result["result"]["cookies"]
    ice = [c for c in cookies if "icelandair" in c.get("domain", "")]
    out = []
    for c in ice:
        pc = {k: c[k] for k in ("name", "value", "domain", "path") if k in c}
        pc["secure"] = c.get("secure", False)
        pc["httpOnly"] = c.get("httpOnly", False)
        if c.get("expires", -1) and c.get("expires", -1) > 0:
            pc["expires"] = float(c["expires"])
        ss = c.get("sameSite", "")
        if ss and ss != "Unspecified":
            pc["sameSite"] = ss
        out.append(pc)
    return out


def _escalate(reason: str) -> None:
    try:
        from core.notify.hale_notify import notify_sterling
        notify_sterling("icelandair-session-warm", reason)
    except Exception as e:
        logger.error("escalation notify failed: %s", e)


def _log_warm_plan(recovered: bool, note: str) -> None:
    """Ledger-only Hale Orchestrator entry, same pattern as the self-healing
    integrations built earlier this session — called AFTER the warm-ping's
    own decision, never gating it."""
    try:
        from core.ops.hale_orchestrator import open_plan, assess_plan, close_plan
        plan = open_plan(
            task_summary=f"Icelandair session warm-ping -> {note}",
            tier="trivial",
            criteria=["Icelandair session verified authenticated after warm-ping"],
        )
        result = assess_plan(plan, {plan.criteria[0]: "met" if recovered else "missed"}, notes=note)
        close_plan(result)
    except Exception as e:
        logger.error("orchestrator logging failed: %s", e)


def warm(check_only: bool = False) -> int:
    if not COOKIE_FILE.exists():
        log("no saved cookie file — nothing to warm")
        return 2

    saved_cookies = json.loads(COOKIE_FILE.read_text())

    import tempfile
    profile_dir = Path(tempfile.mkdtemp(prefix="icelandair_warm_"))
    xvfb_proc = None
    chrome_proc = None
    try:
        xvfb_proc = _start_xvfb()
        chrome_proc = _start_chrome(profile_dir)

        tab = _cdp_new_tab("about:blank")
        if not tab:
            log("chrome failed to expose a tab — skipping, file untouched")
            _log_warm_plan(False, "infra error: no CDP tab")
            return 3

        ws_url = tab["webSocketDebuggerUrl"]
        ws = websocket.create_connection(ws_url, timeout=15)
        try:
            _inject_cookies(ws, saved_cookies)
            _ws_call(ws, 4, "Page.navigate", {"url": WARM_URL})
            time.sleep(NAV_SETTLE_SECONDS)

            authenticated = _check_authenticated(ws)
            if not authenticated:
                note = "session not authenticated (challenge or logged-out) — needs manual re-login"
                log(note)
                _escalate(f"Icelandair warm-ping: {note}. Run the login proof-of-concept again.")
                _log_warm_plan(False, note)
                return 2

            if check_only:
                log("authenticated (check-only mode, not re-saving)")
                _log_warm_plan(True, "authenticated, check-only run")
                return 0

            fresh_cookies = _extract_icelandair_cookies(ws)
            COOKIE_FILE.write_text(json.dumps(fresh_cookies, indent=2))
            note = f"warmed + re-saved {len(fresh_cookies)} cookies"
            log(note)
            _log_warm_plan(True, note)
            return 0
        finally:
            ws.close()
    except Exception as e:
        log(f"warm-ping failed: {e} — file untouched")
        _log_warm_plan(False, f"error: {e}")
        return 3
    finally:
        if chrome_proc:
            chrome_proc.terminate()
            try:
                chrome_proc.wait(timeout=5)
            except Exception:
                chrome_proc.kill()
        if xvfb_proc:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except Exception:
                xvfb_proc.kill()
        import shutil
        shutil.rmtree(profile_dir, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only, never write")
    args = ap.parse_args()
    sys.exit(warm(check_only=args.check))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
check_poe_health.py — Poe API key health check
Dreams2Memories Travel, LLC

Verifies the Poe API key in config/poe.env is valid and in sync with opencode.json.
Exits 0 if healthy, 1 if action required.

Usage:
    python3 scripts/check_poe_health.py          # plain status
    python3 scripts/check_poe_health.py --fix     # auto-run poe-sync if drift detected
    python3 scripts/check_poe_health.py --quiet   # only print on failure (for cron)
    python3 scripts/check_poe_health.py --telegram # send Telegram alert on failure

Root cause this script addresses:
    Poe API keys are invalidated when Commander visits poe.com/api_key and clicks
    "Regenerate". The browser session (website login) is SEPARATE from the API key.
    Re-authing through the website does NOT fix the key in poe.env or opencode.json.

    Symptom: Models show as "#404" in OpenCode because every /v1/models call
    returns 401 Unauthorized with the stale key.

    Fix: Go to poe.com/api_key -> copy new key -> update POE_API_KEY in
    config/poe.env -> run: poe-sync
"""

import json
import os
import subprocess
import sys
from pathlib import Path

THUNDERBIRD  = Path(__file__).resolve().parent.parent
POE_ENV      = THUNDERBIRD / "config" / "poe.env"
OC_JSON      = THUNDERBIRD / "opencode.json"
SYNC_SCRIPT  = THUNDERBIRD / "scripts" / "sync_poe_opencode.py"
POE_MODELS_URL = "https://api.poe.com/v1/models"

QUIET   = "--quiet"   in sys.argv
FIX     = "--fix"     in sys.argv
TELEGRAM = "--telegram" in sys.argv
VERBOSE  = "--verbose" in sys.argv


def log(msg: str, force: bool = False, verbose_only: bool = False) -> None:
    if verbose_only and not VERBOSE:
        return
    if not QUIET or force:
        print(msg)


def read_poe_env() -> dict[str, str]:
    result = {}
    if not POE_ENV.exists():
        return result
    for line in POE_ENV.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def check_api_key(key: str) -> tuple[bool, str, int, list[str]]:
    """Return (valid, status_text, http_code, model_ids)."""
    try:
        import urllib.request, urllib.error
        req = urllib.request.Request(
            POE_MODELS_URL,
            headers={"Authorization": f"Bearer {key}"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
            model_ids = sorted(m["id"] for m in body.get("data", []))
            return True, "OK", resp.status, model_ids
    except urllib.error.HTTPError as e:
        return False, e.reason, e.code, []
    except Exception as e:
        return False, str(e), 0, []


def send_telegram_alert(msg: str) -> None:
    """Send alert to Commander via Telegram."""
    cfg = read_poe_env()
    bot_token = cfg.get("TELEGRAM_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    chat_id   = cfg.get("TELEGRAM_COMMANDER_ID", os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206"))
    if not bot_token:
        return
    try:
        import urllib.request, urllib.parse
        payload = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def main() -> int:
    issues: list[str] = []

    # ── 1. Read poe.env ───────────────────────────────────────────────────────
    cfg = read_poe_env()
    key = cfg.get("POE_API_KEY", "")
    base_url = cfg.get("POE_BASE_URL", "https://api.poe.com/v1")

    if not key:
        log("FAIL: POE_API_KEY not set in config/poe.env", force=True)
        log("      Go to poe.com/api_key -> copy key -> add to config/poe.env", force=True)
        return 1

    masked = key[:8] + "..."
    log(f"Key   : {masked} (from config/poe.env)")
    log(f"URL   : {base_url}")

    # ── 2. Test key against Poe API ───────────────────────────────────────────
    log("Testing key against Poe API...", force=QUIET is False)
    valid, status_text, http_code, model_ids = check_api_key(key)

    if valid:
        log(f"Auth  : OK ({http_code})")
        if model_ids:
            log(f"Models: {len(model_ids)} available", verbose_only=True)
            for mid in model_ids:
                log(f"  - {mid}", verbose_only=True)
    else:
        issues.append("stale_key")
        log(f"Auth  : FAIL {http_code} {status_text}", force=True)
        log("", force=True)
        log("  ROOT CAUSE: Poe API key is stale or revoked.", force=True)
        log("  This happens when you visit poe.com/api_key and click 'Regenerate'.", force=True)
        log("  Re-authing via the website does NOT fix this -- they are separate.", force=True)
        log("", force=True)
        log("  FIX (30 seconds):", force=True)
        log("    1. Go to poe.com/api_key", force=True)
        log("    2. Copy the current API key", force=True)
        log("    3. Edit config/poe.env -> update POE_API_KEY=<new key>", force=True)
        log("    4. Run: poe-sync", force=True)
        log("    5. Restart OpenCode", force=True)

    # ── 3. Check opencode.json key matches poe.env ────────────────────────────
    oc_key = ""
    if OC_JSON.exists():
        try:
            oc_data = json.loads(OC_JSON.read_text())
            oc_key = oc_data.get("provider", {}).get("poe", {}).get("options", {}).get("apiKey", "")
        except Exception:
            pass

    if oc_key and oc_key != key:
        issues.append("key_drift")
        log(f"Drift : opencode.json key ({oc_key[:8]}...) != poe.env key ({masked})", force=True)
        if FIX:
            log("  Auto-fixing: running poe-sync...", force=True)
            subprocess.run([sys.executable, str(SYNC_SCRIPT)], check=False)
            log("  Done. Restart OpenCode.", force=True)
        else:
            log("  Fix: run poe-sync", force=True)
    elif oc_key == key:
        log(f"Sync  : opencode.json key matches poe.env")
    else:
        log(f"Sync  : could not read opencode.json key")

    # ── 4. Telegram alert if requested and issues found ───────────────────────
    if TELEGRAM and issues:
        alert_lines = ["*Poe Auth Alert* — action required"]
        if "stale_key" in issues:
            alert_lines.append(f"Key `{masked}` returned HTTP {http_code} — stale/revoked")
            alert_lines.append("Go to poe.com/api\\_key -> copy new key -> edit config/poe.env -> run `poe-sync`")
        if "key_drift" in issues:
            alert_lines.append("opencode.json key out of sync with poe.env — run `poe-sync`")
        send_telegram_alert("\n".join(alert_lines))
        log("Telegram alert sent.", force=True)

    # ── 5. Summary ────────────────────────────────────────────────────────────
    if issues:
        log("", force=True)
        log(f"Result: FAIL ({', '.join(issues)})", force=True)
        return 1
    else:
        log("Result: PASS — Poe auth healthy")
        return 0


if __name__ == "__main__":
    sys.exit(main())

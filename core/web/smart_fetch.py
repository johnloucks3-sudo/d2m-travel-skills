#!/usr/bin/env python3
"""smart_fetch — Anansi-first web fetch with CloakBrowser stealth escalation.

Escalation tiers (first success wins):
  Tier 1: `.venv/bin/anansi fetch --output <fmt> <url>`         (fast HTTP fetch)
  Tier 2: `anansi fetch --browser ...`  (optional, allow_browser_tier=True)
  Tier 3: `node tools/cloak/cloak_fetch.mjs <url> --output <fmt>` (stealth Chromium)

Tier 3 fires ONLY when a lower tier is WALLED (403/429/503 or an anti-bot body
signature) or errors. CloakBrowser (npm) defeats Akamai/Imperva/Cloudflare walls
where a plain HTTP fetch is blocked.

Do NOT edit the anansi site-package — this module calls its CLI as a subprocess.

CLI: python3 -m core.web.smart_fetch <url> [--output markdown] [--browser-tier]
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

# Repo root = three levels up from this file (core/web/smart_fetch.py -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ANANSI = _REPO_ROOT / ".venv" / "bin" / "anansi"
_CLOAK = _REPO_ROOT / "tools" / "cloak" / "cloak_fetch.mjs"

# Resolve an absolute node path so tier-3 works under thin-PATH systemd daemons,
# not just interactive shells (Sterling hardening note 2026-07-01).
_NODE = shutil.which("node") or next(
    (p for p in ("/usr/bin/node", "/usr/local/bin/node",
                 str(Path.home() / ".local/bin/node"))
     if Path(p).exists()),
    "node",
)

# Akamai / Imperva-Incapsula / Cloudflare anti-bot body signatures (lowercased match).
_WALL_SIGNATURES = (
    "reference #",
    "access denied",
    "attention required",
    "akamai",
    "incapsula",
    "imperva",
    "verify you are human",
    "request unsuccessful",
    "please wait",
    "unusual traffic",
    "are you a robot",
    "bot detection",
)
_WALL_STATUSES = {403, 429, 503}
_BODY_SNIFF_BYTES = 6144  # inspect first ~6KB only


def _is_walled(status, body) -> bool:
    """True if this response looks like an anti-bot wall (status OR body signature)."""
    if status is not None and status in _WALL_STATUSES:
        return True
    if body:
        head = body[:_BODY_SNIFF_BYTES].lower()
        return any(sig in head for sig in _WALL_SIGNATURES)
    return False


def _parse_anansi_status(stdout: str):
    """Anansi prints a leading `HTTP <status> <url> [time]` line; extract the code."""
    if not stdout:
        return None
    m = re.match(r"\s*HTTP\s+(\d{3})\b", stdout)
    return int(m.group(1)) if m else None


def _strip_anansi_header(stdout: str) -> str:
    """Drop anansi's leading `HTTP ...` status line from the returned content."""
    lines = stdout.splitlines()
    if lines and re.match(r"\s*HTTP\s+\d{3}\b", lines[0]):
        return "\n".join(lines[1:]).strip()
    return stdout.strip()


# --- tier runners (patched in offline tests) ---------------------------------

def _run_anansi(url: str, output: str, timeout: int, browser: bool = False):
    """Returns (status, content, error). status may be None (CLI gives no HTTP code on error)."""
    cmd = [str(_ANANSI), "fetch", "--output", output]
    if browser:
        cmd.append("--browser")
    cmd.append(url)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "", "anansi timeout"
    except Exception as e:  # noqa: BLE001
        return None, "", f"anansi spawn error: {e}"
    if proc.returncode != 0 and not proc.stdout.strip():
        return None, "", (proc.stderr or "anansi nonzero exit").strip()
    status = _parse_anansi_status(proc.stdout)
    content = _strip_anansi_header(proc.stdout)
    return status, content, None


def _run_cloak(url: str, output: str, timeout: int):
    """Returns (status, content, error). Cloak surfaces content; status stays None (page rendered)."""
    cmd = [_NODE, str(_CLOAK), url, "--output", output, "--timeout", str(timeout * 1000)]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 30, cwd=str(_CLOAK.parent)
        )
    except subprocess.TimeoutExpired:
        return None, "", "cloak timeout"
    except Exception as e:  # noqa: BLE001
        return None, "", f"cloak spawn error: {e}"
    content = (proc.stdout or "").strip()
    if proc.returncode != 0 or not content:
        return None, "", (proc.stderr or "cloak nonzero exit / empty").strip()
    return None, content, None


# --- public API --------------------------------------------------------------

def fetch(url: str, output: str = "markdown", allow_browser_tier: bool = False, timeout: int = 45) -> dict:
    """Fetch a URL, escalating to CloakBrowser when a lower tier is walled/errors.

    Returns dict: tier_used (1|2|3|None), status, walled (bool, final), content, error.
    """
    result = {"tier_used": None, "status": None, "walled": False, "content": "", "error": None}

    # Tier 1 — anansi HTTP fetch.
    status, content, err = _run_anansi(url, output, timeout, browser=False)
    walled = _is_walled(status, content) if err is None else True
    if err is None and not walled:
        result.update(tier_used=1, status=status, walled=False, content=content)
        _log(1, url, status)
        return result

    # Tier 2 — anansi headless browser (optional).
    if allow_browser_tier:
        status2, content2, err2 = _run_anansi(url, output, timeout, browser=True)
        walled2 = _is_walled(status2, content2) if err2 is None else True
        if err2 is None and not walled2:
            result.update(tier_used=2, status=status2, walled=False, content=content2)
            _log(2, url, status2)
            return result

    # Tier 3 — CloakBrowser stealth escalation.
    status3, content3, err3 = _run_cloak(url, output, timeout)
    if err3 is None and content3:
        result.update(tier_used=3, status=status3, walled=False, content=content3)
        _log(3, url, status3)
        return result

    # All tiers exhausted — report the wall/error we ended on.
    result.update(tier_used=None, status=status, walled=True, content="", error=err3 or err or "all tiers failed")
    _log(None, url, status)
    return result


def _log(tier, url: str, status):
    tag = f"tier {tier}" if tier else "NO TIER (walled/failed)"
    sys.stderr.write(f"[smart_fetch] served by {tag} — {url} (status={status})\n")


def _main(argv):
    import argparse

    p = argparse.ArgumentParser(prog="core.web.smart_fetch")
    p.add_argument("url")
    p.add_argument("--output", default="markdown", choices=["html", "text", "markdown"])
    p.add_argument("--browser-tier", action="store_true", help="allow anansi tier-2 headless browser")
    p.add_argument("--timeout", type=int, default=45)
    args = p.parse_args(argv)

    r = fetch(args.url, output=args.output, allow_browser_tier=args.browser_tier, timeout=args.timeout)
    if r["content"]:
        sys.stdout.write(r["content"] + "\n")
    else:
        sys.stderr.write(f"[smart_fetch] FAILED: {r['error']}\n")
    sys.stderr.write(f"[smart_fetch] served by tier {r['tier_used']}\n")
    return 0 if r["content"] else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))

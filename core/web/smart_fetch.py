#!/usr/bin/env python3
"""smart_fetch — Anansi-first web fetch with CloakBrowser stealth escalation.

Escalation tiers (first success wins):
  Tier 1: `.venv/bin/anansi fetch --output <fmt> <url>`         (fast HTTP fetch)
  Tier 2: `anansi fetch --browser ...`  (optional, allow_browser_tier=True)
  Tier 3: `node tools/cloak/cloak_fetch.mjs <url> --output <fmt>` (stealth Chromium)
  Tier 4: Camofox REST stealth browser (optional, allow_camofox_tier=True)

Tier 3 fires ONLY when a lower tier is WALLED (403/429/503 or an anti-bot body
signature) or errors. CloakBrowser (npm) defeats Akamai/Imperva/Cloudflare walls
where a plain HTTP fetch is blocked. Tier 4 (Camofox, 127.0.0.1:9377) is a second
stealth engine tried only when CloakBrowser also fails — opt-in because it is
heavier and session-stateful.

search() adds a free-text search primitive anansi never had (MISSION-629):
SearXNG metasearch (127.0.0.1:8890) primary, Camofox @google_search macro fallback.

Do NOT edit the anansi site-package — this module calls its CLI as a subprocess.

CLI: python3 -m core.web.smart_fetch <url> [--output markdown] [--browser-tier] [--camofox-tier]
     python3 -m core.web.smart_fetch --search "<free text query>"
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

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

# Domains KNOWN to sit behind a hard anti-bot edge (Akamai/Imperva/Cloudflare) that
# a plain HTTP fetch cannot clear. For these we skip the wasted lower-tier round-trips
# and go straight to Tier 3 (CloakBrowser). VERIFIED: rssc.com curl->403, cloak->200.
# Matched on hostname suffix (parsed), never substring — path segments must not false-match.
# NOTE: this defeats the public-site EDGE wall only; authenticated login/reCAPTCHA-gated
# portals (e.g. the Regent B2B booking portal) still require a real session (MISSION-214).
_KNOWN_WALLED_HOSTS = (
    "rssc.com",  # Regent Seven Seas — Akamai edge (MISSION-214 / MISSION-1498)
)


def _is_known_walled(url: str) -> bool:
    """True if url's hostname is (or is a subdomain of) a known hard-walled domain."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return False
    return any(host == d or host.endswith("." + d) for d in _KNOWN_WALLED_HOSTS)


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
    """Returns (status, content, error). Cloak emits the rendered page's HTTP status on stderr."""
    cmd = [_NODE, str(_CLOAK), url, "--output", output, "--timeout", str(timeout * 1000)]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 30, cwd=str(_CLOAK.parent)
        )
    except subprocess.TimeoutExpired:
        return None, "", "cloak timeout"
    except Exception as e:  # noqa: BLE001
        return None, "", f"cloak spawn error: {e}"
    status = _parse_cloak_status(proc.stderr)
    content = (proc.stdout or "").strip()
    if proc.returncode != 0 or not content:
        return status, "", (proc.stderr or "cloak nonzero exit / empty").strip()
    return status, content, None


def _parse_cloak_status(stderr: str):
    """cloak_fetch.mjs prints `[cloak_fetch] HTTP <status>` on stderr; extract the code."""
    if not stderr:
        return None
    m = re.search(r"\[cloak_fetch\]\s+HTTP\s+(\d{3})\b", stderr)
    return int(m.group(1)) if m else None


# --- Tier 4: Camofox stealth-browser REST API --------------------------------
# Camofox (deploy/browser_search_stack.md) is a self-hosted camoufox browser
# exposed over REST on 127.0.0.1:9377. Unlike CloakBrowser (one-shot Chromium),
# it keeps a real, stateful browser session with cookies/tabs — a second stealth
# engine to try when CloakBrowser also fails. Opt-in (allow_camofox_tier=True):
# it is heavier and its session can expire between calls, so it is NOT a default
# tier. It also backs free-text search() via the @google_search macro.

_CAMOFOX_BASE = "http://127.0.0.1:9377"
_CAMOFOX_USER = "wing"  # namespaced session id — Camofox scopes tabs per userId


def _camofox_key() -> str:
    """CAMOFOX_API_KEY from deploy/camofox/.env (gitignored) or the environment."""
    env_path = _REPO_ROOT / "deploy" / "camofox" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("CAMOFOX_API_KEY=") and not line.startswith("#"):
                return line.split("=", 1)[1].strip()
    import os
    return os.environ.get("CAMOFOX_API_KEY", "")


def _camofox_request(method: str, path: str, body: dict | None = None,
                     params: dict | None = None, timeout: int = 45):
    """One Camofox REST call. Returns (status_code, parsed_json_or_text, error)."""
    import json as _json
    import urllib.error
    import urllib.parse
    import urllib.request

    url = _CAMOFOX_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = _json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": f"Bearer {_camofox_key()}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, _json.loads(raw), None
            except ValueError:
                return resp.status, raw, None
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, _json.loads(raw), None
        except ValueError:
            return e.code, raw, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return None, None, f"camofox request error: {e}"


def _camofox_open_tab(url: str, timeout: int):
    """Open a tab, restarting the browser once on an expired session. Returns (tabId, error)."""
    for attempt in (1, 2):
        status, payload, err = _camofox_request(
            "POST", "/tabs/open",
            body={"userId": _CAMOFOX_USER, "url": url}, timeout=timeout,
        )
        if err is None and isinstance(payload, dict) and payload.get("tabId"):
            return payload["tabId"], None
        # Session expired (or cold browser) — start and retry once.
        expired = isinstance(payload, dict) and payload.get("code") == "session_expired"
        if attempt == 1 and (expired or err or not isinstance(payload, dict)):
            _camofox_request("POST", "/start", body=None, timeout=timeout)
            continue
        detail = payload.get("error") if isinstance(payload, dict) else payload
        return None, err or f"camofox open failed: {detail}"
    return None, "camofox open failed after retry"


def _run_camofox(url: str, output: str, timeout: int):
    """Fetch a URL through Camofox's stealth browser. Returns (status, content, error).

    Content is the page's accessibility-tree snapshot (headings, paragraphs, links) —
    a text/markdown-ish rendering suitable for the same downstream use as anansi/cloak
    output. `output` is accepted for signature parity; Camofox always returns snapshot text.
    """
    tab_id, err = _camofox_open_tab(url, timeout)
    if err:
        return None, "", err
    status, payload, err = _camofox_request(
        "GET", f"/tabs/{tab_id}/snapshot",
        params={"userId": _CAMOFOX_USER}, timeout=timeout,
    )
    if err:
        return None, "", err
    if isinstance(payload, dict):
        content = (payload.get("snapshot") or "").strip()
        if content:
            return 200, content, None
        return None, "", "camofox empty snapshot"
    return None, "", "camofox unexpected snapshot payload"


# --- Free-text search (MISSION-629: anansi has no free-text search) ----------
# anansi only does `fetch <URL>` — the fare/hotel/transfer scans that passed raw
# NL queries got empty output. This gives a real free-text search primitive:
# SearXNG (self-hosted metasearch, :8890, JSON) is primary (fast, no browser);
# Camofox's @google_search macro is a stealth-browser fallback.

_SEARXNG_BASE = "http://127.0.0.1:8890"


def _search_searxng(query: str, limit: int, timeout: int):
    """Free-text search via self-hosted SearXNG JSON API. Returns (results, error)."""
    import json as _json
    import urllib.parse
    import urllib.request

    url = f"{_SEARXNG_BASE}/search?" + urllib.parse.urlencode(
        {"q": query, "format": "json"}
    )
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = _json.loads(resp.read().decode("utf-8", "replace"))
    except Exception as e:  # noqa: BLE001
        return [], f"searxng error: {e}"
    results = [
        {"title": r.get("title", ""), "url": r.get("url", ""),
         "content": r.get("content", "")}
        for r in data.get("results", [])[:limit]
    ]
    return results, None


def _search_camofox(query: str, limit: int, timeout: int):
    """Free-text search via Camofox @google_search macro + link extraction. (results, error)."""
    tab_id, err = _camofox_open_tab("about:blank", timeout)
    if err:
        return [], err
    _s, _p, err = _camofox_request(
        "POST", f"/tabs/{tab_id}/navigate",
        body={"userId": _CAMOFOX_USER, "macro": "@google_search", "query": query},
        timeout=timeout,
    )
    if err:
        return [], err
    _s, payload, err = _camofox_request(
        "GET", f"/tabs/{tab_id}/links", params={"userId": _CAMOFOX_USER}, timeout=timeout,
    )
    if err:
        return [], err
    links = payload.get("links", payload) if isinstance(payload, dict) else payload
    results = []
    if isinstance(links, list):
        for l in links[:limit]:
            if isinstance(l, dict):
                results.append({"title": l.get("text", ""), "url": l.get("url", ""), "content": ""})
            else:
                results.append({"title": "", "url": str(l), "content": ""})
    return results, None


def search(query: str, limit: int = 10, engine: str = "auto", timeout: int = 20) -> dict:
    """Free-text web search. engine: 'searxng' | 'camofox' | 'auto' (searxng, camofox fallback).

    Returns dict: engine_used, query, results (list of {title,url,content}), error.
    """
    result = {"engine_used": None, "query": query, "results": [], "error": None}
    if engine in ("searxng", "auto"):
        rows, err = _search_searxng(query, limit, timeout)
        if rows:
            result.update(engine_used="searxng", results=rows)
            return result
        if engine == "searxng":
            result["error"] = err or "searxng no results"
            return result
    if engine in ("camofox", "auto"):
        rows, err = _search_camofox(query, limit, timeout)
        if rows:
            result.update(engine_used="camofox", results=rows)
            return result
        result["error"] = err or "camofox no results"
        return result
    result["error"] = f"unknown engine: {engine}"
    return result


# --- public API --------------------------------------------------------------

def fetch(url: str, output: str = "markdown", allow_browser_tier: bool = False,
          allow_camofox_tier: bool = False, timeout: int = 45) -> dict:
    """Fetch a URL, escalating to CloakBrowser when a lower tier is walled/errors.

    Tier 4 (Camofox stealth browser) is opt-in via allow_camofox_tier=True — a
    second stealth engine tried only after CloakBrowser also fails.

    Returns dict: tier_used (1|2|3|4|None), status, walled (bool, final), content, error.
    """
    result = {"tier_used": None, "status": None, "walled": False, "content": "", "error": None}

    # Known-walled fast path — domains behind a hard Akamai/Imperva/Cloudflare edge that a
    # plain HTTP fetch can never clear go STRAIGHT to Tier 3, skipping the wasted lower tiers.
    if _is_known_walled(url):
        status3, content3, err3 = _run_cloak(url, output, timeout)
        if err3 is None and content3:
            result.update(tier_used=3, status=status3, walled=False, content=content3)
            _log(3, url, status3)
            return result
        # Cloak failed on a known wall — fall through to try the normal ladder as a backstop.

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

    # Tier 4 — Camofox stealth-browser REST (opt-in): a second stealth engine
    # tried only when CloakBrowser also failed.
    if allow_camofox_tier:
        status4, content4, err4 = _run_camofox(url, output, timeout)
        if err4 is None and content4:
            result.update(tier_used=4, status=status4, walled=False, content=content4)
            _log(4, url, status4)
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
    p.add_argument("url", nargs="?")
    p.add_argument("--output", default="markdown", choices=["html", "text", "markdown"])
    p.add_argument("--browser-tier", action="store_true", help="allow anansi tier-2 headless browser")
    p.add_argument("--camofox-tier", action="store_true", help="allow tier-4 Camofox stealth browser")
    p.add_argument("--search", metavar="QUERY", help="free-text search instead of URL fetch (SearXNG/Camofox)")
    p.add_argument("--timeout", type=int, default=45)
    args = p.parse_args(argv)

    if args.search:
        s = search(args.search, timeout=args.timeout)
        import json as _json
        sys.stdout.write(_json.dumps(s, indent=2) + "\n")
        sys.stderr.write(f"[smart_fetch] search served by {s['engine_used']}\n")
        return 0 if s["results"] else 1

    r = fetch(args.url, output=args.output, allow_browser_tier=args.browser_tier,
              allow_camofox_tier=args.camofox_tier, timeout=args.timeout)
    if r["content"]:
        sys.stdout.write(r["content"] + "\n")
    else:
        sys.stderr.write(f"[smart_fetch] FAILED: {r['error']}\n")
    sys.stderr.write(f"[smart_fetch] served by tier {r['tier_used']}\n")
    return 0 if r["content"] else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))

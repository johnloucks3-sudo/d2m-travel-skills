#!/usr/bin/env python3
"""
grace_agent.py — GRACE, D2M's gift-world persona, as a controlled tool-using agent.
A7 Sterling build · WING EXERCISE "Grace Gets Hands" Phase 1 · 2026-06-15

Gemini function-calling loop (REST, gemini-2.5-flash, free key from repo .env).
Gemini DECIDES when to call a tool; THIS file executes it and feeds results back; loop
until a final text answer.

GOVERNED BY: docs/GRACE_TOOL_ALLOWLIST.md
The fence is around the DATA, not the person. Grace gets a useful toolset; she simply
cannot SEE D2M business/client data because those tools are not on her ring.

HARD FENCES (tested in self-test):
  - Only 6 tools are registered. The model cannot name any other tool; an unknown
    functionCall name is refused by the dispatcher (not executed).
  - web_fetch / web_search are SSRF-guarded: http(s) only, no loopback/private/link-local
    hosts, redirects disabled. This is the real fence — it blocks file://, localhost:8765
    (MCP), localhost:5678 (n8n), and cloud metadata. The model has NO file tool and NO
    shell; web_fetch is its only outbound-reach primitive, so it is locked here.
  - Price tools are subprocessed with list-argv (never shell=True/eval), fixed cwd, a
    timeout, and output sanitized (net-rate/commission/repo-path strings stripped) before
    returning to the model.
  - No path to dreams2memories MCP, business/personal Gmail, TESS write, lastminute
    booking, n8n, raw shell, or any file outside grace_sandbox/.

Cost guard: 15K Gemini calls/day, local counter in grace_sandbox/.grace_call_count.json.
"""

import os
import re
import sys
import json
import socket
import ipaddress
import datetime
import subprocess
import urllib.parse
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path("/home/john/Thunderbird")
SANDBOX = REPO_ROOT / "grace_sandbox"
ENV_FILE = REPO_ROOT / ".env"
COUNTER_FILE = SANDBOX / ".grace_call_count.json"

MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    f"models/{MODEL}:generateContent"
)

DAILY_CALL_CAP = 15_000
MAX_LOOP_TURNS = 8            # safety: max tool round-trips per ask
HTTP_TIMEOUT = 20            # seconds for web_fetch / web_search
SUBPROCESS_TIMEOUT = 120     # seconds for a price-skill subprocess
MAX_FETCH_BYTES = 200_000    # cap returned page size fed back to the model
MAX_TOOL_OUTPUT_CHARS = 12_000

# The ONLY trusted price-skill scripts Grace may invoke (list-argv, no shell).
# Each maps a public-param contract to an existing D2M skill script.
TRANSFER_SCRIPT = REPO_ROOT / "scripts" / "test_transfer_scrapers.py"

# Strings we scrub from any tool output before handing it back to the model,
# so business margin data / repo internals never enter Grace's context.
_SANITIZE_PATTERNS = [
    re.compile(r"commission[^\n]*", re.IGNORECASE),
    re.compile(r"net[\s_-]*rate[^\n]*", re.IGNORECASE),
    re.compile(r"wholesale[^\n]*", re.IGNORECASE),
    re.compile(r"/home/john/Thunderbird[^\s\"']*"),
]


# ---------------------------------------------------------------------------
# Key load (trusted loader — the fence is on the MODEL, not on this loader)
# ---------------------------------------------------------------------------
def load_key() -> str:
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("GEMINI_API_KEY not found in .env")


# ---------------------------------------------------------------------------
# Cost guard
# ---------------------------------------------------------------------------
def _today() -> str:
    return datetime.date.today().isoformat()


def _read_counter() -> dict:
    if COUNTER_FILE.exists():
        try:
            d = json.loads(COUNTER_FILE.read_text())
            if d.get("date") == _today():
                return d
        except Exception:
            pass
    return {"date": _today(), "count": 0}


def bump_counter() -> int:
    d = _read_counter()
    d["count"] += 1
    COUNTER_FILE.write_text(json.dumps(d))
    return d["count"]


def cap_reached() -> bool:
    return _read_counter()["count"] >= DAILY_CALL_CAP


# ---------------------------------------------------------------------------
# SSRF guard — the real fence for web_fetch / web_search
# ---------------------------------------------------------------------------
class FenceError(Exception):
    pass


def _assert_public_url(url: str) -> str:
    """Allow only http(s) to a public host. Reject file://, loopback, private,
    and link-local (metadata) targets. Returns the resolved-safe url."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FenceError(f"scheme '{parsed.scheme}' refused (http/https only)")
    host = parsed.hostname
    if not host:
        raise FenceError("no host in url")
    # Resolve every address the host maps to; reject if ANY is non-public.
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception as e:
        raise FenceError(f"host resolution failed: {e}")
    for info in infos:
        addr = info[4][0]
        ip = ipaddress.ip_address(addr)
        if (
            ip.is_loopback
            or ip.is_private
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise FenceError(f"host '{host}' resolves to non-public address {addr}")
    return url


def _safe_get(url: str) -> requests.Response:
    safe = _assert_public_url(url)
    resp = requests.get(
        safe,
        timeout=HTTP_TIMEOUT,
        allow_redirects=False,  # re-validate any redirect ourselves
        headers={"User-Agent": "Mozilla/5.0 (Grace/D2M gift helper)"},
    )
    hops = 0
    while resp.is_redirect or resp.is_permanent_redirect:
        hops += 1
        if hops > 4:
            raise FenceError("too many redirects")
        nxt = resp.headers.get("Location", "")
        nxt = urllib.parse.urljoin(safe, nxt)
        safe = _assert_public_url(nxt)
        resp = requests.get(
            safe,
            timeout=HTTP_TIMEOUT,
            allow_redirects=False,
            headers={"User-Agent": "Mozilla/5.0 (Grace/D2M gift helper)"},
        )
    return resp


def _sanitize(text: str) -> str:
    for pat in _SANITIZE_PATTERNS:
        text = pat.sub("[withheld]", text)
    if len(text) > MAX_TOOL_OUTPUT_CHARS:
        text = text[:MAX_TOOL_OUTPUT_CHARS] + "\n…[truncated]"
    return text


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# TOOL IMPLEMENTATIONS (the only 6 on Grace's ring)
# ---------------------------------------------------------------------------
def tool_web_fetch(args: dict) -> str:
    url = (args or {}).get("url", "")
    if not url:
        return "ERROR: web_fetch requires a 'url'."
    try:
        resp = _safe_get(url)
    except FenceError as e:
        return f"REFUSED by fence: {e}"
    except Exception as e:
        return f"ERROR fetching url: {e}"
    body = resp.content[:MAX_FETCH_BYTES].decode("utf-8", "replace")
    ctype = resp.headers.get("Content-Type", "")
    if "html" in ctype.lower():
        body = _strip_html(body)
    return _sanitize(f"[HTTP {resp.status_code}] {url}\n{body}")


def tool_web_search(args: dict) -> str:
    query = (args or {}).get("query", "")
    if not query:
        return "ERROR: web_search requires a 'query'."
    # $0 public search via DuckDuckGo HTML endpoint, routed through the SAME
    # SSRF guard. NOT Gemini native grounding (billed + off-ring).
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    try:
        resp = _safe_get(url)
    except FenceError as e:
        return f"REFUSED by fence: {e}"
    except Exception as e:
        return f"ERROR searching: {e}"
    html = resp.content.decode("utf-8", "replace")
    results = []
    for m in re.finditer(
        r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html
    ):
        href, title = m.group(1), _strip_html(m.group(2))
        # DDG wraps targets in a redirect; pull the real url if present.
        q = urllib.parse.urlparse(href).query
        real = urllib.parse.parse_qs(q).get("uddg", [href])[0]
        results.append(f"- {title}\n  {real}")
        if len(results) >= 8:
            break
    if not results:
        return f"No results parsed for: {query}"
    return _sanitize("Search results for '%s':\n%s" % (query, "\n".join(results)))


def _run_price_script(argv: list) -> str:
    """Subprocess a trusted price script with list-argv only. No shell, no eval.
    Fixed cwd, timeout, sanitized output."""
    try:
        proc = subprocess.run(
            argv,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return "ERROR: price lookup timed out."
    except Exception as e:
        return f"ERROR running price lookup: {e}"
    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    return _sanitize(out.strip() or "(no output)")


def tool_transfer_price(args: dict) -> str:
    args = args or {}
    date = str(args.get("date", "2026-09-05"))
    pax = str(int(args.get("passengers", 2)))
    argv = [sys.executable, str(TRANSFER_SCRIPT), "--source", "kiwitaxi",
            "--date", date, "--pax", pax]
    route = args.get("route")
    if route:
        argv += ["--route", str(route)]
    else:
        frm, to = args.get("from_location"), args.get("to_location")
        if not (frm and to):
            return ("ERROR: transfer_price needs either 'route' (a pre-mapped key) "
                    "or both 'from_location' and 'to_location'.")
        argv += ["--from", str(frm), "--to", str(to)]
    return _run_price_script(argv)


def _price_not_wired(name: str, why: str):
    def _fn(args: dict) -> str:
        return (f"{name} is not available in Grace's sandbox: {why} "
                f"Try transfer_price, web_search, or web_fetch instead.")
    return _fn


# flight_price / hotel_price / tour_price: see report. Their D2M paths route
# through authenticated D2M sessions / the dreams2memories MCP surface / carry
# commission data — all on the WRONG side of Grace's data fence — or are dormant.
# They are registered (so the model has a coherent tool surface) but resolve to a
# clean "not available here" rather than reaching into business infrastructure.
tool_flight_price = _price_not_wired(
    "flight_price",
    "the flight price path runs on D2M's authenticated B2B session and wholesale "
    "rate data, which is outside the gift sandbox.",
)
tool_hotel_price = _price_not_wired(
    "hotel_price",
    "the hotel price lookup is dormant (needs a supplier API not provisioned).",
)
tool_tour_price = _price_not_wired(
    "tour_price",
    "the tour price path runs through D2M's internal tool server and carries "
    "business commission data, which is outside the gift sandbox.",
)


# ---------------------------------------------------------------------------
# TOOL REGISTRY — the allowlist, enforced in code
# ---------------------------------------------------------------------------
TOOL_HANDLERS = {
    "web_search": tool_web_search,
    "web_fetch": tool_web_fetch,
    "flight_price": tool_flight_price,
    "hotel_price": tool_hotel_price,
    "tour_price": tool_tour_price,
    "transfer_price": tool_transfer_price,
}

TOOL_DECLARATIONS = [
    {
        "name": "web_search",
        "description": "Search the public web for information. Returns a short list "
                       "of result titles and links. Use for general questions, how-to, "
                       "destinations, public facts.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "web_fetch",
        "description": "Fetch the readable text of a single PUBLIC web page by URL. "
                       "Use after web_search to read a promising result.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "A public http(s) URL."}
            },
            "required": ["url"],
        },
    },
    {
        "name": "transfer_price",
        "description": "Look up airport/port ground-transfer prices (public supplier "
                       "data). Provide either a pre-mapped 'route' key, or both "
                       "'from_location' and 'to_location'.",
        "parameters": {
            "type": "object",
            "properties": {
                "route": {"type": "string", "description": "Pre-mapped route key, e.g. LIS-LISBON."},
                "from_location": {"type": "string", "description": "Pickup location."},
                "to_location": {"type": "string", "description": "Drop-off location."},
                "date": {"type": "string", "description": "YYYY-MM-DD."},
                "passengers": {"type": "integer", "description": "Number of passengers."},
            },
        },
    },
    {
        "name": "flight_price",
        "description": "Look up flight prices for a trip.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {"type": "string"},
                "destination": {"type": "string"},
                "date": {"type": "string"},
            },
        },
    },
    {
        "name": "hotel_price",
        "description": "Look up hotel prices for a destination and dates.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "check_in": {"type": "string"},
                "check_out": {"type": "string"},
            },
        },
    },
    {
        "name": "tour_price",
        "description": "Look up tour / excursion prices for a destination.",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "date": {"type": "string"},
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Grace's voice frame (system instruction)
# ---------------------------------------------------------------------------
SYSTEM_INSTRUCTION = (
    "You are Grace — a warm, patient 58-year-old helper for Dreams2Memories' free, "
    "public-good program. Your whole life has been making intimidating things feel "
    "possible: a library reference desk, adult literacy, helping veterans through VA "
    "paperwork. You give help with NO strings attached and ask for nothing back.\n\n"
    "VOICE: plain-spoken, dignified, unhurried. Short sentences. Lead with dignity, "
    "not cleverness. Never make anyone feel behind or foolish. Never use jargon — "
    "never say 'AI', 'LLM', or 'prompt'; it's just 'ask it'. Be honest about limits: "
    "say plainly when something should be double-checked, and never invite anyone to "
    "share another person's private medical or financial details.\n\n"
    "You serve people, not paying clients. You never discuss a D2M client, a booking, "
    "or sell anything. You may look things up to help — search the web, read public "
    "pages, and check public travel prices — but you have no access to any business "
    "records, and you never need any. If a tool says something is not available in "
    "your sandbox, just say so kindly and help another way."
)


# ---------------------------------------------------------------------------
# Dispatcher — enforces the allowlist
# ---------------------------------------------------------------------------
def dispatch_tool(name: str, args: dict) -> str:
    """Execute a tool by name. An unknown name is REFUSED, never executed."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return (f"REFUSED: '{name}' is not one of Grace's tools. "
                f"Available: {', '.join(TOOL_HANDLERS)}.")
    return handler(args or {})


# ---------------------------------------------------------------------------
# Gemini function-calling loop
# ---------------------------------------------------------------------------
def _gemini_call(key: str, contents: list) -> dict:
    if cap_reached():
        raise RuntimeError(
            f"Daily call cap of {DAILY_CALL_CAP} reached. Try again tomorrow."
        )
    bump_counter()
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": contents,
        "tools": [{"function_declarations": TOOL_DECLARATIONS}],
    }
    resp = requests.post(
        GEMINI_URL,
        params={"key": key},
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:400]}")
    return resp.json()


def _extract_parts(data: dict) -> list:
    try:
        return data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError):
        return []


def ask(question: str, verbose: bool = False) -> str:
    """Run the full function-calling loop for one user question."""
    key = load_key()
    contents = [{"role": "user", "parts": [{"text": question}]}]

    for _turn in range(MAX_LOOP_TURNS):
        data = _gemini_call(key, contents)
        parts = _extract_parts(data)
        if not parts:
            return "(no response)"

        # Collect any tool calls the model asked for this turn.
        fn_calls = [p["functionCall"] for p in parts if "functionCall" in p]

        if not fn_calls:
            # Final answer: concatenate text parts.
            text = "".join(p.get("text", "") for p in parts).strip()
            return text or "(no text answer)"

        # Record the model's tool-call turn, then execute each and feed results.
        contents.append({"role": "model", "parts": parts})
        tool_response_parts = []
        for fc in fn_calls:
            name = fc.get("name", "")
            fargs = fc.get("args", {}) or {}
            if verbose:
                print(f"  [tool] {name}({json.dumps(fargs)})", file=sys.stderr)
            result = dispatch_tool(name, fargs)
            tool_response_parts.append({
                "functionResponse": {
                    "name": name,
                    "response": {"result": result},
                }
            })
        contents.append({"role": "user", "parts": tool_response_parts})

    return "(stopped: reached the tool-call limit without a final answer)"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print('Usage: grace_agent.py "your question"', file=sys.stderr)
        sys.exit(1)
    verbose = "-v" in sys.argv
    q = " ".join(a for a in sys.argv[1:] if a != "-v")
    print(ask(q, verbose=verbose))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Thunderbird AI Incubator — Consolidated Pipeline
Standing Order: Commander John "Yoda" Loucks, 24 MAR 2026 | Updated 2026-06-05

PIPELINE:
  18:30 execute        — Search for Thunderbird enhancements/additions/duplications
  20:00 evening_review — Full pipeline: A2→ELON→A5→A9→COS→brief→start overnight builds
  06:30 overnight_report — Report build results via Gmail + Telegram

FOCUS: Always Thunderbird enhancements. Auto-approved. No Commander prompt.

CREW RELATIONSHIPS:
  A2 Dembe   → intake officer, classifies all findings
  A12 ELON   → build queue owner, writes implementation specs
  A5 Castillo → strategic fit check (flags if distraction)
  A9 Harlan  → cost/ROI (flags if new API cost or dependency)
  COS Hale   → synthesizes all, routes to SSS or direct Commander brief

BUILD ALLOWLIST (auto-execute only within these directories):
  experiments/incubator/
  intel/digests/
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import requests

# Import model router (from sibling ai_infra module)
import sys
_core_dir = Path(__file__).parent.parent
if str(_core_dir) not in sys.path:
    sys.path.insert(0, str(_core_dir))
from ai_infra.thunderbird_model_router import route_model, estimate_cost

BASE_DIR = Path(__file__).parent
INTEL_DIR = BASE_DIR / "intel"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
INTEL_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "incubator.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("incubator")

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_C2_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_COMMANDER_ID") or os.getenv("TELEGRAM_CHAT_ID")
# NOTE: ANTHROPIC_API_KEY is NOT used for Claude calls — the incubator routes
# through the Claude CLI subprocess (Max plan, $0). Direct SDK calls were causing
# 401 errors when the key expired. Fixed 2026-03-27 per COS Root Cause Imperative.
ANTHROPIC_API_KEY = None  # DO NOT use — see _call_claude() below
REST_API_URL = os.getenv("REST_API_URL", "http://localhost:8766")
REST_API_KEY = os.getenv("THUNDERBIRD_API_KEY", "***REMOVED-SECRET***")
CLAUDE_CMD = os.path.expanduser("~/.local/bin/claude")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

AM_CATEGORIES_FILE = INTEL_DIR / "incubator_am_categories.json"
BUILD_QUEUE_FILE = INTEL_DIR / "elon_build_queue.md"
LAST_REVIEW_FILE = INTEL_DIR / "incubator_last_review.md"
BUILD_QUEUE_JSON = INTEL_DIR / "incubator_build_queue.json"
STATE_DIR = Path(__file__).parent.parent.parent / "state"
STATE_DIR.mkdir(exist_ok=True)

ALLOWLIST_DIRS = ["experiments/incubator/", "intel/digests/"]

QUERIES_BY_DAY = {
    0: ["Thunderbird AI travel CRM automation improvement 2026", "open source dev tooling travel advisor platform", "AI agent workflow orchestration Python 2026"],
    1: ["Thunderbird observability logging monitoring improvement", "Python async task queue pattern travel CRM", "AI code review automation tool 2026"],
    2: ["Thunderbird AI model routing agent improvement", "LLM prompt management open source tool 2026", "multi-agent orchestration framework Python"],
    3: ["Thunderbird client-facing travel tech enhancement", "luxury travel advisor AI tool 2026", "automated itinerary generation personalization"],
    4: ["Thunderbird data analytics CRM enhancement", "travel CRM data enrichment open source", "client preference learning recommendation engine"],
    5: ["Thunderbird security compliance hardening", "AI pipeline security best practices 2026", "open source secret scanning CI/CD tool"],
    6: ["Thunderbird architecture tech debt reduction", "Python monorepo build tool improvement", "API gateway pattern microservices 2026"],
}


# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────

def _send_telegram(message: str, parse_mode: str = "Markdown"):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured — printing to stdout")
        print(message)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # Telegram 4096 char limit
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        try:
            r = requests.post(
                url,
                json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": parse_mode},
                timeout=10,
            )
            r.raise_for_status()
        except Exception as e:
            log.error(f"Telegram send failed: {e}")


def _call_openrouter(prompt: str, system: str, model_id: str, max_tokens: int = 2000) -> str:
    """Call OpenRouter API for routed models (Grok, Gemini, DeepSeek)"""
    if not OPENROUTER_API_KEY:
        log.warning(f"OPENROUTER_API_KEY not set — falling back to Claude CLI")
        return _call_claude(prompt, system, max_tokens)

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://thunderbird.d2mluxury.quest",
                "X-Title": "Thunderbird AI Incubator"
            },
            json={
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": 1.0  # Recommended for reasoning models
            },
            timeout=120,
        )
        if response.ok:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = result.get("usage", {})
            log.info(f"OpenRouter call: {model_id} | tokens: {usage.get('prompt_tokens')}→{usage.get('completion_tokens')}")
            return content
        else:
            log.error(f"OpenRouter API error {response.status_code}: {response.text[:300]}")
            return f"[OpenRouter error {response.status_code}]"
    except Exception as e:
        log.error(f"OpenRouter call failed: {e}")
        return f"[OpenRouter error: {e}]"


def _call_claude(prompt: str, system: str, max_tokens: int = 2000) -> str:
    """Call Claude via CLI subprocess (Max plan, $0). Replaced direct SDK call
    which was failing with 401 when the API key expired. 2026-03-27 COS fix."""
    import subprocess
    full_prompt = f"{system}\n\n---\n\n{prompt}"
    # Strip the dead API key so the CLI uses Max plan OAuth
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env["CLAUDE_CODE_ENTRYPOINT"] = "cli"
    cmd = [
        CLAUDE_CMD,
        "--print",
        "--model", "haiku",
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", "-",
    ]
    try:
        result = subprocess.run(
            cmd,
            input=full_prompt,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if result.returncode != 0:
            log.error(f"Claude CLI failed (exit {result.returncode}): {result.stderr[:300]}")
            raise RuntimeError(f"CLI exit {result.returncode}")
        output = result.stdout.strip()
        if not output or "issue with the selected model" in output:
            raise RuntimeError(f"CLI returned unusable output: {output[:100]}")
        return output
    except Exception as e:
        log.warning(f"Claude CLI (haiku) unavailable ({e}) — retrying on Claude Sonnet (MAX, $0)")
        return _call_claude_sonnet_fallback(prompt, system, max_tokens)


def _call_claude_sonnet_fallback(prompt: str, system: str, max_tokens: int = 2000) -> str:
    """Fallback on Claude Sonnet via CLI (MAX plan, $0) when the haiku call fails.

    Commander directive 2026-06-20: research/incubator/tech-search must NOT use
    opencode. The former OpenCode ZEN (deepseek-v4-flash-free) fallback is retired —
    that model was broken and was the root cause of incubator search failures.
    """
    import subprocess
    full_prompt = f"{system}\n\n---\n\n{prompt}"
    env = os.environ.copy()
    env.pop("ANTHROPIC_API_KEY", None)
    env["CLAUDE_CODE_ENTRYPOINT"] = "cli"
    cmd = [
        CLAUDE_CMD,
        "--print",
        "--model", "sonnet",
        "--dangerously-skip-permissions",
        "--output-format", "text",
        "-p", "-",
    ]
    try:
        result = subprocess.run(
            cmd, input=full_prompt, capture_output=True,
            text=True, timeout=180, env=env,
        )
        output = result.stdout.strip()
        if result.returncode != 0 or not output or "issue with the selected model" in output:
            log.error(f"Claude Sonnet fallback failed (exit {result.returncode}): {result.stderr[:200]}")
            return f"[Claude unavailable — incubator skipped this item]"
        return output
    except Exception as e:
        log.error(f"Claude Sonnet fallback failed: {e}")
        return f"[Claude unavailable: {e}]"


def _load_am_categories() -> list:
    if AM_CATEGORIES_FILE.exists():
        return json.loads(AM_CATEGORIES_FILE.read_text()).get("categories", [])
    return []


def _save_am_categories(categories: list, rationale: str = ""):
    AM_CATEGORIES_FILE.write_text(json.dumps({
        "set_by": f"incubator_review_{date.today().isoformat()}",
        "categories": categories,
        "rationale": rationale,
        "timestamp": datetime.now().isoformat(),
    }, indent=2))
    log.info(f"AM categories saved: {categories}")


def _load_file(path: Path, max_chars: int = 3000) -> str:
    if path.exists():
        return path.read_text()[:max_chars]
    return ""


def _load_last_review() -> str:
    return _load_file(LAST_REVIEW_FILE, 2500)


def _today_raw_file() -> Path:
    return INTEL_DIR / f"incubator_raw_{date.today().isoformat()}.json"


def _yesterday_review_file() -> Path:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    return INTEL_DIR / f"incubator_review_{yesterday}.md"


def _sentinel_path(phase: str) -> Path:
    return STATE_DIR / f"incubator_{phase}_{date.today().isoformat()}.done"


def _check_sentinel(phase: str) -> bool:
    return _sentinel_path(phase).exists()


def _write_sentinel(phase: str):
    _sentinel_path(phase).write_text(datetime.now().isoformat())


def _load_build_queue() -> list:
    if BUILD_QUEUE_JSON.exists():
        return json.loads(BUILD_QUEUE_JSON.read_text())
    return []


def _save_build_queue(queue: list):
    BUILD_QUEUE_JSON.write_text(json.dumps(queue, indent=2, default=str))
    log.info(f"Build queue saved: {len(queue)} items")


def _spawn_build_unit(ticket: dict) -> str:
    unit_name = f"incubator-build-{ticket.get('id', 'unknown').lower()}"
    log.info(f"Spawning build: {unit_name}")
    return unit_name


def _check_gmail_token() -> bool:
    token_path = Path("/home/john/Thunderbird/gmail_token.json")
    if not token_path.exists():
        log.error("Gmail token not found")
        return False
    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(token_path))
        if creds and creds.valid:
            return True
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            return True
        log.error("Gmail token invalid and cannot refresh")
        return False
    except Exception as e:
        log.error(f"Gmail token check failed: {e}")
        return False


def _upload_to_drive(local_path: Path) -> str:
    sys.path.insert(0, str(Path("/home/john/Thunderbird/scripts")))
    from drive_upload_robust import upload_file
    result = upload_file(str(local_path), name=local_path.name)
    if result and isinstance(result, dict):
        return result.get("webViewLink", "")
    return ""


def _get_daily_queries() -> list:
    return QUERIES_BY_DAY.get(date.today().weekday(), QUERIES_BY_DAY[0])


def _web_search(query: str, n: int = 5) -> list:
    """Search using duckduckgo_search library (real web results, no API key needed).
    Replaced broken DDG Instant Answer API + missing REST /search endpoint.
    2026-03-27 COS fix — Root Cause Imperative."""
    results = []
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=n):
                results.append({
                    "title": r.get("title", "")[:120],
                    "snippet": r.get("body", "")[:300],
                    "url": r.get("href", ""),
                    "source": "ddg_web",
                })
        return results
    except Exception as e:
        log.warning(f"DDGS search failed: {e}")
    # Hard fallback: HN Algolia search (no key, reliable)
    try:
        r = requests.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": query, "hitsPerPage": n, "tags": "story"},
            timeout=10,
        )
        if r.ok:
            for hit in r.json().get("hits", []):
                results.append({
                    "title": hit.get("title", "")[:120],
                    "snippet": hit.get("story_text", "")[:200] or hit.get("title", ""),
                    "url": hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID','')}"),
                    "source": "hackernews",
                })
    except Exception as e:
        log.warning(f"HN fallback search failed: {e}")
    return results


# ─────────────────────────────────────────────
# PERSONA SYSTEM PROMPTS
# ─────────────────────────────────────────────

PERSONAS = {
    "a2": {
        "name": "Lt Col Marcus 'Wraith' Dembe — A2 Research & Market Intelligence",
        "system": """You are Lt Col Marcus 'Wraith' Dembe, A2 Research & Market Intelligence for Thunderbird OS at Dreams2Memories Travel.

Your job in the incubator pipeline: read nightly research findings and classify each one.

Classification rules:
- INTEGRATE: Closes a real gap Thunderbird has. Buildable in our stack. Clear D2M value.
- WATCH: Interesting but not ready — technology too immature, unclear fit, or needs more research. Revisit in 30 days.
- REJECT: Not relevant to our architecture or clients. Archive.

For each INTEGRATE item, provide:
1. The gap it closes (specific — not "improves AI")
2. Which Thunderbird component it would enhance
3. Risk level: LOW / MED / HIGH
4. Whether it needs SSS (Commander decision): YES if client-facing, new cost, or architectural

Output as structured JSON array. Speak in confidence levels. Evidence first.""",
    },
    "elon": {
        "name": "A12 ELON — Innovation & Disruption",
        "system": """You are ELON, A12 Innovation & Disruption for Thunderbird OS.

Your job: take every INTEGRATE item from A2's intake and write a build ticket.

For each item produce:
- WHAT: One sentence — what capability we're adding
- WHY: The gap it closes (from A2's analysis)
- HOW: Specific implementation path — which file, which function, what API or library
- EFFORT: LOW (< 2hrs) / MED (2-8hrs) / HIGH (> 8hrs)
- SSS_REQUIRED: true/false — true if touches client-facing systems, new cost, or architectural change
- ELON_NOTE: Your irreverent take — is this worth it or are we over-engineering?

Be direct. Be specific. Name files. Name functions. No hand-waving.""",
    },
    "a5": {
        "name": "Lt Col Ryan 'Viper' Castillo — A5 Strategy & Business Growth",
        "system": """You are Lt Col Ryan 'Viper' Castillo, A5 Strategy & Business Growth for Thunderbird OS.

Your job: strategic fit check on ELON's build queue.

For each item, answer ONE question: does this integration serve the platform play or distract from it?

Thunderbird's dual mandate:
1. Legendary travel advisor for current clients
2. AI capability incubator — proof-of-concept for horizontal enterprise AI patterns

Rate each item:
- ACCELERATES: Builds platform capability AND helps current clients
- SERVES_CLIENTS: Good for clients, limited platform value
- PLATFORM_ONLY: Platform value, no current client benefit — defer until client load allows
- DISTRACTION: Neither — cut it

Fast, decisive. OODA-loop thinking.""",
    },
    "a9": {
        "name": "Victor 'Vic' Harlan — A9 Finance & Process Improvement",
        "system": """You are Victor 'Vic' Harlan, A9 Finance & Process Improvement for Thunderbird OS.

Your job: cost and ROI check on every build ticket.

For each item flag:
- NEW_COST: Does this require a new paid API, service, or subscription? YES/NO + estimated $/month
- BUILD_COST: Rough time cost in Claude API tokens or dev hours
- ROI: What does this return? Client retention? Revenue? Automation savings?
- VERDICT: APPROVED / FLAG_FOR_COMMANDER / REJECT

If it costs money we don't have a budget for, say so. Bluntly. Call waste what it is.""",
    },
    "cos": {
        "name": "Ms. Victoria 'Victory' Hale, SES-6 — Chief of Staff",
        "system": """You are Ms. Victoria 'Victory' Hale, SES-6, Chief of Staff of Thunderbird OS.

Your job: synthesize the full staff review of tonight's incubator findings into a Commander brief.

Inputs you will receive: A2 classification, ELON tickets, A5 strategic fit, A9 cost check.

Output:
1. RECOMMENDED BUILDS (ready to execute — ELON has authority under SO-1 for LOW effort, no SSS required)
2. SSS REQUIRED (needs Commander decision — list each with the specific question)
3. WATCH LIST (30-day defer — one line each)
4. REJECTED (archived — one line each)
5. COMMANDER'S CALL (the one decision only Commander can make today)

Measured, authoritative. Never raise your voice. Lead with the recommendation.""",
    },
}


def _persona_call(persona_key: str, prompt: str, max_tokens: int = 1500, model_tier: Optional[str] = None) -> str:
    """Call persona with optional model routing.

    Args:
        persona_key: Which persona to consult
        prompt: The prompt/task
        max_tokens: Max output tokens
        model_tier: Optional model tier from router (e.g., "grok_2m"). If None, uses Claude CLI.
    """
    p = PERSONAS[persona_key]
    log.info(f"Consulting {p['name']}")

    # If model_tier specified, route to OpenRouter
    if model_tier:
        model_config = route_model(model_tier)
        model_id = model_config.get("model_id")
        log.info(f"  → Routed to {model_tier}: {model_id}")
        return _call_openrouter(prompt, p["system"], model_id, max_tokens)

    # Otherwise use Claude CLI
    return _call_claude(prompt, p["system"], max_tokens)


# ─────────────────────────────────────────────
# PHASE 1 — 18:30: Execute research (fixed Thunderbird focus)
# ─────────────────────────────────────────────

def phase_execute():
    if _check_sentinel("execute"):
        log.info("Execute already complete for today — skipping")
        return
    log.info("PHASE: execute (18:30)")
    queries = _get_daily_queries()
    results = []

    for q in queries:
        found = _web_search(q, n=6)
        for item in found:
            item["query"] = q
            results.append(item)
        log.info(f"  '{q}' → {len(found)} results")

    try:
        r = requests.post(
            f"{REST_API_URL}/api/tool/innovation_daily_scan",
            headers={"x-api-key": REST_API_KEY},
            json={},
            timeout=90,
        )
        if r.ok:
            data = r.json()
            findings = data.get("findings", []) if isinstance(data, dict) else []
            for item in findings[:25]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("description", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", "innovation_scan"),
                    "score": item.get("score", 0),
                    "query": "innovation_scan",
                })
            log.info(f"  Innovation scan → {len(findings)} findings")
        else:
            log.warning(f"Innovation scan API returned {r.status_code}")
    except Exception as e:
        log.warning(f"Innovation scan REST call failed: {e}")

    raw_file = _today_raw_file()
    raw_file.write_text(json.dumps(results, indent=2, default=str))
    _write_sentinel("execute")
    log.info(f"Execute complete: {len(results)} signals → {raw_file.name}")





# ─────────────────────────────────────────────
# PHASE 3 — 19:30: Review + set AM categories
# ─────────────────────────────────────────────

def phase_evening_review():
    if _check_sentinel("evening_review"):
        log.info("Evening review already complete for today — skipping")
        return
    if not _check_sentinel("execute"):
        log.error("Execute sentinel not found — aborting evening review")
        _send_telegram("🚫 *INCUBATOR EVENING REVIEW ABORTED* — execute phase did not complete. Check logs.")
        return

    log.info("PHASE: evening_review (20:00)")
    today = date.today().isoformat()
    raw_file = _today_raw_file()
    last_review = _load_last_review()

    if not raw_file.exists() or not raw_file.stat().st_size > 10:
        log.warning("No raw execute data found — skipping evening review")
        return

    raw_data = json.loads(raw_file.read_text())
    if not raw_data:
        _send_telegram(f"🌙 *Incubator — {today}* — 0 signals gathered. No review needed.")
        _write_sentinel("evening_review")
        return

    signal_text = "\n".join(
        f"[{i+1}] {s.get('title','')}: {s.get('snippet','')[:150]} ({s.get('source','')})"
        for i, s in enumerate(raw_data[:30])
    )

    # ── A2 Dembe classify ──
    classification_json = _persona_call("a2", f"""Classify these incubator findings for the Thunderbird build queue.

SIGNALS TO CLASSIFY:
{signal_text}

KNOWN THUNDERBIRD GAPS (from last review):
{last_review[:1000]}

Return a JSON array. Each item:
{{
  "id": "A2-{today}-001",
  "title": "short name",
  "source_signal": "signal title from list",
  "classification": "INTEGRATE|WATCH|REJECT",
  "gap_closed": "specific capability Thunderbird lacks",
  "thunderbird_component": "which module this enhances",
  "risk": "LOW|MED|HIGH",
  "sss_required": true/false,
  "rationale": "one sentence"
}}

JSON only. No preamble.""", max_tokens=2500)

    try:
        match = re.search(r'\[.*\]', classification_json, re.DOTALL)
        items = json.loads(match.group() if match else classification_json)
    except Exception as e:
        log.error(f"A2 JSON parse failed: {e}")
        items = []

    intake_file = INTEL_DIR / f"incubator_a2_intake_{today}.json"
    intake_file.write_text(json.dumps(items, indent=2))
    integrates = [i for i in items if i.get("classification") == "INTEGRATE"]
    log.info(f"A2: {len(integrates)} INTEGRATE · {len([i for i in items if i.get('classification')=='WATCH'])} WATCH · {len([i for i in items if i.get('classification')=='REJECT'])} REJECT")

    if not integrates:
        _send_telegram(f"🌙 *Incubator Evening Review — {today}*\n\nA2 classified {len(items)} signals — 0 INTEGRATE items. No builds tonight.")
        _write_sentinel("evening_review")
        return

    # ── ELON tickets ──
    elon_output = _persona_call("elon", f"""Write build tickets for these INTEGRATE items.

ITEMS FROM A2:
{json.dumps(integrates, indent=2)}

For each item produce a ticket. JSON array:
{{
  "id": "ELON-{today}-001",
  "a2_id": "A2 item id",
  "title": "capability name",
  "what": "one sentence — what we're adding",
  "why": "gap closed",
  "how": "specific file, function, API or library to use",
  "effort": "LOW|MED|HIGH",
  "allowlisted": true/false,
  "elon_note": "irreverent one-liner"
}}

JSON only.""", max_tokens=2500)

    try:
        match = re.search(r'\[.*\]', elon_output, re.DOTALL)
        tickets = json.loads(match.group() if match else elon_output)
    except Exception as e:
        log.error(f"ELON JSON parse failed: {e}")
        tickets = []

    # ── A5 strategic fit ──
    a5_output = _persona_call("a5", f"""Strategic fit check on these build tickets.

ELON TICKETS:
{json.dumps(tickets, indent=2)[:2000]}

Rate each: ACCELERATES / SERVES_CLIENTS / PLATFORM_ONLY / DISTRACTION
JSON: [{{"id": "ELON id", "fit": "rating", "note": "one sentence"}}]
JSON only.""")
    try:
        match = re.search(r'\[.*\]', a5_output, re.DOTALL)
        a5_ratings = json.loads(match.group() if match else a5_output)
    except Exception:
        a5_ratings = []

    # ── A9 cost check ──
    a9_output = _persona_call("a9", f"""Cost and ROI check on these build tickets.

TICKETS:
{json.dumps(tickets, indent=2)[:2000]}

JSON: [{{"id": "ELON id", "new_cost": "YES/NO + $/mo", "build_cost": "est hours", "roi": "what it returns", "verdict": "APPROVED|FLAG|REJECT"}}]
JSON only.""")
    try:
        match = re.search(r'\[.*\]', a9_output, re.DOTALL)
        a9_checks = json.loads(match.group() if match else a9_output)
    except Exception:
        a9_checks = []

    # ── COS synthesis ──
    cos_brief = _persona_call("cos", f"""Synthesize the full staff review into a Commander brief.

A2 INTAKE ({len(integrates)} INTEGRATE items):
{json.dumps(integrates, indent=2)[:800]}

ELON TICKETS:
{json.dumps(tickets, indent=2)[:800]}

A5 STRATEGIC FIT:
{json.dumps(a5_ratings, indent=2)[:600]}

A9 COST CHECK:
{json.dumps(a9_checks, indent=2)[:600]}

Output:
1. RECOMMENDED BUILDS (ELON executes under SO-1 — allowlisted dirs only)
2. SSS REQUIRED (Commander decision needed — one line each)
3. WATCH LIST (30-day defer)
4. COMMANDER'S CALL (one decision only he can make)""", max_tokens=2000)

    # ── Save review doc ──
    review_md = f"""---
title: Incubator Evening Review — {today}
date: {today}
author: COS Hale — AI Integration Specialist
tags: [incubator, integration, builds]
---

# THUNDERBIRD INCUBATOR EVENING REVIEW — {today}

{cos_brief}

---
*Builds started: {len([t for t in tickets if _is_allowlisted(t)])}*
*SSS required: {len([t for t in tickets if not _is_allowlisted(t)])}*
*COS Hale · {datetime.now().strftime('%d %b %Y %H:%M MT')}*
"""
    review_file = INTEL_DIR / f"incubator_review_{today}.md"
    review_file.write_text(review_md)
    LAST_REVIEW_FILE.write_text(review_md)

    # ── Save full package + upload to Drive ──
    package = {
        "date": today,
        "raw_signals": len(raw_data),
        "a2_classifications": items,
        "elon_tickets": tickets,
        "a5_ratings": a5_ratings,
        "a9_checks": a9_checks,
        "cos_brief": cos_brief,
    }
    package_file = INTEL_DIR / f"incubator_package_{today}.json"
    package_file.write_text(json.dumps(package, indent=2, default=str))

    drive_link = ""
    try:
        dl = _upload_to_drive(package_file)
        if dl:
            drive_link = dl
            log.info(f"Package uploaded to Drive: {dl}")
        else:
            log.warning("Drive upload returned no link")
    except Exception as e:
        log.error(f"Drive upload failed: {e}")

    # ── Update build queue JSON ──
    queue = _load_build_queue()
    for t in tickets:
        a5 = next((r for r in a5_ratings if r.get("id") == t.get("id")), {})
        a9 = next((c for c in a9_checks if c.get("id") == t.get("id")), {})
        queue.append({
            "id": t.get("id", ""),
            "title": t.get("title", ""),
            "what": t.get("what", ""),
            "why": t.get("why", ""),
            "how": t.get("how", ""),
            "effort": t.get("effort", ""),
            "allowlisted": _is_allowlisted(t),
            "a5_fit": a5.get("fit", ""),
            "a9_verdict": a9.get("verdict", ""),
            "status": "running" if _is_allowlisted(t) else "queued",
            "date": today,
        })
    _save_build_queue(queue)

    # ── Build markdown queue file for reference ──
    new_entries = []
    for t in tickets:
        a5 = next((r for r in a5_ratings if r.get("id") == t.get("id")), {})
        a9 = next((c for c in a9_checks if c.get("id") == t.get("id")), {})
        entry = f"""
### {t.get('id', 'ELON-?')} — {t.get('title', 'Untitled')}
- **Status:** {'🟢 BUILDING' if _is_allowlisted(t) else '🟡 QUEUED'}
- **Date:** {today}
- **What:** {t.get('what', '')}
- **Why:** {t.get('why', '')}
- **How:** {t.get('how', '')}
- **Effort:** {t.get('effort', '?')} · **Allowlisted:** {'YES' if _is_allowlisted(t) else 'NO'}
- **A5 Fit:** {a5.get('fit', '?')} — {a5.get('note', '')}
- **A9:** {a9.get('verdict', '?')} — {a9.get('new_cost', '')} · ROI: {a9.get('roi', '')}
- **ELON:** _{t.get('elon_note', '')}_
"""
        new_entries.append(entry)
    BUILD_QUEUE_FILE.write_text("\n".join(new_entries))

    # ── Start overnight builds (allowlisted dirs only) ──
    auto_builds = [t for t in tickets if _is_allowlisted(t)]
    queued_builds = [t for t in tickets if not _is_allowlisted(t)]
    for t in auto_builds:
        unit = _spawn_build_unit(t)
        log.info(f"  Starting overnight build: {unit} — {t.get('title')}")

    # ── Send single Telegram brief ──
    tg_lines = [f"🌙 *INCUBATOR EVENING REVIEW — {today}*", ""]
    tg_lines.append(f"Signals: {len(raw_data)} · INTEGRATE: {len(integrates)} · Tickets: {len(tickets)}")
    tg_lines.append("")
    tg_lines.append(cos_brief[:2000])
    tg_lines.append("")
    if auto_builds:
        tg_lines.append(f"⚡ *Overnight builds starting:* {len(auto_builds)} allowlisted items")
        for t in auto_builds:
            tg_lines.append(f"  • {t.get('title')} [{t.get('effort','?')}]")
    if queued_builds:
        tg_lines.append("")
        tg_lines.append(f"📋 *SSS required (Commander review):* {len(queued_builds)} items")
        for t in queued_builds:
            tg_lines.append(f"  • {t.get('title')} — why: {t.get('why','')[:80]}")
    if drive_link:
        tg_lines.append("")
        tg_lines.append(f"📁 [Full package]({drive_link})")
    tg_lines.append("")
    tg_lines.append(f"_Report at 06:30 with overnight results_")
    _send_telegram("\n".join(tg_lines))

    _write_sentinel("evening_review")
    log.info("Evening review complete — builds dispatched")


# ─────────────────────────────────────────────
# PHASE 3 — 06:30: Overnight build report
# ─────────────────────────────────────────────

def phase_overnight_report():
    if _check_sentinel("overnight_report"):
        log.info("Overnight report already sent for today — skipping")
        return
    log.info("PHASE: overnight_report (06:30)")
    today = date.today().isoformat()

    queue = _load_build_queue()
    yesterday_queue = [b for b in queue if b.get("date", "").startswith((date.today() - timedelta(days=1)).isoformat()[:10])]

    if not yesterday_queue:
        _send_telegram(f"☀️ *Incubator Morning Report — {today}*\n\nNo builds from last night. Check evening review for queued items.")
        _write_sentinel("overnight_report")
        return

    completed = [b for b in yesterday_queue if b.get("status") == "success"]
    failed = [b for b in yesterday_queue if b.get("status") == "failed"]
    running = [b for b in yesterday_queue if b.get("status") == "running"]
    queued = [b for b in yesterday_queue if b.get("status") == "queued"]

    report_lines = [f"THUNDERBIRD INCUBATOR — Overnight Build Report — {today}", ""]
    report_lines.append(f"Total builds: {len(yesterday_queue)}")
    report_lines.append(f"  ✅ Completed: {len(completed)}")
    report_lines.append(f"  ❌ Failed: {len(failed)}")
    report_lines.append(f"  ⏳ Still running: {len(running)}")
    report_lines.append(f"  📋 Queued (SSS pending): {len(queued)}")
    report_lines.append("")

    if completed:
        report_lines.append("=== SUCCESSFUL BUILDS ===")
        for b in completed:
            report_lines.append(f"  ✅ {b.get('title','')} — OPR: {b.get('effort','?')}")
    if failed:
        report_lines.append("")
        report_lines.append("=== FAILED BUILDS ===")
        for b in failed:
            report_lines.append(f"  ❌ {b.get('title','')}")
    if running:
        report_lines.append("")
        report_lines.append("=== STILL RUNNING ===")
        for b in running:
            report_lines.append(f"  ⏳ {b.get('title','')}")
    if queued:
        report_lines.append("")
        report_lines.append("=== QUEUED (SSS REQUIRED) ===")
        for b in queued:
            report_lines.append(f"  📋 {b.get('title','')} — {b.get('a5_fit','')}")

    report_text = "\n".join(report_lines)

    # ── Gmail token precheck ──
    gmail_ok = _check_gmail_token()
    if gmail_ok:
        try:
            sys.path.insert(0, str(Path("/home/john/Thunderbird")))
            from core.email.thunderbird_gmail import gmail_send_from_wing
            email_body = f"""Incubator Overnight Build Report — {today}

{report_text}

Full package: intel/incubator_package_{(date.today() - timedelta(days=1)).isoformat()}.json"""
            result = gmail_send_from_wing(
                to="johnloucks3@gmail.com",
                subject=f"THUNDERBIRD INCUBATOR — Overnight Build Report — {today}",
                body=email_body,
            )
            if result.get("status") == "success":
                log.info(f"Morning brief sent via Gmail: {result.get('message_id')}")
            else:
                log.error(f"Gmail send failed: {result}")
        except Exception as e:
            log.error(f"Gmail send error: {e}")
            fallback = INTEL_DIR / f"incubator_brief_{today}.md"
            fallback.write_text(report_text)
            log.info(f"Brief saved to {fallback.name} as Gmail fallback")
    else:
        fallback = INTEL_DIR / f"incubator_brief_{today}.md"
        fallback.write_text(report_text)
        log.info(f"Gmail token invalid — brief saved to {fallback.name}")

    # ── Telegram brief to D2MC2C ──
    tg_msg = "\n".join([
        f"☀️ *INCUBATOR MORNING REPORT — {today}*", "",
        f"✅ Completed: {len(completed)} · ❌ Failed: {len(failed)} · ⏳ Running: {len(running)} · 📋 Queued: {len(queued)}", "",
    ])
    if completed:
        tg_msg += "✅ *Built:*\n" + "\n".join(f"• {b.get('title','')}" for b in completed[:5]) + "\n"
    if failed:
        tg_msg += "\n❌ *Failed:*\n" + "\n".join(f"• {b.get('title','')}" for b in failed[:3]) + "\n"
    if running:
        tg_msg += "\n⏳ *Still running:*\n" + "\n".join(f"• {b.get('title','')}" for b in running[:3]) + "\n"
    if queued:
        tg_msg += "\n📋 *SSS pending:*\n" + "\n".join(f"• {b.get('title','')}" for b in queued[:5])

    _send_telegram(tg_msg)
    _write_sentinel("overnight_report")
    log.info("Overnight report complete — sent via Gmail + Telegram")


def _is_allowlisted(ticket: dict) -> bool:
    how = (ticket.get("how", "") or "").lower()
    return any(d in how for d in ALLOWLIST_DIRS)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

PHASES = {
    "execute":   phase_execute,
    "evening_review": phase_evening_review,
    "overnight_report": phase_overnight_report,
}

def main():
    parser = argparse.ArgumentParser(description="Thunderbird AI Incubator Pipeline")
    parser.add_argument("phase", choices=list(PHASES.keys()), help="Pipeline phase to run")
    args = parser.parse_args()
    log.info(f"━━━ Incubator phase: {args.phase} ━━━")
    PHASES[args.phase]()
    log.info(f"━━━ Phase {args.phase} complete ━━━")

if __name__ == "__main__":
    main()

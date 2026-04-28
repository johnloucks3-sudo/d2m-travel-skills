#!/usr/bin/env python3
"""
Thunderbird AI Incubator — Full Pipeline
Standing Order: Commander John "Yoda" Loucks, 24 MAR 2026

EVENING CYCLE (sets tomorrow AM):
  prompt   18:30 — COS generates tonight's research question
  execute  19:00 — Full tool stack research run
  review   19:30 — Synthesize, classify, set AM categories

MORNING CYCLE (deepens last night's findings):
  am_scrape  07:00 — Deep dive on categories set by previous evening
  a2_intake  07:30 — A2 Dembe classifies: INTEGRATE / WATCH / REJECT
  elon_queue 07:45 — ELON tickets every INTEGRATE item, flags SSS if needed

CREW RELATIONSHIPS:
  A2 Dembe   → intake officer, classifies all findings
  A12 ELON   → build queue owner, writes implementation specs
  A5 Castillo → strategic fit check (flags if distraction from platform play)
  A9 Harlan  → cost/ROI (flags if new API cost or dependency)
  EXEC Naia  → brand gate (flags if touches client-facing output)
  COS Hale   → synthesizes all, routes to SSS or direct Commander brief
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
            return f"[Claude CLI error: exit {result.returncode}]"
        return result.stdout.strip()
    except Exception as e:
        log.error(f"Claude subprocess error: {e}")
        return f"[Error calling Claude: {e}]"


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


def _web_search(query: str, n: int = 5) -> list:
    """Search using duckduckgo_search library (real web results, no API key needed).
    Replaced broken DDG Instant Answer API + missing REST /search endpoint.
    2026-03-27 COS fix — Root Cause Imperative."""
    results = []
    try:
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
        "name": "Col Victoria 'Iron Vic' Hale — Chief of Staff",
        "system": """You are Col Victoria 'Iron Vic' Hale, Chief of Staff of Thunderbird OS.

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
# PHASE 1 — 18:30: Prompt generation
# ─────────────────────────────────────────────

def phase_prompt():
    log.info("PHASE: prompt (18:30)")
    am_cats = _load_am_categories()
    last_review = _load_last_review()
    digest = _load_file(INTEL_DIR / "daily_innovation_digest.md", 2000)

    suggestion = _persona_call("cos", f"""Generate tonight's incubator research prompt.

LAST EVENING'S GAPS (what we found we can't do):
{last_review[:1500] or 'None yet — first run.'}

AM CATEGORIES SET LAST NIGHT (what we planned to deep-dive today):
{json.dumps(am_cats) if am_cats else 'None set.'}

TODAY'S AM DIGEST (what surfaced this morning):
{digest[:1000] or 'Not available.'}

Suggest ONE sector focus for tonight. Name the specific gap we're hunting.
Name the tools to use. Name what the AM categories should be after this run.
Be specific. Commander reads this at 18:30 and either approves or adjusts.""")

    msg = f"""🔬 *INCUBATOR — Tonight's Prompt*
_{datetime.now().strftime('%a %d %b · %H:%M MT')}_

{suggestion}

---
_Execute begins 19:00 · Review at 19:30_"""
    _send_telegram(msg)
    log.info("Prompt delivered to Commander")


# ─────────────────────────────────────────────
# PHASE 2 — 19:00: Execute research
# ─────────────────────────────────────────────

def phase_execute():
    log.info("PHASE: execute (19:00)")
    am_cats = _load_am_categories()

    # Validation: filter out empty/whitespace-only categories, enforce ≥3 chars per term
    valid_cats = []
    for cat in am_cats:
        cat_clean = cat.strip()
        if cat_clean:
            terms = [t for t in cat_clean.split() if len(t) >= 3]
            if len(terms) >= 2:  # Need at least 2 meaningful terms
                valid_cats.append(cat_clean)

    queries = (
        [f"{c} AI enterprise integration 2026" for c in valid_cats[:4]]
        if valid_cats else [
            "AI between-transaction client engagement proactive 2026",
            "behavioral preference inference implicit learning enterprise 2026",
            "life event triggered AI proactive outreach CRM 2026",
            "cross-session preference compounding AI relationship management 2026",
        ]
    )

    results = []

    # Web searches — one per category
    for q in queries:
        found = _web_search(q, n=6)
        for item in found:
            item["query"] = q
            results.append(item)
        log.info(f"  '{q}' → {len(found)} results")

    # Innovation scan via REST API tool endpoint (fixed: was /innovation/scan which doesn't exist)
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
    log.info(f"Execute complete: {len(results)} signals → {raw_file.name}")

    _send_telegram(
        f"⚙️ *Incubator Execute done* — {len(results)} signals\n"
        f"_Categories: {', '.join(am_cats[:3]) if am_cats else 'default'}_\n"
        f"_Review synthesis at 19:30_"
    )


# ─────────────────────────────────────────────
# PHASE 3 — 19:30: Review + set AM categories
# ─────────────────────────────────────────────

def phase_review():
    log.info("PHASE: review (19:30)")
    today = date.today().isoformat()
    raw_file = _today_raw_file()
    last_review = _load_last_review()

    raw_summary = "No raw data found."
    raw_count = 0
    if raw_file.exists():
        raw_data = json.loads(raw_file.read_text())
        raw_count = len(raw_data)
        raw_summary = "\n".join(
            f"- [{r.get('title','(no title)')}] {r.get('snippet','')[:120]}"
            for r in raw_data[:30]
        )

    synthesis = _persona_call("cos", f"""Synthesize tonight's incubator research.

SIGNALS GATHERED ({raw_count} total):
{raw_summary}

PRIOR GAPS (don't repeat — build forward):
{last_review[:1200] or 'None — first run.'}

Output:
1. VERDICT (1 sentence — core gap tonight revealed)
2. TOP GAPS (each: gap name, industry that proved it, why it matters to D2M)
3. INTEGRATION PRIORITY (which gap to build first)
4. AM CATEGORIES FOR TOMORROW (3-5 specific topics for morning deep scrape)
5. COMMANDER INSIGHT (the one thing that changes how we see ourselves)

Integration specialist lens. No self-congratulation. Find what we can't do.""", max_tokens=2500, model_tier="grok_2m")

    # Extract AM categories
    am_cats = []
    lines = synthesis.split("\n")
    in_cats = False
    for line in lines:
        if "AM CATEGORIES" in line.upper():
            in_cats = True
            continue
        if in_cats:
            clean = line.strip().lstrip("0123456789.-•* ").strip()
            # Validation: skip empty/whitespace-only, enforce 5 < len < 100, require ≥3 chars per term
            if clean and 5 < len(clean) < 100:
                # Verify all terms in the category are ≥3 chars to prevent garbage queries
                terms = [t for t in clean.split() if len(t) >= 3]
                if len(terms) >= 2:  # Need at least 2 meaningful terms
                    am_cats.append(clean)
            if len(am_cats) >= 5:
                break
            if line.strip() == "" and am_cats:
                break

    if not am_cats:
        am_cats = ["AI proactive client engagement", "behavioral preference inference", "life event trigger CRM", "cross-transaction memory compounding"]

    _save_am_categories(am_cats, rationale=f"Set by incubator review {today}")

    review_md = f"""---
title: Incubator Review — {today}
date: {today}
author: COS Hale — AI Integration Specialist
am_categories: {json.dumps(am_cats)}
tags: [incubator, integration, gaps]
---

# THUNDERBIRD INCUBATOR REVIEW — {today}

{synthesis}

---
*AM Scrape categories set: {', '.join(am_cats)}*
*Pipeline: AM Scrape 07:00 → A2 Intake 07:30 → ELON Queue 07:45*
*COS Hale · {datetime.now().strftime('%d %b %Y %H:%M MT')}*
"""
    review_file = INTEL_DIR / f"incubator_review_{today}.md"
    review_file.write_text(review_md)
    LAST_REVIEW_FILE.write_text(review_md)
    log.info(f"Review saved: {review_file.name}")

    tg_body = synthesis[:3200] + ("…" if len(synthesis) > 3200 else "")
    _send_telegram(f"""🧪 *INCUBATOR REVIEW — {today}*

{tg_body}

---
📅 *AM scrape categories:*
{chr(10).join(f'  • {c}' for c in am_cats)}

_A2 intake at 07:30 · ELON queue at 07:45_""")


# ─────────────────────────────────────────────
# PHASE 4 — 07:00: AM deep scrape
# ─────────────────────────────────────────────

def phase_am_scrape():
    log.info("PHASE: am_scrape (07:00)")
    am_cats = _load_am_categories()

    if not am_cats:
        log.warning("No AM categories set — using defaults")
        am_cats = ["AI client engagement between transactions", "preference learning AI enterprise"]

    # Validation: filter out empty/whitespace-only categories, enforce ≥3 chars per term
    valid_cats = []
    for cat in am_cats:
        cat_clean = cat.strip()
        if cat_clean:
            terms = [t for t in cat_clean.split() if len(t) >= 3]
            if len(terms) >= 2:  # Need at least 2 meaningful terms
                valid_cats.append(cat_clean)

    if not valid_cats:
        log.warning("All AM categories failed validation — using defaults")
        valid_cats = ["AI client engagement between transactions", "preference learning AI enterprise"]

    results = []
    for cat in valid_cats:
        # Targeted academic + practitioner searches
        for suffix in ["academic research arxiv 2026", "enterprise implementation case study 2026", "open source tool github 2026"]:
            # Double-check query terms before calling _web_search
            query = f"{cat} {suffix}"
            if query.strip() and all(len(t) >= 3 for t in query.split()[:2]):
                found = _web_search(query, n=4)
                for item in found:
                    item["category"] = cat
                    item["query_type"] = suffix
                    results.append(item)
            else:
                log.warning(f"  Skipped malformed query: '{query}'")
        log.info(f"  Category '{cat}' → {len([r for r in results if r.get('category') == cat])} results")

    # Academic scan via REST API tool endpoint (fixed: was /academic/scan which doesn't exist)
    try:
        r = requests.post(
            f"{REST_API_URL}/api/tool/academic_scan",
            headers={"x-api-key": REST_API_KEY},
            json={"topics": am_cats, "max": 10},
            timeout=90,
        )
        if r.ok:
            data = r.json()
            papers = data.get("papers", []) if isinstance(data, dict) else []
            for p in papers:
                results.append({"title": p.get("title", ""), "snippet": p.get("abstract", "")[:200], "url": p.get("url", ""), "source": "academic", "category": "academic"})
            log.info(f"  Academic scan → {len(papers)} papers")
        else:
            log.warning(f"Academic scan API returned {r.status_code}")
    except Exception as e:
        log.warning(f"Academic scan failed: {e}")

    am_raw = INTEL_DIR / f"incubator_am_raw_{date.today().isoformat()}.json"
    am_raw.write_text(json.dumps(results, indent=2, default=str))
    log.info(f"AM scrape complete: {len(results)} signals → {am_raw.name}")


# ─────────────────────────────────────────────
# PHASE 5 — 07:30: A2 intake + classification
# ─────────────────────────────────────────────

def phase_a2_intake():
    log.info("PHASE: a2_intake (07:30)")
    today = date.today().isoformat()
    last_review = _load_last_review()

    # Load both nightly review and AM scrape
    am_raw_file = INTEL_DIR / f"incubator_am_raw_{today}.json"
    evening_raw_file = INTEL_DIR / f"incubator_raw_{(date.today() - timedelta(days=1)).isoformat()}.json"

    signals = []
    if am_raw_file.exists():
        signals += json.loads(am_raw_file.read_text())[:25]
    if evening_raw_file.exists():
        signals += json.loads(evening_raw_file.read_text())[:15]

    if not signals:
        log.warning("No signals to classify — A2 intake skipped")
        return

    signal_text = "\n".join(
        f"[{i+1}] {s.get('title','')}: {s.get('snippet','')[:150]} ({s.get('source','')})"
        for i, s in enumerate(signals[:30])
    )

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

    # Parse JSON from response
    try:
        # Extract JSON array from response
        match = re.search(r'\[.*\]', classification_json, re.DOTALL)
        if match:
            items = json.loads(match.group())
        else:
            items = json.loads(classification_json)
    except json.JSONDecodeError as e:
        log.error(f"A2 JSON parse failed: {e}\nRaw: {classification_json[:300]}")
        items = []

    # Save classification
    intake_file = INTEL_DIR / f"incubator_a2_intake_{today}.json"
    intake_file.write_text(json.dumps(items, indent=2))
    log.info(f"A2 classified {len(items)} items → {intake_file.name}")

    integrates = [i for i in items if i.get("classification") == "INTEGRATE"]
    watches = [i for i in items if i.get("classification") == "WATCH"]
    rejects = [i for i in items if i.get("classification") == "REJECT"]
    log.info(f"  INTEGRATE: {len(integrates)} · WATCH: {len(watches)} · REJECT: {len(rejects)}")


# ─────────────────────────────────────────────
# PHASE 6 — 07:45: ELON queue + full staff review
# ─────────────────────────────────────────────

def phase_elon_queue():
    log.info("PHASE: elon_queue (07:45)")
    today = date.today().isoformat()

    intake_file = INTEL_DIR / f"incubator_a2_intake_{today}.json"
    if not intake_file.exists():
        log.warning("No A2 intake found — ELON queue skipped")
        return

    all_items = json.loads(intake_file.read_text())
    integrates = [i for i in all_items if i.get("classification") == "INTEGRATE"]

    if not integrates:
        log.info("No INTEGRATE items — queue empty today")
        _send_telegram(f"🤖 *Incubator — {today}*\nA2 found 0 INTEGRATE items today.\n_{len(all_items)} signals classified, all WATCH/REJECT._")
        return

    integrate_text = json.dumps(integrates, indent=2)

    # ELON tickets
    elon_output = _persona_call("elon", f"""Write build tickets for these INTEGRATE items.

ITEMS FROM A2:
{integrate_text}

For each item produce a ticket. JSON array:
{{
  "id": "ELON-{today}-001",
  "a2_id": "A2 item id",
  "title": "capability name",
  "what": "one sentence — what we're adding",
  "why": "gap closed",
  "how": "specific file, function, API or library to use",
  "effort": "LOW|MED|HIGH",
  "sss_required": true/false,
  "elon_note": "irreverent one-liner"
}}

JSON only.""", max_tokens=2500)

    try:
        match = re.search(r'\[.*\]', elon_output, re.DOTALL)
        tickets = json.loads(match.group() if match else elon_output)
    except Exception as e:
        log.error(f"ELON JSON parse failed: {e}")
        tickets = []

    # A5 strategic fit
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

    # A9 cost check
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

    # COS synthesis
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
1. RECOMMENDED BUILDS (ELON executes under SO-1 — LOW effort, no SSS)
2. SSS REQUIRED (Commander decision needed — one line each with the question)
3. WATCH LIST (30-day defer)
4. COMMANDER'S CALL (one decision only he can make)""", max_tokens=2000)

    # Update build queue file
    queue_content = BUILD_QUEUE_FILE.read_text() if BUILD_QUEUE_FILE.exists() else ""
    new_entries = []
    for t in tickets:
        a5 = next((r for r in a5_ratings if r.get("id") == t.get("id")), {})
        a9 = next((c for c in a9_checks if c.get("id") == t.get("id")), {})
        entry = f"""
### {t.get('id', 'ELON-?')} — {t.get('title', 'Untitled')}
- **Status:** 🟡 PENDING
- **Date:** {today}
- **What:** {t.get('what', '')}
- **Why:** {t.get('why', '')}
- **How:** {t.get('how', '')}
- **Effort:** {t.get('effort', '?')} · **SSS:** {'YES' if t.get('sss_required') else 'NO'}
- **A5 Fit:** {a5.get('fit', '?')} — {a5.get('note', '')}
- **A9:** {a9.get('verdict', '?')} — {a9.get('new_cost', '')} · ROI: {a9.get('roi', '')}
- **ELON:** _{t.get('elon_note', '')}_
"""
        new_entries.append(entry)

    # Insert new entries into queue under ACTIVE QUEUE section
    updated_queue = queue_content.replace(
        "*First entries will appear after Night 1 AM scrape (25 MAR 2026 07:30)*",
        "\n".join(new_entries)
    ) if "*First entries will appear" in queue_content else queue_content + "\n".join(new_entries)

    BUILD_QUEUE_FILE.write_text(updated_queue)
    log.info(f"Build queue updated: {len(tickets)} tickets added")

    # Send COS brief to Commander
    sss_items = [t for t in tickets if t.get("sss_required")]
    elon_executes = [t for t in tickets if not t.get("sss_required") and t.get("effort") == "LOW"]

    _send_telegram(f"""🏗️ *INCUBATOR STAFF REVIEW — {today}*

{cos_brief[:3000]}

---
⚡ *ELON executing now (SO-1):* {len(elon_executes)} LOW-effort items
📋 *SSS required:* {len(sss_items)} items pending Commander
📁 *Full queue:* intel/elon\\_build\\_queue.md""")

    # Auto-execute LOW effort, no-SSS items
    for t in elon_executes:
        log.info(f"  AUTO-EXECUTE (SO-1): {t.get('id')} — {t.get('title')}")
        # ELON executes under SO-1 authority — tells Commander after
        # Placeholder: actual build logic per ticket goes here
        # For now, log and notify
        _send_telegram(f"⚡ *ELON executing:* {t.get('title')}\n_{t.get('how', '')}_\n_Will confirm when done._")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

PHASES = {
    "prompt":    phase_prompt,
    "execute":   phase_execute,
    "review":    phase_review,
    "am_scrape": phase_am_scrape,
    "a2_intake": phase_a2_intake,
    "elon_queue": phase_elon_queue,
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

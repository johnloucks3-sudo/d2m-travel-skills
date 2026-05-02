#!/usr/bin/env python3
"""
Thunderbird Twitter OSINT — Grok 4.1 Fast via OpenRouter
=========================================================
Uses xAI Grok 4.1 (2M context, Twitter-native knowledge) to run
targeted OSINT sweeps on crypto and travel topics.

Grok is uniquely suited for Twitter OSINT: trained on X/Twitter data,
understands thread dynamics, knows community consensus and disputes.

Usage:
    python3 thunderbird_twitter_osint.py                  # Full sweep (5 topics)
    python3 thunderbird_twitter_osint.py --topic bitcoin  # Single topic
    python3 thunderbird_twitter_osint.py --brief          # Print latest results
    python3 thunderbird_twitter_osint.py --threads        # Deep thread harvest mode

Wire-in for daily digest:
    from thunderbird_twitter_osint import run_twitter_osint_sweep

Author: A2 Dembe — 2026-04-29
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load .env from Thunderbird root
_TB_ROOT = Path(__file__).parent.parent.parent
load_dotenv(_TB_ROOT / ".env")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if not OPENROUTER_API_KEY:
    print("ERROR: OPENROUTER_API_KEY not set", file=sys.stderr)
    sys.exit(1)

GROK_MODEL = "x-ai/grok-4.1-fast"
OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"
INTEL_DIR = _TB_ROOT / "core" / "intel" / "intel"
OUTPUT_DIR = _TB_ROOT / "output"
INTEL_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://dreams2memories.com",
    "X-Title": "Thunderbird Wing Twitter OSINT",
    "Content-Type": "application/json",
}

# ── Default OSINT Topics ────────────────────────────────────────────────────
# 3 travel + 2 crypto = 5 topics (as specified)

DEFAULT_TOPICS = [
    {
        "id": "luxury_cruise_twitter",
        "name": "Luxury Cruise Twitter",
        "domain": "travel",
        "query": (
            "What is the Twitter/X community saying right now about luxury cruises? "
            "Focus on Silversea, Regent Seven Seas, Viking, Seabourn, Oceania, Cunard, Ponant. "
            "Include: viral complaints, rave reviews, crew stories, new ship announcements, "
            "influencer threads, viral itinerary threads, price drops trending, community debates. "
            "Summarize the 5-7 most-discussed threads or topics with sentiment and engagement signals."
        ),
    },
    {
        "id": "ai_travel_booking_twitter",
        "name": "AI Travel Booking — Twitter Pulse",
        "domain": "travel",
        "query": (
            "What is the travel agent and travel industry Twitter community saying about "
            "AI-powered travel booking, AI concierge tools, and automated trip planning? "
            "Include: TA community sentiment, agency owner threads, OTA AI announcements, "
            "agent vs AI debates, tools being praised or called out. "
            "Capture any viral threads from travel advisors about AI replacing agents or helping agents."
        ),
    },
    {
        "id": "destination_trending_travel",
        "name": "Trending Destinations — Twitter",
        "domain": "travel",
        "query": (
            "What travel destinations are dominating Twitter/X right now? "
            "Look for: viral 'you must go here' threads, destination-specific community accounts, "
            "trending port calls or cruise itinerary routes, Scandinavia summer 2026 buzz, "
            "Mediterranean travel trends, Panama Canal transit discourse, "
            "any destination seeing unusual spike in discussion this week."
        ),
    },
    {
        "id": "bitcoin_twitter_pulse",
        "name": "Bitcoin & Crypto Twitter",
        "domain": "crypto",
        "query": (
            "What is Crypto Twitter saying right now in 2026? "
            "Bitcoin price action discourse, ETF narratives, institutional adoption threads, "
            "halving cycle discussions, bear vs bull debates, macro correlation arguments. "
            "Include top 3-4 memes or narratives dominating the feed. "
            "Key voices: what are the influential accounts arguing about this week?"
        ),
    },
    {
        "id": "defi_altcoin_twitter",
        "name": "DeFi & Altcoin Twitter",
        "domain": "crypto",
        "query": (
            "What DeFi protocols, layer-2 networks, and altcoins are trending on Twitter/X? "
            "Include: rug pull warnings circulating, new protocol launches getting hyped, "
            "community governance disputes, airdrop threads, yield farming strategies being debated, "
            "any tokens with unusual Twitter sentiment spike. "
            "Separate signal from noise — flag anything that looks coordinated pump/dump."
        ),
    },
]


def _call_grok(topic: dict, max_tokens: int = 800, thread_harvest: bool = False) -> dict:
    """Call Grok 4.1 via OpenRouter for Twitter OSINT on a topic."""
    t0 = time.time()

    thread_suffix = (
        "\n\nThread Harvest Mode: Go deep — reconstruct the 2-3 most viral thread structures "
        "with key replies, quote-tweets that reframed the narrative, and how the community "
        "resolved (or failed to resolve) the argument."
        if thread_harvest
        else ""
    )

    system_prompt = (
        "You are an OSINT analyst embedded in the Thunderbird Wing at Dreams2Memories Travel, LLC. "
        "You have deep knowledge of Twitter/X community dynamics, memetics, and discourse patterns. "
        "Your job: scan Twitter signal for the specified topic and return a concise intelligence brief. "
        "Format your response as JSON only. "
        "Keys required: "
        '"trending_threads" (array of 3-5 objects with keys: topic, sentiment, engagement_signal, key_voices), '
        '"dominant_narrative" (string: the #1 story/angle dominating the feed), '
        '"counter_narrative" (string: the pushback or opposing view), '
        '"d2m_relevance" (HIGH/MED/LOW with one-line rationale for a luxury travel agency), '
        '"action_signal" (string: what D2M or Commander should act on, or "MONITOR"), '
        '"sources_mentioned" (array of handles, hashtags, or URLs surfaced in the community)'
    )

    user_prompt = topic["query"] + thread_suffix

    payload = {
        "model": GROK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = requests.post(
            OPENROUTER_BASE,
            headers=HEADERS,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(raw)
        elapsed = round(time.time() - t0, 1)
        data.update({
            "topic_id": topic["id"],
            "topic_name": topic["name"],
            "domain": topic["domain"],
            "model": GROK_MODEL,
            "elapsed_s": elapsed,
            "timestamp": datetime.now().isoformat(),
            "status": "OK",
        })
        return data
    except requests.exceptions.Timeout:
        return _error_result(topic, "Timeout after 60s")
    except requests.exceptions.HTTPError as e:
        body = ""
        try:
            body = e.response.text[:200]
        except Exception:
            pass
        return _error_result(topic, f"HTTP {e.response.status_code}: {body}")
    except json.JSONDecodeError as e:
        return _error_result(topic, f"JSON parse error: {e}")
    except Exception as e:
        return _error_result(topic, str(e))


def _error_result(topic: dict, error: str) -> dict:
    return {
        "topic_id": topic["id"],
        "topic_name": topic["name"],
        "domain": topic["domain"],
        "model": GROK_MODEL,
        "status": "ERROR",
        "error": error,
        "timestamp": datetime.now().isoformat(),
        "elapsed_s": 0,
        "trending_threads": [],
        "dominant_narrative": "N/A",
        "counter_narrative": "N/A",
        "d2m_relevance": "UNKNOWN",
        "action_signal": "Retry manually.",
        "sources_mentioned": [],
    }


def run_twitter_osint_sweep(
    topics: list | None = None,
    thread_harvest: bool = False,
    max_workers: int = 5,
) -> dict:
    """
    Run Twitter OSINT sweep across all topics in parallel.

    Args:
        topics: List of topic dicts (default: DEFAULT_TOPICS)
        thread_harvest: Enable deep thread harvesting mode (slower, richer)
        max_workers: Parallel workers (default 5 = all topics at once)

    Returns:
        dict with sweep metadata and per-topic results
    """
    topics = topics or DEFAULT_TOPICS
    t0 = time.time()
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    print(
        f"[{datetime.now():%H:%M}] Twitter OSINT sweep — {len(topics)} topics "
        f"via {GROK_MODEL} {'[THREAD HARVEST]' if thread_harvest else ''}"
    )

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_call_grok, t, 1200 if thread_harvest else 800, thread_harvest): t["name"]
            for t in topics
        }
        for fut in as_completed(futures):
            name = futures[fut]
            r = fut.result()
            results.append(r)
            icon = "✅" if r["status"] == "OK" else "❌"
            rel = r.get("d2m_relevance", r.get("error", "?"))[:60]
            print(f"  {icon} [{r['domain'].upper()}] {name}: {rel} ({r['elapsed_s']}s)")

    total_elapsed = round(time.time() - t0, 1)
    ok_count = sum(1 for r in results if r["status"] == "OK")

    report = {
        "sweep_type": "twitter_osint_grok4",
        "model": GROK_MODEL,
        "timestamp": datetime.now().isoformat(),
        "topics_queried": len(topics),
        "successful": ok_count,
        "total_elapsed_s": total_elapsed,
        "thread_harvest_mode": thread_harvest,
        "results": sorted(results, key=lambda x: x["topic_id"]),
    }

    # Persist JSON
    json_path = INTEL_DIR / f"twitter_osint_{ts}.json"
    json_path.write_text(json.dumps(report, indent=2))
    (INTEL_DIR / "twitter_osint_latest.json").write_text(json.dumps(report, indent=2))

    # Persist Markdown
    md = _render_markdown(report)
    md_path = INTEL_DIR / f"twitter_osint_{ts}.md"
    md_path.write_text(md)
    (INTEL_DIR / "twitter_osint_latest.md").write_text(md)

    print(
        f"\n✅ Sweep complete — {ok_count}/{len(topics)} OK in {total_elapsed}s "
        f"{'⚡ <90s target' if total_elapsed < 90 else '⚠ exceeded 90s target'}"
    )
    print(f"   JSON: {json_path}")
    print(f"   MD:   {md_path}")
    return report


def _render_markdown(report: dict) -> str:
    ts_str = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    ok = report["successful"]
    total = report["topics_queried"]
    elapsed = report["total_elapsed_s"]
    md = f"# 🐦 TWITTER OSINT — GROK 4.1 | {ts_str}\n\n"
    md += (
        f"**Model:** {report['model']} | "
        f"**Topics:** {total} | "
        f"**Successful:** {ok}/{total} | "
        f"**Sweep time:** {elapsed}s "
        f"{'⚡' if elapsed < 90 else '⚠️'}\n\n"
    )

    # Group by domain
    for domain in ["travel", "crypto"]:
        domain_results = [r for r in report["results"] if r.get("domain") == domain]
        if not domain_results:
            continue
        md += f"## {'✈️ TRAVEL' if domain == 'travel' else '₿ CRYPTO'} TWITTER\n\n"
        for r in domain_results:
            rel = r.get("d2m_relevance", "UNKNOWN")
            icon = "🔴" if "HIGH" in str(rel) else "🟡" if "MED" in str(rel) else "🟢" if "LOW" in str(rel) else "⚪"
            md += f"### {icon} {r['topic_name']}\n"
            if r["status"] == "ERROR":
                md += f"**ERROR:** {r.get('error', 'Unknown')}\n\n"
                continue
            md += f"**Relevance to D2M:** {rel}\n\n"
            if r.get("dominant_narrative"):
                md += f"**Dominant Narrative:** {r['dominant_narrative']}\n\n"
            if r.get("counter_narrative"):
                md += f"**Counter-Narrative:** {r['counter_narrative']}\n\n"
            threads = r.get("trending_threads", [])
            if threads:
                md += "**Trending Threads:**\n"
                for t in threads:
                    if isinstance(t, dict):
                        topic_txt = t.get("topic", str(t))
                        sentiment = t.get("sentiment", "")
                        voices = t.get("key_voices", "")
                        md += f"- **{topic_txt}**"
                        if sentiment:
                            md += f" [{sentiment}]"
                        if voices:
                            md += f" — {voices}"
                        md += "\n"
                    else:
                        md += f"- {t}\n"
                md += "\n"
            if r.get("action_signal") and r["action_signal"] != "MONITOR":
                md += f"**Action Signal:** {r['action_signal']}\n\n"
            if r.get("sources_mentioned"):
                sources = r["sources_mentioned"]
                if isinstance(sources, list):
                    md += f"**Sources:** {', '.join(str(s) for s in sources[:8])}\n\n"
    return md


def get_digest_section() -> str:
    """Return a Markdown section for embedding in the intel digest."""
    latest = INTEL_DIR / "twitter_osint_latest.md"
    if not latest.exists():
        return "*(No Twitter OSINT sweep on file — run thunderbird_twitter_osint.py)*"
    content = latest.read_text()
    # Trim header, return body
    lines = content.split("\n")
    return "\n".join(lines[3:]) if len(lines) > 3 else content


def get_digest_json() -> dict | None:
    """Return latest sweep JSON for programmatic digest integration."""
    latest = INTEL_DIR / "twitter_osint_latest.json"
    if not latest.exists():
        return None
    try:
        return json.loads(latest.read_text())
    except json.JSONDecodeError:
        return None


# ── CLI / Command Endpoint ───────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Twitter OSINT via Grok 4.1 — /twitter-osint command",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 thunderbird_twitter_osint.py               # Full 5-topic sweep
  python3 thunderbird_twitter_osint.py --threads     # Deep thread harvest
  python3 thunderbird_twitter_osint.py --brief       # Print latest cached results
  python3 thunderbird_twitter_osint.py --topic luxury_cruise_twitter
  python3 thunderbird_twitter_osint.py --list-topics
        """,
    )
    parser.add_argument("--threads", action="store_true", help="Deep thread harvest mode")
    parser.add_argument("--brief", action="store_true", help="Print latest cached results")
    parser.add_argument("--topic", default="", help="Run single topic by ID")
    parser.add_argument("--list-topics", action="store_true", help="List available topic IDs")
    parser.add_argument("--workers", type=int, default=5, help="Parallel workers (default 5)")
    args = parser.parse_args()

    if args.list_topics:
        print("Available topics:")
        for t in DEFAULT_TOPICS:
            print(f"  {t['id']:<40} [{t['domain']}] {t['name']}")
        return

    if args.brief:
        latest = INTEL_DIR / "twitter_osint_latest.json"
        if not latest.exists():
            print("No sweep on file. Run without --brief first.")
            return
        data = json.loads(latest.read_text())
        print(f"Twitter OSINT — {data['timestamp'][:16]} | {data['successful']}/{data['topics_queried']} OK | {data['total_elapsed_s']}s")
        print()
        for r in data["results"]:
            rel = r.get("d2m_relevance", "?")[:60]
            icon = "✅" if r["status"] == "OK" else "❌"
            action = r.get("action_signal", "")[:80]
            print(f"  {icon} [{r['domain'].upper()}] {r['topic_name']}")
            print(f"       Relevance: {rel}")
            if action and action != "MONITOR":
                print(f"       Action: {action}")
            print()
        return

    if args.topic:
        topic_list = [t for t in DEFAULT_TOPICS if t["id"] == args.topic]
        if not topic_list:
            print(f"Unknown topic '{args.topic}'. Use --list-topics.")
            sys.exit(1)
    else:
        topic_list = DEFAULT_TOPICS

    run_twitter_osint_sweep(
        topics=topic_list,
        thread_harvest=args.threads,
        max_workers=args.workers,
    )


if __name__ == "__main__":
    main()

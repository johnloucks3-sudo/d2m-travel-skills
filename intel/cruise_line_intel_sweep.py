#!/usr/bin/env python3
"""
Monthly cruise line intelligence sweep — MISSION-380
Scans news/updates for D2M's 5 primary cruise lines using Perplexity + Serper.
Run monthly (first of month via systemd timer or n8n).

Lines monitored: Regent Seven Seas, Silversea, Viking Ocean, Princess, Carnival
"""

import os
import json
import datetime
import urllib.request

PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "cruise_intel")

CRUISE_LINES = [
    "Regent Seven Seas Cruises",
    "Silversea Cruises",
    "Viking Ocean Cruises",
    "Princess Cruises",
    "Carnival Cruise Line",
]

INTEL_CATEGORIES = [
    "new ships fleet expansion 2026 2027",
    "itinerary changes cancellations 2026",
    "pricing promotions advisor commission",
    "onboard experience changes amenities",
]


def perplexity_query(question: str) -> str:
    if not PERPLEXITY_API_KEY:
        return "[WARN] PERPLEXITY_API_KEY not set"
    payload = json.dumps({
        "model": "llama-3.1-sonar-small-128k-online",
        "messages": [{"role": "user", "content": question}],
        "max_tokens": 400,
    }).encode()
    req = urllib.request.Request(
        "https://api.perplexity.ai/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[ERROR] {e}"


def run_sweep():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    results = {}

    for line in CRUISE_LINES:
        print(f"\nSweeping: {line}...")
        line_results = {}
        question = (
            f"What are the most significant news updates, changes, or announcements "
            f"from {line} in 2026? Focus on: fleet changes, itinerary updates, "
            f"advisor/commission changes, new products. Be concise — bullet points."
        )
        answer = perplexity_query(question)
        line_results["summary"] = answer
        print(f"  Done ({len(answer)} chars)")
        results[line] = line_results

    out_file = os.path.join(OUTPUT_DIR, f"cruise_line_intel_{date_str}.json")
    with open(out_file, "w") as f:
        json.dump({"date": date_str, "lines": results}, f, indent=2)

    print(f"\nSaved: {out_file}")
    print("\n=== CRUISE LINE INTEL BRIEF ===")
    for line, data in results.items():
        print(f"\n--- {line} ---")
        summary = data.get("summary", "")
        print(summary[:500] + ("..." if len(summary) > 500 else ""))

    return out_file


if __name__ == "__main__":
    run_sweep()

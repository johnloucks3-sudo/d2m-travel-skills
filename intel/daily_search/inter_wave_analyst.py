#!/usr/bin/env python3
"""
Inter-Wave Analyst — ELON + Whetstone signal-scoring engine.

After each wave: score every category result, rank them, sharpen queries
toward implementable tools for the next wave.

ELON doctrine:  zero in on adoptable tools — concrete, free, wirable today.
Whetstone rule: freshness and specificity beat volume. Kill stale angles.
Hale role:      structural coordination only — this code, not prompt rewrites.
"""

import json
import re
from pathlib import Path
from typing import Optional

SEARCH_DIR = Path(__file__).parent

# ── Signal scoring ─────────────────────────────────────────────────────────────

# Keywords that signal an actionable, implementation-ready result
SIGNAL_KEYWORDS = [
    "github.com", "pip install", "npm install", "docker pull", "docker run",
    "curl ", "api key", "free tier", "rate limit", "per day", "per minute",
    "endpoint", "open source", "mit license", "apache 2", "integration",
    "install", "deploy", "configure", "sdk", "library", "webhook",
    "bearer", "byok", "self-host", "open-source", "requests/day",
]

# Keywords that signal an off-target or useless result
NOISE_KEYWORDS = [
    "can't answer", "cannot answer", "can't reliably", "i can't reliably",
    "unrelated", "not contain", "no results", "insufficient",
    "don't have access", "not available", "no information",
    "social posts", "none of the results", "can't verify", "not enough",
    "search results you provided", "i can't answer this",
]

# Category IDs confirmed as structural dead zones across multiple waves
# (cruise/portal intel that Perplexity consistently can't retrieve)
DEAD_ZONES = {13, 45, 46}


def score_result(result: dict) -> float:
    """Score a single category result 0–100. Higher = more actionable."""
    text = (result.get("result") or "").lower()
    if not text:
        return 0.0

    score = 0.0

    # Length (0–30 pts): longer usually means more detail
    score += min(30.0, len(text) / 200.0)

    # Citations (0–15 pts)
    citations = result.get("citations") or []
    score += min(15.0, len(citations) * 1.5)

    # Signal keyword hits (0–35 pts)
    signal_hits = sum(1 for kw in SIGNAL_KEYWORDS if kw in text)
    score += min(35.0, signal_hits * 3.5)

    # GitHub citation bonus (0–10 pts)
    gh_cites = sum(1 for c in citations if "github.com" in c.lower())
    score += min(10.0, gh_cites * 5.0)

    # Noise penalty (–20 per hit)
    noise_hits = sum(1 for kw in NOISE_KEYWORDS if kw in text)
    score -= noise_hits * 20.0

    # Dead zone penalty
    if result.get("id") in DEAD_ZONES:
        score -= 25.0

    return max(0.0, min(100.0, score))


def analyze_wave(wave_path: Path) -> list:
    """
    Load a wave JSON, score all results.
    Returns list sorted by score descending, rank and rank_pct added.
    """
    data = json.loads(wave_path.read_text())
    results = data.get("results", [])

    scored = []
    for r in results:
        s = score_result(r)
        scored.append({
            "id":             r["id"],
            "name":           r["name"],
            "score":          round(s, 1),
            "result_len":     len(r.get("result") or ""),
            "citation_count": len(r.get("citations") or []),
            "is_noise":       s < 10.0,
            "result_preview": (r.get("result") or "")[:400],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    n = max(len(scored) - 1, 1)
    for i, item in enumerate(scored):
        item["rank"]     = i + 1
        item["rank_pct"] = round(i / n * 100)

    return scored


# ── Query sharpening ──────────────────────────────────────────────────────────

def sharpen_query(cat: dict, sr: Optional[dict]) -> str:
    """
    Generate a sharpened query for wave N+1 based on wave N signal quality.

    Top tier  (score >=50, rank_pct <=30): drill to exact install/API/example.
    Mid tier  (score >=20, rank_pct <=70): tighten to free-tier specifics.
    Low tier  / noise: pivot to "most adoptable OSS in this space."
    Dead zone: replace with adjacent high-value angle.
    """
    name = cat["name"]
    score    = sr["score"]    if sr else 0.0
    rank_pct = sr["rank_pct"] if sr else 100
    preview  = sr["result_preview"] if sr else ""

    if sr and cat.get("id") in DEAD_ZONES:
        return (
            f"The search term '{name}' returns off-topic results via Perplexity. "
            f"Instead: what is the best OPEN-SOURCE tool a solo travel advisor could use "
            f"in this space right now? Must have >500 GitHub stars and active 2026 commits. "
            f"Provide: repo URL, pip/docker install command, and what problem it solves in one sentence."
        )

    if score >= 50 and rank_pct <= 30:
        # Top performer: drill to implementation
        return (
            f"You are a senior engineer. Find the SINGLE best tool for '{name}' as of June 2026. "
            f"Prior search found this signal: {preview[:200]}. "
            f"Now give: (1) exact GitHub repo URL or package name, "
            f"(2) one-line install command (pip/npm/docker), "
            f"(3) free tier limits (requests/day or tokens/min), "
            f"(4) a working 10-line Python or curl integration example. "
            f"Pick ONE winner. If multiple exist, state which and why in one sentence."
        )

    if score >= 20 and rank_pct <= 70:
        # Mid performer: tighten to free-tier and actionability
        return (
            f"Focus on '{name}'. Ignore general overviews — give me what a 1-person agency "
            f"can actually USE free or under $20/month as of June 2026. "
            f"Name the tool, state the free tier limits, give the API endpoint format, "
            f"and one concrete 30-second integration step."
        )

    # Low signal or noise: pivot to adjacent adoptable OSS
    return (
        f"Category '{name}' may have limited Perplexity coverage. "
        f"What is the MOST ADOPTABLE open-source tool solving a similar problem right now? "
        f"Criteria: >500 GitHub stars, commits in 2026, free self-host or generous free tier. "
        f"Give repo URL, one-line install, and what specific problem it solves in one sentence."
    )


# ── Category evolution ────────────────────────────────────────────────────────

def evolve_categories(base_categories: list, wave_results_path: Path, wave_num: int) -> list:
    """
    Core evolution loop: score wave N, return evolved categories for wave N+1.

    Rules:
    - Dead zones: removed after wave 1
    - All categories: query sharpened based on signal quality
    - Top-3 scorers (wave 2+): get a DEEP DIVE clone inserted alongside original
    - Structural removes free up slots — new categories fill them
    """
    scored = analyze_wave(wave_results_path)
    score_by_id = {s["id"]: s for s in scored}

    evolved = []
    removed_ids = []

    for cat in base_categories:
        cid = cat["id"]
        sr  = score_by_id.get(cid)

        # Remove confirmed dead zones after first wave of data
        if wave_num >= 1 and cid in DEAD_ZONES:
            removed_ids.append(cid)
            continue

        new_cat = dict(cat)
        new_cat["query"] = sharpen_query(cat, sr)
        if sr:
            new_cat["_w_score"] = sr["score"]
            new_cat["_w_rank"]  = sr["rank"]
        evolved.append(new_cat)

    # Wave 2+: deep-dive clones for top-3 non-noise results
    if wave_num >= 2:
        top3 = [s for s in scored if not s["is_noise"]][:3]
        next_id = max((c["id"] for c in evolved), default=100) + 1
        for hit in top3:
            evolved.append({
                "id":                next_id,
                "name":              f"DEEP DIVE: {hit['name']}",
                "persona":           "ELON",
                "query": (
                    f"Deep implementation drill: {hit['name']}. "
                    f"Prior wave signal (excerpt): {hit['result_preview'][:250]}. "
                    f"Now find: (1) the GitHub repo with the most stars for this exact use case, "
                    f"(2) exact free-tier docker/pip command to get running in 5 minutes, "
                    f"(3) a production-ready Python snippet (10–20 lines) that calls it. "
                    f"Be concrete — no overviews, no hedging."
                ),
                "recency":           "week",
                "routine_candidate": False,
                "haiku_eligible":    False,
                "cadence":           "daily",
                "notes":             f"Auto deep-dive from wave {wave_num} top result.",
            })
            next_id += 1

    return evolved


def write_categories_live(categories: list, path: Optional[Path] = None) -> Path:
    """Write evolved categories to categories_live.json for next wave pickup."""
    out = path or (SEARCH_DIR / "categories_live.json")
    out.write_text(json.dumps(categories, indent=2))
    return out


def print_wave_report(scored: list, wave_num: int) -> None:
    """Print inter-wave quality report to stdout."""
    signal = [s for s in scored if not s["is_noise"]]
    noise  = [s for s in scored if s["is_noise"]]
    print(f"\n{'─'*62}")
    print(f"  ⚡ INTER-WAVE ANALYSIS — After Wave {wave_num}")
    print(f"  Signal: {len(signal)}  Noise: {len(noise)}  Total: {len(scored)}")
    print(f"  Top 5 → sharpening to implementation detail:")
    for s in scored[:5]:
        print(f"    [{s['id']:02d}] {s['name'][:48]:<48}  {s['score']:5.1f}")
    if noise:
        print(f"  Pivoting/removing {len(noise)} low-signal categories.")
    print(f"{'─'*62}\n")


def top_signals_eod(all_wave_paths: list, n: int = 5) -> list:
    """
    Across all waves, find the top-N unique categories by best score seen.
    Returns list of dicts for EOD synthesis.
    """
    best = {}
    for wp in all_wave_paths:
        try:
            scored = analyze_wave(wp)
            for s in scored:
                cid = s["id"]
                if cid not in best or s["score"] > best[cid]["score"]:
                    best[cid] = s
        except Exception:
            pass
    ranked = sorted(best.values(), key=lambda x: x["score"], reverse=True)
    return ranked[:n]

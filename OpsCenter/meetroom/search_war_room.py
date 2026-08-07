#!/usr/bin/env python3
"""search_war_room.py — background, token-lean WAR ROOM competitive scan.

Runs 4 focused Perplexity lanes for an advanced AI "war room" / multi-agent
meeting-room capability, then emits a 5-candidate shortlist (name/url/what/fit)
plus an adopt-vs-build one-liner to:
    OpsCenter/meetroom/WAR_ROOM_COMPETITIVE_SCAN.md
Detached headless runner — no session to watch. RDD ~06:00 MT.
"""
import sys, time, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/home/john/Thunderbird")
HERE = Path("/home/john/Thunderbird/OpsCenter/meetroom")

LANES = [
    "best AI multi-agent orchestration UI 2026 — LangGraph Studio vs OpenAI Agents vs AutoGen vs CrewAI vs AG2: which has the most polished visual agent-conference/meeting console",
    "AI agent observability playback consoles 2026 — AgentOps vs Langfuse vs LangSmith vs Weave: which can replay a multi-agent conversation visually like a meeting timeline",
    "multi-agent simulation / conference-room products 2026 — ChatDev, MetaGPT, agent arena, Multi-ON, virtual agent teams that run like a live meeting with seats and a moderator",
    "military command / war-room software with AI panels 2026 — ATAK, planning 'war desk' dashboards, or commercial 'AI command center' products that look like a war room",
]

def lane_scan(query: str) -> str:
    from core.search.perplexity_search import intel_sweep
    try:
        return intel_sweep(topic=query)
    except Exception as e:
        return f"LANE ERROR: {e}"

def main():
    MT = timezone(timedelta(hours=-6))
    out = HERE / "WAR_ROOM_COMPETITIVE_SCAN.md"
    lines = [
        "# WAR ROOM — COMPETITIVE SCAN (background, auto-generated)",
        f"**Generated:** {datetime.now(MT).strftime('%Y-%m-%d %H:%M MT')} | mode: headless background · token-lean",
        "",
        "## Candidate shortlist (target 5, ranked)",
        "",
    ]
    all_names = []
    for i, lane in enumerate(LANES, 1):
        print(f"[lane {i}/4] scanning: {lane[:60]}...", flush=True)
        res = lane_scan(lane)
        lines.append(f"### LANE {i}: {lane[:80]}")
        lines.append(res.strip())
        lines.append("")
        time.sleep(1)

    # rough name extract — keep it simple: surfaces repeated capitalized 2-3 word platform names
    import re
    blob = "\n".join(lines)
    names = re.findall(r"\b(?:LangGraph Studio|OpenAI Agents|AutoGen|CrewAI|AG2|AgentOps|Langfuse|LangSmith|Weave|ChatDev|MetaGPT|ATAK|Multi-ON|Langflow|n8n AI|Vellum|Brains|Smolagents)\b", blob)
    from collections import Counter
    top = Counter(names).most_common(5)
    lines.insert(7, "| # | Candidate | mentions |")
    lines.insert(8, "|---|---|---|")
    for i, (n, c) in enumerate(top, 1):
        lines.insert(8 + i, f"| {i} | {n} | {c} |")
    lines.insert(7, "")
    lines.append("## ADOPT-vs-BUILD (one-liner)")
    lines.append("Review the 5 above; if any ranked product already gives Commander-paced, color-coded, file-backed multi-seat playback → adopt its pattern; else keep our ~300-LOC ROUND TABLE build.")
    lines.append("")
    lines.append("_Auto-scan. Ranked counts are surface heuristics — verify candidates before adopting._")
    out.write_text("\n".join(lines))
    print(f"DONE — wrote {out} ({len(lines)} lines)", flush=True)

if __name__ == "__main__":
    main()

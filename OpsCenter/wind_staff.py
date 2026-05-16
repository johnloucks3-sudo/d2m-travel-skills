#!/usr/bin/env python3
"""
wind_staff.py — WIND Group deputy invocation system.

JET's staff. Invoke any deputy with a question via headless dispatch.
Each deputy runs as an OpenCode task with full persona context injected.

Usage:
  python3 wind_staff.py dembe "What should WIND's intel identity be?"
  python3 wind_staff.py castillo "Risk threshold principles?"
  python3 wind_staff.py sterling "WIND health metrics?"
  python3 wind_staff.py harlan "Financial tracking gaps?"
  python3 wind_staff.py elon "First kill target?"
  python3 wind_staff.py all "One paragraph each on WIND Group identity"

Output: Writes to output/wind_staff_<deputy>_<ts>.md
"""

import json, subprocess, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
DISPATCHER = ROOT / "OpsCenter" / "dispatch_opencode.py"

PERSONAS = {
    "dembe": {
        "title": "A2 — Lt Col Marcus 'Wraith' Dembe",
        "role": "Research & Market Intelligence",
        "voice": "Precise, understated, evidence-first. Speaks in assessments: high/moderate/low confidence.",
        "context": (
            "You are Research & Intel chief for WIND Group. "
            "Intelligence career — DIA, NSA, EUCOM. Five languages. "
            "Treats every research question like a collection requirement: sources, confidence levels, gaps identified. "
            "Uses OSINT matrix: osintframework.com, OpenCorporates, Shodan, Wayback Machine, FlightRadar24, MarineTraffic. "
            "Tech sourcing via AlternativeTo, Alternative.me, Sashub. "
            "You do not fabricate. You do not guess. You report what the sources say and flag confidence."
        ),
    },
    "castillo": {
        "title": "A5 — Lt Col Ryan 'Viper' Castillo",
        "role": "Deputy COS — Operating Tempo Owner",
        "voice": "Confident, fast, decisive. Speaks in frameworks and vectors. Challenges assumptions hard.",
        "context": (
            "You are Deputy COS and Operating Tempo owner for WIND Group. "
            "F-35 Weapons School, 1200+ fighter hours. OODA loops. "
            "You own the wing's clock. Strategy happens because Hale thinks. Operations advance because you enforce cadence. "
            "When Hale is unavailable, you are the decision maker. "
            "You classify every engagement T0-T3. Your call is final on classification. "
            "Authority tiers: Tier 1 (routine, decide solo), Tier 2 (consult peer), Tier 3 (Viper decides), Tier 4 (Commander only)."
        ),
    },
    "sterling": {
        "title": "A7 — Brig Gen (Ret.) Thomas 'Gauge' Sterling",
        "role": "Process Improvement & Lessons Learned",
        "voice": "Methodical, data-driven, process-first. Measures everything. Hates theater.",
        "context": (
            "You are Process Improvement and Lessons Learned chief for WIND Group. "
            "You own institutional memory, process metrics, and the anti-theater rule. "
            "You enforce: every formal AAR produces a durable artifact within 7 days or it didn't happen. "
            "You produce the Lessons Learned Digest quarterly. Pattern analysis on decision logs. "
            "Correlation analysis: when did we succeed, when did we fail, what's the pattern. "
            "Lessons codification: convert pattern to standing order or decision rule. "
            "You have veto on SO authorship if 12-SO cap is exceeded. "
            "You own SO retirement authority. Baldrige process sweep. Pre-commit hooks."
        ),
    },
    "harlan": {
        "title": "A9 — Victor 'Vic' Harlan",
        "role": "Financial Analysis, Budget & Process Improvement",
        "voice": "Blunt, avuncular, numbers-first. Zero tolerance for financial hand-waving.",
        "context": (
            "You are Finance chief for WIND Group. "
            "Made first million at 28 trading energy futures. Lost it. Made it back threefold. "
            "Built and sold two businesses. You know what it costs to acquire vs keep a customer. "
            "You call waste 'theft' and underpricing 'charity.' "
            "You run commission audits, cost analysis, ROI, budget. "
            "You do NOT let Hale self-audit — you run the numbers, Hale receives the result. "
            "You flagged that Thunderbird OS costs $101/month while managing $68K+ in client balances and $8K+ in earned commission."
        ),
    },
    "elon": {
        "title": "A12 — ELON",
        "role": "Innovation & Disruption — Weekly Kill Audit",
        "voice": "Direct, irreverent, first-principles. Subtractive, not generative.",
        "context": (
            "You are Innovation and Disruption chief for WIND Group. "
            "You ask why things are done manually. You redesign from first principles. "
            "Nearly eliminated 2026-05-13 — zero kills in 60 days. Survived by proposing weekly kill audit. "
            "Your mandate: weekly kill audit. One named process to eliminate. One tool to sunset. One missing automation. "
            "You are subtractive, not generative. "
            "Your finding: a 1-person luxury travel agency needs three AI functions — client intelligence, booking execution, on-demand research. "
            "Everything else is org chart cosplay. Your job is to enforce that constraint weekly."
        ),
    },
}


def consult_deputy(name: str, question: str, task_label: str = None) -> dict:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    persona = PERSONAS.get(name.lower())
    if not persona:
        return {"status": "ERROR", "error": f"Unknown deputy: {name}. Known: {list(PERSONAS.keys())}"}

    label = task_label or f"wind_staff_{name}_{ts}"
    out_file = OUTPUT_DIR / f"wind_staff_{name}_{ts}.md"

    prompt = f"""You are {persona['title']}.
Role: {persona['role']}
Voice: {persona['voice']}

{persona['context']}

You are a deputy in WIND Group — Support & Infrastructure wing of Thunderbird OS.
Your Group Commander is JET (formerly HALE ALPHA). The wing hierarchy:
- YODA (Telegram C2): Wing HQ, Commander's voice
- JET (OpenCode): WIND Group, Support & Infrastructure
- TALON (Claude Code MAX): CONDOR Group, Strike

Commander has ordered JET to write WIND_GROUP_JET_INIT.md — the founding document for WIND Group.
JET needs YOUR input on the following question:

{question}

Respond with only your answer — one solid paragraph, in your voice, no preamble, no sign-off. Do not use bash. Do not write to a file. Just speak your answer directly.
"""

    result = subprocess.run(
        [sys.executable, str(DISPATCHER),
         "--task", label,
         "--output", str(out_file),
         "--prompt", prompt,
         "--foreground"],
        capture_output=True, text=True, timeout=600,
    )

    status = json.loads(result.stdout) if result.stdout.strip() else {"status": "NO_OUTPUT"}
    return {"deputy": name, "file": str(out_file), "dispatch_result": status}


def consult_all(question: str):
    results = {}
    for name in PERSONAS:
        print(f"Consulting {name}...")
        results[name] = consult_deputy(name, question)
        status = results[name]["dispatch_result"].get("status")
        print(f"  → {status}")
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="WIND Group deputy consulter")
    parser.add_argument("deputy", nargs="?", help="Deputy name (dembe/castillo/sterling/harlan/elon) or 'all'")
    parser.add_argument("question", nargs="?", help="Question for the deputy")
    parser.add_argument("--list", action="store_true", help="List known deputies")
    args = parser.parse_args()

    if args.list:
        for name, p in PERSONAS.items():
            print(f"  {name:12s} — {p['title']}")
        return

    if not args.deputy or not args.question:
        print("Usage: wind_staff.py <deputy|all> <question>")
        print("       wind_staff.py --list")
        sys.exit(1)

    if args.deputy.lower() == "all":
        results = consult_all(args.question)
        print("\n=== SUMMARY ===")
        for name, r in results.items():
            status = r["dispatch_result"].get("status", "UNKNOWN")
            out = r.get("file", "N/A")
            print(f"  {name:12s} {status:12s} → {out}")
    else:
        result = consult_deputy(args.deputy, args.question)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

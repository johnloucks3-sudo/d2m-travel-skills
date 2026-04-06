#!/usr/bin/env python3
"""
Thunderbird Grok OSINT Sweep
=============================
Uses xAI Grok API to scan 8-10 OSINT intelligence domains.
Writes structured JSON report + Markdown digest.

Usage:
    python3 thunderbird_grok_osint.py [--once|--brief]
    python3 thunderbird_grok_osint.py  # full sweep, saves to intel/

Author: Hale (COS) — 2026-04-04
"""

import os
import sys
import json
import time
import textwrap
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from openai import OpenAI

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
if not XAI_API_KEY:
    print("ERROR: XAI_API_KEY not set")
    sys.exit(1)

client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")

BASE = Path(__file__).parent
INTEL_DIR = BASE / "intel"
LOGS_DIR = BASE / "logs"
INTEL_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── OSINT Domains ──────────────────────────────────────────────────────────
# Each domain fires a targeted Grok search query.
# Grok has real-time web access built in.

DOMAINS = [
    {
        "id": "claude_alternatives",
        "name": "Claude Alternatives / LLM Landscape",
        "query": "What are the best alternatives to Claude AI in 2026? Include GPT-5, Gemini 2.5, DeepSeek R2, Qwen3, open source models. Pricing, benchmarks, strengths vs Claude Sonnet and Opus. Focus on cost-effective options for AI agent developers."
    },
    {
        "id": "ai_agents_frameworks",
        "name": "AI Agent Frameworks & Multi-Agent",
        "query": "Latest AI agent frameworks 2026: LangGraph, CrewAI, Agno, AutoGen, A2A protocol, AgentOS. Multi-agent orchestration tools. What's new, production-ready, and worth adopting? Focus on travel/enterprise applications."
    },
    {
        "id": "autonomous_coding",
        "name": "Autonomous Coding Agents",
        "query": "Claude Code alternatives and autonomous coding agents in 2026. Cursor, GitHub Copilot Agent, Devin, OpenHands, Codex, Cline. CLI coding agents and IDE agent tools. What's the state of the art?"
    },
    {
        "id": "travel_tech_agentic",
        "name": "Travel Tech + AI Agents",
        "query": "AI agentic travel technology 2026. AI travel booking agents, automated trip planning, travel agency AI automation, conversational travel booking. Which startups and cruise lines are deploying AI agents? Funding news, new platforms, MCP tools for travel."
    },
    {
        "id": "cruise_industry_ai",
        "name": "Cruise Industry Digital + AI",
        "query": "Cruise industry AI and digital transformation 2026. Royal Caribbean, Carnival, Viking, Silversea, Regent, MSC AI deployments. Route optimization, guest personalization, booking automation, predictive maintenance."
    },
    {
        "id": "open_source_llm",
        "name": "Open Source LLM Breakthroughs",
        "query": "Open source LLM breakthroughs 2026. Qwen3, Llama 4, DeepSeek, Mistral. Model benchmarks, cost comparisons, local deployment options. Which open source models can run at home and compete with Claude Opus and GPT-5?"
    },
    {
        "id": "inference_hardware",
        "name": "Inference Speed & Hardware",
        "query": "LLM inference optimization 2026. vLLM, TensorRT-LLM, Groq LPU, Cerebras. Speed benchmarks, cost per token, latency improvements. NVIDIA Vera Rubin, AMD MI400. What's practical for local agent inference?"
    },
    {
        "id": "ai_memory_systems",
        "name": "AI Agent Memory & Cross-Session",
        "query": "AI agent memory frameworks 2026. Cross-session memory, persistent agent memory, episodic memory for LLMs. Bedrock AgentCore, MemGPT, Letta, LangMem, Graphiti. How to give AI agents long-term memory?"
    },
    {
        "id": "enterprise_ai_deployment",
        "name": "Enterprise AI Deployment Patterns",
        "query": "Enterprise AI agent deployment patterns 2026. What works in production vs what's just demos? PwC agentOS, Sana Agents, AWS Bedrock agents. Best practices for scaling AI agents in a small business like a travel agency."
    },
    {
        "id": "reasoning_models",
        "name": "Reasoning Models & Benchmarks",
        "query": "Reasoning AI models 2026. AIME, MATH, GPQA benchmarks. o3, Claude Opus 4, Gemini 3, DeepSeek R2 reasoning models. Chain-of-thought evolution, test-time compute, inference-time scaling. Which model reasons best?"
    },
]


def query_grok(domain: dict) -> dict:
    """Query Grok (xAI) for OSINT on a domain."""
    try:
        resp = client.chat.completions.create(
            model="grok-3-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an OSINT analyst for Dreams2Memories Travel, LLC — a luxury "
                        "travel agency building an AI-powered concierge system called Thunderbird. "
                        "Search the current web for the most recent information on this topic. "
                        "Return ONLY a JSON object with these keys: "
                        '"key_findings" (array of 3-5 bullet strings), '
                        '"d2m_relevance" (HIGH/MED/LOW with one-line rationale), '
                        '"tools_or_products" (array of names), '
                        '"sources" (array of URLs or source names), '
                        '"action_item" (string: what D2M should do about this, if anything, or "MONITOR")'
                    )
                },
                {
                    "role": "user",
                    "content": domain["query"]
                }
            ],
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        data["domain_id"] = domain["id"]
        data["domain_name"] = domain["name"]
        data["timestamp"] = datetime.now().isoformat()
        data["status"] = "OK"
        return data
    except Exception as e:
        return {
            "domain_id": domain["id"],
            "domain_name": domain["name"],
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "key_findings": [],
            "d2m_relevance": "UNKNOWN",
            "tools_or_products": [],
            "sources": [],
            "action_item": "Retry manually.",
        }


def run_full_sweep():
    """Run all 10 domains in parallel via Grok."""
    print(f"[{datetime.now():%H:%M}] Starting Grok OSINT sweep — {len(DOMAINS)} domains")
    results = []
    
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(query_grok, d): d["name"] for d in DOMAINS}
        for fut in as_completed(futures):
            name = futures[fut]
            r = fut.result()
            results.append(r)
            status_icon = "✅" if r["status"] == "OK" else "❌"
            print(f"  {status_icon} {name}: {r.get('d2m_relevance', r.get('error', 'OK'))}")

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    report = {
        "timestamp": datetime.now().isoformat(),
        "sweep_type": "grok_osint",
        "domains_queried": len(DOMAINS),
        "successful": sum(1 for r in results if r["status"] == "OK"),
        "results": results,
    }

    # JSON
    json_path = INTEL_DIR / f"grok_osint_{timestamp}.json"
    json_path.write_text(json.dumps(report, indent=2))

    # Markdown digest
    md = f"# 🔍 GROK OSINT SWEEP — {datetime.now():%Y-%m-%d %H:%M MT}\n\n"
    md += f"**Engine:** xAI Grok 3 Mini | **Domains:** {len(DOMAINS)} | **Successful:** {report['successful']}/{len(DOMAINS)}\n\n"
    
    # Summary by relevance
    high = [r for r in results if "HIGH" in str(r.get("d2m_relevance", ""))]
    med = [r for r in results if "MED" in str(r.get("d2m_relevance", ""))]
    low = [r for r in results if "LOW" in str(r.get("d2m_relevance", ""))]
    
    md += f"## 📊 RELEVANCE SUMMARY\n"
    md += f"- 🔴 HIGH: {len(high)} domain(s)\n"
    md += f"- 🟡 MED: {len(med)} domain(s)\n"
    md += f"- 🟢 LOW: {len(low)} domain(s)\n\n"

    for r in sorted(results, key=lambda x: {"HIGH": 0, "MED": 1, "LOW": 2, "UNKNOWN": 3}.get(x.get("d2m_relevance","UNKNOWN"), 3)):
        rel = r.get("d2m_relevance", "UNKNOWN")
        icon = "🔴" if "HIGH" in rel else "🟡" if "MED" in rel else "🟢" if "LOW" in rel else "⚪"
        md += f"## {icon} {r['domain_name']}\n"
        md += f"**Relevance:** {rel}\n\n"
        if r.get("key_findings"):
            md += "**Key Findings:**\n"
            for f in r["key_findings"]:
                md += f"- {f}\n"
            md += "\n"
        if r.get("tools_or_products"):
            md += f"**Tools/Products:** {', '.join(r['tools_or_products'])}\n\n"
        md += f"**Action:** {r.get('action_item', 'See full JSON for details.')}\n\n"

    md_path = INTEL_DIR / f"grok_osint_{timestamp}.md"
    md_path.write_text(md)

    # Also write as latest for easy access
    (INTEL_DIR / "grok_osint_latest.json").write_text(json.dumps(report, indent=2))
    (INTEL_DIR / "grok_osint_latest.md").write_text(md)

    print(f"\n✅ Sweep complete. {report['successful']}/{len(DOMAINS)} domains OK.")
    print(f"   JSON: {json_path}")
    print(f"   MD:   {md_path}")
    return report


def run_brief():
    """Just print the latest sweep brief."""
    latest = INTEL_DIR / "grok_osint_latest.json"
    if not latest.exists():
        print("No Grok OSINT sweep found. Run full sweep first.")
        return
    report = json.loads(latest.read_text())
    for r in report["results"]:
        rel = r.get("d2m_relevance", "???")
        icon = "🔴" if "HIGH" in rel else "🟡" if "MED" in rel else "🟢"
        action = r.get("action_item", "")[:80]
        print(f"  {icon} {r['domain_name']} [{rel}] → {action}")


if __name__ == "__main__":
    if "--brief" in sys.argv:
        run_brief()
    else:
        run_full_sweep()

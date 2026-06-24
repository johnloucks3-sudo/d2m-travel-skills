#!/usr/bin/env python3
"""
Tool Trim Audit — Weekly AI Tool Utilization Sweep
====================================================
Doctrine: SO_TOOL_TRIM_AUDIT_20260622
Cadence: Weekly (until tool hedge is under control, then monthly)
Threshold: 1 call/month = earns its place. 0 calls in 30 days = candidate for review.
Replacement policy: Case 1 (direct swap) / Case 2 (partial overlap) / Case 3 (full dup = treat as Case 2).
Decision authority: Hale decides. Escalates to Commander on financial / strategic.
CI rule: 14-day data window before decommission recommendation. Nothing discarded on CI status alone.

Usage:
    python3 scripts/tool_trim_audit.py [--days 7] [--report-only]
    python3 scripts/tool_trim_audit.py --send   # Send report to Commander via Telegram
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
REPO        = Path(__file__).parent.parent
ENV_FILE    = REPO / ".env"
LOGS_DIR    = REPO / "logs"
AUDIT_STATE = REPO / "OpsCenter" / "state" / "tool_trim_state.json"

# ── Tool registry ─────────────────────────────────────────────────────────────
# Each entry: env_key, display_name, log_patterns (grep these in logs + journal),
#             function (what it does), known_replacements (list of other tool keys)
TOOL_REGISTRY = [
    {
        "env_key": "ANTHROPIC_API_KEY",
        "name": "Anthropic / Claude",
        "patterns": ["anthropic.com", "claude-", "ANTHROPIC_API_KEY", "claude_code"],
        "function": "primary LLM — orchestration, synthesis, client copy",
        "replacements": [],
        "core": True,  # Never audit for retirement — Wing foundation
    },
    {
        "env_key": "GEMINI_API_KEY",
        "name": "Gemini / Google AI",
        "patterns": ["gemini", "google.generativeai", "generativelanguage.googleapis"],
        "function": "large-context doc extraction, PDF layout, deck plans",
        "replacements": [],
    },
    {
        "env_key": "XAI_API_KEY",
        "name": "XAI / Grok",
        "patterns": ["xai", "grok", "XAI_API_KEY", "x.ai"],
        "function": "ZEN counter-voice, strategic dissent, independent reasoning",
        "replacements": [],
    },
    {
        "env_key": "GROQ_API_KEY",
        "name": "Groq",
        "patterns": ["groq", "GROQ_API_KEY", "groq.com"],
        "function": "fast inference — classification, log scans, status checks (free tier)",
        "replacements": ["CEREBRAS_API_KEY", "DEEPINFRA_API_KEY"],
    },
    {
        "env_key": "CEREBRAS_API_KEY",
        "name": "Cerebras",
        "patterns": ["cerebras", "CEREBRAS_API_KEY"],
        "function": "ultra-fast inference — simple lookups, classification",
        "replacements": ["GROQ_API_KEY"],
    },
    {
        "env_key": "PERPLEXITY_API_KEY",
        "name": "Perplexity",
        "patterns": ["perplexity", "PERPLEXITY_API_KEY", "perplexity.ai"],
        "function": "web search + synthesis for daily intel waves",
        "replacements": [],
    },
    {
        "env_key": "POE_API_KEY",
        "name": "Poe",
        "patterns": ["poe", "POE_API_KEY", "poe.com"],
        "function": "multi-model access (Claude, GPT, etc.) — legacy fallback",
        "replacements": ["ANTHROPIC_API_KEY"],
    },
    {
        "env_key": "DEEPINFRA_API_KEY",
        "name": "DeepInfra",
        "patterns": ["deepinfra", "DEEPINFRA_API_KEY", "deepinfra.com"],
        "function": "open-source model hosting — low-cost inference",
        "replacements": ["GROQ_API_KEY", "CEREBRAS_API_KEY"],
    },
    {
        "env_key": "HF_API_KEY",
        "name": "HuggingFace",
        "patterns": ["huggingface", "HF_API_KEY", "hf.co", "huggingface.co"],
        "function": "model hosting / inference (datasets, embeddings)",
        "replacements": [],
    },
    {
        "env_key": "FIRECRAWL_API_KEY",
        "name": "Firecrawl",
        "patterns": ["firecrawl", "FIRECRAWL_API_KEY"],
        "function": "web scraping with JS rendering",
        "replacements": [],
    },
    {
        "env_key": "SERPER_API_KEY",
        "name": "Serper",
        "patterns": ["serper", "SERPER_API_KEY", "serper.dev"],
        "function": "Google search API",
        "replacements": ["PERPLEXITY_API_KEY"],
    },
    {
        "env_key": "LLAMA_CLOUD_API_KEY",
        "name": "Llama Cloud",
        "patterns": ["llama_cloud", "LLAMA_CLOUD_API_KEY", "llamacloud"],
        "function": "PDF/document parsing (LlamaParse)",
        "replacements": ["GEMINI_API_KEY"],
    },
    {
        "env_key": "N8N_API_KEY",
        "name": "n8n",
        "patterns": ["n8n", "N8N_API_KEY"],
        "function": "workflow automation / webhook triggers",
        "replacements": [],
    },
    {
        "env_key": "PEXELS_API_KEY",
        "name": "Pexels",
        "patterns": ["pexels", "PEXELS_API_KEY"],
        "function": "stock photography for client materials",
        "replacements": ["UNSPLASH_SECRET_KEY"],
    },
    {
        "env_key": "UNSPLASH_SECRET_KEY",
        "name": "Unsplash",
        "patterns": ["unsplash", "UNSPLASH_SECRET_KEY"],
        "function": "stock photography for client materials",
        "replacements": ["PEXELS_API_KEY"],
    },
    {
        "env_key": "CLOUDFLARE_API_TOKEN",
        "name": "Cloudflare",
        "patterns": ["cloudflare", "CLOUDFLARE_API_TOKEN"],
        "function": "DNS / domain management",
        "replacements": [],
        "core": True,
    },
    {
        "env_key": "GITHUB_TOKEN",
        "name": "GitHub",
        "patterns": ["github", "GITHUB_TOKEN", "api.github.com"],
        "function": "repo access, CI, trending API for wave intel",
        "replacements": [],
        "core": True,
    },
]

# APIs retired / confirmed dead — skip measurement, just report as RETIRED
RETIRED_KEYS = {
    "OPENROUTER_API_KEY": "RETIRED MISSION-267 (Commander-approved 2026-06-15)",
    "OPENAI_API_KEY":     "RETIRED MISSION-267",
    "PINECONE_API_KEY":   "RETIRED MISSION-267",
    "GOOGLE_AI_API_KEY":  "RETIRED MISSION-267 (use GEMINI_API_KEY)",
    "GOOGLE_GENERATIVE_AI_API_KEY": "RETIRED MISSION-267 (alias, use GEMINI_API_KEY)",
    "DEEPSEEK_API_KEY":   "RETIRED — OpenRouter lane decommissioned",
}


def _load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _env_has_key(env: dict, key: str) -> bool:
    v = env.get(key, "")
    return bool(v) and "RETIRED" not in v.upper() and "PLACEHOLDER" not in v.upper()


def _count_log_hits(patterns: list[str], since_days: int) -> int:
    """Count occurrences of any pattern in logs modified in last since_days."""
    if not LOGS_DIR.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=since_days)
    count  = 0

    for log_file in LOGS_DIR.rglob("*.log"):
        try:
            if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
                continue
            text = log_file.read_text(errors="ignore")
            for pat in patterns:
                count += text.lower().count(pat.lower())
        except Exception:
            continue

    return count


def _count_journal_hits(patterns: list[str], since_days: int) -> int:
    """Count recent systemd journal entries matching any pattern."""
    since_arg = f"--since={since_days} days ago"
    count = 0
    for pat in patterns:
        try:
            result = subprocess.run(
                ["journalctl", "--user", since_arg, "--no-pager", "-q",
                 "--grep", pat, "--case-sensitive=false"],
                capture_output=True, text=True, timeout=10
            )
            count += len(result.stdout.strip().splitlines())
        except Exception:
            pass
    return count


def _count_code_refs(patterns: list[str]) -> int:
    """Count Python files that actively call this tool (rough proxy for wired paths)."""
    py_files = [f for f in REPO.rglob("*.py") if "__pycache__" not in str(f)]
    callers  = set()
    for py in py_files:
        try:
            text = py.read_text(errors="ignore")
            if any(pat.lower() in text.lower() for pat in patterns):
                callers.add(py)
        except Exception:
            continue
    return len(callers)


def _verdict(tool: dict, calls_7d: int, code_refs: int, has_replacement: bool) -> str:
    """
    Apply Case 1/2/3 logic to produce a verdict.
    Threshold: 1 call/month ≈ 0.25/week. At 7-day window, ≥1 = active.
    """
    if tool.get("core"):
        return "CORE — never audit"

    if calls_7d == 0 and code_refs == 0:
        if has_replacement:
            return "REVIEW — Case 1 candidate (zero utilization, replacement exists)"
        return "REVIEW — Case 2 candidate (zero utilization, no direct replacement)"

    if calls_7d == 0 and code_refs > 0:
        return "WATCH — wired but not called this week"

    return f"ACTIVE — {calls_7d} calls/7d"


def run_audit(days: int = 7) -> dict:
    env = _load_env()
    now = datetime.now(timezone.utc)
    results = {
        "generated_at": now.isoformat(),
        "window_days": days,
        "threshold": "1 call/30d",
        "tools": [],
        "retired": [],
    }

    # Retired keys
    for key, note in RETIRED_KEYS.items():
        if _env_has_key(env, key):
            results["retired"].append({"env_key": key, "note": note,
                                       "action": "Remove from .env — dead weight"})

    # Active tools
    for tool in TOOL_REGISTRY:
        key = tool["env_key"]
        if not _env_has_key(env, key):
            results["tools"].append({
                "name": tool["name"],
                "env_key": key,
                "status": "NO KEY",
                "calls_7d": 0,
                "code_refs": 0,
                "verdict": "NO KEY — inactive",
            })
            continue

        calls_log  = _count_log_hits(tool["patterns"], days)
        calls_jrnl = _count_journal_hits(tool["patterns"], days)
        calls_7d   = calls_log + calls_jrnl
        code_refs  = _count_code_refs(tool["patterns"])

        has_replacement = any(_env_has_key(env, r) for r in tool.get("replacements", []))
        verdict = _verdict(tool, calls_7d, code_refs, has_replacement)

        results["tools"].append({
            "name":            tool["name"],
            "env_key":         key,
            "function":        tool["function"],
            "calls_7d":        calls_7d,
            "code_refs":       code_refs,
            "has_replacement": has_replacement,
            "replacements":    tool.get("replacements", []),
            "verdict":         verdict,
            "core":            tool.get("core", False),
        })

    # Save state
    AUDIT_STATE.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_STATE.write_text(json.dumps(results, indent=2))

    return results


def format_report(results: dict) -> str:
    lines = [
        "⚡ TOOL TRIM AUDIT — WEEKLY SWEEP",
        f"Generated: {results['generated_at'][:19].replace('T',' ')} UTC",
        f"Window: {results['window_days']} days | Threshold: {results['threshold']}",
        "",
    ]

    # Tier 1: Review candidates
    review = [t for t in results["tools"] if "REVIEW" in t["verdict"]]
    watch  = [t for t in results["tools"] if "WATCH"  in t["verdict"]]
    active = [t for t in results["tools"] if "ACTIVE" in t["verdict"]]
    core   = [t for t in results["tools"] if "CORE"   in t["verdict"]]
    no_key = [t for t in results["tools"] if "NO KEY" in t["verdict"]]

    if review:
        lines.append(f"🔴 REVIEW — {len(review)} tools (zero utilization)")
        for t in sorted(review, key=lambda x: x["has_replacement"], reverse=True):
            rep = " [replacement exists]" if t["has_replacement"] else " [no replacement]"
            lines.append(f"  {t['name']}{rep}")
            lines.append(f"    Function: {t['function']}")
            lines.append(f"    Verdict: {t['verdict']}")
        lines.append("")

    if watch:
        lines.append(f"🟡 WATCH — {len(watch)} tools (wired but not called this week)")
        for t in watch:
            lines.append(f"  {t['name']} — {t['code_refs']} code refs, 0 calls/7d")
        lines.append("")

    if active:
        lines.append(f"🟢 ACTIVE — {len(active)} tools earning their place")
        for t in sorted(active, key=lambda x: -x["calls_7d"]):
            lines.append(f"  {t['name']} — {t['calls_7d']} calls/7d, {t['code_refs']} refs")
        lines.append("")

    if core:
        lines.append(f"🔵 CORE — {len(core)} tools (never audited for retirement)")
        for t in core:
            lines.append(f"  {t['name']}")
        lines.append("")

    if results.get("retired"):
        lines.append(f"💀 DEAD KEYS IN .ENV — {len(results['retired'])} (remove now)")
        for r in results["retired"]:
            lines.append(f"  {r['env_key']}: {r['note']}")
        lines.append("")

    if no_key:
        lines.append(f"⚫ NO KEY — {len(no_key)} tools not configured")
        for t in no_key:
            lines.append(f"  {t['name']}")
        lines.append("")

    lines += [
        "─" * 50,
        "Decision authority: Hale decides. Escalate to Commander on financial/strategic.",
        "CI rule: 14-day data window before decommission. Nothing discarded on CI alone.",
        "Replacement policy: Case 1 = swap+decommission | Case 2/3 = integrate+audit.",
    ]
    return "\n".join(lines)


def _tg_send(token: str, chat_id: str, text: str) -> bool:
    import urllib.request
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return bool(json.loads(resp.read()).get("ok"))
    except Exception as e:
        print(f"[tool_trim] Telegram error: {e}")
        return False


def send_report(report_text: str, results: dict | None = None) -> bool:
    """
    Send audit report via Telegram.

    Routing (SO-TELEGRAM-ROUTING-20260622):
      - Full report → relay channel (-5248121475)
      - If REVIEW candidates with replacements exist → also send a short summary to Commander (7554895206)
    """
    import sys
    sys.path.insert(0, str(REPO / "core" / "comms"))
    try:
        from tg_router import COMMANDER_CHAT_ID, RELAY_CHAT_ID
    except ImportError:
        COMMANDER_CHAT_ID = "7554895206"
        RELAY_CHAT_ID     = "-5248121475"

    env   = _load_env()
    token = env.get("TELEGRAM_D2MC2C_TOKEN") or env.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("[tool_trim] No Telegram token — skipping send")
        return False

    # ── Full report → relay ───────────────────────────────────────────────────
    LIMIT = 4000
    chunks: list[str] = []
    current = ""
    for line in report_text.split("\n"):
        candidate = (current + "\n" + line).lstrip("\n") if current else line
        if len(candidate) > LIMIT:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)

    ok = True
    for chunk in chunks:
        if not _tg_send(token, RELAY_CHAT_ID, chunk):
            ok = False

    if ok:
        print(f"[tool_trim] Relay: {len(chunks)} message(s) sent")
    else:
        print("[tool_trim] One or more relay sends failed")

    # ── REVIEW summary → Commander (only when replacements exist = actionable) ─
    if results:
        actionable = [
            t for t in results.get("tools", [])
            if "REVIEW" in t.get("verdict", "") and t.get("has_replacement")
        ]
        if actionable:
            summary_lines = [
                "⚡ TOOL TRIM — Hale action required",
                f"{len(actionable)} tool(s) at zero utilization with ready replacement:",
            ]
            for t in actionable:
                reps = ", ".join(t.get("replacements", []))
                summary_lines.append(f"  • {t['name']} → replace with {reps}")
            summary_lines.append("Full report in relay. Hale decides; escalate to Commander on financial/strategic.")
            if not _tg_send(token, COMMANDER_CHAT_ID, "\n".join(summary_lines)):
                ok = False
            else:
                print(f"[tool_trim] Commander: REVIEW summary sent ({len(actionable)} items)")

    return ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly AI tool trim audit")
    parser.add_argument("--days",        type=int, default=7, help="Look-back window in days")
    parser.add_argument("--report-only", action="store_true",  help="Print report, do not save state")
    parser.add_argument("--send",        action="store_true",  help="Send report to Commander via Telegram")
    args = parser.parse_args()

    print(f"Running tool trim audit (window: {args.days}d)...")
    results = run_audit(days=args.days)
    report  = format_report(results)

    print(report)

    review_count = sum(1 for t in results["tools"] if "REVIEW" in t["verdict"])
    dead_count   = len(results.get("retired", []))
    print(f"\nSummary: {review_count} review candidates | {dead_count} dead keys to remove")

    if args.send:
        ok = send_report(report, results=results)
        print(f"Telegram: {'sent' if ok else 'FAILED'}")

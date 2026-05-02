#!/usr/bin/env python3
"""
KEYWORD ROUTER — Three-Tier Traffic Control
D2M Thunderbird OS · 2026-04-06 (updated 2026-04-24)

⚠️ CRITICAL FIX: DeepSeek V3.1 is NOT free ($0.27/M tokens). Replaced with FREE OpenRouter tiers.

Routing Table (cost order, cheapest first):
  Tier 1 — Ollama (local, $0): Inbox triage, summarization, classification,
    simple extractions, tag/label tasks. Keywords: summarize, triage, classify,
    scan, label, tag, extract, list, count, check status.
  Tier 2 — FREE OpenRouter tiers ($0 — Nemotron/GPT-OSS/Gemma): Research, ops,
    summarization, light analysis. Default for unmatched tasks. SO 2026-04-24.
  Tier 3 — Claude Sonnet MAX (reserved, $0 via OAuth): Creative writing,
    client copy, strategy, architecture, conflict resolution, voice drafts.

Keywords → Claude (reserved):
  "architect", "strategy", "design", "resolve", "conflict", "tiebreak",
  "judge", "creative", "write", "compose", "author", "draft",
  "analyze deeply", "synthesis", "original", "policy", "decision",
  "escalat", "voice", "diplomat", "negotiat", "propose", "client email",
  "client copy", "client draft"

Keywords → Ollama (local inference):
  "summarize", "triage", "classify", "scan inbox", "label", "tag",
  "extract", "list tasks", "count", "check status", "categorize"

Default: FREE OpenRouter (Nemotron/GPT-OSS FREE, $0, SO 2026-04-24)
Tiebreak: If both FREE and Claude have touched a task → Claude precedent wins.
"""

import json
import re
import sys
import os
from pathlib import Path

# Tier 1: Ollama — low-cost local inference for bulk/simple operations
OLLAMA_KEYWORDS = [
    r'\bsummariz(?:e|ing|ed|ation)\b',
    r'\btriag(?:e|ing|ed)\b',
    r'\bclassif(?:y|ying|ied|ication)\b',
    r'\bscan\s+inbox\b',
    r'\blabel(?:ing|ed)?\b',
    r'\btag(?:ging|ged)?\b',
    r'\bextract(?:ing|ed|ion)?\b',
    r'\blist\s+(?:tasks|items|pending|open)\b',
    r'\bcount(?:ing)?\s+(?:tasks|items|emails)\b',
    r'\bcheck\s+status\b',
    r'\bcategoriz(?:e|ing|ed|ation)\b',
    r'\bdedup(?:licate|licating)?\b',
    r'\bparse\s+(?:inbox|email|task)\b',
]

OLLAMA_KEYWORD_PATTERN = re.compile(
    '|'.join(OLLAMA_KEYWORDS), re.IGNORECASE
)

# Tier 3: Claude keywords (reserved for high-value tasks)
CLAUDE_KEYWORDS = [
    r'\barchitect(?:ure|s)?\b',
    r'\bstrateg(?:y|ic)\b',
    r'\bresolv(?:ed|e|es|ing)?\b',
    r'\bconflict(?:s)?\b',
    r'\btiebreak(?:er|ing)?\b',
    r'\bjud(?:ge|ging|gment|ment)\b',
    r'\bcreative(?:ly)?\b',
    r'\b(?:write|compose|author(?:ed)?|draft(?:ed|ing)?|wrote)\b',
    r'\banalyz[e]*\s+deeply\b',
    r'\bsynthes(?:is|ize)\b',
    r'\boriginal(?:ity)?\b',
    r'\bpolicy\b',
    r'\bdecision\b',
    r'\bescalat(?:ed|e|es|ing)?\b',
    r'\bvoice\b',
    r'\bdiplomat(?:ic)?\b',
    r'\bnegotiat(?:e|ed|es|ing)?\b',
    r'\bpropos(?:e|ed|al|als)?\b',
    r'\bclient\s+(?:email|copy|draft)\b',
    r'\bcommander\s+directed\b',
    r'\bcommander\s+order(?:ed|s)?\b',
    r'\bcommander\s+task(?:ed|s)?\b',
    r'\byoda\s+(?:directed|ordered|tasked|says|said|wants)\b',
]

CLAUDE_KEYWORD_PATTERN = re.compile(
    '|'.join(CLAUDE_KEYWORDS), re.IGNORECASE
)

# Claude precedence: if claude has already contributed to this task
CLAUDE_PRECEDENCE_KEYWORDS = [
    r'\bclaude\s+already\b',
    r'\bprevious\s+claude\b',
    r'\bescalat(?:ed|e|es|ing)?\b',
    r'\bdeadlock\b',
    r'\bstan?doff\b',
]

CLAUDE_PRECEDENCE_PATTERN = re.compile(
    '|'.join(CLAUDE_PRECEDENCE_KEYWORDS), re.IGNORECASE
)


def classify_task(task_text, task_context=None):
    """
    Classify a task text and return routing decision.
    Returns: {"engine": "ollama"|"deepseek"|"claude", "confidence": 0.0-1.0, "reason": str}

    Tier priority (cheapest first):
      1. ollama  — local $0 inference for triage/summarize/classify
      2. goose   — OpenCode/DeepSeek V3.1 for research/file ops/code
      3. claude  — Sonnet MAX for creative/strategy/client copy
    """
    if not task_text:
        return {
            "engine": "goose",
            "confidence": 0.7,
            "reason": "Empty task, default to OpenCode/DeepSeek (cost-aware fallback)"
        }

    combined = task_text
    if task_context:
        combined = f"{task_text} {task_context}"

    # 1. Claude precedence override (escalation/tiebreak)
    if CLAUDE_PRECEDENCE_PATTERN.search(combined):
        return {
            "engine": "claude",
            "confidence": 0.99,
            "reason": "Claude precedence detected (tiebreak/escalation rule)"
        }

    # 2. Claude keywords — reserved high-value tasks
    claude_matches = CLAUDE_KEYWORD_PATTERN.findall(combined)
    if claude_matches:
        keyword_count = len(claude_matches)
        confidence = min(0.5 + (keyword_count * 0.1), 0.9)
        keywords_found = list(set(claude_matches))[:5]
        return {
            "engine": "claude",
            "confidence": confidence,
            "reason": f"Claude keywords detected: {', '.join(keywords_found)}"
        }

    # 3. Ollama keywords — local inference for bulk/simple ops
    ollama_matches = OLLAMA_KEYWORD_PATTERN.findall(combined)
    if ollama_matches:
        keywords_found = list(set(ollama_matches))[:3]
        return {
            "engine": "ollama",
            "confidence": 0.8,
            "reason": f"Ollama tier: low-complexity task ({', '.join(keywords_found)}). Local inference, $0 cost."
        }

    # 4. Default: OpenCode/DeepSeek V3.1
    return {
        "engine": "goose",
        "confidence": 0.7,
        "reason": "No Claude/Ollama keywords detected. OpenCode/DeepSeek default (cost-aware)."
    }


def route_to_engine(task_text, task_id=None, task_context=None):
    """
    Route a task and return execution instructions.

    Returns: {
        "engine": "deepseek"|"claude",
        "command": str,  # The actual CLI command to run
        "confidence": float,
        "reason": str
    }
    """
    decision = classify_task(task_text, task_context)

    if decision["engine"] == "claude":
        command = f"claude -p \"{task_text}\""
        if task_id:
            command = f"claude -p \"[{task_id}] {task_text}\""
        return {
            **decision,
            "command": command,
            "instructions": "Route to Claude Sonnet MAX via claude -p (headless API)"
        }

    elif decision["engine"] == "ollama":
        # Local Ollama inference — zero API cost
        # Write task to a temp file and invoke the wrapper to avoid shell escaping issues
        ollama_script = (
            "python3 /home/john/Thunderbird/scripts/ollama_run_task.py"
        )
        if task_id:
            ollama_script += f" --task-id {task_id}"
        return {
            **decision,
            "command": ollama_script,
            "instructions": "Route to local Ollama (phi3:mini) — $0 cost, ~4s latency. Fallback: OpenRouter on failure.",
            "task_text": task_text,
        }

    else:
        # Default: OpenCode/DeepSeek V3.1
        opencode_inbox = "/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md"
        command = f"echo \"{task_text}\" >> {opencode_inbox}"
        if task_id:
            command = f"echo '[{task_id}] {task_text}' >> {opencode_inbox}"
        return {
            **decision,
            "command": command,
            "instructions": "Route to OpenCode (DeepSeek V3.1) via opencode_inbox"
        }


def validate_routing(routing_decision, budget_remaining=0.0):
    """
    Validate routing decision against budget constraints.
    Block Claude if budget is exhausted.
    Returns: {"allowed": bool, "reason": str}
    """
    if routing_decision["engine"] == "claude" and budget_remaining <= 0:
        return {
            "allowed": False,
            "reason": f"Claude blocked: Budget exhausted (${budget_remaining:.2f}). Fallback to DeepSeek."
        }
    return {"allowed": True, "reason": "Budget check passed"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: keyword_router.py <task_text> [--context context_file]")
        sys.exit(0)

    task_text = sys.argv[1]
    context = None

    if "--context" in sys.argv:
        ctx_idx = sys.argv.index("--context")
        if ctx_idx + 1 < len(sys.argv):
            ctx_path = sys.argv[ctx_idx + 1]
            if os.path.exists(ctx_path):
                with open(ctx_path, 'r') as f:
                    context = f.read()

    decision = classify_task(task_text, context)
    route = route_to_engine(task_text, task_context=context)

    print(f"Task: {task_text}")
    print(f"Engine: {decision['engine'].upper()}")
    print(f"Confidence: {decision['confidence']:.0%}")
    print(f"Reason: {decision['reason']}")
    print(f"Command: {route['command']}")

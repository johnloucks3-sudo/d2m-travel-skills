#!/usr/bin/env python3
"""
KEYWORD ROUTER — Dual-Brain Traffic Control
D2M Thunderbird OS · 2026-04-06 (updated)
OpenCode/DeepSeek-first routing — Claude reserved for high-value tasks only

Routing Table:
  OpenCode/DeepSeek V3.1 (default): All tasks not explicitly matched to Claude.
    Research, scans, summaries, file ops, classifications, extractions, lists.
  Claude Sonnet MAX (reserved): Creative writing, client copy, strategy,
    architecture decisions, conflict resolution, escalation, voice-matched drafts.

Keywords → Claude (reserved):
  "architect", "strategy", "design", "resolve", "conflict", "tiebreak",
  "judge", "creative", "write", "compose", "author", "draft",
  "analyze deeply", "synthesis", "original", "policy", "decision",
  "escalat", "voice", "diplomat", "negotiat", "propose", "client email",
  "client copy", "client draft"

Default: OpenCode/DeepSeek V3.1 (free, unlimited turns)
Tiebreak: If both DeepSeek and Claude have touched a task → Claude precedent wins.
"""

import json
import re
import sys
import os
from pathlib import Path

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
    Returns: {"engine": "deepseek"|"claude", "confidence": 0.0-1.0, "reason": str}
    """
    if not task_text:
        return {
            "engine": "goose",
            "confidence": 0.7,
            "reason": "Empty task, default to OpenCode/DeepSeek (cost-aware fallback)"
        }

    # 1. Check for Claude precedence (override)
    combined = task_text
    if task_context:
        combined = f"{task_text} {task_context}"

    if CLAUDE_PRECEDENCE_PATTERN.search(combined):
        return {
            "engine": "claude",
            "confidence": 0.99,
            "reason": "Claude precedence detected (tiebreak/escalation rule)"
        }

    # 2. Check for Claude keywords (default now)
    claude_matches = CLAUDE_KEYWORD_PATTERN.findall(combined)
    if claude_matches:
        keyword_count = len(claude_matches)
        # Confidence scales with keyword density but caps at 0.9
        confidence = min(0.5 + (keyword_count * 0.1), 0.9)
        keywords_found = list(set(claude_matches))[:5]  # Top 5 unique
        return {
            "engine": "claude",
            "confidence": confidence,
            "reason": f"Claude keywords detected: {', '.join(keywords_found)}"
        }

    # 3. Default: OpenCode/DeepSeek V3.1 (cost-aware fallback for unknown/generic tasks)
    return {
        "engine": "goose",
        "confidence": 0.7,
        "reason": "No Claude keywords detected. OpenCode/DeepSeek default (cost-aware)."
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
        # Use claude -p for headless execution (API-based, no Desktop app required)
        command = f"claude -p \"{task_text}\""
        if task_id:
            command = f"claude -p \"[{task_id}] {task_text}\""

        return {
            **decision,
            "command": command,
            "instructions": "Route to Claude Sonnet MAX via claude -p (headless API)"
        }
    else:
        # Use OpenCode with DeepSeek V3.1 via opencode_inbox
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

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


# ════════════════════════════════════════════════════════════════════════
# HALE ESCALATION — LAYER 1: Pre-flight Substrate Classifier
# Added 2026-05-04 per SO_HALE_REAL_AUTONOMY_20260504.md
# ════════════════════════════════════════════════════════════════════════
#
# Purpose: Detect Hale-tier reasoning load BEFORE the request hits a small
# substrate model (Haiku/Gemini Flash). Force-route to Sonnet/Opus when
# Hale reasoning is required.
#
# Returns substrate decision: "haiku" | "sonnet" | "opus".
# Decision precedence: Opus > Sonnet > Haiku (most-restrictive wins).
#
# Distinct from classify_task() above (which routes to engine families).
# This function is called by thunderbird_model_dispatcher.py via the
# select_substrate() chain — see Layer 1+3+4 integration.

# ── OPUS-TIER PATTERNS (force Opus 4.7) ─────────────────────────────────
OPUS_TIER_PATTERNS = [
    # Strategic horizon language
    r'\blong[- ]term\b',
    r'\bnext\s+(?:quarter|year|fiscal)\b',
    r'\bgrowth\s+strateg(?:y|ic)\b',
    r'\bbusiness\s+model\b',
    r'\bmulti[- ]quarter\b',
    # Conflict arbitration
    r'\bhale\s+(?:vs|versus)\b',
    r'\bdeepseek\s+says\b',
    r'\bmodels?\s+disagree\b',
    r'\barbitrate\b',
    r'\barbitration\b',
    r'\btiebreak(?:er)?\b',
    # Constitutional / charter-level work
    r'\brewrite\s+(?:so|standing\s+order|charter)\b',
    r'\boperating\s+constitution\b',
    r'\bfirst\s+principles?\b',
    r'\bcharter[- ]level\b',
    # Explicit Opus request
    r'(?:^|\W)/opus\b',
    r'\buse\s+opus\b',
    r'\bopus\s+please\b',
    r'\bopus\s+only\b',
    r'\bclaude\s+opus\b',
]
OPUS_TIER_RE = re.compile('|'.join(OPUS_TIER_PATTERNS), re.IGNORECASE)

# ── HALE-TIER PATTERNS (force Sonnet 4.6) ───────────────────────────────
HALE_TIER_PATTERNS = [
    # Persona invocation
    r'\bhale\b',
    r'\bcos\b',
    r'\biron\s+vic\b',
    r'\bcol\s+hale\b',
    r'\bchief\s+of\s+staff\b',
    # Strategic verbs (reasoning-heavy)
    r'\bdecid(?:e|ing|ed)\b',
    r'\brecommend(?:ation|ed|ing)?\b',
    r'\bpropos(?:e|al|ed|ing)\b',
    r'\bsynthesiz(?:e|ed|ing)\b',
    r'\bevaluat(?:e|ed|ing|ion)\b',
    r'\bassess(?:ment|ed|ing)?\b',
    r'\bdiagnos(?:e|is|ed|ing)\b',
    r'\broot[- ]cause\b',
    # Multi-source synthesis cues
    r'\bcompar(?:e|ing|ison)\b',
    r'\bweigh(?:ing|ed)?\b',
    r'\btradeoffs?\b',
    r'\btrade[- ]offs?\b',
    r'\bacross\s+(?:all|the|these|both|multiple)\b',
    r'\bbetween\s+(?:these|the|all|both)\b',
    # Decision framework cues
    r'\boptions?\b',
    r'\bpros\s+and\s+cons\b',
    r'\bshould\s+we\b',
    r'\bwhich\s+is\s+(?:better|best|right)\b',
    r"\bwhat'?s\s+the\s+right\s+call\b",
    r'\bwhat\s+would\s+you\s+(?:do|recommend)\b',
    # Mission board P1/P2 references
    r'\bmission\s+board\b',
    r'\b(?:p1|p2|priority\s*[12])\b',
    # Client lifecycle work
    r'\bfpd\b',
    r'\bvalidat(?:e|ion|ing|ed)\b',
    r'\bdossier\b',
    r'\blifecycle\b',
    r'\bphase\s*[123]\b',
    # Commander-direct conversational vocatives
    r'(?:^|\W)sir(?:[,.\s]|$)',
    r'(?:^|\W)yoda(?:[,.\s]|$)',
    r'(?:^|\W)boss(?:[,.\s]|$)',
    r'(?:^|\W)commander(?:[,.\s]|$)',
    # Multi-step problem framing
    r'\bfirst\b.{0,80}\bthen\b.{0,80}\b(?:finally|last|after\s+that)\b',
    # Root-cause framing
    r'\bwhy\s+is\b',
    r"\bwhat'?s\s+causing\b",
    r"\bwhat'?s\s+wrong\s+with\b",
    r'\bwhy\s+(?:did|does|do)n\'?t\b',
]
HALE_TIER_RE = re.compile('|'.join(HALE_TIER_PATTERNS), re.IGNORECASE)

# ── ROUTINE PATTERNS (Haiku/Gemini stays) ───────────────────────────────
# Used as a sanity check — if the request matches ONLY routine patterns
# and no Hale/Opus pattern, leave at default. Currently informational.
ROUTINE_PATTERNS = [
    r'\bwhat\s+time\s+is\b',
    r'\bis\s+\w+\s+running\b',
    r'\bread\s+file\b',
    r'\bformat\s+(?:this\s+)?as\s+(?:json|csv|markdown|table)\b',
    r'\bshow\s+me\s+the\s+contents?\b',
    r'\blist\s+files?\b',
    r'\bcheck\s+(?:if|whether)\b',
]
ROUTINE_RE = re.compile('|'.join(ROUTINE_PATTERNS), re.IGNORECASE)


def classify_substrate(request: str) -> dict:
    """Classify a request and return the required substrate model tier.

    Args:
        request: The raw user/task text to be sent to the model.

    Returns:
        Dict with keys:
          substrate (str): "haiku" | "sonnet" | "opus"
          reason (str): Human-readable rationale
          matched_patterns (list[str]): Distinct regex matches that fired
          tier (str): "OPUS-TIER" | "HALE-TIER" | "ROUTINE"
    """
    if not request or not request.strip():
        return {
            "substrate": "haiku",
            "reason": "empty request — default routine",
            "matched_patterns": [],
            "tier": "ROUTINE",
        }

    # 1. Opus-tier check (highest precedence)
    opus_matches = OPUS_TIER_RE.findall(request)
    if opus_matches:
        unique = sorted(set(m.lower().strip() for m in opus_matches if m))
        return {
            "substrate": "opus",
            "reason": f"matched OPUS-TIER pattern: {', '.join(unique[:5])}",
            "matched_patterns": unique,
            "tier": "OPUS-TIER",
        }

    # 2. Hale-tier check
    hale_matches = HALE_TIER_RE.findall(request)
    if hale_matches:
        unique = sorted(set(m.lower().strip() for m in hale_matches if m))
        return {
            "substrate": "sonnet",
            "reason": f"matched HALE-TIER pattern: {', '.join(unique[:5])}",
            "matched_patterns": unique,
            "tier": "HALE-TIER",
        }

    # 3. Routine — default substrate (caller decides Haiku vs Gemini)
    routine_matches = ROUTINE_RE.findall(request)
    return {
        "substrate": "haiku",
        "reason": (
            "matched ROUTINE pattern: " + ', '.join(sorted(set(routine_matches)))
            if routine_matches
            else "no Hale/Opus pattern detected — routine default"
        ),
        "matched_patterns": sorted(set(routine_matches)),
        "tier": "ROUTINE",
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

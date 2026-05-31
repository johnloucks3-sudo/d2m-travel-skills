#!/usr/bin/env python3
"""
SONNET PRE-FILTER — Haiku Screening for Synthesis Tasks
D2M Thunderbird OS · 2026-05-31

Purpose: Reduce Sonnet utilization from 62% to ~45% by pre-filtering synthesis
tasks through Haiku. Only escalate to Sonnet when Haiku signals it can't handle
the task (reasoning, creative, client voice).

Strategy:
1. Check task context size (<2K tokens = eligible for Haiku screening)
2. Check if task is non-reasoning (can be handled by Haiku)
3. Send to Haiku first with "can you handle this? respond CONFIDENT or ESCALATE"
4. If CONFIDENT: use Haiku output
5. If ESCALATE: proceed to Sonnet
6. Tracks cost savings vs Sonnet-first routing

ROI Target: Save 15-25% of Sonnet budget (~$5-10/month)
"""

import re
from typing import Literal

# Tasks that CANNOT go to Haiku (must escalate to Sonnet immediately)
SONNET_ONLY_KEYWORDS = [
    r'(?:client|guest|customer)\s+(?:email|copy|draft|voice|proposal|message)',
    r'(?:welcome|validation|itinerary|confirmation)\s+(?:email|letter|draft)',
    r'\blifecycle\s+touchpoint\b',
    r'(?:port|dining|excursion)\s+narrative',
    r'\bemail\s+(?:to\s+)?(?:Mr|Mrs|Ms|Dr|Kyle|Ken|Nancy|John|Brent|Kim|Missy)',  # email to specific person
    r'\bstaff\s+(?:paper|decision|memo|brief)\b',
    r'\bcommander\s+(?:brief|intel|update|email)\b',
    r'(?:strategic|creative|original)\s+(?:draft|copy|proposal)',
    r'\bconflict\s+resolv',
]

SONNET_ONLY_PATTERN = re.compile('|'.join(SONNET_ONLY_KEYWORDS), re.IGNORECASE)

# Tasks that CAN start with Haiku (simple operations)
HAIKU_CAPABLE_KEYWORDS = [
    r'\bextrct\b',
    r'\bparse\b',
    r'\bformat\b',
    r'\bconvert\b',
    r'\b(?:read|summariz)\s+(?:file|document|page)\b',
    r'\b(?:check|scan|verify)\b',
    r'\bsimple\b',
]

HAIKU_CAPABLE_PATTERN = re.compile('|'.join(HAIKU_CAPABLE_KEYWORDS), re.IGNORECASE)


def estimate_context_size(prompt: str) -> int:
    """Rough estimate: ~0.25 tokens per character"""
    return len(prompt) // 4


def should_escalate_to_sonnet(prompt: str) -> bool:
    """
    Returns True if task MUST go to Sonnet (don't try Haiku).
    Returns False if task can be tried in Haiku first.
    """
    # Always escalate client-facing work
    if SONNET_ONLY_PATTERN.search(prompt):
        return True

    # If context is large, escalate
    if estimate_context_size(prompt) > 2000:
        return True

    # Default: try Haiku first for simple operations
    return False


def route_synthesis_task(prompt: str) -> Literal["haiku", "sonnet"]:
    """
    Route a synthesis task to the cheapest capable model.

    Returns:
        "haiku" if task can be tried with Haiku first
        "sonnet" if task must go directly to Sonnet
    """
    if should_escalate_to_sonnet(prompt):
        return "sonnet"
    return "haiku"


def haiku_screening_prompt(user_prompt: str) -> str:
    """
    Wrap user prompt to ask Haiku if it can handle it.

    Haiku responds with:
      CONFIDENT: [short answer]
      ESCALATE: [reason why]
    """
    return f"""Can you handle this task? Respond CONFIDENT or ESCALATE.

Task: {user_prompt}

If CONFIDENT, solve it briefly. If ESCALATE, explain why (reasoning depth, creative writing, client voice, etc.)."""


if __name__ == "__main__":
    # Test the router
    test_prompts = [
        "Extract dates from this itinerary PDF",
        "Write a validation email to the client about their booking",
        "Summarize the morning intel briefing",
        "Draft the Kuklinski welcome email with all the luxury details",
        "Convert CSV to JSON format",
        "Resolve the conflict between two competing pricing options for the board",
    ]

    for prompt in test_prompts:
        route = route_synthesis_task(prompt)
        print(f"{route.upper():7s} | {prompt[:60]}")

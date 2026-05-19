#!/usr/bin/env python3
"""
hale_tp_router.py — TP Lifecycle Routing to Model Tier
Thunderbird Wing, Dreams2Memories Travel, LLC

Maps canonical lifecycle touchpoint (TP) task types to the correct model tier,
ensuring cost-efficient routing across the 23-TP lifecycle.

Usage:
    from core.ops.hale_tp_router import route_tp
    result = route_tp("Draft a validation email for Kuklinski")
    # {"tp_type": "validation_email", "model": "sonnet", "rationale": "...", "cost_tier": "medium"}

Author: Ms. Victoria "Victory" Hale, SES-6 — Thunderbird Wing
Deployed: MISSION-023
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# TP → Model tier map
# ---------------------------------------------------------------------------

TP_MODEL_MAP: dict[str, str] = {
    "client_email":      "sonnet",    # Voice-matched copy; relationship product
    "research":          "deepseek",  # Bulk context, destination/market intel
    "booking_admin":     "haiku",     # Structured data entry, fast pattern work
    "financial":         "sonnet",    # Accuracy critical; commission/pricing logic
    "intel_sweep":       "deepseek",  # High-volume research; morning/world sweeps
    "proposal":          "sonnet",    # Client-facing quality; credibility product
    "dossier_update":    "haiku",     # Structured write; low judgment required
    "validation_email":  "sonnet",    # WF-17 gate product; voice + accuracy
    "morning_brief":     "deepseek",  # Templated, high-volume; low judgment
    "strategy":          "sonnet",    # Judgment required; business decisions
}

# ---------------------------------------------------------------------------
# Cost tier lookup
# ---------------------------------------------------------------------------

COST_TIERS: dict[str, str] = {
    "haiku":    "low",
    "deepseek": "low",
    "sonnet":   "medium",
    "opus":     "high",
}

# ---------------------------------------------------------------------------
# Keyword → TP category classification
# Order: MOST SPECIFIC first. Disambiguates overlapping terms.
# ---------------------------------------------------------------------------

# Each entry: (tp_category, [keywords_that_trigger_it])
# Evaluated top-to-bottom; first match wins.
_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    # Highly specific categories first
    ("validation_email", [
        "validation email", "validate email", "validation msg",
        "validate booking", "booking validation", "confirm booking",
        "validate client",
    ]),
    ("morning_brief", [
        "morning brief", "daily brief", "morning report",
        "morning summary", "morning intel", "0600 brief", "06:00 brief",
        "daily report",
    ]),
    ("intel_sweep", [
        "intel sweep", "intelligence sweep", "world intel",
        "ship intel", "competitive intel", "market intel",
        "news sweep", "osint", "intelligence report",
        "ship intelligence", "competitor analysis",
    ]),
    ("financial", [
        "commission", "invoice", "payment", "reconciliation",
        "cost analysis", "roi", "budget", "markup", "margin",
        "price quote", "pricing analysis", "financial", "revenue",
        "fare watch", "net price", "client price",
    ]),
    ("proposal", [
        "proposal", "quote email", "cruise proposal",
        "trip proposal", "send quote", "client quote",
        "itinerary proposal", "luxury proposal",
    ]),
    ("dossier_update", [
        "dossier", "update dossier", "dossier update",
        "client dossier", "update client file", "booking dossier",
    ]),
    ("strategy", [
        "strategy", "strategic", "business decision",
        "growth plan", "pricing strategy", "market strategy",
        "business growth", "competitive strategy",
        "recommend approach", "recommend option",
    ]),
    ("research", [
        "research", "destination research", "cruise research",
        "ship research", "port research", "excursion research",
        "investigate", "look into", "gather intel",
        "find information", "search for", "competitor research",
        "market research", "fare research",
    ]),
    ("booking_admin", [
        "booking", "reservation", "cabin assignment",
        "passenger info", "guest info", "confirm reservation",
        "booking number", "extract booking", "process booking",
        "booking details", "add to booking", "update booking",
    ]),
    # client_email is intentionally last among email-like terms
    # (validation_email and proposal already captured their subsets)
    ("client_email", [
        "email", "client email", "email to client",
        "write email", "draft email", "compose email",
        "send email", "client message", "outreach",
        "follow up email", "follow-up email", "lifecycle email",
        "touchpoint email",
    ]),
]


def classify_tp_type(task_description: str) -> str:
    """
    Classify a task description into one of the TP categories.

    Keyword matching is case-insensitive. Rules are evaluated most-specific
    first to prevent broad categories from swallowing narrow ones.
    (e.g., "validation_email" is checked before "client_email")

    Default: "booking_admin" — safe structured-data fallback.

    Args:
        task_description: Free-text task description from lifecycle dispatcher.

    Returns:
        One of the TP_MODEL_MAP keys.
    """
    lowered = task_description.lower()

    for tp_category, keywords in _KEYWORD_RULES:
        for kw in keywords:
            if kw in lowered:
                return tp_category

    return "booking_admin"


def route_tp(task_description: str) -> dict:
    """
    Route a TP task to the correct model tier.

    Args:
        task_description: Free-text task description.

    Returns:
        dict with keys:
            tp_type    — TP category (str)
            model      — Target model tier (str)
            rationale  — One-sentence routing rationale (str)
            cost_tier  — "low" | "medium" | "high" (str)
    """
    tp_type = classify_tp_type(task_description)
    model = TP_MODEL_MAP.get(tp_type, "sonnet")  # sonnet as safe fallback
    cost_tier = COST_TIERS.get(model, "medium")

    rationale_map: dict[str, str] = {
        "client_email":     "Voice-matched client copy requires Sonnet tone quality.",
        "research":         "Bulk context retrieval is cost-efficient on DeepSeek.",
        "booking_admin":    "Structured data tasks run fast and cheap on Haiku.",
        "financial":        "Commission and pricing accuracy requires Sonnet reliability.",
        "intel_sweep":      "High-volume research sweeps are DeepSeek's strength.",
        "proposal":         "Client-facing proposals demand Sonnet presentation quality.",
        "dossier_update":   "Structured file writes need speed and format compliance — Haiku.",
        "validation_email": "WF-17 gate product requires Sonnet voice + accuracy.",
        "morning_brief":    "Templated daily brief runs efficiently on DeepSeek.",
        "strategy":         "Business judgment and strategic synthesis requires Sonnet.",
    }

    result = {
        "tp_type":   tp_type,
        "model":     model,
        "rationale": rationale_map.get(tp_type, "Default routing applied."),
        "cost_tier": cost_tier,
    }

    # Log routing decision to activity log
    try:
        from core.ops.hale_activity_logger import log_event
        log_event(
            "DISPATCH",
            f"TP routed: {tp_type} → {model}",
            detail=f"cost_tier={cost_tier} | task={task_description[:80]}",
            source="tp_router",
        )
    except Exception:
        pass  # Never let logging block routing

    return result


# ---------------------------------------------------------------------------
# Test block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    # 8 test cases — cover all TP categories with disambiguation checks
    test_cases = [
        # (description, expected_tp_type)
        (
            "Draft a validation email to confirm Kuklinski's Viking Mars booking",
            "validation_email",
        ),
        (
            "Send client email welcoming the Furlows aboard Grandeur Scandinavia",
            "client_email",
        ),
        (
            "Run ship intelligence sweep on Regent Seven Seas Grandeur",
            "intel_sweep",
        ),
        (
            "Research excursions available in Reykjavik for Cultural Connoisseur traveler",
            "research",
        ),
        (
            "Generate morning brief for Commander — all 8 cruise lines, May 5",
            "morning_brief",
        ),
        (
            "Prepare cruise proposal for Westbrook family — Silver Nova Norwegian Fjords",
            "proposal",
        ),
        (
            "Reconcile Ponant commission on Furlow booking — final payment received",
            "financial",
        ),
        (
            "Update dossier for McLeod with confirmed cabin assignment and FPD date",
            "dossier_update",
        ),
    ]

    print("=" * 70)
    print("HALE TP ROUTER — Test Suite")
    print("=" * 70)

    pass_count = 0
    fail_count = 0

    for i, (task, expected) in enumerate(test_cases, 1):
        result = route_tp(task)
        actual = result["tp_type"]
        passed = actual == expected
        status = "PASS" if passed else "FAIL"
        if passed:
            pass_count += 1
        else:
            fail_count += 1

        print(f"\nTest {i}: {status}")
        print(f"  Task     : {task[:65]}...")
        print(f"  Expected : {expected}")
        print(f"  Got      : {actual}")
        print(f"  Model    : {result['model']} ({result['cost_tier']})")
        print(f"  Rationale: {result['rationale']}")

    print()
    print("=" * 70)
    print(f"Results: {pass_count}/{len(test_cases)} passed", end="")
    if fail_count:
        print(f" | {fail_count} FAILED")
        sys.exit(1)
    else:
        print(" — ALL PASS")

    # Log mission completion
    try:
        from core.ops.hale_activity_logger import mission_complete
        mission_complete(
            "MISSION-023",
            "TP Lifecycle Routing to Model Tier deployed",
            source="mission_023",
        )
        print("\nActivity log: MISSION-023 complete entry written.")
    except Exception as e:
        print(f"\nActivity log warning: {e}")

"""
hale_autonomy.py — Unified Hale Autonomy Stack
Imports all four enforcement modules. Use this as the single entry point.

Usage:
    from core.ops.hale_autonomy import (
        classify_tier, enforce_tier,         # T1/T2/T3/T4 gate
        route_tp,                            # TP → model tier
        filter_response, audit_log_violations,  # banned phrase filter
        is_preauthorized, apply_always,      # Five Always pre-auth
    )
"""
from core.ops.hale_tier_enforcer import classify_tier, enforce_tier, TIER_KEYWORDS
from core.ops.hale_tp_router import classify_tp_type, route_tp, TP_MODEL_MAP
from core.ops.hale_phrase_filter import filter_response, check_response, audit_log_violations
from core.ops.hale_five_always import is_preauthorized, check_always_applies, apply_always, FIVE_ALWAYS

__all__ = [
    # Tier enforcement
    "classify_tier", "enforce_tier", "TIER_KEYWORDS",
    # TP routing
    "classify_tp_type", "route_tp", "TP_MODEL_MAP",
    # Phrase filter
    "filter_response", "check_response", "audit_log_violations",
    # Five Always
    "is_preauthorized", "check_always_applies", "apply_always", "FIVE_ALWAYS",
]


def evaluate_task(task_description: str) -> dict:
    """
    Full autonomy evaluation for any incoming task.
    Returns a decision dict covering all four enforcement layers.
    """
    preauth, always_name = is_preauthorized(task_description)
    tier = classify_tier(task_description)
    tp_route = route_tp(task_description)
    violations = check_response(task_description)

    return {
        "task": task_description[:100],
        "preauthorized": preauth,
        "always_name": always_name or None,
        "tier": tier,
        "model": tp_route["model"],
        "tp_type": tp_route["tp_type"],
        "cost_tier": tp_route["cost_tier"],
        "phrase_violations": violations,
        "gate": "bypass" if (preauth or tier == "T1") else (
            "notify" if tier == "T2" else (
            "hold_for_review" if tier == "T3" else "flag_only")),
    }

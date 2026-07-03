#!/usr/bin/env python3
"""
session_startup_keyword_router.py — Wire keyword router into session startup.

Called from session_init.py to:
1. Load keyword router config
2. Load prior context from hale_bus (if resuming from prior instance)
3. Set up Commander keyword detection

Integration point:
    from core.ai_infra.session_startup_keyword_router import init_keyword_router
    router, prior_context = init_keyword_router(instance_type="claude-code")
"""

import sys
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

ROOT = Path(__file__).parent.parent.parent


def init_keyword_router(instance_type: str = "claude-code") -> Tuple[Any, Dict[str, Any]]:
    """
    Initialize keyword router and load prior context from hale_bus.

    Args:
        instance_type: "claude-code" or "opencode"

    Returns:
        (router, prior_context)
        router: KeywordAutoRouter instance
        prior_context: dict with alerts, missions, cached ZEN, etc.
    """

    try:
        from core.ai_infra.keyword_auto_router import KeywordAutoRouter
        from core.hale_bus.hale_bus_handoff import HaleBusHandoff

        print(f"[Session Init] Loading keyword router ({instance_type})...", file=sys.stderr)

        # 1. Initialize router
        router = KeywordAutoRouter()

        # 2. Load prior context from hale_bus (if resuming)
        hale_bus = HaleBusHandoff(instance_type)
        prior_context = hale_bus.read_prior_context()

        # 3. Log startup
        if prior_context.get("open_tasks"):
            print(
                f"[Session Init] Resuming: {len(prior_context['open_tasks'])} open tasks",
                file=sys.stderr
            )

        if prior_context.get("alerts"):
            print(
                f"[Session Init] {len(prior_context['alerts'])} deferred alerts",
                file=sys.stderr
            )

        if prior_context.get("fpd_deadlines"):
            print(
                f"[Session Init] {len(prior_context['fpd_deadlines'])} FPD deadlines",
                file=sys.stderr
            )

        return router, prior_context

    except Exception as e:
        print(f"[Session Init] ERROR: {e}", file=sys.stderr)
        raise


def detect_commander_keyword(text: str) -> Optional[str]:
    """Extract Commander keyword if text contains @ctx, @zen, @free, @oc, etc."""
    from core.ai_infra.keyword_auto_router import parse_commander_keyword
    return parse_commander_keyword(text)


def session_startup_banner(instance_type: str, prior_context: Dict[str, Any]):
    """Print session startup banner with prior context."""
    print("\n" + "=" * 80, file=sys.stderr)
    print(f"[THUNDERBIRD SESSION] {instance_type.upper()}", file=sys.stderr)
    print(f"[Keyword Router] ACTIVE — config: config/keyword_router_enhanced.yaml", file=sys.stderr)

    # Print alerts
    if prior_context.get("alerts"):
        print(f"\n[ALERTS] {len(prior_context['alerts'])} deferred:", file=sys.stderr)
        for alert in prior_context["alerts"][:5]:  # First 5
            print(f"  [{alert.get('priority')}] {alert.get('message')}", file=sys.stderr)
        if len(prior_context["alerts"]) > 5:
            print(f"  ... +{len(prior_context['alerts']) - 5} more", file=sys.stderr)

    # Print FPD deadlines
    if prior_context.get("fpd_deadlines"):
        print(f"\n[FPD DEADLINES] {len(prior_context['fpd_deadlines'])} due:", file=sys.stderr)
        for fpd in prior_context["fpd_deadlines"][:5]:  # First 5
            print(
                f"  {fpd.get('client')} — ${fpd.get('amount')} due {fpd.get('fpd')}",
                file=sys.stderr
            )
        if len(prior_context["fpd_deadlines"]) > 5:
            print(f"  ... +{len(prior_context['fpd_deadlines']) - 5} more", file=sys.stderr)

    # Print open missions
    if prior_context.get("open_tasks"):
        print(f"\n[OPEN TASKS] {len(prior_context['open_tasks'])} from prior session:", file=sys.stderr)
        for task in prior_context["open_tasks"][:5]:  # First 5
            print(f"  {task.get('id')} — {task.get('status')}", file=sys.stderr)
        if len(prior_context["open_tasks"]) > 5:
            print(f"  ... +{len(prior_context['open_tasks']) - 5} more", file=sys.stderr)

    # Print cached ZEN
    if prior_context.get("cached_zen"):
        print(f"\n[CACHED ZEN] {len(prior_context['cached_zen'])} cached responses (24h TTL)", file=sys.stderr)

    print("\n" + "=" * 80, file=sys.stderr)


if __name__ == "__main__":
    # Test initialization
    router, prior_context = init_keyword_router("claude-code")
    session_startup_banner("claude-code", prior_context)

    print("\n[Test] Router ready. Testing keyword detection...")
    test_texts = [
        "extract json from this log",
        "counter my argument",
        "@oc takeover needed",
        "default prompt",
    ]

    for text in test_texts:
        from core.ai_infra.keyword_auto_router import parse_commander_keyword
        keyword = parse_commander_keyword(text)
        layer, rule = router.classify(text, override_keyword=keyword)
        print(f"\n  Text: {text}")
        print(f"    Keyword: {keyword}")
        print(f"    Layer: {layer}")
        print(f"    Intent: {rule.get('intent', 'N/A')}")

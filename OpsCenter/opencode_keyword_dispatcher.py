#!/usr/bin/env python3
"""
opencode_keyword_dispatcher.py — OpenCode orchestrator using shared keyword router.

When Commander types @oc or @oc-takeover, OpenCode uses this dispatcher to:
1. Load prior context from Claude Code checkpoint (hale_bus)
2. Claim open missions
3. Route new work via keyword router
4. Use free models (Groq, Cerebras, GitHub, Ollama, Poe)

Integration: Call from OpenCode session_init

Usage:
    from OpsCenter.opencode_keyword_dispatcher import OpenCodeDispatcher

    dispatcher = OpenCodeDispatcher()
    result, tool, metadata = dispatcher.route_and_execute(prompt)
"""

import sys
import json
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

ROOT = Path(__file__).parent.parent


class OpenCodeDispatcher:
    """OpenCode main dispatcher — uses shared keyword router."""

    def __init__(self):
        """Initialize with prior context from hale_bus."""
        from core.ai_infra.session_startup_keyword_router import init_keyword_router
        from core.hale_bus.hale_bus_handoff import HaleBusHandoff

        self.router, self.prior_context = init_keyword_router("opencode")
        self.hale_bus = HaleBusHandoff("opencode")

        # Claim prior missions
        self._claim_prior_missions()

        print(f"[OpenCode Dispatcher] Ready. {len(self.prior_context.get('open_tasks', []))} prior tasks claimed.", file=sys.stderr)

    def _claim_prior_missions(self):
        """Claim open missions from prior Claude Code session."""
        for task in self.prior_context.get("open_tasks", []):
            mission_id = task.get("id")
            if mission_id:
                self.hale_bus.claim_work(mission_id, status="in_progress_oc")

    def route_and_execute(self, prompt: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Route prompt via keyword router and execute.

        Returns:
            (result_text, tool_used, metadata)
        """
        from core.ai_infra.keyword_auto_router import (
            parse_commander_keyword,
            route_and_execute
        )

        # Check for Commander keyword override
        keyword = parse_commander_keyword(prompt)

        # Route via shared router
        result, tool, metadata = route_and_execute(prompt, self.router, keyword)

        return result, tool, metadata

    def handle_ctx_data_processing(self, prompt: str, rule: Dict[str, Any]) -> str:
        """Handle sandbox data processing via ctx_execute_file."""
        # In actual use, this would invoke the ctx tool
        # For now, return metadata indicating sandbox execution
        return f"[ctx_execute_file] {rule.get('intent', 'processing')}"

    def handle_free_infer(self, prompt: str, rule: Dict[str, Any]) -> str:
        """Handle free model inference."""
        from core.ai_infra.free_model_router import free_infer

        provider_chain = rule.get("provider_chain", ["groq"])
        model = rule.get("model", "llama-3.3-70b-versatile")
        max_tokens = rule.get("max_tokens", 2048)

        for provider in provider_chain:
            try:
                result = free_infer(
                    prompt,
                    provider=provider,
                    model=model,
                    max_tokens=max_tokens
                )
                print(f"[OpenCode] {provider} → {model}", file=sys.stderr)
                return result
            except Exception as e:
                print(f"[OpenCode] {provider} failed: {e}", file=sys.stderr)
                continue

        raise RuntimeError(f"All providers failed: {provider_chain}")

    def handle_zen_reasoning(self, prompt: str, rule: Dict[str, Any]) -> str:
        """Handle ZEN counter-reasoning."""
        # Check cache first
        cached = self.hale_bus.get_cached_zen(prompt)
        if cached:
            print("[OpenCode ZEN] Cache hit", file=sys.stderr)
            return cached

        # Execute ZEN
        from core.ai_infra.free_model_router import free_infer

        provider_chain = rule.get("provider_chain", ["github-r1"])
        model = rule.get("model", "DeepSeek-R1")

        for provider in provider_chain:
            try:
                result = free_infer(prompt, provider=provider, model=model, max_tokens=500)
                self.hale_bus.cache_zen_response(prompt, result)
                print(f"[OpenCode ZEN] {provider} → cached", file=sys.stderr)
                return result
            except Exception as e:
                print(f"[OpenCode ZEN] {provider} failed: {e}", file=sys.stderr)
                continue

        raise RuntimeError(f"ZEN failed across all providers: {provider_chain}")

    def checkpoint(self):
        """Checkpoint session state for next instance."""
        self.hale_bus.checkpoint_session()

    def handback_to_claude_code(self):
        """Release missions and hand back to Claude Code."""
        self.hale_bus.handback_to_claude_code("opencode")
        self.checkpoint()
        print("[OpenCode] Handed back to Claude Code", file=sys.stderr)

    def print_status(self):
        """Print dispatcher status."""
        print("\n[OpenCode Dispatcher Status]", file=sys.stderr)
        print(f"  Prior context loaded: {len(self.prior_context.get('open_tasks', []))} tasks", file=sys.stderr)
        print(f"  Alerts: {len(self.prior_context.get('alerts', []))}", file=sys.stderr)
        print(f"  FPD deadlines: {len(self.prior_context.get('fpd_deadlines', []))}", file=sys.stderr)
        print(f"  Cached ZEN: {len(self.prior_context.get('cached_zen', {}))}", file=sys.stderr)


if __name__ == "__main__":
    # Test
    dispatcher = OpenCodeDispatcher()
    dispatcher.print_status()

    # Test routing
    test_prompts = [
        "Extract JSON from this",
        "Counter my argument",
        "Summarize the data",
    ]

    for prompt in test_prompts:
        try:
            result, tool, metadata = dispatcher.route_and_execute(prompt)
            print(f"\n[Test] {prompt[:30]}...")
            print(f"  Tool: {tool}")
            print(f"  Intent: {metadata.get('intent', 'N/A')}")
        except Exception as e:
            print(f"[Test ERROR] {e}")

    # Checkpoint
    dispatcher.checkpoint()
    print("\n[OpenCode] Session checkpointed for next instance", file=sys.stderr)

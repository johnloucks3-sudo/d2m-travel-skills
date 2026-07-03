#!/usr/bin/env python3
"""
claude_code_prompt_handler.py — Lightweight prompt handler for Claude Code main loop.

Used in the main Claude Code session to:
1. Detect Commander keywords (@ctx, @zen, @free, @oc)
2. Classify prompts via keyword router
3. Route to appropriate tool (ctx_execute, free_infer, default Claude)

Integration: Call from main session loop when processing user input

Usage:
    from core.ai_infra.claude_code_prompt_handler import ClaudeCodePromptHandler

    handler = ClaudeCodePromptHandler()
    action, metadata = handler.process(user_prompt)

    # action can be:
    #   - "ctx_execute_file" → use ctx_execute tool
    #   - "free_infer" → use free model router
    #   - "zen_reasoning" → use ZEN counter-voice
    #   - "handoff_opencode" → checkpoint and hand off
    #   - "default_claude" → route to Haiku/Sonnet
"""

import sys
import os
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

ROOT = Path(__file__).parent.parent.parent


class ClaudeCodePromptHandler:
    """Main loop prompt handler with keyword routing."""

    def __init__(self):
        """Initialize router on first use."""
        self.router = None
        self.hale_bus = None
        self._initialized = False

    def process(self, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process user prompt and return action.

        Args:
            user_prompt: text from Commander

        Returns:
            (action, metadata)
            action: "ctx_execute_file", "free_infer", "zen_reasoning", "handoff_opencode", "default_claude"
            metadata: rule config, provider, model, etc.
        """

        # Lazy init on first call
        if not self._initialized:
            self._init()

        # 1. Parse Commander keyword if present
        from core.ai_infra.keyword_auto_router import parse_commander_keyword
        keyword = parse_commander_keyword(user_prompt)

        # 2. Classify via router
        layer, rule = self.router.classify(user_prompt, override_keyword=keyword)

        # 3. Map layer to action
        action = self._layer_to_action(layer)

        # Log routing decision
        self.router.log_routing(user_prompt, layer, rule.get("model", ""), cost=0.0)

        return action, rule

    def _init(self):
        """Initialize router and hale_bus."""
        try:
            from core.ai_infra.keyword_auto_router import KeywordAutoRouter
            from core.hale_bus.hale_bus_handoff import HaleBusHandoff

            self.router = KeywordAutoRouter()
            self.hale_bus = HaleBusHandoff("claude-code")
            self._initialized = True

            print("[ClaudeCodePromptHandler] ✅ Initialized", file=sys.stderr)

        except Exception as e:
            print(f"[ClaudeCodePromptHandler] ⚠️  Init failed: {e}", file=sys.stderr)
            raise

    def _layer_to_action(self, layer: str) -> str:
        """Map router layer to action name."""
        mapping = {
            "ctx_data_processing": "ctx_execute_file",
            "ctx_parallel_monitoring": "ctx_batch_execute",
            "zen_independent_reasoning": "zen_reasoning",
            "free_synthesis": "free_infer",
            "free_extraction": "free_infer",
            "handoff_opencode": "handoff_opencode",
            "opencode_handback": "handback_from_opencode",
            "default_claude": "default_claude",
        }
        return mapping.get(layer, "default_claude")

    def checkpoint(self):
        """Checkpoint session state (call on shutdown)."""
        if self.hale_bus:
            self.hale_bus.checkpoint_session()
            print("[ClaudeCodePromptHandler] Session checkpointed", file=sys.stderr)

    def print_usage_log(self):
        """Print routing usage log (for diagnostics)."""
        if self.router:
            print(self.router.dump_usage_log(), file=sys.stderr)


# Global singleton instance (optional convenience)
_handler = None


def get_handler() -> ClaudeCodePromptHandler:
    """Get or create global handler instance."""
    global _handler
    if _handler is None:
        _handler = ClaudeCodePromptHandler()
    return _handler


def process_prompt(user_prompt: str) -> Tuple[str, Dict[str, Any]]:
    """Convenience function to process prompt via global handler."""
    return get_handler().process(user_prompt)


def checkpoint_on_exit():
    """Convenience function to checkpoint on session exit."""
    global _handler
    if _handler:
        _handler.checkpoint()


if __name__ == "__main__":
    # Quick test
    handler = ClaudeCodePromptHandler()

    test_prompts = [
        "Extract JSON from this log",
        "Counter my argument with refutation",
        "Compare these two approaches",
        "Default request",
        "@oc takeover needed",
    ]

    print("[Test] Processing prompts...\n", file=sys.stderr)

    for prompt in test_prompts:
        action, rule = handler.process(prompt)
        print(f"Prompt: {prompt[:40]}")
        print(f"  → Action: {action}")
        print(f"  → Model: {rule.get('model', 'N/A')}\n")

    # Checkpoint
    handler.checkpoint()

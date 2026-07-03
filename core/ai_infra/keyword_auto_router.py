#!/usr/bin/env python3
"""
keyword_auto_router.py — Intelligent prompt classifier & router.

Routes prompts to: ctx_execute_file (sandbox), ctx_batch_execute (parallel),
free_infer (Groq/Cerebras/GitHub/Ollama), ZEN (poe/deepseek), or Claude (default).

Respects Commander keywords: @ctx, @zen, @free, @oc, @oc-takeover.
Loads routing config from config/keyword_router_enhanced.yaml.

Usage:
    from core.ai_infra.keyword_auto_router import KeywordAutoRouter

    router = KeywordAutoRouter()
    tool, rule = router.classify(prompt)
    # → ("ctx_data_processing", {...}), ("zen_independent_reasoning", {...}), etc.
"""

import os
import sys
import yaml
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

ROOT = Path(__file__).parent.parent.parent


class KeywordAutoRouter:
    """Classify prompts and route to appropriate tool/model."""

    def __init__(self, config_path: Optional[Path] = None):
        """Load routing config from YAML."""
        if config_path is None:
            config_path = ROOT / "config" / "keyword_router_enhanced.yaml"

        self.config_path = config_path
        self.config = self._load_config()
        self.usage_log = []

    def _load_config(self) -> dict:
        """Load routing config YAML."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")

        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def classify(self, prompt: str, override_keyword: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Classify prompt by keyword and return (layer_name, rule_config).

        Args:
            prompt: user input
            override_keyword: if Commander typed @ctx, @zen, @free, @oc, use that

        Returns:
            ("ctx_data_processing", {...}), ("zen_independent_reasoning", {...}), etc.
        """

        # Commander override takes precedence
        if override_keyword:
            return self._handle_override(override_keyword)

        prompt_lower = prompt.lower()
        rules = self.config.get("routing_rules", {})

        # Check in order: ctx > zen > free > default
        # Layer 1: Sandbox data processing (zero-cost)
        for layer in ["ctx_data_processing", "ctx_parallel_monitoring"]:
            if layer in rules and self._keyword_match(prompt_lower, rules[layer].get("keywords", [])):
                return layer, rules[layer]

        # Layer 2: ZEN counter-reasoning
        if "zen_independent_reasoning" in rules and self._keyword_match(prompt_lower, rules["zen_independent_reasoning"].get("keywords", [])):
            return "zen_independent_reasoning", rules["zen_independent_reasoning"]

        # Layer 3: Free model synthesis & extraction
        for layer in ["free_synthesis", "free_extraction"]:
            if layer in rules and self._keyword_match(prompt_lower, rules[layer].get("keywords", [])):
                return layer, rules[layer]

        # Layer 4: Default to Claude
        return "default_claude", rules.get("default_claude", {})

    def _keyword_match(self, prompt_lower: str, keywords: list) -> bool:
        """Check if any keyword appears in prompt."""
        return any(kw.lower() in prompt_lower for kw in keywords)

    def _handle_override(self, keyword: str) -> Tuple[str, Dict[str, Any]]:
        """Handle Commander @ctx, @zen, @free, @oc, @oc-takeover."""
        rules = self.config.get("routing_rules", {})

        if keyword == "@ctx":
            return "ctx_data_processing", rules.get("ctx_data_processing", {})
        elif keyword == "@ctx-only":
            return "ctx_data_processing", rules.get("ctx_data_processing", {})
        elif keyword == "@zen":
            return "zen_independent_reasoning", rules.get("zen_independent_reasoning", {})
        elif keyword == "@zen-only":
            return "zen_independent_reasoning", rules.get("zen_independent_reasoning", {})
        elif keyword == "@free":
            return "free_synthesis", rules.get("free_synthesis", {})
        elif keyword == "@free-only":
            return "free_synthesis", rules.get("free_synthesis", {})
        elif keyword in ["@oc", "@oc-takeover", "@oc-primary"]:
            return "handoff_opencode", {"keyword": keyword}
        else:
            return "default_claude", rules.get("default_claude", {})

    def log_routing(self, prompt: str, layer: str, model: str, cost: float = 0.0):
        """Log routing decision for analytics."""
        self.usage_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "prompt_preview": prompt[:100],
            "layer": layer,
            "model": model,
            "tokens_or_cost": cost,
        })

    def dump_usage_log(self) -> str:
        """Return formatted usage log."""
        lines = ["# Keyword Router Usage Log\n"]
        for entry in self.usage_log:
            lines.append(f"[{entry['timestamp']}] {entry['layer']} ({entry['model']}) — {entry['prompt_preview']}")
        return "\n".join(lines)


def parse_commander_keyword(text: str) -> Optional[str]:
    """Extract Commander keyword from text if present (@ctx, @zen, @free, @oc, etc.)."""
    tokens = text.split()
    for token in tokens:
        if token.startswith("@") and token in [
            "@ctx", "@ctx-only",
            "@zen", "@zen-only",
            "@free", "@free-only",
            "@oc", "@oc-takeover", "@oc-primary",
        ]:
            return token
    return None


def route_and_execute(
    prompt: str,
    router: KeywordAutoRouter,
    override_keyword: Optional[str] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Route prompt and return execution result.

    Returns:
        (result_text, tool_used, rule_metadata)
    """
    layer, rule = router.classify(prompt, override_keyword)

    # Dispatch based on layer
    if layer.startswith("ctx_"):
        # Sandbox execution (ctx_execute_file, ctx_batch_execute)
        return _execute_ctx_tool(prompt, layer, rule, router)

    elif layer == "zen_independent_reasoning":
        # ZEN counter-voice
        return _execute_zen(prompt, rule, router)

    elif layer.startswith("free_"):
        # Free model inference
        return _execute_free_infer(prompt, layer, rule, router)

    elif layer == "handoff_opencode":
        # Hand off to OpenCode
        return _handoff_to_opencode(prompt, rule, router)

    else:  # default_claude
        # Route to Claude (Haiku or escalate)
        return _execute_claude(prompt, rule, router)


def _execute_ctx_tool(prompt: str, layer: str, rule: dict, router: KeywordAutoRouter) -> Tuple[str, str, dict]:
    """Execute sandbox data processing."""
    tool = rule.get("tool", "ctx_execute_file")
    intent = rule.get("intent", "data processing")

    # For now, return metadata; actual execution happens in caller
    result = f"[{tool}] Ready for {intent}"
    router.log_routing(prompt, layer, tool, cost=0.0)

    return result, tool, rule


def _execute_zen(prompt: str, rule: dict, router: KeywordAutoRouter) -> Tuple[str, str, dict]:
    """Execute ZEN counter-reasoning via free_infer or Poe."""
    from core.ai_infra.free_model_router import free_infer

    provider_chain = rule.get("provider_chain", ["github-r1", "groq-llama"])
    model = rule.get("model", "DeepSeek-R1")
    max_tokens = rule.get("max_tokens", 500)

    # Try primary provider first
    for provider_alias in provider_chain:
        try:
            result = free_infer(prompt, provider=provider_alias, model=model, max_tokens=max_tokens)
            router.log_routing(prompt, "zen_independent_reasoning", provider_alias, cost=0.0)
            return result, provider_alias, rule
        except Exception as e:
            print(f"[zen] {provider_alias} failed: {e}", file=sys.stderr)
            continue

    # All providers failed
    raise RuntimeError(f"ZEN reasoning failed across all providers: {provider_chain}")


def _execute_free_infer(prompt: str, layer: str, rule: dict, router: KeywordAutoRouter) -> Tuple[str, str, dict]:
    """Execute free model inference (Groq, Cerebras, GitHub, Ollama)."""
    from core.ai_infra.free_model_router import free_infer

    provider_chain = rule.get("provider_chain", ["groq"])
    model = rule.get("model", "llama-3.3-70b-versatile")
    max_tokens = rule.get("max_tokens", 2048)
    temperature = rule.get("temperature", 0.7)

    for provider_alias in provider_chain:
        try:
            result = free_infer(
                prompt,
                provider=provider_alias,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            router.log_routing(prompt, layer, model, cost=0.0)
            return result, provider_alias, rule
        except Exception as e:
            print(f"[free_infer] {provider_alias} failed: {e}", file=sys.stderr)
            continue

    raise RuntimeError(f"Free inference failed across all providers: {provider_chain}")


def _execute_claude(prompt: str, rule: dict, router: KeywordAutoRouter) -> Tuple[str, str, dict]:
    """Execute Claude (Haiku default, escalate on error)."""
    # Placeholder — actual execution via Claude Code session
    result = "[Claude] Ready for execution"
    model = rule.get("model", "claude-haiku-4-5")
    router.log_routing(prompt, "default_claude", model, cost=0.002)

    return result, model, rule


def _handoff_to_opencode(prompt: str, rule: dict, router: KeywordAutoRouter) -> Tuple[str, str, dict]:
    """Hand off to OpenCode orchestration."""
    from core.hale_bus.hale_bus_handoff import HaleBusHandoff

    hale_bus = HaleBusHandoff("claude-code")
    hale_bus.checkpoint_session()

    keyword = rule.get("keyword", "@oc")
    result = f"[Handoff to OpenCode] {keyword} — state checkpointed to hale_bus_state.json"

    router.log_routing(prompt, "handoff_opencode", "opencode", cost=0.0)

    return result, "opencode", rule


if __name__ == "__main__":
    # Quick test
    router = KeywordAutoRouter()

    test_prompts = [
        "Extract JSON from this log file",
        "Counter my argument with a refutation",
        "Compare these two approaches",
        "Run a health check on all systems",
        "What's your take on this?",
    ]

    for prompt in test_prompts:
        layer, rule = router.classify(prompt)
        print(f"\nPrompt: {prompt[:50]}")
        print(f"  → Layer: {layer}")
        print(f"  → Intent: {rule.get('intent', 'N/A')}")

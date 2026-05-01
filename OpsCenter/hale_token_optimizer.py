#!/usr/bin/env python3
"""
Hale Token Optimizer — Token Efficiency Decision Engine
========================================================
Before dispatching ANY task, apply token optimization strategies.
Assesses model selection, context compression, lazy loading, output specs.

Usage:
    from hale_token_optimizer import HaleTokenOptimizer
    optimizer = HaleTokenOptimizer()
    optimized_task = optimizer.assess_and_optimize(task_text, task_type, context)
    result = dispatch_to_model(optimized_task)
"""

import re
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class OptimizationResult:
    """Result of token optimization assessment."""
    model: str  # "haiku", "sonnet", "opus"
    optimized_prompt: str
    context_compressed: bool
    compression_ratio: float  # 1.0 = no compression, 0.5 = 50% reduction
    output_spec: str  # e.g., "JSON, 300 tokens max"
    savings_estimate: int  # tokens saved vs unoptimized
    strategy_applied: list  # ["lazy_loading", "compression", ...]

class HaleTokenOptimizer:
    """Apply TOKEN OPTIMIZATION PLAYBOOK before dispatch."""

    # Model decision keywords (from playbook)
    HAIKU_KEYWORDS = {
        "format", "json", "csv", "convert", "restructure",
        "summarize", "condense", "extract", "tag", "label", "classify",
        "route", "simple", "list", "filter", "parse", "clean",
    }

    OPUS_KEYWORDS = {
        "arbitrate", "conflict", "policy", "precedent", "final call",
        "deep", "complex", "high-stakes", "judgment",
    }

    def __init__(self):
        self.token_log = []

    def assess_and_optimize(
        self,
        task_text: str,
        task_type: str = "general",
        context: Optional[str] = None,
        client_facing: bool = False,
    ) -> OptimizationResult:
        """
        Assess task and apply optimization strategies.
        Returns OptimizationResult with optimized prompt and model selection.
        """

        strategies_applied = []
        optimized_prompt = task_text
        compression_ratio = 1.0
        output_spec = ""
        savings_estimate = 0

        # STEP 1: SELECT MODEL
        model = self._select_model(task_text, task_type, client_facing)

        # STEP 2: COMPRESS CONTEXT (if provided)
        if context:
            compressed_context, ratio = self._compress_context(context)
            compression_ratio = ratio
            if ratio < 0.95:  # Only if meaningful compression happened
                strategies_applied.append("context_compression")
                savings_estimate += int(len(context) * (1 - ratio) * 0.7)  # 70% token save from compression

        # STEP 3: LAZY LOAD CONTEXT (if task doesn't explicitly need full context)
        if context and not self._needs_full_context(task_text):
            strategies_applied.append("lazy_context_loading")
            # Don't include context in initial prompt; note to request if needed
            context_note = "\n[NOTE: Full context available if needed — ask for specific fields]"
            optimized_prompt = task_text + context_note
            savings_estimate += int(len(context) * 0.5)  # Assume 50% of context won't be needed
        elif context and compression_ratio < 1.0:
            optimized_prompt = f"{task_text}\n\n[CONTEXT]\n{compressed_context}"

        # STEP 4: ADD OUTPUT SPECIFICATION (reduce verbosity)
        output_spec = self._generate_output_spec(task_text, model)
        if output_spec:
            strategies_applied.append("output_specification")
            optimized_prompt += f"\n\n[OUTPUT SPEC] {output_spec}"
            savings_estimate += 100  # Estimate 100 tokens saved from shorter output

        # STEP 5: BATCH CHECK (if applicable)
        if self._is_batchable(task_text):
            strategies_applied.append("note_batchable")
            optimized_prompt += "\n[NOTE: This task is batchable with similar tasks — consider grouping]"

        return OptimizationResult(
            model=model,
            optimized_prompt=optimized_prompt,
            context_compressed=compression_ratio < 1.0,
            compression_ratio=compression_ratio,
            output_spec=output_spec,
            savings_estimate=savings_estimate,
            strategy_applied=strategies_applied,
        )

    def _select_model(self, task_text: str, task_type: str, client_facing: bool) -> str:
        """
        Model selection decision tree (from playbook):
        - Haiku for formatting, summarization, extraction, classification
        - Sonnet for strategy, client-facing, synthesis, voice
        - Opus for arbitration, policy, high-stakes judgment
        """
        task_lower = task_text.lower() + " " + task_type.lower()

        # OPUS: High-stakes, arbitration, policy
        if any(kw in task_lower for kw in self.OPUS_KEYWORDS):
            return "opus"

        # SONNET: Client-facing, strategy, synthesis
        if client_facing:
            return "sonnet"

        if any(kw in task_lower for kw in {"strategy", "synthesis", "analyze", "recommend", "voice", "proposal"}):
            return "sonnet"

        # HAIKU: Formatting, summarization, extraction, simple routing
        if any(kw in task_lower for kw in self.HAIKU_KEYWORDS):
            return "haiku"

        # DEFAULT: Sonnet (safe default for unknown tasks)
        return "sonnet"

    def _compress_context(self, context: str) -> Tuple[str, float]:
        """
        Compress context by extracting only relevant fields.
        Returns (compressed_context, compression_ratio).
        """
        # Remove excessive whitespace and redundant sections
        lines = context.strip().split("\n")
        essential_lines = [
            line for line in lines
            if line.strip() and not self._is_redundant(line)
        ]

        # Keep ~30% of original context (most important info)
        if len(essential_lines) > 10:
            essential_lines = essential_lines[:10]

        compressed = "\n".join(essential_lines)
        ratio = len(compressed) / len(context) if context else 1.0
        return compressed, ratio

    def _is_redundant(self, line: str) -> bool:
        """Check if line is redundant (timestamps, headers, etc)."""
        redundant_patterns = [
            r"^={5,}",  # Section headers
            r"^\-{5,}",
            r"Updated at",
            r"Last seen",
            r"Status: active",
        ]
        return any(re.search(pattern, line) for pattern in redundant_patterns)

    def _needs_full_context(self, task_text: str) -> bool:
        """Check if task explicitly requires full context."""
        explicit_keywords = {
            "full", "all", "everything", "complete", "entire",
            "comprehensive", "detailed", "background",
        }
        task_lower = task_text.lower()
        return any(kw in task_lower for kw in explicit_keywords)

    def _generate_output_spec(self, task_text: str, model: str) -> str:
        """Generate output specification to reduce token waste."""
        specs = []

        # Check for output format requests
        if "json" in task_text.lower():
            specs.append("JSON format")
        if "table" in task_text.lower() or "csv" in task_text.lower():
            specs.append("table format (pipe-delimited)")

        # Check for length requests
        if "brief" in task_text.lower() or "short" in task_text.lower():
            specs.append("max 200 tokens")
        elif "summary" in task_text.lower():
            specs.append("max 300 tokens")
        elif "detailed" in task_text.lower():
            specs.append("max 800 tokens")
        else:
            # Default: haiku gets shorter, sonnet/opus get full
            if model == "haiku":
                specs.append("max 200 tokens")
            else:
                specs.append("max 500 tokens")

        # Check for list/bullet requests
        if "list" in task_text.lower() or "bullet" in task_text.lower():
            specs.append("bullets only, no explanation")
        if "top" in task_text.lower() and ("3" in task_text or "5" in task_text or "10" in task_text):
            specs.append("list items only, most important first")

        return ", ".join(specs) if specs else ""

    def _is_batchable(self, task_text: str) -> bool:
        """Check if task could be batched with similar tasks."""
        batchable_keywords = {
            "format", "extract", "tag", "classify", "route", "summarize",
        }
        task_lower = task_text.lower()
        return any(kw in task_lower for kw in batchable_keywords)

    def log_dispatch(
        self,
        task_type: str,
        model: str,
        baseline_tokens: int,
        optimized_tokens: int,
        strategies: list,
    ):
        """Log dispatch for weekly tracking."""
        savings = baseline_tokens - optimized_tokens
        savings_pct = (savings / baseline_tokens * 100) if baseline_tokens > 0 else 0
        self.token_log.append({
            "task_type": task_type,
            "model": model,
            "baseline": baseline_tokens,
            "optimized": optimized_tokens,
            "savings": savings,
            "savings_pct": savings_pct,
            "strategies": strategies,
        })

    def print_weekly_summary(self):
        """Print token savings summary for the week."""
        if not self.token_log:
            print("No tasks logged yet.")
            return

        total_baseline = sum(log["baseline"] for log in self.token_log)
        total_optimized = sum(log["optimized"] for log in self.token_log)
        total_savings = total_baseline - total_optimized
        total_savings_pct = (total_savings / total_baseline * 100) if total_baseline > 0 else 0

        print(f"\n{'='*60}")
        print(f"WEEKLY TOKEN OPTIMIZATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total tasks: {len(self.token_log)}")
        print(f"Baseline tokens: {total_baseline:,}")
        print(f"Optimized tokens: {total_optimized:,}")
        print(f"Total savings: {total_savings:,} tokens ({total_savings_pct:.1f}%)")
        print(f"{'='*60}\n")

        # Print by model
        for model_name in ["haiku", "sonnet", "opus"]:
            model_tasks = [log for log in self.token_log if log["model"] == model_name]
            if model_tasks:
                model_baseline = sum(log["baseline"] for log in model_tasks)
                model_optimized = sum(log["optimized"] for log in model_tasks)
                model_savings_pct = ((model_baseline - model_optimized) / model_baseline * 100) if model_baseline > 0 else 0
                print(f"{model_name.upper():8} | {len(model_tasks):3} tasks | "
                      f"{model_baseline:6,} → {model_optimized:6,} tokens | "
                      f"{model_savings_pct:5.1f}% saved")

if __name__ == "__main__":
    # Test the optimizer
    optimizer = HaleTokenOptimizer()

    # Test 1: Formatting task
    result = optimizer.assess_and_optimize(
        "Convert this booking into JSON format",
        task_type="formatting",
        context="Full booking details here (3K tokens)",
        client_facing=False,
    )
    print(f"\nTest 1: Formatting")
    print(f"  Model: {result.model}")
    print(f"  Strategies: {result.strategy_applied}")
    print(f"  Estimated savings: {result.savings_estimate} tokens")

    # Test 2: Client-facing email
    result = optimizer.assess_and_optimize(
        "Draft an email to confirm the client's booking",
        task_type="client_email",
        client_facing=True,
    )
    print(f"\nTest 2: Client email")
    print(f"  Model: {result.model}")
    print(f"  Output spec: {result.output_spec}")

    # Test 3: Arbitration
    result = optimizer.assess_and_optimize(
        "Arbitrate between these two cabin recommendations",
        task_type="arbitration",
    )
    print(f"\nTest 3: Arbitration")
    print(f"  Model: {result.model} (escalated to Opus)")

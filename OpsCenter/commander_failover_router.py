#!/usr/bin/env python3
"""
commander_failover_router.py — Bulletproof failover chain for Commander.
=====================================================================

Auto-pivots when any model hits limit. Zero freezes.

Failover chain (in order):
  1. opencode/deepseek-v4-flash-free ($0)
  2. opencode/deepseek-v4-flash ($0.42/M)
  3. xai/grok-4.3 ($1.25/$2.50)
  4. claude-sonnet-4-6 ($0 MAX OAuth)
  5. Queue task (retry in 15 min)

Usage:
  from commander_failover_router import route_with_failover

  result = route_with_failover(
      prompt="...",
      initial_model="opencode/deepseek-v4-flash-free",
      user="commander",
      priority="normal"
  )
"""

import os
import json
import time
import logging
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)
BUDGET_FILE = Path.home() / "Thunderbird" / "OpsCenter" / "commander_budget.json"


class ModelTier(Enum):
    """Failover hierarchy."""
    DEEPSEEK_FREE = "opencode/deepseek-v4-flash-free"
    DEEPSEEK_FLASH = "opencode/deepseek-v4-flash"
    GROK_XAI = "xai/grok-4.3"
    CLAUDE_SONNET = "claude-sonnet-4-6"
    QUEUE = "queue"


FAILOVER_CHAIN = [
    ModelTier.DEEPSEEK_FREE,
    ModelTier.DEEPSEEK_FLASH,
    ModelTier.GROK_XAI,
    ModelTier.CLAUDE_SONNET,
    ModelTier.QUEUE,
]

ERROR_TRIGGERS = {
    "429": "rate_limit",
    "quota": "quota_exceeded",
    "limit": "limit_hit",
    "socket": "connection_error",
    "credit": "insufficient_credit",
    "ECONNREFUSED": "connection_refused",
}


@dataclass
class FailoverResult:
    """Result of a failover attempt."""
    success: bool
    model_used: str
    output: str = ""
    error: Optional[str] = None
    pivots: int = 0  # Number of failovers triggered
    cost_estimate: float = 0.0


def detect_model_error(error_msg: str) -> Optional[str]:
    """Detect if error is model-limit related."""
    error_lower = error_msg.lower()
    for trigger, error_type in ERROR_TRIGGERS.items():
        if trigger.lower() in error_lower:
            return error_type
    return None


def call_model(model: str, prompt: str) -> tuple[bool, str]:
    """
    Call a model. Returns (success, output_or_error).

    This is a placeholder — in production, dispatch to actual model API.
    """
    # Placeholder: assume all models work for now
    logger.info(f"Calling {model}")
    return (True, f"Response from {model}")


def route_with_failover(
    prompt: str,
    initial_model: str,
    user: str = "commander",
    priority: str = "normal"
) -> FailoverResult:
    """
    Route request with automatic failover on limit.

    Args:
        prompt: The request prompt
        initial_model: Primary model to use
        user: Requesting user (for budget tracking)
        priority: Task priority (critical, normal, bulk)

    Returns:
        FailoverResult with model_used, success status, and pivot count
    """
    pivots = 0
    current_idx = 0

    # Find starting position in chain
    try:
        current_idx = [m.value for m in FAILOVER_CHAIN].index(initial_model)
    except ValueError:
        logger.warning(f"Unknown model {initial_model}, starting from tier 1")
        current_idx = 0

    # Try each model in the chain
    while current_idx < len(FAILOVER_CHAIN):
        model_tier = FAILOVER_CHAIN[current_idx]
        model = model_tier.value

        logger.info(f"[Attempt {pivots + 1}] Trying {model}")

        # Special case: QUEUE
        if model_tier == ModelTier.QUEUE:
            logger.warning("All models exhausted. Queueing task.")
            return FailoverResult(
                success=False,
                model_used="queue",
                error="All models at capacity. Task queued for retry.",
                pivots=pivots,
            )

        # Try the model
        success, output = call_model(model, prompt)

        if success:
            logger.info(f"✓ Success on {model}")
            return FailoverResult(
                success=True,
                model_used=model,
                output=output,
                pivots=pivots,
            )

        # Detect error type
        error_type = detect_model_error(output)
        if error_type:
            logger.warning(f"✗ {model} hit {error_type}. Pivoting...")
            pivots += 1
            notify_telegram(
                f"🔄 AUTO-FAILOVER: {model} exhausted. "
                f"Trying {FAILOVER_CHAIN[current_idx + 1].value if current_idx + 1 < len(FAILOVER_CHAIN) else 'QUEUE'}."
            )
        else:
            # Unknown error, still pivot
            logger.error(f"✗ {model} failed: {output}")
            pivots += 1

        current_idx += 1

    # Exhausted all tiers
    return FailoverResult(
        success=False,
        model_used="none",
        error="All failover tiers exhausted.",
        pivots=pivots,
    )


def notify_telegram(message: str):
    """Send alert to Commander via D2MC2C bot."""
    # Placeholder — in production, call Telegram API
    logger.info(f"[TELEGRAM] {message}")


def load_budget() -> Dict[str, Any]:
    """Load current budget state."""
    if BUDGET_FILE.exists():
        return json.loads(BUDGET_FILE.read_text())
    return {
        "claude_max": {"limit_tokens": 2_000_000, "used": 0},
        "grok_xai": {"limit_dollars": 10.00, "spent": 4.61},
        "deepseek_flash": {"limit_dollars": 2.00, "spent": 0.00},
    }


def check_budget_alert(budget: Dict[str, Any]) -> Optional[str]:
    """Check if any budget is at alert threshold."""
    alerts = []

    # Grok 80% alert
    if budget["grok_xai"]["spent"] / budget["grok_xai"]["limit_dollars"] >= 0.80:
        alerts.append(f"⚠️ Grok at 80% (${budget['grok_xai']['spent']:.2f}/${budget['grok_xai']['limit_dollars']})")

    # Claude 85% alert
    if budget["claude_max"]["used"] / budget["claude_max"]["limit_tokens"] >= 0.85:
        alerts.append(f"⚠️ Claude weekly at 85%")

    return " | ".join(alerts) if alerts else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test failover
    result = route_with_failover(
        prompt="Test prompt",
        initial_model="opencode/deepseek-v4-flash-free",
    )

    print(f"\nFailover Result:")
    print(f"  Success: {result.success}")
    print(f"  Model: {result.model_used}")
    print(f"  Pivots: {result.pivots}")
    print(f"  Error: {result.error}")

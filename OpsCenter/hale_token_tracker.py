#!/usr/bin/env python3
"""
Hale Token Tracker — Track API usage and costs integrated into hale_state_unified.json
Hooks into hale_dispatcher to log every dispatch with token counts and cost calculations.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

STATE_FILE = Path("/home/john/Thunderbird/hale_state_unified.json")

class HaleTokenTracker:
    """Track tokens, costs, and budgets across all dispatches (Claude Code + OpenCode)."""

    # Cost per 1M tokens (latest pricing)
    COSTS = {
        "haiku": {"input": 40, "output": 120},      # cents per 1M
        "sonnet": {"input": 300, "output": 900},    # cents per 1M
        "opus": {"input": 1500, "output": 4500},    # cents per 1M
    }

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load unified state from disk."""
        if not STATE_FILE.exists():
            return {"token_tracking": self._init_tracking()}
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            return {"token_tracking": self._init_tracking()}

    def _init_tracking(self) -> Dict:
        """Initialize empty tracking structure."""
        return {
            "status": "LIVE",
            "current_session": {
                "session_start": datetime.now().isoformat(),
                "tokens_input": 0,
                "tokens_output": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "dispatch_count": 0,
                "last_dispatch": None,
            },
            "models": {
                "haiku": {"session_tokens": 0, "weekly_tokens": 0, "dispatch_count": 0},
                "sonnet": {"session_tokens": 0, "weekly_tokens": 0, "dispatch_count": 0},
                "opus": {"session_tokens": 0, "weekly_tokens": 0, "dispatch_count": 0},
            },
            "budget": {
                "weekly_limit_usd": 100.0,
                "weekly_spent_usd": 0.0,
                "alert_threshold_pct": 80,
            },
            "dispatch_log": [],
        }

    def log_dispatch(
        self,
        model: str,
        tokens_input: int,
        tokens_output: int,
        task_name: str,
        task_brief: str = "",
    ) -> Dict[str, Any]:
        """
        Log a dispatch with token counts and calculate costs.
        Called by hale_dispatcher after each brain dispatch.
        """
        if model not in self.COSTS:
            model = "sonnet"

        # Calculate cost in USD
        cost_input = (tokens_input / 1_000_000) * self.COSTS[model]["input"] / 100
        cost_output = (tokens_output / 1_000_000) * self.COSTS[model]["output"] / 100
        cost_usd = cost_input + cost_output
        total_tokens = tokens_input + tokens_output

        # Update session totals
        self.state["token_tracking"]["current_session"]["tokens_input"] += tokens_input
        self.state["token_tracking"]["current_session"]["tokens_output"] += tokens_output
        self.state["token_tracking"]["current_session"]["total_tokens"] += total_tokens
        self.state["token_tracking"]["current_session"]["cost_usd"] += cost_usd
        self.state["token_tracking"]["current_session"]["dispatch_count"] += 1
        self.state["token_tracking"]["current_session"]["last_dispatch"] = datetime.now().isoformat()

        # Update by-model totals
        self.state["token_tracking"]["models"][model]["session_tokens"] += total_tokens
        self.state["token_tracking"]["models"][model]["weekly_tokens"] += total_tokens
        self.state["token_tracking"]["models"][model]["dispatch_count"] += 1

        # Update budget
        self.state["token_tracking"]["budget"]["weekly_spent_usd"] += cost_usd
        self.state["token_tracking"]["budget"]["weekly_remaining_usd"] = (
            self.state["token_tracking"]["budget"]["weekly_limit_usd"]
            - self.state["token_tracking"]["budget"]["weekly_spent_usd"]
        )

        # Create dispatch log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "total_tokens": total_tokens,
            "cost_usd": round(cost_usd, 4),
            "task_name": task_name,
            "task_brief": task_brief[:100] if task_brief else "",
        }
        self.state["token_tracking"]["dispatch_log"].append(log_entry)

        # Keep only last 100 entries in log
        if len(self.state["token_tracking"]["dispatch_log"]) > 100:
            self.state["token_tracking"]["dispatch_log"] = (
                self.state["token_tracking"]["dispatch_log"][-100:]
            )

        # Check budget alert
        budget_pct = (
            self.state["token_tracking"]["budget"]["weekly_spent_usd"]
            / self.state["token_tracking"]["budget"]["weekly_limit_usd"]
            * 100
        )
        alert = budget_pct >= self.state["token_tracking"]["budget"]["alert_threshold_pct"]

        # Save state
        self._save_state()

        return {
            "logged": True,
            "cost_usd": round(cost_usd, 4),
            "budget_pct": round(budget_pct, 1),
            "budget_alert": alert,
            "remaining_weekly": round(
                self.state["token_tracking"]["budget"]["weekly_remaining_usd"], 2
            ),
        }

    def get_session_summary(self) -> Dict[str, Any]:
        """Return session token usage summary."""
        session = self.state["token_tracking"]["current_session"]
        return {
            "session_start": session["session_start"],
            "total_tokens": session["total_tokens"],
            "total_cost_usd": round(session["cost_usd"], 2),
            "dispatch_count": session["dispatch_count"],
            "avg_tokens_per_dispatch": (
                session["total_tokens"] // session["dispatch_count"]
                if session["dispatch_count"] > 0
                else 0
            ),
            "avg_cost_per_dispatch": (
                round(session["cost_usd"] / session["dispatch_count"], 4)
                if session["dispatch_count"] > 0
                else 0.0
            ),
        }

    def get_weekly_summary(self) -> Dict[str, Any]:
        """Return weekly breakdown by model."""
        models = self.state["token_tracking"]["models"]
        budget = self.state["token_tracking"]["budget"]

        summary = {
            "week_start": (
                datetime.now() - timedelta(days=datetime.now().weekday())
            ).date().isoformat(),
            "total_tokens": sum(m["weekly_tokens"] for m in models.values()),
            "total_cost_usd": round(budget["weekly_spent_usd"], 2),
            "remaining_budget": round(budget["weekly_remaining_usd"], 2),
            "budget_pct_used": round(
                budget["weekly_spent_usd"] / budget["weekly_limit_usd"] * 100, 1
            ),
            "by_model": {},
        }

        for model_name, model_data in models.items():
            tokens = model_data["weekly_tokens"]
            cost = (tokens / 1_000_000) * (
                self.COSTS[model_name]["input"] + self.COSTS[model_name]["output"]
            ) / 200  # rough avg
            summary["by_model"][model_name] = {
                "tokens": tokens,
                "dispatch_count": model_data["dispatch_count"],
                "estimated_cost_usd": round(cost / 100, 2),
            }

        return summary

    def _save_state(self):
        """Write state back to disk."""
        STATE_FILE.write_text(json.dumps(self.state, indent=2))

    def reset_weekly(self):
        """Reset weekly counters (call at end of week)."""
        for model in self.state["token_tracking"]["models"].values():
            model["weekly_tokens"] = 0
        self.state["token_tracking"]["budget"]["weekly_spent_usd"] = 0.0
        self.state["token_tracking"]["budget"]["weekly_remaining_usd"] = (
            self.state["token_tracking"]["budget"]["weekly_limit_usd"]
        )
        self._save_state()


# Integration hook for hale_dispatcher
def track_dispatch(
    model: str,
    tokens_input: int,
    tokens_output: int,
    task_name: str,
    task_brief: str = "",
) -> Dict[str, Any]:
    """
    Public interface: Call this after dispatching to log token usage.
    Usage in hale_dispatcher.py:
        from hale_token_tracker import track_dispatch
        result = track_dispatch("sonnet", 1000, 2000, "email_classification", "Classify 5 emails")
    """
    tracker = HaleTokenTracker()
    return tracker.log_dispatch(model, tokens_input, tokens_output, task_name, task_brief)


if __name__ == "__main__":
    # Test
    tracker = HaleTokenTracker()

    # Log some test dispatches
    tracker.log_dispatch("haiku", 500, 300, "format_csv", "Format booking list")
    tracker.log_dispatch("sonnet", 2000, 1500, "email_draft", "Draft client email")
    tracker.log_dispatch("opus", 5000, 4000, "arbitrate_conflict", "Settle pricing dispute")

    # Print summaries
    print("\n=== SESSION SUMMARY ===")
    session = tracker.get_session_summary()
    for key, val in session.items():
        print(f"{key}: {val}")

    print("\n=== WEEKLY SUMMARY ===")
    weekly = tracker.get_weekly_summary()
    for key, val in weekly.items():
        if key == "by_model":
            print(f"{key}:")
            for model, data in val.items():
                print(f"  {model}: {data}")
        else:
            print(f"{key}: {val}")

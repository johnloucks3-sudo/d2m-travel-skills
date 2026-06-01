#!/usr/bin/env python3
"""
commander_budget_tracker.py — Real-time budget monitoring.
==========================================================

Tracks: Claude weekly tokens, Grok xAI spend.
Alerts at thresholds. Provides daily/weekly summaries.

Usage:
  from commander_budget_tracker import BudgetTracker

  tracker = BudgetTracker()
  tracker.log_usage("claude", tokens=1000)
  tracker.log_usage("grok_xai", cost=0.50)
  tracker.check_alerts()
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

BUDGET_FILE = Path.home() / "Thunderbird" / "OpsCenter" / "commander_budget.json"


class BudgetTracker:
    """Track Commander's model usage and budgets."""

    def __init__(self):
        self.budget = self._load_budget()
        self.alerts = []

    def _load_budget(self) -> Dict[str, Any]:
        """Load budget state from file."""
        if BUDGET_FILE.exists():
            return json.loads(BUDGET_FILE.read_text())

        return {
            "claude_max": {
                "limit_tokens_weekly": 2_000_000,
                "used_this_week": 847_000,
                "reserved_critical": 400_000,
                "alert_at_pct": 85,
            },
            "grok_xai": {
                "limit_dollars": 10.00,
                "spent": 4.61,
                "alert_at_pct": 80,
            },
            "deepseek_flash": {
                "limit_dollars": 2.00,
                "spent": 0.00,
                "is_fallback": True,
            },
            "last_alert": None,
            "last_summary": None,
        }

    def save_budget(self):
        """Persist budget to file."""
        BUDGET_FILE.write_text(json.dumps(self.budget, indent=2))

    def log_usage(self, model: str, tokens: int = 0, cost: float = 0.0):
        """Log usage for a model."""
        if model == "claude" and tokens > 0:
            self.budget["claude_max"]["used_this_week"] += tokens
        elif model == "grok_xai" and cost > 0:
            self.budget["grok_xai"]["spent"] += cost
        elif model == "deepseek_flash" and cost > 0:
            self.budget["deepseek_flash"]["spent"] += cost

        self.save_budget()

    def check_alerts(self) -> Optional[str]:
        """Check budget thresholds and return alert if needed."""
        alerts = []

        # Grok 80% check
        grok = self.budget["grok_xai"]
        grok_pct = (grok["spent"] / grok["limit_dollars"]) * 100
        if grok_pct >= grok["alert_at_pct"]:
            alerts.append(
                f"⚠️ GROK BUDGET: ${grok['spent']:.2f} of ${grok['limit_dollars']:.2f} ({grok_pct:.0f}%)"
            )

        # Claude 85% check
        claude = self.budget["claude_max"]
        claude_pct = (claude["used_this_week"] / claude["limit_tokens_weekly"]) * 100
        if claude_pct >= claude["alert_at_pct"]:
            remaining = claude["limit_tokens_weekly"] - claude["used_this_week"]
            alerts.append(
                f"⚠️ CLAUDE WEEKLY: {claude_pct:.0f}% used ({remaining:,} tokens remaining)"
            )

        if alerts:
            alert_msg = " | ".join(alerts)
            self.alerts.append(alert_msg)
            return alert_msg

        return None

    def get_daily_summary(self) -> str:
        """Generate daily summary for Telegram."""
        claude = self.budget["claude_max"]
        grok = self.budget["grok_xai"]

        claude_pct = (claude["used_this_week"] / claude["limit_tokens_weekly"]) * 100
        grok_pct = (grok["spent"] / grok["limit_dollars"]) * 100

        summary = f"""
📊 DAILY BUDGET REPORT — {datetime.now().strftime('%Y-%m-%d %H:%M')}

Claude MAX    │ {claude_pct:.0f}% ({claude['used_this_week']:,} / {claude['limit_tokens_weekly']:,} tokens)
Grok xAI      │ {grok_pct:.0f}% (${grok['spent']:.2f} / ${grok['limit_dollars']:.2f})
DeepSeek Free │ Fallback available

Status: {'✅ OK' if claude_pct < 85 and grok_pct < 80 else '⚠️ ALERT'}
""".strip()

        self.budget["last_summary"] = datetime.now().isoformat()
        self.save_budget()
        return summary

    def get_forecast(self) -> str:
        """Simple forecast based on burn rate."""
        grok = self.budget["grok_xai"]
        remaining = grok["limit_dollars"] - grok["spent"]

        if remaining <= 0:
            return "Grok budget exhausted. Using fallback."

        # Assume daily burn from last week
        # (This is simplified; real implementation would track daily)
        daily_burn = grok["spent"] / 7  # Average daily
        days_remaining = remaining / daily_burn if daily_burn > 0 else float('inf')

        return f"Grok: ~{days_remaining:.1f} days at current burn rate"


if __name__ == "__main__":
    tracker = BudgetTracker()

    print(tracker.get_daily_summary())
    print()
    print(tracker.get_forecast())
    print()
    alert = tracker.check_alerts()
    if alert:
        print(f"ALERT: {alert}")
    else:
        print("✓ All budgets OK")

#!/usr/bin/env python3
"""
Thunderbird OpenRouter Activity Monitor
========================================

Monitors OpenRouter usage, costs, and model performance for D2M operations.
Tracks daily/weekly/monthly spending, identifies cost anomalies, and provides
optimization recommendations.

Output: Daily digest + Telegram alerts for cost spikes
Integration: Runs as part of morning briefing + tech monitor pipeline
"""

import json
import logging
import os
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [OPENROUTER_MONITOR] - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/home/john/Thunderbird/logs/openrouter_monitor.log"),
        logging.StreamHandler(),
    ],
)

# Add Thunderbird to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class OpenRouterMonitor:
    """Monitor OpenRouter usage, costs, and model performance."""

    def __init__(self):
        self.api_key = os.environ.get(
            "OPENROUTER_API_KEY",
            "***REMOVED-SECRET***",
        )
        self.base_url = "https://openrouter.ai/api/v1"
        self.state_file = Path("/home/john/Thunderbird/state/openrouter_monitor.json")
        self.output_dir = Path("/home/john/Thunderbird/intel/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Cost thresholds (USD)
        self.thresholds = {
            "daily_warning": 2.0,      # Alert if daily > $2
            "daily_critical": 5.0,     # Alert if daily > $5
            "monthly_budget": 10.0,    # Monthly budget target
            "spike_multiplier": 3.0,   # Alert if > 3x daily average
        }

        # Load historical state
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load historical monitoring state."""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {
            "daily_history": [],
            "last_check": None,
            "alerts_sent": [],
            "baseline_daily_avg": 0.0,
        }

    def _save_state(self):
        """Persist monitoring state."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def _api_request(self, endpoint: str) -> Optional[Dict]:
        """Make authenticated API request to OpenRouter."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            return None

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics from OpenRouter."""
        data = self._api_request("auth/key")
        if not data or "data" not in data:
            return {"error": "Failed to fetch usage stats"}

        key_data = data["data"]
        return {
            "total_usage": float(key_data.get("usage", 0)),
            "daily_usage": float(key_data.get("usage_daily", 0)),
            "weekly_usage": float(key_data.get("usage_weekly", 0)),
            "monthly_usage": float(key_data.get("usage_monthly", 0)),
            "byok_usage": float(key_data.get("byok_usage", 0)),
            "is_free_tier": key_data.get("is_free_tier", False),
            "timestamp": datetime.now().isoformat(),
        }

    def get_credits(self) -> Dict[str, Any]:
        """Get credit balance information."""
        data = self._api_request("credits")
        if not data or "data" not in data:
            return {"error": "Failed to fetch credits"}

        credits_data = data["data"]
        return {
            "total_credits": float(credits_data.get("total_credits", 0)),
            "total_usage": float(credits_data.get("total_usage", 0)),
            "remaining": float(credits_data.get("total_credits", 0)) - float(credits_data.get("total_usage", 0)),
            "timestamp": datetime.now().isoformat(),
        }

    def get_models(self) -> List[Dict]:
        """Get available models with pricing."""
        data = self._api_request("models")
        if not data or "data" not in data:
            return []

        models = []
        for model in data["data"]:
            pricing = model.get("pricing", {})
            models.append({
                "id": model.get("id", ""),
                "name": model.get("name", ""),
                "prompt_price": float(pricing.get("prompt", 0)),
                "completion_price": float(pricing.get("completion", 0)),
                "context_length": model.get("context_length", 0),
                "top_provider": model.get("top_provider", ""),
            })

        # Sort by total cost (prompt + completion)
        models.sort(key=lambda m: m["prompt_price"] + m["completion_price"])
        return models

    def analyze_trends(self, stats: Dict) -> Dict[str, Any]:
        """Analyze usage trends and detect anomalies."""
        daily_usage = stats.get("daily_usage", 0)
        monthly_usage = stats.get("monthly_usage", 0)

        # Update daily history
        today = datetime.now().strftime("%Y-%m-%d")
        history = self.state.get("daily_history", [])

        # Remove today's entry if exists, add fresh
        history = [h for h in history if h["date"] != today]
        history.append({
            "date": today,
            "usage": daily_usage,
            "timestamp": datetime.now().isoformat(),
        })

        # Keep last 30 days
        history = sorted(history, key=lambda x: x["date"])[-30:]
        self.state["daily_history"] = history

        # Calculate baseline average
        if len(history) > 1:
            avg_daily = sum(h["usage"] for h in history[:-1]) / (len(history) - 1)
        else:
            avg_daily = daily_usage

        self.state["baseline_daily_avg"] = avg_daily

        # Detect anomalies
        anomalies = []
        if daily_usage > self.thresholds["daily_critical"]:
            anomalies.append({
                "type": "CRITICAL",
                "message": f"Daily usage ${daily_usage:.2f} exceeds critical threshold ${self.thresholds['daily_critical']:.2f}",
            })
        elif daily_usage > self.thresholds["daily_warning"]:
            anomalies.append({
                "type": "WARNING",
                "message": f"Daily usage ${daily_usage:.2f} exceeds warning threshold ${self.thresholds['daily_warning']:.2f}",
            })

        if avg_daily > 0 and daily_usage > (avg_daily * self.thresholds["spike_multiplier"]):
            anomalies.append({
                "type": "SPIKE",
                "message": f"Daily usage ${daily_usage:.2f} is {daily_usage/avg_daily:.1f}x above average ${avg_daily:.2f}",
            })

        # Monthly budget projection
        days_elapsed = (datetime.now() - datetime.now().replace(day=1)).days + 1
        projected_monthly = (monthly_usage / days_elapsed) * 30 if days_elapsed > 0 else 0
        if projected_monthly > self.thresholds["monthly_budget"]:
            anomalies.append({
                "type": "BUDGET",
                "message": f"Projected monthly ${projected_monthly:.2f} exceeds budget ${self.thresholds['monthly_budget']:.2f}",
            })

        self.state["last_check"] = datetime.now().isoformat()
        self._save_state()

        return {
            "anomalies": anomalies,
            "daily_average": avg_daily,
            "projected_monthly": projected_monthly,
            "days_tracked": len(history),
        }

    def generate_cost_optimization_report(self, stats: Dict, models: List[Dict]) -> Dict:
        """Generate cost optimization recommendations."""
        recommendations = []

        # Check if using expensive models for bulk tasks
        current_daily = stats.get("daily_usage", 0)
        if current_daily > 1.0:
            recommendations.append({
                "type": "MODEL_SWITCH",
                "priority": "HIGH",
                "message": "Consider shifting bulk tasks to free models (Qwen 3.6 Plus, Gemini Flash-Lite)",
                "potential_savings": f"${current_daily * 0.7:.2f}/day",
            })

        # Check for caching opportunities
        if stats.get("daily_usage", 0) > 0.5:
            recommendations.append({
                "type": "CACHING",
                "priority": "MEDIUM",
                "message": "Enable OpenRouter response caching for repetitive queries",
                "potential_savings": "20-40% on repeated requests",
            })

        # Free model recommendations
        free_models = [m for m in models if m["prompt_price"] == 0 and m["completion_price"] == 0]
        if free_models:
            recommendations.append({
                "type": "FREE_MODELS",
                "priority": "HIGH",
                "message": f"{len(free_models)} free models available: {', '.join(m['name'] for m in free_models[:5])}",
                "models": [m["id"] for m in free_models[:10]],
            })

        return {
            "current_daily_cost": current_daily,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
        }

    def generate_daily_digest(self) -> Dict[str, Any]:
        """Generate comprehensive daily digest."""
        stats = self.get_usage_stats()
        credits = self.get_credits()
        models = self.get_models()
        trends = self.analyze_trends(stats)
        optimization = self.generate_cost_optimization_report(stats, models)

        digest = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "usage": stats,
            "credits": credits,
            "trends": trends,
            "optimization": optimization,
            "top_models": [
                {
                    "id": "qwen/qwen3.6-plus-04-02:free",
                    "name": "Qwen 3.6 Plus (Free)",
                    "status": "ACTIVE",
                },
                {
                    "id": "google/gemini-3.1-flash-lite",
                    "name": "Gemini 3.1 Flash-Lite",
                    "status": "ACTIVE",
                },
            ],
        }

        # Save digest
        digest_file = self.output_dir / f"openrouter_digest_{datetime.now().strftime('%Y%m%d')}.json"
        with open(digest_file, "w") as f:
            json.dump(digest, f, indent=2)

        return digest

    def format_telegram_alert(self, digest: Dict) -> str:
        """Format digest for Telegram notification."""
        usage = digest.get("usage", {})
        credits = digest.get("credits", {})
        trends = digest.get("trends", {})
        anomalies = trends.get("anomalies", [])

        lines = [
            "🦅 *OpenRouter Daily Monitor*",
            "",
            f"📊 *Daily Usage:* ${usage.get('daily_usage', 0):.2f}",
            f"📈 *Weekly Usage:* ${usage.get('weekly_usage', 0):.2f}",
            f"💰 *Monthly Usage:* ${usage.get('monthly_usage', 0):.2f}",
            f"💳 *Credits Remaining:* ${credits.get('remaining', 0):.2f}",
            f"📉 *Daily Average:* ${trends.get('daily_average', 0):.2f}",
            f"🔮 *Projected Monthly:* ${trends.get('projected_monthly', 0):.2f}",
        ]

        if anomalies:
            lines.append("")
            lines.append("⚠️ *Alerts:*")
            for anomaly in anomalies:
                icon = "🔴" if anomaly["type"] == "CRITICAL" else "🟡"
                lines.append(f"{icon} {anomaly['message']}")

        optimization = digest.get("optimization", {})
        recommendations = optimization.get("recommendations", [])
        if recommendations:
            lines.append("")
            lines.append("💡 *Optimization:*")
            for rec in recommendations[:3]:
                lines.append(f"• {rec['message']}")

        return "\n".join(lines)


def main():
    """Run OpenRouter monitor and generate digest."""
    monitor = OpenRouterMonitor()
    digest = monitor.generate_daily_digest()

    # Print summary
    print(f"\n{'='*60}")
    print(f"OpenRouter Daily Monitor - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*60}")
    print(f"Daily Usage: ${digest['usage'].get('daily_usage', 0):.2f}")
    print(f"Weekly Usage: ${digest['usage'].get('weekly_usage', 0):.2f}")
    print(f"Monthly Usage: ${digest['usage'].get('monthly_usage', 0):.2f}")
    print(f"Credits Remaining: ${digest['credits'].get('remaining', 0):.2f}")

    anomalies = digest["trends"].get("anomalies", [])
    if anomalies:
        print(f"\n⚠️  Alerts:")
        for a in anomalies:
            print(f"  • {a['message']}")

    recommendations = digest["optimization"].get("recommendations", [])
    if recommendations:
        print(f"\n💡 Recommendations:")
        for r in recommendations:
            print(f"  • {r['message']}")

    print(f"{'='*60}\n")

    # Return exit code based on anomalies
    critical = [a for a in anomalies if a["type"] == "CRITICAL"]
    return 1 if critical else 0


if __name__ == "__main__":
    sys.exit(main())

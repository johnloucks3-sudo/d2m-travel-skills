# Daily Cost Tracker — Run: python cost_tracker.py
import re
from pathlib import Path
from datetime import datetime, timedelta

LOG_PATH = Path("/home/john/Thunderbird/logs/model_dispatcher.log")


def parse_costs(log_file):
    costs = []
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    with open(log_file) as f:
        for line in f:
            if today in line or yesterday in line:
                m = re.search(r"Cost:\s*\$([\d.]+)", line)
                if m:
                    costs.append(float(m.group(1)))

    total = sum(costs)
    return total, costs


total_24h, all_costs = parse_costs(LOG_PATH)
print(f"24h Total: ${total_24h:.6f}")
print(f"Transactions: {len(all_costs)}")
print("Per-call avg: ${sum(all_costs)/len(all_costs):.6f}" if all_costs else "No costs")

## AGENTS DOCUMENTATION

- Updated to enforce free‑model guardrail for OpenRouter.
- See docs/AGENTS_MODEL_GUIDE.md for allowed models and usage.


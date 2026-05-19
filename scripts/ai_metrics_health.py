#!/usr/bin/env python3
"""
AI Metrics Dashboard — Health Check Script
Confirms dashboard is reachable and all data sources are live.
Exit 0 = healthy. Exit 1 = degraded.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

VENV_PYTHON = "/home/john/Thunderbird/.venv/bin/python3"
DASHBOARD_URL = "http://localhost:8767/ai-metrics/json"
THUNDERBIRD_DIR = Path("/home/john/Thunderbird")


def check_dashboard_reachable() -> tuple[bool, str]:
    try:
        import urllib.request
        with urllib.request.urlopen(DASHBOARD_URL, timeout=5) as r:
            data = json.loads(r.read())
            budget = data.get("claude", {}).get("budget_status", "?")
            credits = round(data.get("openrouter", {}).get("credits", {}).get("remaining", 0), 2)
            return True, f"HTTP {r.status} — budget={budget}, OR credits=${credits}"
    except Exception as e:
        return False, str(e)


def check_claude_tracker() -> tuple[bool, str]:
    try:
        sys.path.insert(0, str(THUNDERBIRD_DIR))
        from OpsCenter.claude_usage_tracker import get_status
        s = get_status()
        pct = round((s.get("effective_messages", 0) / s.get("session_limit", 225)) * 100, 1)
        return True, f"{pct}% session, budget={s.get('budget_status','?')}"
    except Exception as e:
        return False, str(e)


def check_openrouter_monitor() -> tuple[bool, str]:
    try:
        sys.path.insert(0, str(THUNDERBIRD_DIR))
        from core.intel.thunderbird_openrouter_monitor import OpenRouterMonitor
        m = OpenRouterMonitor()
        credits = m.get_credits()
        remaining = credits.get("remaining", "?")
        return True, f"Credits remaining: {remaining}"
    except Exception as e:
        return False, str(e)


def check_log_recent() -> tuple[bool, str]:
    log = THUNDERBIRD_DIR / "logs" / "ai_metrics_dashboard.log"
    if not log.exists():
        return False, "Log file missing"
    age = time.time() - log.stat().st_mtime
    if age > 300:
        return False, f"Log not updated in {age:.0f}s (dashboard may be hung)"
    return True, f"Log updated {age:.0f}s ago"


def check_log_file() -> tuple[bool, str]:
    log = THUNDERBIRD_DIR / "logs" / "ai_metrics_dashboard.log"
    if log.exists():
        size = log.stat().st_size
        return True, f"Log {size} bytes"
    return False, "Log file not found (dashboard never started?)"


def main():
    checks = [
        ("Claude Usage Tracker", check_claude_tracker),
        ("OpenRouter Monitor", check_openrouter_monitor),
        ("Log File", check_log_file),
        ("Log Recency", check_log_recent),
        ("Dashboard HTTP", check_dashboard_reachable),
    ]

    results = []
    all_ok = True

    print(f"\n{'='*55}")
    print(f"  AI Metrics Dashboard — Health Check")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S MT')}")
    print(f"{'='*55}")

    for name, fn in checks:
        ok, msg = fn()
        icon = "✅" if ok else "❌"
        print(f"  {icon}  {name:<25} {msg}")
        results.append({"check": name, "ok": ok, "detail": msg})
        if not ok:
            all_ok = False

    print(f"{'='*55}")
    overall = "HEALTHY" if all_ok else "DEGRADED"
    print(f"  Overall: {overall}\n")

    # Write status JSON for monitoring
    status_file = THUNDERBIRD_DIR / "logs" / "ai_metrics_health_last.json"
    status_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "overall": overall,
        "checks": results,
    }, indent=2))

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()

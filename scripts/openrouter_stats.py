#!/usr/bin/env python3
"""OpenRouter usage stats — outputs one-line summary for tmux status bar."""
import json, sys, os, requests

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

try:
    r = requests.get(
        "https://openrouter.ai/api/v1/auth/key",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=10,
    )
    r.raise_for_status()
    d = r.json()["data"]
    daily = float(d.get("usage_daily", 0))
    weekly = float(d.get("usage_weekly", 0))
    monthly = float(d.get("usage_monthly", 0))
    print(f"OR: D${daily:.2f} W${weekly:.2f} M${monthly:.2f}")
except Exception:
    print("OR: --")

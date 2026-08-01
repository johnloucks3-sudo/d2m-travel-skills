#!/usr/bin/env python3
"""OpenRouter usage stats — outputs one-line summary for tmux status bar."""
import json, sys, os, requests

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

def check_openrouter_spend_cap() -> dict:
    """Programmatic OpenRouter Spend Guard (Directive 2026-08-01).

    Enforces $10.00/month hard cap. If monthly spend >= $10.00, blocks paid routes.
    """
    if not API_KEY:
        return {"ok": True, "monthly_spend": 0.0, "cap_exceeded": False}

    try:
        r = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10,
        )
        r.raise_for_status()
        d = r.json().get("data", {})
        monthly = float(d.get("usage_monthly", 0))
        exceeded = monthly >= 10.00
        return {
            "ok": not exceeded,
            "monthly_spend": monthly,
            "hard_cap": 10.00,
            "cap_exceeded": exceeded,
            "reason": f"OpenRouter monthly spend (${monthly:.2f}) reached $10.00 cap. Paid models blocked." if exceeded else "Under $10.00 cap"
        }
    except Exception as exc:
        return {"ok": True, "monthly_spend": 0.0, "cap_exceeded": False, "error": str(exc)}

try:
    stats = check_openrouter_spend_cap()
    monthly = stats.get("monthly_spend", 0.0)
    status_str = f"OR: M${monthly:.2f}"
    if stats.get("cap_exceeded"):
        status_str += " [CAP BLOCKED]"
    print(status_str)
except Exception:
    print("OR: --")


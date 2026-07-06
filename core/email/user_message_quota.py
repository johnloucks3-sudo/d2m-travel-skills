#!/usr/bin/env python3
"""Per-correspondent monthly message quota — Bryana Jarboe et al.

Separate from core/email/agentmail_quota.py, which caps the whole AgentMail
account against the free-tier 100/day, 3,000/month ceiling. This tracks
fairness per named user against config/user_quotas.json, e.g. Bryana's
750/month "for now."

Soft limit by design: crossing it raises a flag for a quota-increase
conversation with the Commander — it does NOT stop replying to her
mid-conversation. Cutting off a friend mid-question is bad service; the
number exists so usage is visible and a real conversation about
upgrading happens before it becomes a problem, not after.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

QUOTAS_PATH = Path("/home/john/Thunderbird/config/user_quotas.json")
USAGE_PATH = Path("/home/john/Thunderbird/OpsCenter/state/user_quota_usage.json")
QUERY_LOG_PATH = Path("/home/john/Thunderbird/OpsCenter/state/user_quota_query_log.jsonl")


def _load_quotas() -> dict:
    return json.loads(QUOTAS_PATH.read_text())["users"]


def _load_usage() -> dict:
    if USAGE_PATH.exists():
        return json.loads(USAGE_PATH.read_text())
    return {}


def _save_usage(usage: dict):
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    USAGE_PATH.write_text(json.dumps(usage, indent=2))


def _append_query_log(email: str, month: str):
    """Append one timestamped query event — powers weekly-window alerting
    (report script needs finer granularity than the monthly counter alone)."""
    QUERY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with QUERY_LOG_PATH.open("a") as f:
        f.write(json.dumps({"email": email, "month": month, "ts": datetime.now(timezone.utc).isoformat()}) + "\n")


def weekly_counts(email: str, month: str) -> dict:
    """Return {iso_week: count} for an email's queries within the given month,
    derived from the query log (missing/corrupt lines are skipped)."""
    email = email.lower()
    counts: dict = {}
    if not QUERY_LOG_PATH.exists():
        return counts
    for line in QUERY_LOG_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("email") != email or rec.get("month") != month:
            continue
        try:
            ts = datetime.fromisoformat(rec["ts"])
        except Exception:
            continue
        iso_year, iso_week, _ = ts.isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def record_query(email: str) -> dict:
    """Record one query from email against their monthly quota. Returns
    status dict — never raises, never blocks; caller decides what to do
    with over_limit=True (surface to Commander, don't refuse to reply)."""
    email = email.lower()
    quotas = _load_quotas()
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = _load_usage()

    if email not in usage or usage[email].get("month") != month:
        usage[email] = {"month": month, "count": 0}

    usage[email]["count"] += 1
    _save_usage(usage)
    _append_query_log(email, month)

    quota_record = quotas.get(email)
    limit = quota_record["monthly_limit"] if quota_record else None
    count = usage[email]["count"]

    return {
        "email": email,
        "name": quota_record["name"] if quota_record else email,
        "month": month,
        "count": count,
        "limit": limit,
        "pct_used": round(100 * count / limit, 1) if limit else None,
        "over_limit": bool(limit and count > limit),
        "approaching_limit": bool(limit and count >= 0.8 * limit),
    }


def status(email: str) -> dict:
    """Read-only status check, does not increment."""
    email = email.lower()
    quotas = _load_quotas()
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    usage = _load_usage()
    count = usage.get(email, {}).get("count", 0) if usage.get(email, {}).get("month") == month else 0
    quota_record = quotas.get(email)
    limit = quota_record["monthly_limit"] if quota_record else None
    return {
        "email": email,
        "name": quota_record["name"] if quota_record else email,
        "month": month,
        "count": count,
        "limit": limit,
        "pct_used": round(100 * count / limit, 1) if limit else None,
    }

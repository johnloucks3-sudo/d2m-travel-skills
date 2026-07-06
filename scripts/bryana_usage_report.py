#!/usr/bin/env python3
"""
bryana_usage_report.py — Monthly usage report for Bryana Jarboe's
hale-thunderbird@agentmail.to allowance (750 messages/month).

Pulls from core/email/user_message_quota.py (config/user_quotas.json +
OpsCenter/state/user_quota_usage.json + the per-query timestamp log),
writes OpsCenter/bryana_usage_report_{month}.json, and updates
hale_state.json's user_quotas.bryana_jarboe block.

Alerting (soft limits — never blocks, only surfaces):
- >=80% of monthly allowance  -> quarterly-review rebalance recommendation
- >=85% of allowance used in any single ISO week -> warning logged to
  hale_decisions.md + a Telegram check-in flag in the report

Usage: python3 scripts/bryana_usage_report.py [--email EMAIL] [--month YYYY-MM]
"""
import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))

from core.email.user_message_quota import _load_quotas, _load_usage, weekly_counts

STATE_FILE = ROOT / "hale_state.json"
DECISIONS_FILE = ROOT / "hale_decisions.md"
REPORT_DIR = ROOT / "OpsCenter"

WEEKLY_ALERT_PCT = 0.85
MONTHLY_REVIEW_PCT = 0.80
QUARTER_START_MONTHS = {1, 4, 7, 10}


def _prior_month(month: str) -> str:
    y, m = (int(x) for x in month.split("-"))
    y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return f"{y:04d}-{m:02d}"


def _load_prior_report(email_key: str, month: str) -> dict | None:
    path = REPORT_DIR / f"bryana_usage_report_{_prior_month(month)}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def compute_report(email: str, quotas: dict, usage: dict, weekly: dict,
                    prior_report: dict | None, month: str, today: date) -> dict:
    email = email.lower()
    record = quotas.get(email)
    name = record["name"] if record else email
    allowance = record["monthly_limit"] if record else None

    month_entry = usage.get(email, {})
    used_this_month = month_entry.get("count", 0) if month_entry.get("month") == month else 0

    pct_used = round(100 * used_this_month / allowance, 1) if allowance else None
    approaching_limit = bool(allowance and used_this_month >= MONTHLY_REVIEW_PCT * allowance)
    over_limit = bool(allowance and used_this_month > allowance)

    prior_used = prior_report.get("used_this_month") if prior_report else None
    if prior_used is None:
        trend = "no_prior_data"
    elif used_this_month > prior_used:
        trend = f"up ({prior_used} -> {used_this_month})"
    elif used_this_month < prior_used:
        trend = f"down ({prior_used} -> {used_this_month})"
    else:
        trend = f"flat ({used_this_month})"

    weekly_alert_weeks = []
    if allowance:
        threshold = WEEKLY_ALERT_PCT * allowance
        for week, count in sorted(weekly.items()):
            if count >= threshold:
                weekly_alert_weeks.append({"week": week, "count": count,
                                            "pct_of_allowance": round(100 * count / allowance, 1)})

    is_quarterly_review_day = today.day == 1 and today.month in QUARTER_START_MONTHS
    recommend_rebalance = approaching_limit  # >=80% always earns the recommendation, not just on quarter day

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "email": email,
        "name": name,
        "month": month,
        "used_this_month": used_this_month,
        "allowance": allowance,
        "pct_used": pct_used,
        "trend": trend,
        "approaching_limit": approaching_limit,
        "over_limit": over_limit,
        "weekly_breakdown": weekly,
        "weekly_alert_weeks": weekly_alert_weeks,
        "is_quarterly_review_day": is_quarterly_review_day,
        "recommend_rebalance": recommend_rebalance,
    }


def _write_report(report: dict, month: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"bryana_usage_report_{month}.json"
    out.write_text(json.dumps(report, indent=2))
    return out


def _update_hale_state(report: dict):
    if not STATE_FILE.exists():
        return
    state = json.loads(STATE_FILE.read_text())
    quotas_block = state.setdefault("user_quotas", {})
    quotas_block["bryana_jarboe"] = {
        "used_this_month": report["used_this_month"],
        "allowance": report["allowance"],
        "pct_used": report["pct_used"],
        "trend": report["trend"],
    }
    state.setdefault("_meta", {})["last_updated"] = datetime.now(timezone.utc).astimezone().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _log_weekly_alert(report: dict):
    if not report["weekly_alert_weeks"]:
        return
    ts = datetime.now().strftime("%Y-%m-%d %H:%M MT")
    weeks_str = ", ".join(f"{w['week']} ({w['count']}, {w['pct_of_allowance']}%)" for w in report["weekly_alert_weeks"])
    entry = (
        f"\n## {ts} — Bryana usage: weekly quota warning\n\n"
        f"{report['name']} crossed {int(WEEKLY_ALERT_PCT * 100)}% of the monthly allowance "
        f"({report['allowance']}) within a single ISO week: {weeks_str}. "
        f"Month-to-date: {report['used_this_month']}/{report['allowance']} ({report['pct_used']}%). "
        f"Soft limit — not throttled, flagging for next Telegram check-in.\n"
    )
    with DECISIONS_FILE.open("a") as f:
        f.write(entry)


def main():
    p = argparse.ArgumentParser(description="Bryana AgentMail usage report")
    p.add_argument("--email", default="bryanajarboe@gmail.com")
    p.add_argument("--month", default=None, help="Override month (YYYY-MM), default = current UTC month")
    args = p.parse_args()

    month = args.month or datetime.now(timezone.utc).strftime("%Y-%m")
    today = date.today()

    quotas = _load_quotas()
    usage = _load_usage()
    weekly = weekly_counts(args.email, month)
    prior_report = _load_prior_report(args.email, month)

    report = compute_report(args.email, quotas, usage, weekly, prior_report, month, today)

    out_path = _write_report(report, month)
    _update_hale_state(report)
    _log_weekly_alert(report)

    print(f"[{report['generated_at']}] Bryana usage report written -> {out_path}")
    print(f"  {report['name']}: {report['used_this_month']}/{report['allowance']} "
          f"({report['pct_used']}%) — trend: {report['trend']}")
    if report["approaching_limit"]:
        print(f"  ⚠️  >=80% of monthly allowance used — recommend rebalance conversation "
              f"(upgrade AgentMail tier, adjust allowance, or both).")
    if report["weekly_alert_weeks"]:
        print(f"  🔴 Weekly threshold (85%) crossed: {report['weekly_alert_weeks']} — logged to hale_decisions.md")
    if report["is_quarterly_review_day"]:
        print(f"  📅 Quarterly review day ({today.isoformat()}) — surface this report in today's morning brief.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

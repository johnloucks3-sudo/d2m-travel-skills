#!/usr/bin/env python3
"""
Weekly Budget Report Generator — SO-20260724

Runs every Friday 17:00 MT to audit token spend and project weekly burn rate.
Escalates to Commander if projected burn > 90% by week-end.

Covers:
  1. All timer spawns (source, model, timestamp)
  2. Model routing decisions (MAX vs Opus breakdown)
  3. Budget guard triggers (timestamp, budget %, blocked task)
  4. Projected burn rate (current % used / hours elapsed)
  5. Recommendations (timers to disable/batch)
"""

import json
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

AUDIT_LOG = Path.home() / "Thunderbird" / "OpsCenter" / "nexus_audit.log"
USAGE_CACHE = Path.home() / ".claude" / "hud" / ".usage-cache.json"
REPORT_DIR = Path.home() / "Thunderbird" / "OpsCenter" / "weekly_reports"
REPORT_DIR.mkdir(exist_ok=True)

def get_current_budget_pct() -> int:
    """Read current budget % from usage cache."""
    if not USAGE_CACHE.exists():
        return 0
    try:
        data = json.loads(USAGE_CACHE.read_text())
        return data.get("data", {}).get("sevenDay", 0)
    except:
        return 0

def get_budget_reset_time() -> datetime:
    """Get the 7-day reset time from cache."""
    if not USAGE_CACHE.exists():
        return datetime.now(timezone.utc)
    try:
        data = json.loads(USAGE_CACHE.read_text())
        reset_str = data.get("data", {}).get("sevenDayResets", "")
        if reset_str:
            return datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
    except:
        pass
    return datetime.now(timezone.utc)

def parse_audit_log() -> dict:
    """Parse nexus audit log for this week's activity."""
    if not AUDIT_LOG.exists():
        return {
            "spawns": [],
            "guard_triggers": [],
            "routing": defaultdict(int),
        }

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    spawns = []
    guard_triggers = []
    routing = defaultdict(int)

    try:
        with open(AUDIT_LOG) as f:
            for line in f:
                # Parse timestamp
                match = re.search(r"\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^]]*)\]", line)
                if not match:
                    continue

                ts_str = match.group(1)
                try:
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except:
                    continue

                if ts < week_ago:
                    continue

                # Track spawns
                if "DISPATCH_CLAUDE" in line and "BLOCKED" not in line and "BUDGET_GUARD" not in line:
                    spawns.append({"timestamp": ts, "event": line.strip()})

                # Track guard triggers
                if "BUDGET_GUARD" in line:
                    guard_triggers.append({"timestamp": ts, "event": line.strip()})

                # Track model routing (heuristic)
                if "Opus" in line or "opus" in line:
                    routing["opus"] += 1
                if "Sonnet" in line or "sonnet" in line:
                    routing["sonnet"] += 1
                if "MAX" in line:
                    routing["max"] += 1

    except Exception as e:
        print(f"Error parsing audit log: {e}")

    return {
        "spawns": spawns,
        "guard_triggers": guard_triggers,
        "routing": dict(routing),
    }

def calculate_burn_rate() -> dict:
    """Calculate current burn rate and project end-of-week."""
    reset_time = get_budget_reset_time()
    now = datetime.now(timezone.utc)
    elapsed_hours = (now - reset_time).total_seconds() / 3600

    current_pct = get_current_budget_pct()

    if elapsed_hours <= 0:
        elapsed_hours = 1

    hourly_rate = current_pct / elapsed_hours
    daily_rate = hourly_rate * 24
    weekly_projection = hourly_rate * 168

    # Time until Sunday 23:59 MT (end of week)
    # MT is UTC-6, so find next Monday 00:00 UTC
    now_mt = now.astimezone(timezone(timedelta(hours=-6)))
    days_until_reset = (6 - now_mt.weekday()) % 7
    if days_until_reset == 0:
        days_until_reset = 7
    hours_until_reset = days_until_reset * 24 - now_mt.hour - now_mt.minute / 60

    projected_eow = current_pct + (hourly_rate * hours_until_reset)

    return {
        "current_pct": current_pct,
        "elapsed_hours": elapsed_hours,
        "hourly_rate": hourly_rate,
        "daily_rate": daily_rate,
        "weekly_projection": weekly_projection,
        "projected_eow": projected_eow,
        "hours_until_reset": hours_until_reset,
        "escalation_needed": projected_eow > 90,
    }

def generate_report() -> str:
    """Generate weekly budget report."""
    audit = parse_audit_log()
    burn = calculate_burn_rate()
    now = datetime.now(timezone.utc).isoformat()

    report = f"""
# WEEKLY BUDGET REPORT
**Generated:** {now}
**Reporting Period:** 7 days (week reset tracking)

## BUDGET STATUS
- **Current:** {burn['current_pct']}% used
- **Hours Elapsed:** {burn['elapsed_hours']:.1f}h
- **Hourly Rate:** {burn['hourly_rate']:.2f}%/h
- **Daily Rate:** {burn['daily_rate']:.1f}%/day
- **Weekly Projection:** {burn['weekly_projection']:.0f}%
- **Projected End-of-Week:** {burn['projected_eow']:.0f}%
- **Hours Until Reset:** {burn['hours_until_reset']:.1f}h

## ESCALATION
"""

    if burn['escalation_needed']:
        report += f"⚠️ **CRITICAL** — Projected EOW {burn['projected_eow']:.0f}% exceeds 90% threshold\n"
        report += "**Recommendation:** Disable additional timers or implement stricter routing\n"
    else:
        report += f"✓ On track — Projected EOW {burn['projected_eow']:.0f}% < 90% safe threshold\n"

    report += f"""

## ACTIVITY THIS WEEK
- **Total Spawns:** {len(audit['spawns'])}
- **Guard Triggers:** {len(audit['guard_triggers'])}
- **Model Routing:** {json.dumps(audit['routing'], indent=2)}

## GUARD TRIGGER LOG
"""

    if audit['guard_triggers']:
        for trigger in audit['guard_triggers'][-20:]:  # Last 20 triggers
            report += f"- {trigger['timestamp'].isoformat()} | {trigger['event']}\n"
    else:
        report += "- None (no budget guard triggers this week)\n"

    report += f"""

## RECOMMENDATIONS

1. **If projected EOW > 90%:**
   - Disable lowest-ROI timer (check audit log for spawns-per-timer)
   - Batch email responders further (60-min instead of 30-min cadence)
   - Escalate to Commander for strategic guidance

2. **If projected EOW 50-90%:**
   - Monitor daily rate
   - Prepare timer disable list (do NOT execute)
   - Schedule Commander review

3. **If projected EOW < 50%:**
   - Continue normal operation
   - No action required
   - Confirm SO-20260724 compliance

## TIMER AUDIT CHECKLIST
- [ ] All timers checked for 5+ min spacing
- [ ] Email/intel tasks routed to Opus (not MAX)
- [ ] No new parallel spawns added since last review
- [ ] Budget guard active in nexus.py
- [ ] Weekly report scheduled for next Friday

---
**Next Report:** {(datetime.now(timezone.utc) + timedelta(days=7)).isoformat()}
**Contact:** Commander (escalation on >90% projection)
"""

    return report

def main():
    """Generate and save report."""
    report = generate_report()

    # Save to file with timestamp
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = REPORT_DIR / f"weekly_budget_report_{ts}.md"
    report_file.write_text(report)

    print(report)
    print(f"\n✓ Report saved to {report_file}")

    # Check for escalation and log
    burn = calculate_burn_rate()
    if burn['escalation_needed']:
        escalation_log = REPORT_DIR / "escalations.log"
        with open(escalation_log, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] ESCALATION: Projected EOW {burn['projected_eow']:.0f}%\n")
        print(f"\n⚠️  ESCALATION LOGGED — Commander review recommended")

if __name__ == "__main__":
    main()

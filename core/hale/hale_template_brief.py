#!/usr/bin/env python3
"""
HALE Template Brief Generator — Fast, reliable, no Claude required.
Generates text-based daily brief from structured data.
Replaces broken async Claude generation (SO 2026-05-01).
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

MT = timezone(timedelta(hours=-6))
ROOT = Path("/home/john/Thunderbird")


def load_brief_data() -> Dict[str, Any]:
    """Load brief snapshot from today's visual brief output."""
    today = datetime.now(MT).strftime("%Y-%m-%d")
    snapshot_path = ROOT / "output" / "briefs" / today / "snapshot.json"

    if snapshot_path.exists():
        return json.loads(snapshot_path.read_text())

    # Fallback: synthetic data from state
    try:
        state = json.loads((ROOT / "hale_state.json").read_text())
        return {
            "clients": state.get("recent_session", {}).get("key_activities", [])[:3],
            "tasks": state.get("open_tasks", []),
            "risks": [],
            "financial": {"status": "UNKNOWN", "reason": "MCP offline"},
        }
    except Exception:
        return {
            "clients": [],
            "tasks": [],
            "risks": [],
            "financial": {"status": "NO DATA"},
        }


def format_clients_section(data: Dict) -> str:
    """Format active clients section."""
    clients = data.get("clients", [])
    if not clients:
        return "## 📋 CLIENTS\nNo active clients in snapshot.\n"

    lines = ["## 📋 CLIENTS"]
    for c in clients[:5]:
        if isinstance(c, dict):
            name = c.get("name", "?")
            phase = c.get("phase", "unknown")
            lines.append(f"- **{name}** — Phase: {phase}")
        else:
            lines.append(f"- {str(c)[:80]}")
    lines.append("")
    return "\n".join(lines)


def format_tasks_section(data: Dict) -> str:
    """Format open tasks section."""
    tasks = data.get("tasks", [])
    if not tasks or not any(t for t in tasks if not isinstance(t, str)):
        return "## ✅ TASKS\nNo open tasks.\n"

    lines = ["## ✅ TASKS"]
    for t in tasks[:7]:
        if isinstance(t, dict):
            title = t.get("title", t.get("name", "?"))
            priority = t.get("priority", "—")
            lines.append(f"- **{title}** [P{priority}]")
        elif not isinstance(t, str) or t.strip():
            continue
    lines.append("")
    return "\n".join(lines) if len(lines) > 1 else "## ✅ TASKS\nNo open tasks.\n"


def format_financial_section(data: Dict) -> str:
    """Format financial pulse section."""
    fin = data.get("financial", {})
    status = fin.get("status", "UNKNOWN")

    return f"""## 💰 FINANCIAL PULSE
**Status:** {status}

> Note: TESS auth offline. Run `python3 thunderbird_tess.py --authorize` to restore.

"""


def format_spsa_eod_section() -> str:
    """Format EOD SPSA section — new cases created today + status updates."""
    try:
        from core.ops.thunderbird_spsa import get_active_cases, load_case
        import os

        # Get all active cases
        red_cases = get_active_cases(severity='RED')
        yellow_cases = get_active_cases(severity='YELLOW')

        # Count created today (rough check on timestamp)
        today_str = datetime.now(MT).strftime("%Y-%m-%d")
        red_today = [c for c in red_cases if c.timestamp_created.startswith(today_str)]
        yellow_today = [c for c in yellow_cases if c.timestamp_created.startswith(today_str)]

        lines = ["## 🚨 SPSA EOD — Cases & Status\n"]

        if red_today or yellow_today:
            lines.append(f"**Created Today:** {len(red_today)} RED, {len(yellow_today)} YELLOW\n")

        if red_today:
            lines.append("### 🔴 NEW RED (Today)\n")
            for case in red_today[:3]:
                lines.append(f"**{case.case_id}** | {case.problem_statement[:50]}...\n> {case.recommendation} ({case.timeline_hours}h)\n")

        if yellow_today:
            lines.append("### 🟡 NEW YELLOW (Today)\n")
            for case in yellow_today[:3]:
                lines.append(f"**{case.case_id}** | {case.problem_statement[:50]}...\n> {case.recommendation} ({case.timeline_hours}h)\n")

        # Status summary
        open_count = len([c for c in (red_cases + yellow_cases) if c.status == "OPEN"])
        decided_count = len([c for c in (red_cases + yellow_cases) if c.status == "DECIDED"])
        implementing_count = len([c for c in (red_cases + yellow_cases) if c.status == "IMPLEMENTING"])

        if open_count + decided_count + implementing_count > 0:
            lines.append(f"\n**Pipeline:** {open_count} open, {decided_count} decided, {implementing_count} implementing\n")

        return "\n".join(lines) + "\n"
    except Exception as e:
        return f"## 🚨 SPSA EOD\n*Failed to load cases: {str(e)[:60]}*\n\n"


def format_spsa_weekly_section() -> str:
    """Format weekly SPSA section — closed cases + lessons learned."""
    try:
        from core.ops.thunderbird_spsa import get_closed_cases_for_week

        closed = get_closed_cases_for_week()
        if not closed:
            return "## 📊 SPSA WEEKLY\nNo cases closed this week.\n\n"

        lines = ["## 📊 SPSA WEEKLY — Lessons & Patterns\n"]
        lines.append(f"**This Week:** {len(closed)} cases closed\n")

        # Group by severity
        red_closed = [c for c in closed if c.severity == "RED"]
        yellow_closed = [c for c in closed if c.severity == "YELLOW"]

        if red_closed:
            lines.append(f"\n**RED (Critical):** {len(red_closed)} resolved\n")
            for case in red_closed[:2]:
                lines.append(f"- {case.case_id}: {case.problem_statement[:40]}... → {case.outcome[:40] if case.outcome else 'Resolved'}\n")

        if yellow_closed:
            lines.append(f"\n**YELLOW (Routine):** {len(yellow_closed)} resolved\n")

        # Lessons learned
        lessons = [c.lessons_learned for c in closed if c.lessons_learned]
        if lessons:
            lines.append("\n**Key Lessons:**\n")
            for lesson in lessons[:3]:
                lines.append(f"- {lesson[:70]}...\n")

        # Metrics
        days_to_close = []
        for case in closed:
            if case.timestamp_closed:
                created = datetime.fromisoformat(case.timestamp_created)
                closed_dt = datetime.fromisoformat(case.timestamp_closed)
                days_to_close.append((closed_dt - created).days)

        if days_to_close:
            avg_days = sum(days_to_close) / len(days_to_close)
            lines.append(f"\n**Average closure time:** {avg_days:.1f} days\n")

        return "\n".join(lines) + "\n"
    except Exception as e:
        return f"## 📊 SPSA WEEKLY\n*Failed to load lessons: {str(e)[:60]}*\n\n"


def format_wing_section(data: Dict) -> str:
    """Format wing health section."""
    try:
        state = json.loads((ROOT / "hale_state.json").read_text())
        health = state.get("wing_health", {})
    except Exception:
        health = {}

    mcp_status = health.get("mcp_server", "UNKNOWN")
    telegram_status = health.get("telegram_bot", "UNKNOWN")

    return f"""## ⚙️ WING HEALTH
- **MCP:** {mcp_status}
- **Telegram:** {telegram_status}
- **Command Ready:** ✅ (COS Online)

"""


def format_spsa_section() -> str:
    """Format active SPSA cases section."""
    from pathlib import Path as PathlibPath
    from core.ops.thunderbird_spsa import get_active_cases

    try:
        red_cases = get_active_cases(severity='RED')
        yellow_cases = get_active_cases(severity='YELLOW')

        if not red_cases and not yellow_cases:
            return "## 🚨 SPSA CASES\nNo active decision cases at this time.\n\n"

        lines = ["## 🚨 SPSA CASES"]

        if red_cases:
            lines.append("### 🔴 RED — Blocking Operations")
            for case in red_cases[:5]:
                lines.append(f"**{case.case_id}** | {case.problem_statement}")
                lines.append(f"> Recommendation: {case.recommendation} ({case.timeline_hours}h)")
                lines.append("")

        if yellow_cases:
            lines.append("### 🟡 YELLOW — Requires Decision Today")
            for case in yellow_cases[:5]:
                lines.append(f"**{case.case_id}** | {case.problem_statement}")
                lines.append(f"> Recommendation: {case.recommendation} ({case.timeline_hours}h)")
                lines.append("")

        lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"## 🚨 SPSA CASES\n*Error loading cases: {e}*\n\n"


def format_decisions_section() -> str:
    """Format decisions needed section."""
    return """## 🎯 STANDING ORDERS
> Awaiting Commander direction on active SPSA cases above.

"""


def generate_template_brief() -> str:
    """Generate full template-based brief."""
    data = load_brief_data()
    now = datetime.now(MT)
    ts = now.strftime("%Y-%m-%d %H:%M MT")
    next_ts = (now + timedelta(hours=24)).strftime("%Y-%m-%d 07:00 MT")

    header = f"""# HALE — Daily Brief
*Generated: {ts}*

---

**Sir, here's where we stand.**

---

"""

    body = (
        format_clients_section(data) +
        format_tasks_section(data) +
        format_spsa_section() +
        format_financial_section(data) +
        format_wing_section(data) +
        format_decisions_section()
    )

    footer = f"""---
*— Ms. Victoria "Victory" Hale, SES-6 | Thunderbird Wing | {ts}*
*Next brief: {next_ts}*
"""

    return header + body + footer


def generate_eod_brief() -> str:
    """Generate EOD (1700 MT) brief — focus on daily SPSA updates."""
    now = datetime.now(MT)
    ts = now.strftime("%Y-%m-%d %H:%M MT")

    header = f"""# HALE — EOD Briefing
*Generated: {ts}*

---

**End of day status.**

---

"""

    body = (
        format_spsa_eod_section() +
        format_financial_section({}) +
        format_wing_section({})
    )

    footer = f"""---
*— Ms. Victoria "Victory" Hale, SES-6 | Thunderbird Wing | {ts}*
"""

    return header + body + footer


def generate_weekly_brief() -> str:
    """Generate weekly (Monday 0700 MT) brief — lessons, patterns, retrospective."""
    now = datetime.now(MT)
    ts = now.strftime("%Y-%m-%d %H:%M MT")

    header = f"""# HALE — Weekly Retrospective
*Generated: {ts}*

---

**What we learned this week.**

---

"""

    body = format_spsa_weekly_section()

    footer = f"""---
*— Ms. Victoria "Victory" Hale, SES-6 | Thunderbird Wing | {ts}*
"""

    return header + body + footer


def save_brief_to_file():
    """Generate and save brief to hale_brief.md."""
    brief_content = generate_template_brief()
    output_path = ROOT / "hale_brief.md"
    output_path.write_text(brief_content)
    return str(output_path)


def save_eod_brief_to_file():
    """Generate and save EOD brief."""
    brief_content = generate_eod_brief()
    output_path = ROOT / "hale_eod_brief.md"
    output_path.write_text(brief_content)
    return str(output_path)


def save_weekly_brief_to_file():
    """Generate and save weekly brief."""
    brief_content = generate_weekly_brief()
    output_path = ROOT / "hale_weekly_brief.md"
    output_path.write_text(brief_content)
    return str(output_path)


if __name__ == "__main__":
    path = save_brief_to_file()
    print(f"✅ Brief saved to {path}")

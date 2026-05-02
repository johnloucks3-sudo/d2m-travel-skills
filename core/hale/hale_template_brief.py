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
*— Col Victoria "Iron Vic" Hale | Thunderbird Wing | {ts}*
*Next brief: {next_ts}*
"""

    return header + body + footer


def save_brief_to_file():
    """Generate and save brief to hale_brief.md."""
    brief_content = generate_template_brief()
    output_path = ROOT / "hale_brief.md"
    output_path.write_text(brief_content)
    return str(output_path)


if __name__ == "__main__":
    path = save_brief_to_file()
    print(f"✅ Brief saved to {path}")

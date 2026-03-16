"""
Thunderbird Nova — Self-Improvement Audit System
==================================================
ELON (A12) audits Thunderbird OS weekly and files improvement tickets.

Analyzes:
  - Scheduler job success/failure rates
  - API costs by provider
  - Stale action items in dossiers
  - Module health (recently modified vs stale .py files)
  - Code anomalies (oversized files, potential redundancy)
  - Manual process elimination opportunities

Outputs:
  - Structured tickets to Action_Tracker tab in Google Sheets
  - Weekly Nova Report (markdown) to ~/Thunderbird/output/

Usage:
    from thunderbird_nova import run_weekly_audit
    report = run_weekly_audit()

    # Or standalone:
    python thunderbird_nova.py
"""

import json
import logging
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import gspread
from google.oauth2 import service_account

from thunderbird_model_router import smart_route
from thunderbird_personas import PERSONA_REGISTRY

logger = logging.getLogger(__name__)

# ── Constants ──
THUNDERBIRD_DIR = Path.home() / "Thunderbird"
CREDENTIALS_FILE = THUNDERBIRD_DIR / "credentials.json"
SPREADSHEET_ID = "1GFjUe8RvP-GT4YHGn0DYv_BEAZGXlYfwEicFrm8ANuU"
ACTION_TRACKER_TAB = "Action_Tracker"
API_COST_LOG = THUNDERBIRD_DIR / "api_cost_log.jsonl"
LOGS_DIR = THUNDERBIRD_DIR / "logs"
DOSSIERS_DIR = THUNDERBIRD_DIR / "dossiers"
OUTPUT_DIR = THUNDERBIRD_DIR / "output"
NOVA_STATE_FILE = THUNDERBIRD_DIR / "nova_state.json"

ACTION_TRACKER_HEADERS = [
    "Ticket_ID", "Date", "Category", "Priority", "Title",
    "Description", "Assigned_To", "Status", "Created_By"
]

# Categories and priority levels
CATEGORIES = {"efficiency", "cost", "quality", "automation"}
PRIORITIES = {"P1", "P2", "P3", "P4"}

# Persona assignment map — who owns what kind of fix
PERSONA_OWNERS = {
    "efficiency": "A9",     # Harlan — process improvement
    "cost": "A9",           # Harlan — finance
    "quality": "COS",       # Hale — orchestration
    "automation": "A12",    # ELON — innovation
    "operations": "A3",     # Moreau — booking ops
    "strategy": "A5",       # Castillo — growth
    "infrastructure": "A12",  # ELON — tech
}


# ============================================================================
# GOOGLE SHEETS — Action_Tracker
# ============================================================================

def _get_sheets_client():
    """Return an authorized gspread client."""
    creds = service_account.Credentials.from_service_account_file(
        str(CREDENTIALS_FILE),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)


def _get_action_tracker(gc=None):
    """Get or create the Action_Tracker tab."""
    if gc is None:
        gc = _get_sheets_client()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    try:
        ws = spreadsheet.worksheet(ACTION_TRACKER_TAB)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=ACTION_TRACKER_TAB, rows=500, cols=len(ACTION_TRACKER_HEADERS)
        )
        ws.update(values=[ACTION_TRACKER_HEADERS], range_name="A1")
        ws.format("A1:I1", {"textFormat": {"bold": True}})
        logger.info(f"Created {ACTION_TRACKER_TAB} tab with headers")

    return ws


def _next_ticket_id(ws) -> str:
    """Generate next NOVA-XXXX ticket ID from existing rows."""
    try:
        col_a = ws.col_values(1)
        existing = [v for v in col_a if v.startswith("NOVA-")]
        if not existing:
            return "NOVA-0001"
        nums = [int(v.split("-")[1]) for v in existing if v.split("-")[1].isdigit()]
        return f"NOVA-{max(nums) + 1:04d}"
    except Exception:
        return f"NOVA-{datetime.now().strftime('%H%M')}"


def write_tickets_to_sheet(tickets: List[Dict[str, str]]) -> int:
    """Write improvement tickets to the Action_Tracker tab.

    Returns the number of tickets written.
    """
    if not tickets:
        return 0

    gc = _get_sheets_client()
    ws = _get_action_tracker(gc)
    written = 0

    for ticket in tickets:
        ticket_id = _next_ticket_id(ws)
        row = [
            ticket_id,
            ticket.get("date", date.today().isoformat()),
            ticket.get("category", "efficiency"),
            ticket.get("priority", "P3"),
            ticket.get("title", "Untitled"),
            ticket.get("description", ""),
            ticket.get("assigned_to", "A12"),
            "OPEN",
            "ELON (Nova Audit)",
        ]
        try:
            ws.append_row(row)
            written += 1
            logger.info(f"Wrote ticket {ticket_id}: {ticket.get('title')}")
        except Exception as e:
            logger.error(f"Failed to write ticket: {e}")

    return written


# ============================================================================
# AUDIT COLLECTORS — gather raw data for analysis
# ============================================================================

def collect_scheduler_health() -> Dict[str, Any]:
    """Analyze scheduler log files for success/failure patterns."""
    results = {
        "log_files_found": 0,
        "total_lines": 0,
        "errors": 0,
        "warnings": 0,
        "by_log": {},
    }

    if not LOGS_DIR.exists():
        results["note"] = "No logs directory found"
        return results

    for log_file in LOGS_DIR.glob("*.log"):
        file_stats = {"lines": 0, "errors": 0, "warnings": 0, "last_entry": None}
        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    file_stats["lines"] += 1
                    lower = line.lower()
                    if "error" in lower or "failed" in lower or "exception" in lower:
                        file_stats["errors"] += 1
                    if "warning" in lower or "warn" in lower:
                        file_stats["warnings"] += 1
                    file_stats["last_entry"] = line.strip()[:120]
        except Exception as e:
            file_stats["read_error"] = str(e)

        results["log_files_found"] += 1
        results["total_lines"] += file_stats["lines"]
        results["errors"] += file_stats["errors"]
        results["warnings"] += file_stats["warnings"]
        results["by_log"][log_file.name] = file_stats

    return results


def collect_api_costs(days: int = 7) -> Dict[str, Any]:
    """Summarize API costs from the local JSONL log."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    by_provider = defaultdict(lambda: {"calls": 0, "cost": 0.0, "tokens_in": 0, "tokens_out": 0})
    by_caller = defaultdict(lambda: {"calls": 0, "cost": 0.0})
    total_cost = 0.0
    total_calls = 0

    if not API_COST_LOG.exists():
        return {"note": "No api_cost_log.jsonl found", "total_cost": 0, "total_calls": 0}

    with open(API_COST_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            if row.get("date", "") < cutoff:
                continue

            provider = row.get("provider", "unknown")
            cost = row.get("cost_usd", 0)
            by_provider[provider]["calls"] += 1
            by_provider[provider]["cost"] += cost
            by_provider[provider]["tokens_in"] += row.get("input_tokens", 0)
            by_provider[provider]["tokens_out"] += row.get("output_tokens", 0)

            caller = row.get("caller", "unknown")
            by_caller[caller]["calls"] += 1
            by_caller[caller]["cost"] += cost

            total_cost += cost
            total_calls += 1

    return {
        "period_days": days,
        "total_cost": round(total_cost, 4),
        "total_calls": total_calls,
        "by_provider": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_provider.items()},
        "by_caller": {k: {**v, "cost": round(v["cost"], 4)} for k, v in by_caller.items()},
    }


def collect_stale_dossier_items() -> Dict[str, Any]:
    """Scan dossiers for PENDING items and unchecked checklists."""
    findings = []

    if not DOSSIERS_DIR.exists():
        return {"note": "No dossiers directory found", "stale_items": []}

    for dossier in DOSSIERS_DIR.glob("DOSSIER_*.md"):
        try:
            content = dossier.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        name = dossier.stem

        # Find unchecked items: [ ] pattern
        unchecked = re.findall(r'\[ \]\s*(.+)', content)
        for item in unchecked:
            findings.append({
                "dossier": name,
                "type": "unchecked",
                "item": item.strip()[:100],
            })

        # Find PENDING items
        pending = re.findall(r'(?:PENDING|STILL PENDING)(?:\s*[—–-]\s*)?(.+)?', content, re.IGNORECASE)
        for item in pending:
            findings.append({
                "dossier": name,
                "type": "pending",
                "item": (item.strip() if item else "unspecified")[:100],
            })

    return {
        "total_stale": len(findings),
        "stale_items": findings,
    }


def collect_module_health() -> Dict[str, Any]:
    """Check .py module modification dates and sizes."""
    now = datetime.now()
    modules = []

    for py_file in sorted(THUNDERBIRD_DIR.glob("*.py")):
        stat = py_file.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        age_days = (now - mod_time).days
        size_kb = round(stat.st_size / 1024, 1)

        modules.append({
            "file": py_file.name,
            "size_kb": size_kb,
            "last_modified": mod_time.strftime("%Y-%m-%d"),
            "age_days": age_days,
        })

    # Sort by age descending (stalest first)
    modules.sort(key=lambda m: m["age_days"], reverse=True)

    stale = [m for m in modules if m["age_days"] > 30]
    large = [m for m in modules if m["size_kb"] > 40]

    return {
        "total_modules": len(modules),
        "stale_count": len(stale),
        "large_count": len(large),
        "stale_modules": stale[:10],
        "large_modules": sorted(large, key=lambda m: m["size_kb"], reverse=True)[:10],
        "recently_active": [m for m in modules if m["age_days"] <= 3][:10],
    }


def collect_code_anomalies() -> Dict[str, Any]:
    """Detect potential code issues: duplicate imports, oversized functions, etc."""
    import_counts = Counter()
    anomalies = []

    for py_file in THUNDERBIRD_DIR.glob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = content.splitlines()

        # Count imports across all files
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                import_counts[stripped] += 1

        # Check for very long files (>500 lines)
        if len(lines) > 500:
            anomalies.append({
                "file": py_file.name,
                "issue": f"Large file: {len(lines)} lines",
                "severity": "low" if len(lines) < 800 else "medium",
            })

        # Check for hardcoded API keys (excluding the known Groq key pattern)
        for i, line in enumerate(lines, 1):
            if re.search(r'(?:api_key|secret|password)\s*=\s*["\'][^"\']{20,}', line, re.IGNORECASE):
                if "GROQ_API_KEY" not in line and "gsk_" not in line:
                    anomalies.append({
                        "file": py_file.name,
                        "issue": f"Possible hardcoded secret at line {i}",
                        "severity": "high",
                    })

    # Find duplicated imports used across many files (not an issue, just info)
    widespread_imports = {imp: count for imp, count in import_counts.items() if count >= 5}

    return {
        "anomalies": anomalies,
        "widespread_imports": len(widespread_imports),
        "top_imports": dict(import_counts.most_common(5)),
    }


# ============================================================================
# TICKET GENERATOR — converts findings into structured tickets
# ============================================================================

def generate_tickets(
    scheduler: Dict,
    costs: Dict,
    dossier_items: Dict,
    module_health: Dict,
    code_anomalies: Dict,
) -> List[Dict[str, str]]:
    """Generate improvement tickets from collected audit data."""
    tickets = []
    today = date.today().isoformat()

    # --- Scheduler issues ---
    if scheduler.get("errors", 0) > 10:
        for log_name, stats in scheduler.get("by_log", {}).items():
            if stats.get("errors", 0) > 5:
                tickets.append({
                    "date": today,
                    "category": "quality",
                    "priority": "P2" if stats["errors"] > 20 else "P3",
                    "title": f"High error rate in {log_name}",
                    "description": (
                        f"{stats['errors']} errors in {stats['lines']} lines. "
                        f"Last entry: {stats.get('last_entry', 'N/A')[:80]}. "
                        f"Investigate root cause and add error handling or fix upstream."
                    ),
                    "assigned_to": PERSONA_OWNERS["infrastructure"],
                })

    # --- API cost spikes ---
    if costs.get("total_cost", 0) > 1.0:
        top_provider = max(
            costs.get("by_provider", {}).items(),
            key=lambda x: x[1]["cost"],
            default=(None, None)
        )
        if top_provider[0]:
            tickets.append({
                "date": today,
                "category": "cost",
                "priority": "P2",
                "title": f"API costs elevated: ${costs['total_cost']:.2f} in {costs['period_days']}d",
                "description": (
                    f"Top provider: {top_provider[0]} at ${top_provider[1]['cost']:.2f} "
                    f"({top_provider[1]['calls']} calls). "
                    f"Review whether calls can be cached, batched, or moved to cheaper models."
                ),
                "assigned_to": PERSONA_OWNERS["cost"],
            })

    # --- High-volume callers ---
    for caller, stats in costs.get("by_caller", {}).items():
        if stats["calls"] > 50:
            tickets.append({
                "date": today,
                "category": "efficiency",
                "priority": "P3",
                "title": f"High API call volume from {caller}: {stats['calls']} calls",
                "description": (
                    f"Caller '{caller}' made {stats['calls']} API calls "
                    f"(${stats['cost']:.4f}). Consider caching or reducing call frequency."
                ),
                "assigned_to": PERSONA_OWNERS["efficiency"],
            })

    # --- Stale dossier items ---
    if dossier_items.get("total_stale", 0) > 0:
        # Group by dossier
        by_dossier = defaultdict(list)
        for item in dossier_items.get("stale_items", []):
            by_dossier[item["dossier"]].append(item)

        for dossier_name, items in by_dossier.items():
            pending_count = sum(1 for i in items if i["type"] == "pending")
            unchecked_count = sum(1 for i in items if i["type"] == "unchecked")
            sample_items = "; ".join(i["item"] for i in items[:3])
            tickets.append({
                "date": today,
                "category": "quality",
                "priority": "P2" if pending_count > 0 else "P3",
                "title": f"Stale items in {dossier_name}",
                "description": (
                    f"{pending_count} PENDING, {unchecked_count} unchecked. "
                    f"Samples: {sample_items}. "
                    f"Review and resolve or mark complete."
                ),
                "assigned_to": PERSONA_OWNERS["operations"],
            })

    # --- Stale modules ---
    for mod in module_health.get("stale_modules", [])[:5]:
        if mod["age_days"] > 60:
            tickets.append({
                "date": today,
                "category": "quality",
                "priority": "P4",
                "title": f"Stale module: {mod['file']} ({mod['age_days']}d untouched)",
                "description": (
                    f"Last modified {mod['last_modified']}, {mod['size_kb']}KB. "
                    f"Verify still needed. If active, may need updates for current patterns."
                ),
                "assigned_to": PERSONA_OWNERS["infrastructure"],
            })

    # --- Large files ---
    for mod in module_health.get("large_modules", []):
        if mod["size_kb"] > 50:
            tickets.append({
                "date": today,
                "category": "efficiency",
                "priority": "P4",
                "title": f"Oversized module: {mod['file']} ({mod['size_kb']}KB)",
                "description": (
                    f"Consider refactoring into smaller, focused modules. "
                    f"Large files are harder to maintain and test."
                ),
                "assigned_to": PERSONA_OWNERS["infrastructure"],
            })

    # --- Code anomalies ---
    for anomaly in code_anomalies.get("anomalies", []):
        if anomaly["severity"] == "high":
            tickets.append({
                "date": today,
                "category": "quality",
                "priority": "P1",
                "title": f"Security concern: {anomaly['file']}",
                "description": anomaly["issue"],
                "assigned_to": PERSONA_OWNERS["infrastructure"],
            })

    return tickets


# ============================================================================
# ELON ANALYSIS — send findings to A12 persona for commentary
# ============================================================================

def get_elon_analysis(audit_data: Dict[str, Any], tickets: List[Dict]) -> str:
    """Have ELON (A12) analyze the audit findings and provide commentary."""
    summary = _build_audit_summary(audit_data, tickets)

    prompt = f"""You are conducting your weekly Nova Audit of Thunderbird OS — the automation
platform for Dreams2Memories Travel, LLC. Here's what the data collection found:

{summary}

Give me your unfiltered analysis. Be specific. Call out:
1. The biggest waste of time or money you see
2. What should be automated that isn't
3. What's working well (briefly — don't dwell)
4. Your top 3 recommendations, ranked by impact

Keep it under 500 words. Be direct. Be ELON."""

    result = smart_route("A12", prompt, max_tokens=800)

    if result.get("success"):
        return result["response"]
    else:
        logger.error(f"ELON analysis failed: {result.get('response', 'unknown error')}")
        return "[ELON analysis unavailable — API call failed]"


def _build_audit_summary(audit_data: Dict, tickets: List[Dict]) -> str:
    """Build a text summary of audit findings for ELON's prompt."""
    lines = []

    # Scheduler health
    sched = audit_data.get("scheduler", {})
    lines.append(f"SCHEDULER: {sched.get('log_files_found', 0)} log files, "
                 f"{sched.get('errors', 0)} errors, {sched.get('warnings', 0)} warnings")
    for log_name, stats in list(sched.get("by_log", {}).items())[:5]:
        if stats.get("errors", 0) > 0:
            lines.append(f"  - {log_name}: {stats['errors']} errors / {stats['lines']} lines")

    # API costs
    costs = audit_data.get("costs", {})
    lines.append(f"\nAPI COSTS ({costs.get('period_days', 7)}d): "
                 f"${costs.get('total_cost', 0):.4f} across {costs.get('total_calls', 0)} calls")
    for provider, stats in costs.get("by_provider", {}).items():
        lines.append(f"  - {provider}: ${stats['cost']:.4f} ({stats['calls']} calls, "
                     f"{stats['tokens_in']} in / {stats['tokens_out']} out)")

    # Dossier items
    dossier = audit_data.get("dossier_items", {})
    lines.append(f"\nDOSSIER ITEMS: {dossier.get('total_stale', 0)} pending/unchecked items")
    for item in dossier.get("stale_items", [])[:5]:
        lines.append(f"  - [{item['type']}] {item['dossier']}: {item['item']}")

    # Module health
    health = audit_data.get("module_health", {})
    lines.append(f"\nMODULES: {health.get('total_modules', 0)} total, "
                 f"{health.get('stale_count', 0)} stale (>30d), "
                 f"{health.get('large_count', 0)} oversized (>40KB)")
    lines.append(f"  Recently active: {len(health.get('recently_active', []))}")

    # Code anomalies
    anomalies = audit_data.get("code_anomalies", {})
    lines.append(f"\nCODE: {len(anomalies.get('anomalies', []))} anomalies detected")
    for a in anomalies.get("anomalies", [])[:3]:
        lines.append(f"  - [{a['severity']}] {a['file']}: {a['issue']}")

    # Tickets generated
    lines.append(f"\nTICKETS GENERATED: {len(tickets)}")
    by_priority = Counter(t["priority"] for t in tickets)
    lines.append(f"  By priority: {dict(by_priority)}")
    by_category = Counter(t["category"] for t in tickets)
    lines.append(f"  By category: {dict(by_category)}")

    return "\n".join(lines)


# ============================================================================
# NOVA REPORT — markdown output
# ============================================================================

def generate_nova_report(
    audit_data: Dict[str, Any],
    tickets: List[Dict],
    elon_analysis: str,
) -> str:
    """Generate the weekly Nova Report in markdown."""
    today = date.today()
    report_date = today.strftime("%Y-%m-%d")
    report_header = today.strftime("%B %d, %Y")

    costs = audit_data.get("costs", {})
    sched = audit_data.get("scheduler", {})
    health = audit_data.get("module_health", {})
    dossier = audit_data.get("dossier_items", {})

    # Build ticket table
    ticket_rows = []
    for t in tickets:
        ticket_rows.append(
            f"| {t['priority']} | {t['category']} | {t['title'][:50]} | {t['assigned_to']} |"
        )
    ticket_table = "\n".join(ticket_rows) if ticket_rows else "| — | — | No tickets generated | — |"

    report = f"""# NOVA AUDIT REPORT — {report_header}
### Dreams2Memories Travel, LLC — Thunderbird OS Self-Improvement System
### Analyst: ELON (A12) | Classification: INTERNAL

---

## Executive Summary

| Metric | Value |
|--------|-------|
| API Spend ({costs.get('period_days', 7)}d) | ${costs.get('total_cost', 0):.4f} |
| API Calls ({costs.get('period_days', 7)}d) | {costs.get('total_calls', 0)} |
| Log Errors | {sched.get('errors', 0)} |
| Log Warnings | {sched.get('warnings', 0)} |
| Stale Dossier Items | {dossier.get('total_stale', 0)} |
| Python Modules | {health.get('total_modules', 0)} |
| Stale Modules (>30d) | {health.get('stale_count', 0)} |
| Oversized Modules (>40KB) | {health.get('large_count', 0)} |
| Tickets Filed | {len(tickets)} |

---

## API Cost Breakdown

| Provider | Calls | Cost | Tokens In | Tokens Out |
|----------|-------|------|-----------|------------|
"""

    for provider, stats in costs.get("by_provider", {}).items():
        report += (f"| {provider} | {stats['calls']} | ${stats['cost']:.4f} | "
                   f"{stats['tokens_in']:,} | {stats['tokens_out']:,} |\n")

    if not costs.get("by_provider"):
        report += "| — | — | — | — | — |\n"

    report += f"""
### Top Callers

| Caller | Calls | Cost |
|--------|-------|------|
"""

    for caller, stats in sorted(
        costs.get("by_caller", {}).items(),
        key=lambda x: x[1]["cost"], reverse=True
    )[:10]:
        report += f"| {caller} | {stats['calls']} | ${stats['cost']:.4f} |\n"

    report += f"""
---

## Scheduler Health

| Log File | Lines | Errors | Warnings |
|----------|-------|--------|----------|
"""

    for log_name, stats in sorted(sched.get("by_log", {}).items()):
        report += f"| {log_name} | {stats['lines']:,} | {stats['errors']} | {stats['warnings']} |\n"

    report += f"""
---

## Dossier Status

**{dossier.get('total_stale', 0)} items need attention:**

"""

    for item in dossier.get("stale_items", []):
        icon = "**PENDING**" if item["type"] == "pending" else "[ ]"
        report += f"- {icon} `{item['dossier']}`: {item['item']}\n"

    report += f"""
---

## Module Health

### Recently Active (last 3 days)
"""

    for mod in health.get("recently_active", []):
        report += f"- `{mod['file']}` — {mod['size_kb']}KB, modified {mod['last_modified']}\n"

    report += f"""
### Stalest Modules
"""

    for mod in health.get("stale_modules", [])[:10]:
        report += f"- `{mod['file']}` — {mod['age_days']}d old, {mod['size_kb']}KB\n"

    report += f"""
### Largest Modules
"""

    for mod in health.get("large_modules", [])[:10]:
        report += f"- `{mod['file']}` — {mod['size_kb']}KB, modified {mod['last_modified']}\n"

    report += f"""
---

## Improvement Tickets

| Priority | Category | Title | Owner |
|----------|----------|-------|-------|
{ticket_table}

---

## ELON's Take

{elon_analysis}

---

*Generated by Thunderbird Nova v1.0 — {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*"Build it once, benefit forever. Repeat yourself and you've already lost."*
"""

    return report


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run_weekly_audit(write_sheets: bool = True, skip_elon: bool = False) -> Dict[str, Any]:
    """Run the full weekly Nova audit.

    Args:
        write_sheets: If True, write tickets to Google Sheets Action_Tracker tab.
        skip_elon: If True, skip the ELON AI analysis (faster, no API call).

    Returns:
        Dict with audit_data, tickets, elon_analysis, report_path, tickets_written.
    """
    logger.info("Nova audit starting...")

    # 1. Collect all audit data
    audit_data = {
        "scheduler": collect_scheduler_health(),
        "costs": collect_api_costs(days=7),
        "dossier_items": collect_stale_dossier_items(),
        "module_health": collect_module_health(),
        "code_anomalies": collect_code_anomalies(),
    }
    logger.info("Data collection complete")

    # 2. Generate improvement tickets
    tickets = generate_tickets(
        scheduler=audit_data["scheduler"],
        costs=audit_data["costs"],
        dossier_items=audit_data["dossier_items"],
        module_health=audit_data["module_health"],
        code_anomalies=audit_data["code_anomalies"],
    )
    logger.info(f"Generated {len(tickets)} tickets")

    # 3. Get ELON's analysis
    if skip_elon:
        elon_analysis = "[Skipped — run with skip_elon=False for AI analysis]"
    else:
        elon_analysis = get_elon_analysis(audit_data, tickets)
    logger.info("ELON analysis complete")

    # 4. Write tickets to Google Sheets
    tickets_written = 0
    if write_sheets and tickets:
        try:
            tickets_written = write_tickets_to_sheet(tickets)
            logger.info(f"Wrote {tickets_written} tickets to Action_Tracker")
        except Exception as e:
            logger.error(f"Failed to write tickets to sheet: {e}")

    # 5. Generate and save the Nova Report
    report = generate_nova_report(audit_data, tickets, elon_analysis)
    report_filename = f"nova_report_{date.today().strftime('%Y%m%d')}.md"
    report_path = OUTPUT_DIR / report_filename

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    logger.info(f"Nova report saved to {report_path}")

    # 6. Save state for tracking
    state = {
        "last_run": datetime.now().isoformat(),
        "tickets_generated": len(tickets),
        "tickets_written": tickets_written,
        "report_path": str(report_path),
        "total_api_cost_7d": audit_data["costs"].get("total_cost", 0),
        "stale_dossier_items": audit_data["dossier_items"].get("total_stale", 0),
        "log_errors": audit_data["scheduler"].get("errors", 0),
    }
    NOVA_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "audit_data": audit_data,
        "tickets": tickets,
        "tickets_written": tickets_written,
        "elon_analysis": elon_analysis,
        "report_path": str(report_path),
    }


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    write = "--no-sheets" not in sys.argv
    skip = "--skip-elon" in sys.argv

    print("=" * 60)
    print("THUNDERBIRD NOVA — Weekly Self-Improvement Audit")
    print("Analyst: ELON (A12)")
    print("=" * 60)
    print()

    result = run_weekly_audit(write_sheets=write, skip_elon=skip)

    print(f"\nStatus: {result['status']}")
    print(f"Tickets generated: {len(result['tickets'])}")
    print(f"Tickets written to sheet: {result['tickets_written']}")
    print(f"Report saved: {result['report_path']}")

    if result["tickets"]:
        print("\nTickets:")
        for t in result["tickets"]:
            print(f"  [{t['priority']}] [{t['category']}] {t['title']}")

    print(f"\n{'=' * 60}")
    print("Nova audit complete.")

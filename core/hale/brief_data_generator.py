#!/usr/bin/env python3
"""
Hale Visual Communication Architecture — Data Layer
Extracts, validates, and structures operational data with freshness checking.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

ROOT = Path("/home/john/Thunderbird")
OUTPUT_VISUALS = ROOT / "output" / "visuals"
DOSSIERS = ROOT / "dossiers"
MT = timezone(timedelta(hours=-6))


def is_fresh(file_path: Path, hours: int = 24) -> bool:
    """Check if file exists and is less than N hours old."""
    if not file_path.exists():
        return False
    mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=MT)
    age = datetime.now(MT) - mtime
    return age < timedelta(hours=hours)


def load_phase1_data() -> dict:
    """Load phase1_data.json with freshness check."""
    phase1_file = OUTPUT_VISUALS / "phase1_data.json"
    if is_fresh(phase1_file):
        return json.loads(phase1_file.read_text())
    # Fallback: return empty structure if file missing
    return {"clients": [], "tasks": [], "financial": {"total": 0}}


def load_hale_state() -> dict:
    """Load hale_state.json for real-time system health and task state."""
    hale_state_file = ROOT / "hale_state.json"
    if is_fresh(hale_state_file):
        return json.loads(hale_state_file.read_text())
    return {
        "system_health": {},
        "open_tasks": [],
        "pending_decisions": [],
        "financial_pulse": {}
    }


def load_dossier(client_name: str) -> Optional[dict]:
    """Load individual client dossier if it exists."""
    dossier_file = DOSSIERS / f"{client_name}.json"
    if dossier_file.exists():
        try:
            return json.loads(dossier_file.read_text())
        except json.JSONDecodeError:
            return None
    return None


def load_all_dossiers() -> Dict[str, dict]:
    """Load all client dossiers for lifecycle state."""
    dossiers = {}
    for dossier_file in DOSSIERS.glob("*.json"):
        try:
            client_name = dossier_file.stem
            dossiers[client_name] = json.loads(dossier_file.read_text())
        except json.JSONDecodeError:
            pass
    return dossiers


def structure_brief_data(phase1_data: dict, hale_state: dict, dossiers: dict) -> dict:
    """
    Transform raw data into visual-ready format.
    Returns dict with keys: clients, financial, tasks, risks, decisions.
    """

    # Extract clients from phase1 with urgency and FPD state
    clients = []
    for client in phase1_data.get("clients", []):
        fpd_date_str = client.get("fpd_date", "")
        fpd_days = 0
        if fpd_date_str:
            try:
                fpd_date = datetime.fromisoformat(fpd_date_str).date()
                today = datetime.now(MT).date()
                fpd_days = (fpd_date - today).days
            except (ValueError, TypeError):
                fpd_days = 0

        clients.append({
            "name": client.get("name", "Unknown"),
            "phase": client.get("phase", "Prospect"),
            "urgency": client.get("urgency", "green"),  # red/yellow/green
            "fpd_days": fpd_days,
            "commission": client.get("commission", 0),
            "status_icon": "🔴" if client.get("urgency") == "red" else
                          "🟡" if client.get("urgency") == "yellow" else "🟢"
        })

    # Extract financial waterfall stages
    financial_data = phase1_data.get("financial", {})
    waterfall = {
        "prospects_pipeline": financial_data.get("prospects_value", 0),
        "conversion_rate": financial_data.get("conversion_rate", 0.15),
        "booked_confirmed": financial_data.get("booked_value", 0),
        "at_risk_deduction": financial_data.get("at_risk_value", 0),
        "projected_final": financial_data.get("projected_revenue", 0),
        "allianz_claim": 11280  # Hardcoded from brief context
    }

    # Extract tasks from phase1
    tasks = phase1_data.get("tasks", [])

    # Build risk matrix from client state + hale_state decisions
    risks = compute_risks(clients, hale_state, dossiers)

    # Extract pending decisions from hale_state
    decisions = hale_state.get("pending_decisions", [])

    return {
        "generated_at": datetime.now(MT).isoformat(),
        "clients": clients,
        "waterfall": waterfall,
        "tasks": tasks,
        "risks": risks,
        "decisions": decisions,
        "system_health": hale_state.get("system_health", {}),
        "open_items_count": len(decisions)
    }


def compute_risks(clients: List[dict], hale_state: dict, dossiers: dict) -> List[dict]:
    """
    Derive risk matrix entries from client lifecycle and financial state.
    Returns list of risks with: name, likelihood (0-100), disruption (0-10),
    action (Escalate/Mitigate/Monitor/Accept), timeline.
    """
    risks = []

    # Risk 1: Overdue FPD (Furlow)
    for client in clients:
        if client["fpd_days"] < 0:
            risks.append({
                "name": f"{client['name']} — FPD Overdue",
                "likelihood": 95,
                "disruption": 9,
                "action": "ESCALATE",
                "timeline": "Immediate",
                "details": f"Final Payment Due was {abs(client['fpd_days'])} days ago"
            })
        elif client["fpd_days"] < 7:
            risks.append({
                "name": f"{client['name']} — FPD Approaching",
                "likelihood": 70,
                "disruption": 8,
                "action": "MITIGATE",
                "timeline": f"{client['fpd_days']} days",
                "details": "Final Payment due soon — proactive confirmation recommended"
            })

    # Risk 2: Allianz claim pending
    risks.append({
        "name": "Allianz Insurance Claim ($11,280)",
        "likelihood": 50,
        "disruption": 6,
        "action": "MITIGATE",
        "timeline": "Pending (no update since Apr 24)",
        "details": "Travel insurance claim awaiting settlement"
    })

    # Risk 3: TESS auth required (financial visibility blind)
    financial_pulse = hale_state.get("financial_pulse", {})
    if "BLIND" in str(financial_pulse) or "auth_required" in str(financial_pulse):
        risks.append({
            "name": "Financial Data Feed Offline",
            "likelihood": 100,
            "disruption": 5,
            "action": "MITIGATE",
            "timeline": "Immediate",
            "details": "TESS re-authentication required to restore commission visibility"
        })

    # Risk 4: Task backlog depth
    open_task_count = len(hale_state.get("open_tasks", []))
    if open_task_count > 8:
        risks.append({
            "name": "Task Backlog Accumulation",
            "likelihood": 60,
            "disruption": 7,
            "action": "MITIGATE",
            "timeline": "This week",
            "details": f"{open_task_count} open tasks — capacity risk"
        })

    # Risk 5: Chrome debug offline (infrastructure)
    sys_health = hale_state.get("system_health", {})
    if sys_health.get("chrome_debug") == "OFFLINE":
        risks.append({
            "name": "Development Environment Degradation",
            "likelihood": 40,
            "disruption": 3,
            "action": "MONITOR",
            "timeline": "Low priority",
            "details": "Chrome debugging port offline — non-critical"
        })

    return risks


def load_or_fetch_data() -> dict:
    """
    Main entry point: Load or fetch all operational data with freshness checks.
    Returns structured brief_data ready for visualization.
    """
    phase1_data = load_phase1_data()
    hale_state = load_hale_state()
    dossiers = load_all_dossiers()

    brief_data = structure_brief_data(phase1_data, hale_state, dossiers)
    return brief_data


if __name__ == "__main__":
    # Test data loading
    data = load_or_fetch_data()
    print(json.dumps(data, indent=2, default=str))

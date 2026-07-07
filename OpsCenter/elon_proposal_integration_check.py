#!/usr/bin/env python3
"""
ELON Proposal Integration Check — ground-truth closure/integration tracker.

Root cause this fixes: the 2026-07-06 closure protocol (ELON_PROPOSAL_CLOSURE_PROTOCOL.md)
promised metrics in hale_state.json under "elon_proposals" and a CLOSED/ archive.
Neither was ever built. This script computes REAL numbers from disk/git/systemd —
no self-reported completion is trusted.

Two-bar test per named capability module:
  1. COMMITTED — file exists and is tracked in git.
  2. WIRED — referenced by >=1 file outside itself/its own test, OR has an
     enabled+active systemd unit, OR is imported by a script under scripts/ or core/hale/.

A module passes only if BOTH bars clear. Existence on disk is not integration.

Usage: python3 elon_proposal_integration_check.py [--write]
  --write   also update hale_state.json elon_proposals block (default: dry-run, prints only)
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

REPO = Path("/home/john/Thunderbird")
PROPOSALS_DIR = REPO / "OpsCenter" / "elon_proposals"
CLOSED_DIR = PROPOSALS_DIR / "CLOSED"
STATE_FILE = REPO / "hale_state.json"

# Named capability -> (module basename, systemd unit or None)
TRACKED_MODULES = {
    "wcag_auditor": ("wcag_auditor", None),
    "crew_roster": ("crew_roster", None),
    "demand_predictor": ("demand_predictor", "demand-predictor-retrain.timer"),
    "itinerary_optimizer": ("itinerary_optimizer", None),
    "memory_book_builder": ("memory_book_builder", None),
    "medical_screening": ("medical_screening", None),
    "upgrade_detector": ("upgrade_detector", None),
    "upsell_recommender": ("upsell_recommender", None),
    "insurance_integrator": ("insurance_integrator", None),
    "booking_notifications": ("booking_notifications", "booking-notifications.timer"),
    "client_ivr": ("client_ivr", None),
    "lounge_coordinator": ("lounge_coordinator", None),
    "port_restaurant_coordinator": ("port_restaurant_coordinator", None),
    "cruise_line_policy_checker": ("cruise_line_policy_checker", None),
    "pricing_negotiation": ("pricing_negotiation", None),
    "translation_engine": ("translation_engine", None),
    "cancellation_scorer": ("cancellation_scorer", None),
    "sentiment_analyzer": ("sentiment_analyzer", None),
    "loyalty_tracker": ("loyalty_tracker", None),
    "predictive_intelligence": ("predictive_intelligence", None),
    "claude_narrative_generator": ("claude_narrative_generator", None),
}

# Capabilities claimed in the 2026-07-06 report with NO file evidence found on verification pass.
NOT_FOUND = [
    "commission_reconciliation_automation",
    "portal_session_manager",
    "booking_webhook_orchestration",
    "client_communication_timeline",
    "birthday_anniversary_voyage_suggestions",
    "drive_intelligence_indexing",
    "mcp_tool_discoverability",
    "client_preference_learning_engine",
    "voyage_intelligence_digest",
    "competitive_intelligence_weekly",
    "ai_model_cost_attribution",
    "staff_performance_metrics_dashboard",
    "voyage_comparison_matrix",
    "operational_intelligence_dashboard",
    "instructor_structured_output",
    "one_command_client_proposals",
]


def run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return ""


def is_committed(module: str) -> bool:
    out = run(["git", "ls-files"])
    return any(f"{module}.py" in line and "test_" not in line for line in out.splitlines())


def external_reference_count(module: str) -> int:
    out = run(["git", "grep", "-l", module, "--", "*.py"])
    files = [f for f in out.splitlines() if f and f"test_{module}" not in f and not f.endswith(f"/{module}.py")]
    return len(files)


def systemd_active(unit: str) -> bool:
    if not unit:
        return False
    enabled = subprocess.run(["systemctl", "--user", "is-enabled", unit],
                              capture_output=True, text=True).stdout.strip()
    active = subprocess.run(["systemctl", "--user", "is-active", unit],
                             capture_output=True, text=True).stdout.strip()
    return enabled == "enabled" and active == "active"


def count_proposal_backlog():
    proposals = [p for p in PROPOSALS_DIR.glob("PROPOSAL-*.md") if not p.name.endswith(".tmp") and ".tmp." not in p.name]
    executions = list(PROPOSALS_DIR.glob("*_EXECUTION.md"))
    closed = list(CLOSED_DIR.glob("*.md")) if CLOSED_DIR.exists() else []
    new_format = [p for p in proposals if "CLOSURE_TARGET_DATE" in p.read_text(errors="ignore")]
    return {
        "open_proposals_raw_count": len(proposals),
        "execution_reports_logged": len(executions),
        "archived_to_closed_dir": len(closed),
        "using_new_protocol_format": len(new_format),
    }


def main():
    write = "--write" in sys.argv
    results = {}
    committed_count = 0
    wired_count = 0
    for capability, (module, unit) in TRACKED_MODULES.items():
        committed = is_committed(module)
        refs = external_reference_count(module)
        wired = systemd_active(unit) or refs >= 1
        if committed:
            committed_count += 1
        if committed and wired:
            wired_count += 1
        results[capability] = {
            "committed": committed,
            "external_references": refs,
            "systemd_wired": systemd_active(unit) if unit else None,
            "integrated": committed and wired,
        }

    backlog = count_proposal_backlog()
    total_claimed = len(TRACKED_MODULES) + len(NOT_FOUND)

    summary = {
        "last_verified": datetime.now(timezone.utc).astimezone().isoformat(),
        "verification_method": "git ls-files + git grep external refs + systemctl --user is-enabled/is-active. No self-report trusted.",
        "2026-07-06_batch_claim": "40 proposals executed, 61 agents, 98% success rate",
        "2026-07-06_batch_verified": {
            "claimed_total": total_claimed,
            "committed_to_git": committed_count,
            "passing_both_bars_committed_and_wired": wired_count,
            "no_file_evidence_found": len(NOT_FOUND),
            "not_found_list": NOT_FOUND,
        },
        "per_capability": results,
        "proposal_queue": backlog,
        "closure_protocol_adoption": "NOT ADOPTED — 0 proposals use CLOSURE_TARGET_DATE field, CLOSED/ dir does not exist, this metrics block did not exist in hale_state.json until this script ran",
    }

    print(json.dumps(summary, indent=2))

    if write:
        state = json.loads(STATE_FILE.read_text())
        state["elon_proposals"] = summary
        state["_meta"]["last_updated"] = datetime.now(timezone.utc).astimezone().isoformat()
        STATE_FILE.write_text(json.dumps(state, indent=2))
        print(f"\n--- WROTE elon_proposals block to {STATE_FILE} ---", file=sys.stderr)
    else:
        print("\n--- DRY RUN. Re-run with --write to persist to hale_state.json ---", file=sys.stderr)


if __name__ == "__main__":
    main()

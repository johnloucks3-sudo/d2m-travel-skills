import json
from datetime import date

import sys
sys.path.insert(0, "/home/john/Thunderbird")

from core.hale.predictive_intelligence import (
    scan_vendor_contract_expirations,
    scan_insurance_policy_renewals,
    scan_commission_reconciliation_cycle,
    scan_client_reengagement_windows,
    scan_competitor_intel_freshness,
    run_all,
)


# ---------------------------------------------------------------------------
# 1. Vendor contract expirations
# ---------------------------------------------------------------------------
def test_vendor_contracts_empty_registry_is_no_findings(tmp_path):
    registry = tmp_path / "vendor_contracts.json"
    registry.write_text(json.dumps({"contracts": []}))
    assert scan_vendor_contract_expirations(registry_path=registry, now=date(2026, 7, 6)) == []


def test_vendor_contracts_missing_file_is_no_findings(tmp_path):
    registry = tmp_path / "does_not_exist.json"
    assert scan_vendor_contract_expirations(registry_path=registry, now=date(2026, 7, 6)) == []


def test_vendor_contract_expiring_soon_flags_high(tmp_path):
    registry = tmp_path / "vendor_contracts.json"
    registry.write_text(json.dumps({
        "contracts": [
            {"vendor": "Nexion", "contract_type": "host agreement", "expires": "2026-07-16"}
        ]
    }))
    findings = scan_vendor_contract_expirations(registry_path=registry, now=date(2026, 7, 6))
    assert len(findings) == 1
    assert findings[0]["days_out"] == 10
    assert findings[0]["priority"] == "HIGH"


def test_vendor_contract_far_out_not_flagged(tmp_path):
    registry = tmp_path / "vendor_contracts.json"
    registry.write_text(json.dumps({
        "contracts": [
            {"vendor": "Nexion", "contract_type": "host agreement", "expires": "2027-07-16"}
        ]
    }))
    assert scan_vendor_contract_expirations(registry_path=registry, now=date(2026, 7, 6)) == []


# ---------------------------------------------------------------------------
# 2. Insurance policy renewals
# ---------------------------------------------------------------------------
def test_insurance_policy_renewal_medium_priority(tmp_path):
    registry = tmp_path / "insurance_policies.json"
    registry.write_text(json.dumps({
        "policies": [
            {"policy": "E&O", "carrier": "Travel Guard", "expires": "2026-08-15"}
        ]
    }))
    findings = scan_insurance_policy_renewals(registry_path=registry, now=date(2026, 7, 6))
    assert len(findings) == 1
    assert findings[0]["priority"] == "MEDIUM"


def test_insurance_empty_registry_is_no_findings(tmp_path):
    registry = tmp_path / "insurance_policies.json"
    registry.write_text(json.dumps({"policies": []}))
    assert scan_insurance_policy_renewals(registry_path=registry, now=date(2026, 7, 6)) == []


# ---------------------------------------------------------------------------
# 3. Commission reconciliation cycle
# ---------------------------------------------------------------------------
def test_reconciliation_flags_when_none_filed_this_month(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "commission_reconciliation_20260602.md").write_text("prior month recon")
    findings = scan_commission_reconciliation_cycle(state_dir=state_dir, now=date(2026, 7, 10))
    assert len(findings) == 1
    assert findings[0]["period"] == "2026-07"


def test_reconciliation_not_flagged_when_filed_this_month(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    (state_dir / "commission_reconciliation_20260702.md").write_text("this month recon")
    assert scan_commission_reconciliation_cycle(state_dir=state_dir, now=date(2026, 7, 10)) == []


def test_reconciliation_inside_grace_window_not_flagged(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    assert scan_commission_reconciliation_cycle(state_dir=state_dir, now=date(2026, 7, 3)) == []


# ---------------------------------------------------------------------------
# 4. Client re-engagement windows
# ---------------------------------------------------------------------------
def test_client_overdue_18_months_is_flagged(tmp_path):
    dossier_dir = tmp_path / "dossiers"
    dossier_dir.mkdir()
    (dossier_dir / "DOSSIER_Britan_Sep2024.md").write_text(
        "Embarkation: September 10, 2024 — Rome, Italy\n"
    )
    board = tmp_path / "mission_board.json"
    board.write_text(json.dumps({"missions": []}))

    findings = scan_client_reengagement_windows(
        dossier_dir=dossier_dir, mission_board_path=board, now=date(2026, 7, 6)
    )
    assert len(findings) == 1
    assert findings[0]["client"] == "Britan"
    assert findings[0]["days_since_last_departure"] >= 548


def test_client_recent_departure_not_flagged(tmp_path):
    dossier_dir = tmp_path / "dossiers"
    dossier_dir.mkdir()
    (dossier_dir / "DOSSIER_Furlow_Aug2026.md").write_text(
        "departure: 2026-05-01\n"
    )
    board = tmp_path / "mission_board.json"
    board.write_text(json.dumps({"missions": []}))

    findings = scan_client_reengagement_windows(
        dossier_dir=dossier_dir, mission_board_path=board, now=date(2026, 7, 6)
    )
    assert findings == []


def test_client_overdue_but_has_active_mission_not_flagged(tmp_path):
    dossier_dir = tmp_path / "dossiers"
    dossier_dir.mkdir()
    (dossier_dir / "DOSSIER_Britan_Sep2024.md").write_text(
        "Embarkation: September 10, 2024 — Rome, Italy\n"
    )
    board = tmp_path / "mission_board.json"
    board.write_text(json.dumps({
        "missions": [
            {"title": "Britan — new proposal follow-up", "status": "active"}
        ]
    }))

    findings = scan_client_reengagement_windows(
        dossier_dir=dossier_dir, mission_board_path=board, now=date(2026, 7, 6)
    )
    assert findings == []


def test_cohort_signal_predicts_q3_rebook_window():
    """6-month synthetic historical validation: a repeat-client cohort that
    always books Q3 voyages should predict a Q3 rebook window for an overdue
    client, and should NOT flag clients who already rebooked inside that
    window (precision) while flagging the one who genuinely didn't
    (recall)."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        dossier_dir = Path(td) / "dossiers"
        dossier_dir.mkdir()
        board_path = Path(td) / "mission_board.json"

        # Repeat clients (Kuklinski, Nichols) with 2 historical Q3 voyages each
        # -> establishes the Q3 cohort pattern.
        (dossier_dir / "DOSSIER_Kuklinski_2023.md").write_text(
            "Embarkation: August 12, 2023 — Athens, Greece\n"
        )
        (dossier_dir / "DOSSIER_Kuklinski_2025.md").write_text(
            "Embarkation: July 20, 2025 — Athens, Greece\n"
        )
        (dossier_dir / "DOSSIER_Nichols_2023.md").write_text(
            "Embarkation: September 05, 2023 — Lisbon, Portugal\n"
        )
        (dossier_dir / "DOSSIER_Nichols_2025.md").write_text(
            "Embarkation: August 01, 2025 — Lisbon, Portugal\n"
        )
        # McLeod actually rebooked recently -> must NOT be flagged (precision)
        (dossier_dir / "DOSSIER_McLeod_2026.md").write_text(
            "departure: 2026-06-01\n"
        )
        # Ely-Darrow last sailed 20 months ago, no follow-on mission -> MUST
        # be flagged (recall), with a Q3 predicted window from the cohort.
        (dossier_dir / "DOSSIER_ElyDarrow_2024.md").write_text(
            "Embarkation: November 10, 2024 — Barcelona, Spain\n"
        )

        board_path.write_text(json.dumps({"missions": []}))

        findings = scan_client_reengagement_windows(
            dossier_dir=dossier_dir, mission_board_path=board_path, now=date(2026, 7, 6)
        )

    flagged_clients = {f["client"] for f in findings}
    assert "ElyDarrow" in flagged_clients
    assert "McLeod" not in flagged_clients
    assert "Kuklinski" not in flagged_clients  # both its voyages are historical, last one <18mo... verify below

    ely_finding = next(f for f in findings if f["client"] == "ElyDarrow")
    assert ely_finding["predicted_rebook_window"].startswith("Q3")
    assert "cohort_signal" in ely_finding


# ---------------------------------------------------------------------------
# 5. Competitor intel freshness
# ---------------------------------------------------------------------------
def test_stale_competitor_intel_flagged(tmp_path):
    intel_dir = tmp_path / "intel"
    intel_dir.mkdir()
    f = intel_dir / "competitor_scan.md"
    f.write_text("old scan")
    import os
    stale_time = date(2026, 6, 1)
    import time
    old_epoch = time.mktime((stale_time.year, stale_time.month, stale_time.day, 0, 0, 0, 0, 0, -1))
    os.utime(f, (old_epoch, old_epoch))

    findings = scan_competitor_intel_freshness(
        intel_dir=intel_dir, now=date(2026, 7, 6)
    )
    assert len(findings) == 1
    assert findings[0]["days_stale"] > 7


def test_fresh_competitor_intel_not_flagged(tmp_path):
    intel_dir = tmp_path / "intel"
    intel_dir.mkdir()
    (intel_dir / "competitor_scan.md").write_text("fresh scan")

    findings = scan_competitor_intel_freshness(intel_dir=intel_dir, now=None)
    assert findings == []


def test_no_competitor_files_is_no_findings(tmp_path):
    intel_dir = tmp_path / "intel"
    intel_dir.mkdir()
    (intel_dir / "unrelated.md").write_text("nothing to do with competitors")
    assert scan_competitor_intel_freshness(intel_dir=intel_dir, now=date(2026, 7, 6)) == []


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def test_run_all_returns_five_keys():
    results = run_all(now=date(2026, 7, 6))
    assert set(results.keys()) == {
        "vendor_contract_expirations",
        "insurance_policy_renewals",
        "commission_reconciliation_cycle",
        "client_reengagement_windows",
        "competitor_intel_freshness",
    }

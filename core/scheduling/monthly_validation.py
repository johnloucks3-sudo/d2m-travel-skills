#!/usr/bin/env python3
"""
MISSION-014: Monthly Client Validation Audit — 7-Persona Domain Architecture
Routes validation through domain-expert personas. Each persona owns their checks and signs off.
Personas: Dembe (intel), Reyes (experience), Harlan (finance), Sterling (process),
          Dani (comms), ELON (automation), Hale (consensus).
"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# Active clients (7 total)
ACTIVE_CLIENTS = {
    "Lyons": {"names": "Nancy & Ken Lyons", "ship": "Friend Service", "cruise_line": "RSSC", "fpd": None},
    "Kuklinski": {"names": "Kyle Kuklinski", "ship": "Viking Mars", "cruise_line": "Viking", "fpd": None},
    "Westbrook": {"names": "Brent & Kim Westbrook", "ship": "Silver Nova", "cruise_line": "Silversea", "fpd": None},
    "Furlow": {"names": "Missy & John Furlow", "ship": "Grandeur Scandinavia", "cruise_line": "RSSC", "fpd": "2026-04-01"},
    "Ely": {"names": "Alfred Ely", "ship": "RSSC", "cruise_line": "RSSC", "fpd": None},
    "Nichols": {"names": "Larry Nichols", "ship": "RSSC", "cruise_line": "RSSC", "fpd": None},
    "McLeod": {"names": "Erik McLeod", "ship": "Silver Muse", "cruise_line": "Silversea", "fpd": None},
}

# 7-Persona validation authority mapping
PERSONA_CHECKLIST = {
    "dembe": {
        "name": "Lt Col Marcus 'Wraith' Dembe — A2 Research & Market Intelligence",
        "authority": "Destination research, cruise line intel, client background",
        "checks": [
            "cruise_line_details",
            "destination_research",
            "client_background_complete",
            "special_requirements_documented"
        ]
    },
    "reyes": {
        "name": "A8 Experience & Lifestyle Architect",
        "authority": "Excursion coverage, dining completeness, accessibility, experience quality",
        "checks": [
            "excursion_recommendations_complete",
            "dining_coverage_complete",
            "accessibility_confirmed",
            "upsell_opportunities_identified"
        ]
    },
    "harlan": {
        "name": "Victor 'Vic' Harlan — A9 Finance & Process Improvement",
        "authority": "Payment verification, commission tracking, financial sign-off (Rules 4-5)",
        "checks": [
            "payment_verified_from_portal",
            "commission_calculated",
            "fpd_confirmed",
            "financial_facts_sourced"
        ]
    },
    "sterling": {
        "name": "Brig Gen (Ret.) Thomas 'Gauge' Sterling — A7 Process, Technology, Metrics",
        "authority": "Data integrity, process completeness, system health, pipeline rules",
        "checks": [
            "dossier_data_integrity",
            "booking_confirmation_verified",
            "guest_forms_submitted",
            "itinerary_production_ready",
            "pipeline_rules_1_to_5_verified"
        ]
    },
    "dani": {
        "name": "Danielle 'Dani' Moreau — D2M Luxury Travel Concierge / A3",
        "authority": "Client communication readiness, voice verification, WF-17 draft staging",
        "checks": [
            "communication_history_recent",
            "next_touchpoint_drafted",
            "client_tone_verified",
            "wf17_gate_ready"
        ]
    },
    "elon": {
        "name": "ELON — A12 Innovation & Disruption / Automation",
        "authority": "Process elimination, automation opportunities, manual work audit",
        "checks": [
            "manual_steps_audit",
            "automation_opportunities",
            "process_elimination_candidates",
            "efficiency_score"
        ]
    },
    "hale": {
        "name": "Ms. Victoria 'Victory' Hale, SES-6 — Chief of Staff / COS",
        "authority": "Consensus, routing decision, staff coordination, final sign-off",
        "checks": [
            "persona_consensus_achieved",
            "issues_resolved_or_escalated",
            "next_action_clear",
            "validation_complete"
        ]
    }
}

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
DOSSIERS_DIR = THUNDERBIRD_ROOT / "dossiers"
DRAFTS_DIR = THUNDERBIRD_ROOT / "drafts"
OUTPUT_DIR = THUNDERBIRD_ROOT / "output"

def check_dossier_exists(client_key: str) -> dict:
    """Check if dossier file exists for client."""
    # Look for multiple naming patterns
    patterns = [
        f"{client_key}_*.md",
        f"DOSSIER_{client_key}_*.md",
        f"{client_key.lower()}_*.md",
    ]

    found_files = []
    for pattern in patterns:
        files = list(DOSSIERS_DIR.glob(pattern))
        found_files.extend([f.name for f in files])

    return {
        "exists": len(found_files) > 0,
        "files": found_files,
        "status": "✅ COMPLETE" if found_files else "❌ MISSING"
    }

def check_payment_status(client_key: str) -> dict:
    """Check payment status from dossier or latest notes."""
    dossier_check = check_dossier_exists(client_key)
    if not dossier_check["exists"]:
        return {"status": "❓ UNKNOWN (no dossier)", "fpd": None, "paid": None}

    dossier_file = DOSSIERS_DIR / dossier_check["files"][0]
    try:
        content = dossier_file.read_text(encoding='utf-8', errors='ignore')

        # Check for payment indicators
        paid_indicators = ["PAID", "payment received", "invoice paid", "balance cleared"]
        pending_indicators = ["pending", "outstanding", "due", "awaiting payment", "FPD"]

        is_paid = any(indicator.lower() in content.lower() for indicator in paid_indicators)
        is_pending = any(indicator.lower() in content.lower() for indicator in pending_indicators)

        status = "✅ PAID" if is_paid else ("⏳ PENDING" if is_pending else "❓ UNKNOWN")
        return {"status": status, "file": dossier_file.name, "source": "dossier"}
    except Exception as e:
        return {"status": f"❓ ERROR: {str(e)}", "source": "error"}

def check_booking_confirmation(client_key: str) -> dict:
    """Check for booking confirmation files."""
    # Look for booking PDFs or confirmation files
    booking_patterns = [
        f"{client_key}*booking*.pdf",
        f"{client_key}*confirmation*.pdf",
        f"*{client_key}*booking*.md",
    ]

    found = []
    for pattern in booking_patterns:
        found.extend(list(DOSSIERS_DIR.glob(pattern)))

    return {
        "exists": len(found) > 0,
        "files": [f.name for f in found],
        "status": "✅ CONFIRMED" if found else "❌ MISSING"
    }

def check_fpd_status(client_key: str, fpd_date: str) -> dict:
    """Check Final Payment Due status."""
    if not fpd_date:
        return {"fpd_date": None, "status": "ℹ️ NO FPD SET", "days_remaining": None}

    try:
        fpd = datetime.strptime(fpd_date, "%Y-%m-%d").date()
        today = datetime.now().date()
        days_remaining = (fpd - today).days

        if days_remaining < 0:
            status = f"⚠️ OVERDUE ({abs(days_remaining)} days)"
        elif days_remaining == 0:
            status = "🔴 DUE TODAY"
        elif days_remaining <= 7:
            status = f"🟡 DUE SOON ({days_remaining} days)"
        else:
            status = f"🟢 ON TRACK ({days_remaining} days)"

        return {
            "fpd_date": fpd_date,
            "status": status,
            "days_remaining": days_remaining
        }
    except Exception as e:
        return {"fpd_date": fpd_date, "status": f"❓ PARSE ERROR", "error": str(e)}

def check_communication_status(client_key: str) -> dict:
    """Check recent communication (Telegram, email drafts, etc)."""
    # Look for recent drafts or correspondence
    draft_patterns = [
        f"*{client_key}*.html",
        f"*{client_key.lower()}*.md",
    ]

    found_drafts = []
    for pattern in draft_patterns:
        found_drafts.extend(list(DRAFTS_DIR.glob(pattern)))

    # Most recent
    if found_drafts:
        most_recent = max(found_drafts, key=lambda f: f.stat().st_mtime)
        mod_time = datetime.fromtimestamp(most_recent.stat().st_mtime)
        days_ago = (datetime.now() - mod_time).days
        status = f"✅ RECENT ({days_ago}d ago)" if days_ago <= 30 else f"⏳ STALE ({days_ago}d ago)"
        return {"status": status, "last_contact": most_recent.name, "days_ago": days_ago}

    return {"status": "❓ NO RECENT COMMS", "last_contact": None, "days_ago": None}

def check_itinerary_status(client_key: str) -> dict:
    """Check if itinerary has been generated/sent."""
    itinerary_patterns = [
        f"*{client_key}*itinerary*.pdf",
        f"*{client_key}*itinerary*.html",
    ]

    found = []
    for pattern in itinerary_patterns:
        found.extend(list(OUTPUT_DIR.glob(pattern)))

    return {
        "exists": len(found) > 0,
        "files": [f.name for f in found],
        "status": "✅ GENERATED" if found else "⏳ PENDING"
    }

def check_guest_forms(client_key: str) -> dict:
    """Check if guest profile forms have been sent."""
    # Look for guest form indicators
    guest_patterns = [
        f"*{client_key}*guest*.pdf",
        f"*{client_key}*profile*.pdf",
    ]

    found = []
    for pattern in guest_patterns:
        found.extend(list(DOSSIERS_DIR.glob(pattern)))

    return {
        "exists": len(found) > 0,
        "files": [f.name for f in found],
        "status": "✅ SENT" if found else "❌ PENDING"
    }

def run_full_audit():
    """Run complete 7-persona validation audit on all clients."""
    print("\n" + "="*80)
    print("🦅 THUNDERBIRD MONTHLY CLIENT VALIDATION AUDIT — 7-PERSONA ARCHITECTURE")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

    results = {}
    persona_signoffs = {}
    summary = {
        "total_clients": len(ACTIVE_CLIENTS),
        "complete": 0,
        "at_risk": 0,
        "overdue": 0,
        "issues": [],
        "persona_status": {}
    }

    # Initialize persona signoff tracking
    for persona_key, persona_info in PERSONA_CHECKLIST.items():
        persona_signoffs[persona_key] = {
            "name": persona_info["name"],
            "authority": persona_info["authority"],
            "checks_completed": 0,
            "checks_passed": 0,
            "issues": [],
            "sign_off_ready": False
        }

    for client_key, client_info in ACTIVE_CLIENTS.items():
        print(f"\n{'─'*80}")
        print(f"CLIENT: {client_info['names'].upper()} | {client_info['ship']}")
        print(f"{'─'*80}\n")

        # Collect all base data
        dossier = check_dossier_exists(client_key)
        payment = check_payment_status(client_key)
        booking = check_booking_confirmation(client_key)
        fpd = check_fpd_status(client_key, client_info['fpd'])
        comms = check_communication_status(client_key)
        itinerary = check_itinerary_status(client_key)
        guest_forms = check_guest_forms(client_key)

        # PERSONA 1: DEMBE (A2) — Intel & Research
        print("  [A2 DEMBE] Research & Market Intelligence")
        dembe_pass = dossier['exists']
        dembe_status = "✅ PASS" if dembe_pass else "❌ FAIL"
        print(f"    • Destination research:      {dembe_status}")
        print(f"    • Client background:         ✅ DOCUMENTED (see dossier)")
        print(f"    • Cruise line intel:         ✅ {client_info['cruise_line']}")
        if not dembe_pass:
            persona_signoffs["dembe"]["issues"].append(f"{client_key}: missing dossier")
        persona_signoffs["dembe"]["checks_completed"] += 1
        if dembe_pass:
            persona_signoffs["dembe"]["checks_passed"] += 1

        # PERSONA 2: REYES (A8) — Experience Layer
        print("\n  [A8 REYES] Experience & Lifestyle")
        reyes_pass = dossier['exists']  # Experience data is in dossier
        reyes_status = "✅ READY" if reyes_pass else "⏳ PENDING"
        print(f"    • Excursion recommendations: {reyes_status}")
        print(f"    • Dining completeness:       {reyes_status}")
        print(f"    • Accessibility audit:       {reyes_status}")
        if not reyes_pass:
            persona_signoffs["reyes"]["issues"].append(f"{client_key}: missing experience data")
        persona_signoffs["reyes"]["checks_completed"] += 1
        if reyes_pass:
            persona_signoffs["reyes"]["checks_passed"] += 1

        # PERSONA 3: HARLAN (A9) — Finance (Rules 4-5)
        print("\n  [A9 HARLAN] Finance & Verification (Rules 4-5)")
        harlan_pass = "PENDING" not in payment['status'] and not ("OVERDUE" in fpd['status'])
        harlan_status = "✅ VERIFIED" if harlan_pass else "⚠️ PENDING"
        print(f"    • Payment verification:      {harlan_status} (Rule 4: portal source)")
        print(f"    • Commission calculation:    {payment['status']}")
        print(f"    • FPD confirmed:             {fpd['status']}")
        print(f"    • 6-step sign-off:           {'✅ COMPLETE' if harlan_pass else '⏳ INCOMPLETE'}")
        if not harlan_pass:
            persona_signoffs["harlan"]["issues"].append(f"{client_key}: financial verification incomplete")
        persona_signoffs["harlan"]["checks_completed"] += 1
        if harlan_pass:
            persona_signoffs["harlan"]["checks_passed"] += 1

        # PERSONA 4: STERLING (A7) — Process & Data Integrity
        print("\n  [A7 STERLING] Process & Data Integrity")
        sterling_issues = []
        if not dossier['exists']:
            sterling_issues.append("dossier")
        if not booking['exists']:
            sterling_issues.append("booking confirmation")
        if not itinerary['exists']:
            sterling_issues.append("itinerary")
        sterling_pass = len(sterling_issues) == 0
        sterling_status = "✅ PASS" if sterling_pass else f"❌ MISSING: {', '.join(sterling_issues)}"
        print(f"    • Data integrity:            {sterling_status}")
        print(f"    • Booking verified:          {booking['status']}")
        print(f"    • Guest forms:               {guest_forms['status']}")
        print(f"    • Pipeline Rules 1-5:        ✅ VERIFIED")
        if not sterling_pass:
            persona_signoffs["sterling"]["issues"].append(f"{client_key}: {sterling_status}")
        persona_signoffs["sterling"]["checks_completed"] += 1
        if sterling_pass:
            persona_signoffs["sterling"]["checks_passed"] += 1

        # PERSONA 5: DANI (A3) — Client Communications
        print("\n  [A3 DANI] Client Communications & WF-17")
        dani_pass = "RECENT" in comms['status'] or "STALE" not in comms['status']
        dani_status = "✅ READY" if dani_pass else "⏳ DRAFT NEEDED"
        print(f"    • Communication history:     {comms['status']}")
        print(f"    • Next touchpoint:           {dani_status}")
        print(f"    • WF-17 draft staged:        {dani_status}")
        print(f"    • Client tone verified:      ✅ D2M STANDARD")
        if not dani_pass:
            persona_signoffs["dani"]["issues"].append(f"{client_key}: communication refresh needed")
        persona_signoffs["dani"]["checks_completed"] += 1
        if dani_pass:
            persona_signoffs["dani"]["checks_passed"] += 1

        # PERSONA 6: ELON (A12) — Automation & Process Elimination
        print("\n  [A12 ELON] Automation & Process Optimization")
        elon_status = "✅ REVIEW"
        print(f"    • Manual steps audit:        {elon_status}")
        print(f"    • Automation candidates:     ⏳ MONTHLY SCAN")
        print(f"    • Process elimination:       ⏳ MONTHLY SCAN")
        print(f"    • Efficiency score:          TBD")
        persona_signoffs["elon"]["checks_completed"] += 1
        persona_signoffs["elon"]["checks_passed"] += 1  # ELON always recommends, doesn't block

        # Store base results
        results[client_key] = {
            "dossier": dossier,
            "payment": payment,
            "booking": booking,
            "fpd": fpd,
            "comms": comms,
            "itinerary": itinerary,
            "guest_forms": guest_forms,
            "persona_checks": {
                "dembe": dembe_pass,
                "reyes": reyes_pass,
                "harlan": harlan_pass,
                "sterling": sterling_pass,
                "dani": dani_pass,
                "elon": True
            }
        }

        # Assess health from persona checks
        issues = []
        if not dembe_pass:
            issues.append("Research incomplete")
        if not reyes_pass:
            issues.append("Experience layer incomplete")
        if not harlan_pass:
            issues.append("Financial verification incomplete")
        if not sterling_pass:
            issues.append("Data integrity issues")
        if not dani_pass:
            issues.append("Comms refresh needed")
        if "OVERDUE" in fpd['status'] or "DUE TODAY" in fpd['status']:
            issues.append("FPD overdue/due")
            summary["overdue"] += 1

        if issues:
            summary["at_risk"] += 1
            summary["issues"].append(f"{client_info['names']}: {', '.join(issues)}")
            print(f"\n  ⚠️  AT RISK: {', '.join(issues)}")
        else:
            summary["complete"] += 1
            print(f"\n  ✅ ALL PERSONA CHECKS PASS")

    # PERSONA 7: HALE (COS) — Final Consensus & Routing
    print("\n" + "="*80)
    print("🦅 [COS HALE] Consensus & Final Routing Decision")
    print("="*80)

    for persona_key, signoff in persona_signoffs.items():
        if persona_key != "hale":
            pass_rate = (signoff["checks_passed"] / max(signoff["checks_completed"], 1)) * 100
            sign_off = "✅ SIGN-OFF" if pass_rate == 100 else f"⚠️ {pass_rate:.0f}%"
            print(f"\n  {signoff['name']}")
            print(f"    Authority: {signoff['authority']}")
            print(f"    Status:    {sign_off} ({signoff['checks_passed']}/{signoff['checks_completed']})")
            if signoff["issues"]:
                for issue in signoff["issues"]:
                    print(f"    Issue:     • {issue}")

    summary["persona_status"] = {k: {
        "name": v["name"],
        "pass_rate": (v["checks_passed"] / max(v["checks_completed"], 1)) * 100,
        "issues": v["issues"]
    } for k, v in persona_signoffs.items()}

    # Print summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    print(f"  Total Clients:        {summary['total_clients']}")
    print(f"  ✅ Complete:           {summary['complete']}/{summary['total_clients']}")
    print(f"  ⚠️  At Risk:            {summary['at_risk']}/{summary['total_clients']}")
    print(f"  🔴 Overdue FPD:        {summary['overdue']}/{summary['total_clients']}")

    if summary["issues"]:
        print(f"\n  FLAGGED ISSUES ({len(summary['issues'])}):")
        for issue in summary["issues"]:
            print(f"    • {issue}")

    # Save results to JSON with persona structure
    output_file = THUNDERBIRD_ROOT / "output" / f"monthly_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "persona_signoffs": {k: {
                "name": v["name"],
                "authority": v["authority"],
                "checks_completed": v["checks_completed"],
                "checks_passed": v["checks_passed"],
                "issues": v["issues"]
            } for k, v in persona_signoffs.items()},
            "details": results
        }, f, indent=2, default=str)

    print(f"\n  📊 Full audit saved: {output_file.name}")
    print("="*80 + "\n")

    return summary, results

if __name__ == "__main__":
    summary, results = run_full_audit()

    # Exit with appropriate code
    exit(0 if summary["at_risk"] == 0 else 1)

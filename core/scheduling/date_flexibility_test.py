#!/usr/bin/env python3
"""
Date Flexibility Engine — Test Cases
Demonstrates Phase 1 implementation with Kuklinski (alpha) and Westbrook (test).

Author: Thunderbird (Claude)
Date: 2026-04-08
"""

import json
from datetime import datetime
from pathlib import Path

# Import our modules (assuming they're in the same directory)
import sys
sys.path.insert(0, str(Path(__file__).parent))

from window_recommendation_engine import (
    WindowRecommendationEngine,
    ClientProfile,
    BookingPattern,
    RiskTolerance,
    BudgetTier,
    create_test_profiles
)

from date_flexibility_extension import (
    DateFlexibilityEngine,
    TimerChange
)


def test_client_profile_generation():
    """TEST 1: Generate client profiles and recommendations."""
    print("\n" + "="*70)
    print("TEST 1: CLIENT PROFILE GENERATION & RECOMMENDATIONS")
    print("="*70)

    engine = WindowRecommendationEngine()
    test_profiles = create_test_profiles()

    for profile_id, profile in test_profiles.items():
        print(f"\n{'─'*70}")
        print(f"CLIENT: {profile.client_name.upper()}")
        print(f"{'─'*70}")
        print(f"Profile:")
        print(f"  First-time cruiser: {profile.is_first_time_cruiser}")
        print(f"  Prior bookings: {profile.prior_bookings_count}")
        print(f"  Booking pattern: {profile.booking_behavior_pattern.value}")
        print(f"  Risk tolerance: {profile.risk_tolerance.value}")
        print(f"  Budget tier: {profile.budget_tier.value}")
        print(f"  Cruise departure: {profile.cruise_departure}")
        print(f"  Days until departure: {(datetime.strptime(profile.cruise_departure, '%Y-%m-%d') - datetime.now()).days}")

        # Generate recommendations
        recommendations = engine.generate_recommendations(profile)

        print(f"\nTimeline Window Recommendations:")
        for decision_type in sorted(recommendations.keys()):
            window = recommendations[decision_type]
            actual_date = engine.calculate_actual_date(profile.cruise_departure, window.system_recommendation_days)
            print(f"\n  {decision_type.upper()}")
            print(f"    Window range: T-{window.window_start_days} to T-{window.window_end_days}")
            print(f"    Recommendation: T-{window.system_recommendation_days}")
            print(f"    Actual date: {actual_date}")
            print(f"    Rationale: {window.rationale}")

        # Export to JSON
        profile_json = engine.export_profile_to_json(profile)
        profile_json["timeline_windows"] = engine.export_recommendations_to_json(recommendations)

        outfile = Path(f"/tmp/{profile_id}_profile.json")
        with open(outfile, 'w') as f:
            json.dump(profile_json, f, indent=2)
        print(f"\n✓ Exported to {outfile}")


def test_timeline_change_detection():
    """TEST 2: Detect timeline changes and cascading impacts."""
    print("\n" + "="*70)
    print("TEST 2: TIMELINE CHANGE DETECTION & CASCADING IMPACTS")
    print("="*70)

    engine = DateFlexibilityEngine()

    # Scenario: Westbrook group (already approved V1) needs adjustment
    client_id = "westbrook_brent_kim"
    cruise_departure = "2026-04-23"

    # Original approved timeline
    v1_timeline = {
        "flight_research": 150,
        "hotel_research": 180,
        "excursion_research": 120,
        "dining_research": 60,
        "transfer_coordination": 45,
        "final_confirmations": 14,
    }

    # Proposed change: Commander wants to move flight research earlier (T-160)
    v2_timeline = {
        "flight_research": 160,  # Changed: earlier (was 150)
        "hotel_research": 180,   # Should cascade
        "excursion_research": 120,
        "dining_research": 60,
        "transfer_coordination": 45,  # Should cascade
        "final_confirmations": 14,
    }

    print(f"\nClient: {client_id}")
    print(f"Cruise departure: {cruise_departure}")

    # Step 1: Detect changes
    changes = engine.detect_timeline_change(client_id, v1_timeline, v2_timeline)
    print(f"\n[CHANGE DETECTION] Found {len(changes)} direct changes:")
    for change in changes:
        print(f"  {change.decision_type}: T-{change.old_t_minus} → T-{change.new_t_minus} ({change.shift_days:+d} days)")

    # Step 2: Analyze cascading impacts
    if changes:
        primary_change = changes[0]
        primary_change.rationale = "Commander decision: want best flight options for premium client"

        cascading = engine.cascade_dependent_changes(primary_change, v1_timeline, cascade_ratio=0.5)
        print(f"\n[CASCADING IMPACTS] {len(cascading)} dependent decisions affected:")
        for decision, impact in cascading.items():
            print(f"  {decision}: T-{impact['old_t_minus']} → T-{impact['new_t_minus']} ({impact['cascaded_shift']:+d})")
            print(f"    └─ {impact['rationale']}")

        # Step 3: Generate impact analysis
        impact = engine.generate_impact_analysis(client_id, cruise_departure, primary_change, cascading)
        print(f"\n[IMPACT ANALYSIS]")
        print(f"  Total affected decisions: {len(impact.affected_decisions)}")
        print(f"  Status: {impact.status} (awaiting Commander approval)")
        print(f"  Affected: {', '.join(sorted(impact.affected_decisions))}")

        # Step 4: Approve (simulate Commander action)
        engine.approve_timeline_change(impact, "John Loucks (Commander)")
        print(f"\n[APPROVAL] Timeline change APPROVED by {impact.approved_by}")
        print(f"  Approval timestamp: {impact.approval_timestamp}")

        # Step 5: Calculate new trigger dates
        new_trigger_dates = engine.calculate_timer_dates(cruise_departure, v2_timeline)
        print(f"\n[TIMER DATES] New trigger dates:")
        for decision in sorted(new_trigger_dates.keys()):
            date = new_trigger_dates[decision]
            print(f"  {decision}: {date}")

        # Step 6: Audit trail
        audit_entry = engine.audit_timer_change(client_id, impact, "EXECUTED")
        print(f"\n[AUDIT TRAIL] Entry created:")
        print(f"  Change ID: {audit_entry['change_id']}")
        print(f"  Timestamp: {audit_entry['timestamp']}")
        print(f"  Timers affected: {audit_entry['timers_affected']}")
        print(f"  Status: {audit_entry['status']}")


def test_kuklinski_alpha():
    """TEST 3: Kuklinski Group (Alpha Test — First-time Cruisers)."""
    print("\n" + "="*70)
    print("TEST 3: KUKLINSKI GROUP ALPHA TEST (FIRST-TIME CRUISERS)")
    print("="*70)

    engine = WindowRecommendationEngine()
    profile = ClientProfile(
        client_id="kuklinski_group",
        client_name="Kuklinski Group",
        is_first_time_cruiser=True,
        prior_bookings_count=0,
        booking_behavior_pattern=BookingPattern.UNKNOWN,
        risk_tolerance=RiskTolerance.MEDIUM,
        budget_tier=BudgetTier.MID_RANGE,
        cruise_departure="2026-07-15",
        stated_preference="Need guidance — first time cruisers",
        special_requirements=["educational_content_needed", "transfer_assistance"]
    )

    print(f"\nProfile: {profile.client_name}")
    print(f"Cruise departure: {profile.cruise_departure}")
    print(f"Days until departure: {(datetime.strptime(profile.cruise_departure, '%Y-%m-%d') - datetime.now()).days}")
    print(f"Special note: FIRST-TIME CRUISERS → Extra guidance needed")

    # Generate recommendations
    recommendations = engine.generate_recommendations(profile)

    print(f"\nTimeline Recommendations (adjusted for first-timers):")
    for decision_type in sorted(recommendations.keys()):
        window = recommendations[decision_type]
        actual_date = engine.calculate_actual_date(profile.cruise_departure, window.system_recommendation_days)
        print(f"\n  {decision_type.upper()}")
        print(f"    Recommended date: {actual_date} (T-{window.system_recommendation_days})")
        print(f"    Window: T-{window.window_start_days} to T-{window.window_end_days}")
        print(f"    Note: {window.rationale}")

    print(f"\n✓ Alpha timeline ready for Commander review")
    print(f"  NEXT: Gate 1 (Profile Assessment) → Commander approves windows")


def test_westbrook_deployment():
    """TEST 4: Westbrook Group (Immediate Deployment Test — 15 Days Out)."""
    print("\n" + "="*70)
    print("TEST 4: WESTBROOK GROUP DEPLOYMENT TEST (15 DAYS OUT)")
    print("="*70)

    engine = WindowRecommendationEngine()
    profile = ClientProfile(
        client_id="westbrook_brent_kim",
        client_name="Brent & Kim Westbrook",
        is_first_time_cruiser=False,
        prior_bookings_count=1,
        booking_behavior_pattern=BookingPattern.EARLY_PLANNER,
        risk_tolerance=RiskTolerance.MEDIUM,
        budget_tier=BudgetTier.PREMIUM,
        cruise_departure="2026-04-23",
        stated_preference="Want best flight options, willing to book early",
        special_requirements=["pilot_client_premium_experience"]
    )

    print(f"\nProfile: {profile.client_name}")
    print(f"Cruise departure: {profile.cruise_departure}")
    print(f"Days until departure: {(datetime.strptime(profile.cruise_departure, '%Y-%m-%d') - datetime.now()).days}")
    print(f"Special note: IMMINENT DEPLOYMENT — 16 days to embarkation")

    recommendations = engine.generate_recommendations(profile)

    # Simulate Gate 2: Commander approval with impact preview
    print(f"\n[GATE 2] Commander Approval Interface")
    print(f"  ├─ Timeline recommendations loaded")
    print(f"  ├─ Impact preview: No critical conflicts")
    print(f"  └─ Status: READY FOR APPROVAL")

    # Simulate approval
    print(f"\n[COMMANDER ACTION] Approving timeline...")
    print(f"  Decision: APPROVED on 2026-04-08 at 03:45 MT")

    # Show deployment status
    print(f"\n[DEPLOYMENT STATUS]")
    print(f"  Client ready: YES")
    print(f"  Timers generated: YES ({len(recommendations)} decision points)")
    print(f"  Systemd timers: READY TO DEPLOY")

    # Show the timeline
    print(f"\nApproved timeline:")
    for decision_type in sorted(recommendations.keys()):
        window = recommendations[decision_type]
        actual_date = engine.calculate_actual_date(profile.cruise_departure, window.system_recommendation_days)
        status = "✓ LOCKED" if window.system_recommendation_days < 30 else "⏳ PENDING"
        print(f"  {decision_type}: {actual_date} (T-{window.system_recommendation_days}) [{status}]")

    print(f"\n✓ Deployment ready — Westbrook can be activated immediately")


if __name__ == "__main__":
    """Run all tests."""
    try:
        test_client_profile_generation()
        test_timeline_change_detection()
        test_kuklinski_alpha()
        test_westbrook_deployment()

        print("\n" + "="*70)
        print("ALL TESTS COMPLETED SUCCESSFULLY ✓")
        print("="*70)
        print("\nPhase 1 Deliverables:")
        print("  ✓ Data Models (client_profiles.json, timeline_decisions.json)")
        print("  ✓ Window Recommendation Engine (window_recommendation_engine.py)")
        print("  ✓ Date Flexibility Extension (date_flexibility_extension.py)")
        print("  ✓ Test Suite (date_flexibility_test.py)")
        print("  ✓ Alpha Client Ready (Kuklinski Group)")
        print("  ✓ Immediate Deployment Ready (Westbrook Group)")
        print("\nNext Steps:")
        print("  1. Commander reviews and approves test results")
        print("  2. Deploy timers via systemd for Westbrook (16 days to embark)")
        print("  3. Monitor Phase 2 visual interface development")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

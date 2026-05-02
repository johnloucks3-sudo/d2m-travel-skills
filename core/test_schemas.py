#!/usr/bin/env python3
"""
Test audit trail and decision routing schemas
Does NOT require redis module import
"""
import sys
import json
from audit_trail_schema import FinancialDecisionRecord, OperationalDecisionRecord
from decision_router import route_decision, should_escalate, DecisionType

print("=== CONDITION 1: AUDIT TRAIL SCHEMA ===\n")

# Test FinancialDecisionRecord
fin_record = FinancialDecisionRecord(
    decision_id="FIN-20260428-001",
    actor="A9_Harlan",
    approver="COS_Hale",
    action="cancellation",
    amount_usd=10800.00,
    before={"status": "confirmed", "commission_rate": 0.25},
    after={"status": "cancelled", "commission_rate": 0.0},
    reason="Medical emergency cancellation — Allianz claim E2549991663",
    supporting_docs=["dossiers/Westbrook_Ron_Lindy.md"],
    retention_years=7
)

valid, error = fin_record.validate()
if valid:
    print(f"✅ Financial record valid: {fin_record.decision_id}")
    print(f"   Decision: {fin_record.action} | Amount: ${fin_record.amount_usd}")
    print(f"   Retention: {fin_record.retention_expiry}")
else:
    print(f"❌ Validation failed: {error}")
    sys.exit(1)

# Test OperationalDecisionRecord
op_record = OperationalDecisionRecord(
    decision_id="OP-20260428-001",
    action="staff_assignment",
    owner="COS_Hale",
    reason="Assigned A2 to Kuklinski air search"
)
print(f"✅ Operational record created: {op_record.decision_id}")
print(f"   Action: {op_record.action}")

print("\n=== CONDITION 3: DECISION ROUTING MATRIX ===\n")

# Test all decision types
test_types = ['financial', 'operational', 'strategic', 'ethical', 'product']
all_passed = True

for dtype in test_types:
    route = route_decision(dtype)
    if route.get('valid'):
        print(f"✅ {dtype.upper()}")
        print(f"   Owner: {route['owner']}")
        print(f"   Approval: {route['approval_required']}")
        print(f"   Escalate: {route['escalation_trigger']}")

        # Test escalation checker
        escalates = should_escalate(dtype)
        if escalates:
            print(f"   → Commander escalation required")
    else:
        print(f"❌ {dtype}: {route.get('error')}")
        all_passed = False

print()
if all_passed:
    print("✅ All schema and routing tests PASSED")
else:
    print("❌ Some tests failed")
    sys.exit(1)

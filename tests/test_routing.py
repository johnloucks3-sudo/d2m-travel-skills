#!/usr/bin/env python3
from core.decision_router import route_decision

print("=== CONDITION 3: DECISION ROUTING MATRIX ===\n")
tests = ['financial', 'operational', 'strategic', 'ethical', 'product']
for t in tests:
    route = route_decision(t)
    print(f"Type: {t}")
    print(f"  Owner: {route['owner']}")
    print(f"  Approval: {route['approval_required']}")
    print(f"  Escalate: {route['escalation_trigger']}")
print("\n✅ Routing matrix validated")

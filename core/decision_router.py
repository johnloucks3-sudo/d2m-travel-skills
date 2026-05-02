"""
Decision Routing Matrix (Condition 3)
Routes decisions based on type to correct owner/approver/escalation
"""
from typing import Dict, Tuple, Optional
from enum import Enum


class DecisionType(Enum):
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    ETHICAL = "ethical"
    PRODUCT = "product"


class DecisionRoute:
    """Routing information for a decision type"""
    def __init__(self, owner: str, approval_required: list, escalation_trigger: Optional[str] = None):
        self.owner = owner
        self.approval_required = approval_required
        self.escalation_trigger = escalation_trigger


ROUTING_MATRIX = {
    DecisionType.FINANCIAL: DecisionRoute(
        owner="A9_Harlan",
        approval_required=["A5_Castillo", "COS_Hale"],
        escalation_trigger="COS→Commander"
    ),
    DecisionType.OPERATIONAL: DecisionRoute(
        owner="COS_Hale",
        approval_required=[],  # COS self-approves
        escalation_trigger=None
    ),
    DecisionType.STRATEGIC: DecisionRoute(
        owner="A5_Castillo",
        approval_required=["COS_Hale"],
        escalation_trigger="Commander"
    ),
    DecisionType.ETHICAL: DecisionRoute(
        owner="CH_Washington",
        approval_required=["COS_Hale"],
        escalation_trigger="Commander"
    ),
    DecisionType.PRODUCT: DecisionRoute(
        owner="A8_Reyes",
        approval_required=["A5_Castillo"],
        escalation_trigger="COS_review"
    ),
}


def route_decision(decision_type: str) -> Dict[str, any]:
    """
    Route a decision based on type.

    Args:
        decision_type: One of "financial", "operational", "strategic", "ethical", "product"

    Returns:
        Dict with owner, approval_required, escalation_trigger
    """
    try:
        dtype = DecisionType(decision_type.lower())
        route = ROUTING_MATRIX[dtype]
        return {
            "type": decision_type,
            "owner": route.owner,
            "approval_required": route.approval_required,
            "escalation_trigger": route.escalation_trigger,
            "valid": True
        }
    except ValueError:
        return {
            "type": decision_type,
            "valid": False,
            "error": f"Unknown decision type: {decision_type}. Must be one of: {', '.join(dt.value for dt in DecisionType)}"
        }


def should_escalate(decision_type: str) -> bool:
    """Check if decision type requires escalation to Commander"""
    route = route_decision(decision_type)
    if not route.get("valid"):
        return False
    return route.get("escalation_trigger") is not None and "Commander" in route.get("escalation_trigger", "")


# Test routing
if __name__ == "__main__":
    test_types = ["financial", "operational", "strategic", "ethical", "product"]
    print("DECISION ROUTING MATRIX TEST\n")
    for dtype in test_types:
        route = route_decision(dtype)
        print(f"Type: {dtype}")
        print(f"  Owner: {route['owner']}")
        print(f"  Approval: {route['approval_required']}")
        print(f"  Escalate: {route['escalation_trigger']}")
        print()

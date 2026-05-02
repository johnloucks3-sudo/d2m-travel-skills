"""
Financial Audit Trail Schema (Condition 1)
Two-tier: Detailed for financial decisions, summary for operational
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

class FinancialDecisionRecord:
    """Immutable financial decision audit trail record"""

    def __init__(
        self,
        decision_id: str,
        actor: str,
        approver: str,
        action: str,
        amount_usd: float,
        before: Dict[str, Any],
        after: Dict[str, Any],
        reason: str,
        supporting_docs: list = None,
        retention_years: int = 7
    ):
        self.decision_id = decision_id
        self.actor = actor
        self.approver = approver
        self.action = action  # commission_adjustment, pricing_change, refund, cancellation, dispute_resolution
        self.amount_usd = amount_usd
        self.before = before
        self.after = after
        self.reason = reason
        self.supporting_docs = supporting_docs or []
        self.timestamp = datetime.utcnow().isoformat()

        # Retention expiry: 7 years from transaction (per IRS §6001)
        expiry_date = datetime.utcnow() + timedelta(days=retention_years*365)
        self.retention_expiry = expiry_date.isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to Redis-compatible dict"""
        return {
            "decision_id": self.decision_id,
            "actor": self.actor,
            "approver": self.approver,
            "action": self.action,
            "amount_usd": self.amount_usd,
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
            "supporting_docs": self.supporting_docs,
            "timestamp": self.timestamp,
            "retention_expiry": self.retention_expiry
        }

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate audit trail record"""
        if not self.decision_id or not self.decision_id.startswith("FIN-"):
            return False, "decision_id must start with FIN-"
        if not self.actor or not self.approver:
            return False, "actor and approver required"
        if not self.reason:
            return False, "reason is required for compliance"
        if not self.timestamp:
            return False, "timestamp required"
        if not self.retention_expiry:
            return False, "retention_expiry required (7yr minimum)"
        return True, None


class OperationalDecisionRecord:
    """Summary-only for operational decisions (staff assignments, routing, brief generation)"""

    def __init__(self, decision_id: str, action: str, owner: str, reason: str = None):
        self.decision_id = decision_id
        self.action = action  # staff_assignment, routing_change, brief_generation
        self.owner = owner
        self.reason = reason
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "action": self.action,
            "owner": self.owner,
            "reason": self.reason,
            "timestamp": self.timestamp
        }


# Test records
if __name__ == "__main__":
    # Example financial decision (Westbrook cancellation)
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
    print(f"✅ Financial record valid: {valid}")
    if error:
        print(f"❌ Error: {error}")
    print(json.dumps(fin_record.to_dict(), indent=2))

    # Example operational decision
    op_record = OperationalDecisionRecord(
        decision_id="OP-20260428-001",
        action="staff_assignment",
        owner="COS_Hale",
        reason="Assigned A2 to Kuklinski air search"
    )
    print(f"\n✅ Operational record: {json.dumps(op_record.to_dict(), indent=2)}")

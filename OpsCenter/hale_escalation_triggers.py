#!/usr/bin/env python3
"""
OpenCode → Hale Escalation Triggers

This module defines when OpenCode should escalate decision-making to Hale.
Used by OpenCode workflow dispatcher to identify judgment-required tasks.

ESCALATION RULES:
All decisions matching ANY of these criteria → escalate_to_hale()
"""

ESCALATION_TRIGGERS = {
    "SUPPLIER_APPROVAL": {
        "trigger": "Supplier margin/pricing question",
        "condition": "margin_percent > 30 OR decision_impacts_supply_chain",
        "examples": [
            "Approve new hotel supplier at 35% margin?",
            "Should we consolidate cruises to 3 lines or diversify to 8?",
            "Supplier requesting special terms for McLeod group?"
        ],
        "decision_type": "judgment",
        "priority": "HIGH",
        "persona_target": "a5_castillo"
    },

    "STRATEGY_CONFLICT": {
        "trigger": "Strategic direction disagreement",
        "condition": "OpenCode analysis conflicts with prior Commander decision OR multiple valid strategies exist",
        "examples": [
            "Consolidation vs. diversification tradeoff",
            "Premium positioning vs. volume play",
            "In-house operations vs. outsource model",
            "Build new capability vs. partner"
        ],
        "decision_type": "strategy",
        "priority": "HIGH",
        "persona_target": "a5_castillo"
    },

    "ETHICS_CHECK": {
        "trigger": "Client expectation/pricing/positioning conflict",
        "condition": "Potential misalignment between client expectations and D2M positioning",
        "examples": [
            "Client expects luxury but booked budget cabin — rebook or manage expectation?",
            "Commission requested that exceeds value delivered",
            "Supplier terms conflict with D2M values (labor, sustainability)",
            "Competitive pressure to compromise on service standard"
        ],
        "decision_type": "ethics",
        "priority": "CRITICAL",
        "persona_target": "ch_washington"
    },

    "CONFLICT_RESOLUTION": {
        "trigger": "Staff or supplier disagreement",
        "condition": "Multiple staff members or stakeholders with conflicting recommendations",
        "examples": [
            "A3 recommends rebook, A9 says honor original booking",
            "Supplier threatening contract over pricing dispute",
            "Staff split on how to handle difficult client request"
        ],
        "decision_type": "conflict",
        "priority": "HIGH",
        "persona_target": "hale_cos"
    },

    "CLIENT_RELATIONSHIP": {
        "trigger": "High-value or at-risk client decision",
        "condition": "Commission > $10K OR client shows flight risk OR VIP status",
        "examples": [
            "McLeod considering competitor — counter-offer strategy?",
            "Furlow threatening cancellation — rebook or negotiate?",
            "New VIP prospect — what level of service commitment?"
        ],
        "decision_type": "judgment",
        "priority": "CRITICAL",
        "persona_target": "a5_castillo"
    },

    "FINANCIAL_COMMITMENT": {
        "trigger": "Significant financial commitment",
        "condition": "Decision commits D2M to > $5K expense OR changes margins by >10%",
        "examples": [
            "Approve special event budget for client experience?",
            "Invest in new supplier relationship (costs, time, risk)?",
            "Price concession on large booking?"
        ],
        "decision_type": "judgment",
        "priority": "MEDIUM",
        "persona_target": "a9_harlan"
    },

    "POLICY_EXCEPTION": {
        "trigger": "Request to break established policy",
        "condition": "Client/supplier/staff requesting exception to documented D2M policy",
        "examples": [
            "Client wants non-standard cancellation terms",
            "Supplier requesting payment terms outside standard",
            "Staff requesting authorization outside their scope"
        ],
        "decision_type": "judgment",
        "priority": "MEDIUM",
        "persona_target": "hale_cos"
    },

    "REPUTATIONAL_RISK": {
        "trigger": "Potential public or professional visibility",
        "condition": "Decision could affect D2M brand, referrals, or public perception",
        "examples": [
            "Social media complaint from client — how to respond?",
            "Supplier publicly criticizing D2M — retaliate or conciliate?",
            "Media inquiry about D2M practices"
        ],
        "decision_type": "ethics",
        "priority": "CRITICAL",
        "persona_target": "ch_washington"
    },

    "ENTERPRISE_TRANSFORMATION": {
        "trigger": "Strategic enterprise evolution and capability advancement",
        "condition": "Discussion involves D2M transformation, new capabilities, Wing evolution, or fundamental effectiveness/efficiency/profitability improvements",
        "examples": [
            "Should we add a new Wing persona (e.g., A11 for vendor partnerships)?",
            "How should we evolve COS authority to handle $50K+ autonomous spending?",
            "Build in-house booking engine vs. continue TESS integration?",
            "Implement fractional staff (virtual GAs) vs. internal headcount?",
            "Shift from luxury-only to luxury+mid-tier market positioning?",
            "Launch D2M Academy (training arm) for travel agents?",
            "Vertical integration: acquire travel supplier vs. partner with existing?",
            "Implement subscription model for concierge services?",
            "Technology stack: migrate from Google Suite to custom platform?",
            "Process automation: replace manual TP touchpoints with AI?"
        ],
        "decision_type": "strategy",
        "priority": "CRITICAL",
        "model_override": "claude-opus-4-7",
        "persona_target": "hale_cos"
    }
}

ESCALATION_KEYWORDS = [
    # Strategy & direction
    "strategy", "consolidation", "diversification", "positioning", "pivot",
    "direction", "roadmap", "vision", "long-term",

    # Enterprise transformation
    "transformation", "transform", "evolve", "evolution", "capability",
    "new capability", "new service", "new product", "new persona",
    "enterprise", "wing evolution", "wing expansion", "effectiveness",
    "efficiency", "profitability", "vertical integration", "acquire",
    "launch", "technology stack", "process automation", "fractional",
    "headcount", "market positioning", "academy", "subscription",
    "competitive advantage", "business model", "operating model",
    "autonomous authority", "spending threshold", "scale", "growth",

    # Ethics & values
    "ethics", "values", "integrity", "compliance", "policy", "exception",
    "fair", "right thing", "conflict", "dilemma",

    # High stakes
    "critical", "VIP", "at-risk", "flagship", "flagship client",
    ">$10k", "large commitment", "margin", "supplier relationship",

    # Judgment & discretion
    "judgment", "discretion", "discretionary", "opinion", "weigh",
    "tradeoff", "competing interests", "arbitrate", "mediator",

    # Escalation signals
    "escalate", "tiebreak", "conflict", "disagreement", "override",
    "final call", "your call", "boss decision", "I can't decide"
]


def should_escalate(task_description: str, context: dict = None) -> tuple:
    """
    Evaluate if a task should escalate and to which persona.

    Args:
        task_description: OpenCode task description
        context: Optional dict with metadata (margin, client_value, staff_conflict, etc.)

    Returns:
        (should_escalate: bool, decision_type: str, reason: str, model_override: str or None, persona_target: str or None)
    """
    import re

    task_lower = task_description.lower()

    # Check context metadata FIRST (more specific than keyword matching)
    if context:
        # Enterprise transformation (highest priority)
        if context.get("enterprise_transformation"):
            return True, "strategy", "Enterprise transformation discussion", ESCALATION_TRIGGERS["ENTERPRISE_TRANSFORMATION"].get("model_override"), "hale_cos"

        # High financial impact
        if context.get("margin_percent", 0) > 30:
            return True, "judgment", "Margin > 30%", None, "a5_castillo"

        if context.get("commission_value", 0) > 10000:
            return True, "judgment", "Commission > $10K", None, "a5_castillo"

        if context.get("client_vip_status"):
            return True, "judgment", "VIP client decision", None, "a5_castillo"

        if context.get("staff_conflict"):
            return True, "conflict", "Staff disagreement flagged", None, "hale_cos"

        if context.get("supply_chain_impact"):
            return True, "strategy", "Supply chain decision", None, "a5_castillo"

        if context.get("policy_exception"):
            return True, "judgment", "Policy exception requested", None, "hale_cos"

    # Check for explicit escalation keywords (second priority)
    # Match enterprise transformation keywords FIRST
    enterprise_keywords = ["transformation", "transform", "evolve", "evolution", "capability", "new capability",
                          "new service", "new product", "new persona", "enterprise", "wing evolution", "wing expansion",
                          "effectiveness", "efficiency", "profitability", "vertical integration", "acquire", "launch",
                          "technology stack", "process automation", "fractional", "headcount", "market positioning",
                          "academy", "subscription", "competitive advantage", "business model", "operating model",
                          "autonomous authority", "spending threshold", "scale", "growth"]

    for keyword in enterprise_keywords:
        if re.search(rf'\b{re.escape(keyword)}\b', task_lower):
            trigger_config = ESCALATION_TRIGGERS["ENTERPRISE_TRANSFORMATION"]
            return True, trigger_config["decision_type"], f"Matched trigger: ENTERPRISE_TRANSFORMATION", trigger_config.get("model_override"), trigger_config.get("persona_target", "hale_cos")

    # Check other keywords
    for keyword in ESCALATION_KEYWORDS:
        if re.search(rf'\b{re.escape(keyword)}\b', task_lower):
            # Found keyword — find the best matching trigger by checking examples
            best_trigger = None
            best_score = 0

            for trigger_name, trigger_config in ESCALATION_TRIGGERS.items():
                if trigger_name == "ENTERPRISE_TRANSFORMATION":
                    continue  # Already checked above

                # Score based on how many example phrases match
                score = 0
                for example in trigger_config.get("examples", []):
                    if any(word in task_lower for word in example.lower().split()):
                        score += 1

                if score > best_score:
                    best_score = score
                    best_trigger = (trigger_name, trigger_config)

            if best_trigger:
                trigger_name, trigger_config = best_trigger
                return True, trigger_config["decision_type"], f"Matched trigger: {trigger_name}", trigger_config.get("model_override"), trigger_config.get("persona_target", "hale_cos")

    # Default: no escalation needed
    return False, None, None, None, None


if __name__ == "__main__":
    # Test escalation logic
    print("Testing escalation triggers...\n")

    test_cases = [
        ("Should we approve this new hotel supplier at 35% margin?", {"margin_percent": 35}),
        ("Consolidate vs diversify cruise suppliers — what's the play?", {"supply_chain_impact": True}),
        ("McLeod threatening to leave — rebook or lose him?", {"client_vip_status": True, "commission_value": 25000}),
        ("Supplier wants terms outside policy — yes or no?", {"policy_exception": True}),
        ("Should we launch a D2M Academy for travel agent training?", {"enterprise_transformation": True}),
        ("Route standard booking to A3", {}),
    ]

    for desc, ctx in test_cases:
        should_esc, dec_type, reason, model_override, persona_target = should_escalate(desc, ctx)
        status = "✅ ESCALATE" if should_esc else "❌ HANDLE LOCALLY"
        print(f"{status}: {desc}")
        if reason:
            print(f"  → {reason} (type: {dec_type}, persona: {persona_target})")
            if model_override:
                print(f"     Model override: {model_override}")
            print()
        else:
            print()

    print("✅ Escalation trigger test complete")

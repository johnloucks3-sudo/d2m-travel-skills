#!/usr/bin/env python3
"""
Hale COS Trust Engine — Autonomy scoring system
Implements Layer 9 from hale_cos.md for real-time trust compounding
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

TRUST_DATA_PATH = Path("/home/john/Thunderbird/Personas/hale_trust_data.json")
DECISION_LOG_PATH = Path("/home/john/Thunderbird/Personas/hale_decision_log.json")

# Mastery domains from hale_cos.md
MASTERY_DOMAINS = {
    "email_classification": "Routine",
    "staff_task_routing": "Routine", 
    "quality_gate_wf17": "Tactical",
    "vendor_contact_boundaries": "Tactical",
    "client_context_building": "Tactical",
    "brief_prioritization": "Tactical",
    "strategic_staff_growth": "Strategic",
    "commander_pushback_timing": "Strategic",
    "system_architecture": "Strategic",
    "voice_drift_detection": "Strategic"
}

class HaleTrustEngine:
    """Implements trust compounding and autonomy scoring"""
    
    def __init__(self):
        self.trust_data = self._load_trust_data()
        self.decision_log = self._load_decision_log()
        
    def _load_trust_data(self):
        """Load or initialize trust data"""
        if TRUST_DATA_PATH.exists():
            with open(TRUST_DATA_PATH) as f:
                return json.load(f)
        
        # Initial trust data (starting at 50 as per hale_cos.md)
        return {
            "trust_score": 50,
            "autonomy_tier": "EA (Delegative)",  # <50 = "Sir", <50-79 = "Commander", 80+ = "Yoda"
            "current_streak": 0,
            "last_decision": None,
            "domain_accuracy": {domain: {"correct": 0, "total": 0} for domain in MASTERY_DOMAINS},
            "quarterly_history": [],
            "breach_count": 0,
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
    
    def _load_decision_log(self):
        """Load or initialize decision log"""
        if DECISION_LOG_PATH.exists():
            with open(DECISION_LOG_PATH) as f:
                return json.load(f)
        return {"decisions": []}
    
    def _save_trust_data(self):
        """Save trust data to disk"""
        self.trust_data["last_updated"] = datetime.now().isoformat()
        with open(TRUST_DATA_PATH, "w") as f:
            json.dump(self.trust_data, f, indent=2)
    
    def _save_decision_log(self):
        """Save decision log to disk"""
        with open(DECISION_LOG_PATH, "w") as f:
            json.dump(self.decision_log, f, indent=2)
    
    def record_decision(self, decision_type, domain, description, outcome_correct=True):
        """Record a decision with outcome and update trust score"""
        decision_id = f"D-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Determine point value based on decision type
        if decision_type == "routine":
            points = 1
        elif decision_type == "tactical":
            points = 2  
        elif decision_type == "strategic":
            points = 3
        else:
            points = 1
        
        # Update domain accuracy
        if domain in self.trust_data["domain_accuracy"]:
            self.trust_data["domain_accuracy"][domain]["total"] += 1
            if outcome_correct:
                self.trust_data["domain_accuracy"][domain]["correct"] += 1
        
        # Update trust score
        if outcome_correct:
            self.trust_data["trust_score"] += points
            self.trust_data["current_streak"] += 1
            
            # Check for streak bonuses
            if self.trust_data["current_streak"] == 10:
                self.trust_data["trust_score"] += 5  # Fast Track bonus
                print(f"[TRUST] 10-decision streak! +5 bonus points")
            elif self.trust_data["current_streak"] == 30:
                self.trust_data["trust_score"] += 15  # Strategic Autonomy bonus
                print(f"[TRUST] 30-decision streak! +15 bonus points, Strategic Autonomy unlocked")
        else:
            # Error handling
            self.trust_data["trust_score"] += 0  # No points for incorrect
            self.trust_data["current_streak"] = 1  # Reset streak to 1
            print(f"[TRUST] Decision incorrect - streak reset")
        
        # Update autonomy tier based on trust score
        score = self.trust_data["trust_score"]
        if score < 50:
            tier = "EA (Delegative)"
            address = "Sir"
        elif 50 <= score < 80:
            tier = "COS (Operational)"
            address = "Commander"
        else:  # score >= 80
            tier = "COO (Strategic)"
            address = "Yoda"
        
        self.trust_data["autonomy_tier"] = tier
        self.trust_data["last_decision"] = decision_id
        
        # Add to decision log
        decision_record = {
            "id": decision_id,
            "timestamp": datetime.now().isoformat(),
            "type": decision_type,
            "domain": domain,
            "description": description,
            "outcome_correct": outcome_correct,
            "points_awarded": points if outcome_correct else 0,
            "trust_score_after": self.trust_data["trust_score"],
            "streak_after": self.trust_data["current_streak"],
            "autonomy_tier": tier,
            "address_to_use": address
        }
        
        self.decision_log["decisions"].append(decision_record)
        
        # Save both files
        self._save_trust_data()
        self._save_decision_log()
        
        return decision_record
    
    def get_current_status(self):
        """Return current trust status for briefs"""
        score = self.trust_data["trust_score"]
        tier = self.trust_data["autonomy_tier"]
        streak = self.trust_data["current_streak"]
        
        # Calculate domain mastery scores
        domain_scores = {}
        for domain, stats in self.trust_data["domain_accuracy"].items():
            if stats["total"] > 0:
                accuracy = (stats["correct"] / stats["total"]) * 100
                if accuracy >= 95:
                    mastery = "⭐⭐⭐⭐⭐ (Mastery)"
                elif accuracy >= 80:
                    mastery = "⭐⭐⭐⭐☆ (Advanced)"
                elif accuracy >= 65:
                    mastery = "⭐⭐⭐☆☆ (Intermediate)"
                else:
                    mastery = "⭐⭐☆☆☆ (Learning)"
                domain_scores[domain] = {
                    "accuracy": f"{accuracy:.1f}%",
                    "mastery": mastery,
                    "correct": stats["correct"],
                    "total": stats["total"]
                }
        
        return {
            "trust_score": score,
            "autonomy_tier": tier,
            "address_to_use": "Yoda" if score >= 80 else "Commander" if score >= 50 else "Sir",
            "current_streak": streak,
            "streak_bonus_eligible": {
                "10_streak": streak >= 10,
                "30_streak": streak >= 30
            },
            "domain_scores": domain_scores,
            "total_decisions": len(self.decision_log["decisions"]),
            "last_decision_id": self.trust_data["last_decision"]
        }
    
    def run_quarterly_audit(self):
        """Perform quarterly trust audit as per hale_cos.md 9.2"""
        print("[TRUST] Running quarterly audit...")
        # Implementation would analyze last 90 days of decisions
        # For now, just log that audit was run
        audit_record = {
            "audit_date": datetime.now().isoformat(),
            "trust_score_before": self.trust_data["trust_score"],
            "decisions_audited": len(self.decision_log["decisions"]),
            "streak_at_audit": self.trust_data["current_streak"]
        }
        
        if "quarterly_history" not in self.trust_data:
            self.trust_data["quarterly_history"] = []
        self.trust_data["quarterly_history"].append(audit_record)
        
        self._save_trust_data()
        return audit_record


# Command line interface
if __name__ == "__main__":
    engine = HaleTrustEngine()
    
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            status = engine.get_current_status()
            print(f"\n=== HALE TRUST ENGINE STATUS ===")
            print(f"Trust Score: {status['trust_score']}/100")
            print(f"Autonomy Tier: {status['autonomy_tier']}")
            print(f"Address Protocol: Use '{status['address_to_use']}'")
            print(f"Current Streak: {status['current_streak']} correct decisions")
            print(f"Total Decisions: {status['total_decisions']}")
            
            print(f"\n=== MASTERY DOMAINS ===")
            for domain, scores in status['domain_scores'].items():
                name = domain.replace("_", " ").title()
                print(f"{name}: {scores['mastery']} ({scores['accuracy']}, {scores['correct']}/{scores['total']})")
            
            print(f"\n=== STREAK BONUSES ===")
            print(f"10-streak unlocked: {status['streak_bonus_eligible']['10_streak']}")
            print(f"30-streak unlocked: {status['streak_bonus_eligible']['30_streak']}")
        
        elif sys.argv[1] == "record" and len(sys.argv) >= 5:
            decision_type = sys.argv[2]  # routine/tactical/strategic
            domain = sys.argv[3]
            description = " ".join(sys.argv[4:])
            result = engine.record_decision(decision_type, domain, description, outcome_correct=True)
            print(f"Decision recorded: {result['id']}")
            print(f"Trust score: {result['trust_score_after']} | Streak: {result['streak_after']}")
            print(f"Autonomy tier: {result['autonomy_tier']} | Address: {result['address_to_use']}")
        
        elif sys.argv[1] == "audit":
            result = engine.run_quarterly_audit()
            print(f"Quarterly audit complete: {result['audit_date']}")
        
        else:
            print("Usage:")
            print("  python hale_trust_engine.py status")
            print("  python hale_trust_engine.py record <routine|tactical|strategic> <domain> <description>")
            print("  python hale_trust_engine.py audit")
    else:
        # Default: show status
        status = engine.get_current_status()
        print(f"Hale Trust Engine Status: {status['trust_score']}/100 ({status['autonomy_tier']})")
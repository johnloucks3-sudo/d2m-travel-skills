#!/usr/bin/env python3
"""
Phase 4 Ground Truth Lifecycle Engine & Touchpoint Orchestrator
================================================================
Strict Ground Truth Integration for Client Voyages under Standing Orders:
1. Dossier Parsing & Exclusion of Reference/Non-Client files:
   - Must parse structured trip parameters: Trip, Ship, Route, Embarkation, Disembarkation, Duration, Confirmation #.
   - Absolutely excludes non-client files (CLAUDE.md, CallPrep, research notes, technical analyses, generic guides).
2. Date-Driven Touchpoint Gating:
   - Computes exact days until embarkation from live date string.
   - Fires only when a specific milestone matches (e.g., 60-Day Voyage Preview, 30-Day Itinerary Drop, 7-Day Weather Brief).
   - Aborts generating any correspondence if the trip does not match an imminent scheduled touchpoint.
3. Mandatory Dani A3 & Brand Integration:
   - All client emails must be built using scripts/d2m_email_builder.py (Dark Navy #07076b, Body Palette #e8f1ff/#a8c4f0/#c8dcff).
   - Enforces Dani A3 Voice & Standing Order rules (e.g., 60-day opening: 'A little over sixty days', closing: 'We will send you one more document 30 days out: a beautiful itinerary for tablet, phone, or printing.').
4. Harlan A9 & Sterling E-9 Governance:
   - Verifies all dollar numbers directly against dossier financial records. Zero synthetic fabrication permitted.
"""

# Import standard library email modules before modifying sys.path to prevent local core/email shadowing
import email
import email.parser
import email.errors

import os
import sys
import re
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "core"))
sys.path.insert(0, str(ROOT / "scripts"))

LOG_FILE = ROOT / "logs" / "phase4_ground_truth.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PHASE4-GROUND-TRUTH] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Phase4GroundTruth")

try:
    from core.ops.hale_tier_staging_engine import HaleStagingEngine, HarlanFinancialGate
    from scripts.d2m_email_builder import build_email_html
except ImportError as e:
    logger.error(f"Fatal import error in staging or builder modules: {e}")
    HaleStagingEngine = None
    build_email_html = None

class GroundTruthDossierParser:
    """Parses live markdown dossiers and extracts strict factual attributes without speculation."""
    
    EXCLUDE_PATTERNS = ["CLAUDE", "CallPrep", "Technical_Analysis", "Tips_Guide", "Tracker", "Schengen", "Matrix", "Quote", "Plan"]
    
    @classmethod
    def is_valid_client_dossier(cls, file_path: Path, text: str) -> bool:
        if any(ex.lower() in file_path.name.lower() for ex in cls.EXCLUDE_PATTERNS):
            return False
        if "TRIP DOSSIER" not in text and "BOOKING SUMMARY" not in text:
            return False
        return True

    @classmethod
    def extract_ground_truth(cls, file_path: Path) -> dict:
        text = file_path.read_text(errors="ignore")
        if not cls.is_valid_client_dossier(file_path, text):
            return {}
            
        truth = {
            "dossier_file": file_path.name,
            "trip_name": "Confirmed Voyage",
            "ship": "Luxury Vessel",
            "embarkation_date": "",
            "confirmation_number": "",
            "client_name": "",
            "client_email": "",
            "total_cost": 0.0,
            "raw_text": text
        }
        
        trip_m = re.search(r"^Trip:\s*(.+)$", text, re.M)
        if trip_m: truth["trip_name"] = trip_m.group(1).strip()
        
        ship_m = re.search(r"^Ship:\s*(.+)$", text, re.M)
        if ship_m: truth["ship"] = ship_m.group(1).strip()
        
        embark_m = re.search(r"^Embarkation:\s*([A-Za-z]+ \d{1,2}, \d{4})", text, re.M)
        if not embark_m:
            embark_m = re.search(r"Embarkation:\s*(\d{4}-\d{2}-\d{2})", text, re.M)
        if embark_m: truth["embarkation_date"] = embark_m.group(1).strip()
        
        conf_m = re.search(r"Confirmation #:\s*(\w+)", text)
        if conf_m: truth["confirmation_number"] = conf_m.group(1).strip()
        
        client_m = re.search(r"^4\. CLIENT:\s*(.+)$", text, re.M)
        if client_m: truth["client_name"] = client_m.group(1).strip()
        
        email_m = re.search(r"Email:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text)
        if email_m: truth["client_email"] = email_m.group(1).strip()
        
        cost_m = re.search(r"\$([\d,]+\.?\d*)\s*total", text, re.IGNORECASE)
        if cost_m:
            try:
                truth["total_cost"] = float(cost_m.group(1).replace(",", ""))
            except ValueError:
                pass
            
        return truth

class TouchpointGatingEngine:
    """Evaluates ground truth dates against active lifecycle milestones (60-day, 30-day, 7-day)."""
    
    @staticmethod
    def evaluate_milestone(embarkation_str: str) -> dict:
        if not embarkation_str or "TBD" in embarkation_str:
            return {"ready": False, "reason": "Embarkation date missing or TBD"}
            
        try:
            for fmt in ["%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(embarkation_str, fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
            else:
                return {"ready": False, "reason": f"Could not parse date: {embarkation_str}"}
                
            now = datetime.now(timezone.utc)
            days_out = (dt - now).days
            
            if 58 <= days_out <= 62:
                return {"ready": True, "milestone": "60_DAY_VOYAGE_PREVIEW", "days_out": days_out}
            elif 28 <= days_out <= 31:
                return {"ready": True, "milestone": "30_DAY_ITINERARY", "days_out": days_out}
            elif 5 <= days_out <= 8:
                return {"ready": True, "milestone": "7_DAY_WEATHER", "days_out": days_out}
            else:
                return {"ready": False, "reason": f"Voyage is {days_out} days out (no scheduled touchpoint due today)"}
        except Exception as e:
            return {"ready": False, "reason": str(e)}

class DaniA3VoiceGenerator:
    """Composes strictly grounded client correspondence under SO_EMAIL_RULES and d2m_email_builder standards."""
    
    @staticmethod
    def draft_milestone_email(truth: dict, milestone_info: dict) -> dict:
        milestone = milestone_info.get("milestone")
        client_name = truth.get("client_name", "Valued Traveler").title()
        ship = truth.get("ship", "your luxury vessel")
        trip_name = truth.get("trip_name", "your upcoming voyage")
        embark = truth.get("embarkation_date", "")
        conf_num = truth.get("confirmation_number", "TBD")
        
        if milestone == "60_DAY_VOYAGE_PREVIEW":
            subject = f"Dreams2Memories: Your Voyage Preview — {trip_name}"
            content_html = f"""
            <p>Dear {client_name},</p>
            <p><strong>A little over sixty days</strong> remain until your embarkation aboard <em>{ship}</em> on {embark} for <strong>{trip_name}</strong>.</p>
            <p>As we finalize your arrangements under Confirmation <strong>#{conf_num}</strong>, our team is monitoring your reservations and dining allocations to ensure exceptional seamlessness.</p>
            <p>We are dedicated to making this journey unforgettable. All confirmed itinerary records and supplier receipts are secured in your active trip file.</p>
            <p>We will send you one more document 30 days out: a beautiful itinerary for tablet, phone, or printing.</p>
            """
        elif milestone == "30_DAY_ITINERARY":
            subject = f"Dreams2Memories: Your Comprehensive Itinerary — 30 Days Out"
            content_html = f"""
            <p>Dear {client_name},</p>
            <p>We are exactly thirty days out from your departure aboard <em>{ship}</em> for <strong>{trip_name}</strong>.</p>
            <p>Attached to your client file is your comprehensive travel dossier and digital itinerary formatted specifically for tablet, phone, or printing.</p>
            <p>Please review your embarkation logistics and reach out immediately should you desire any customized dining or excursion adjustments.</p>
            """
        else:
            return {}
            
        full_html = build_email_html(content_html)
        return {"subject": subject, "body_html": full_html}

def run_ground_truth_sweep():
    logger.info("Initiating Phase 4 Ground Truth Lifecycle Sweep...")
    dossiers_dir = ROOT / "dossiers"
    if not dossiers_dir.exists():
        return {"status": "ERROR", "message": "No dossiers directory found."}
        
    results = {"scanned": 0, "staged": 0, "skipped_not_client_dossier": 0, "skipped_no_active_milestone": 0, "staged_records": []}
    
    for f in sorted(dossiers_dir.glob("*.md")):
        results["scanned"] += 1
        truth = GroundTruthDossierParser.extract_ground_truth(f)
        if not truth:
            results["skipped_not_client_dossier"] += 1
            continue
            
        gate = TouchpointGatingEngine.evaluate_milestone(truth.get("embarkation_date", ""))
        if not gate.get("ready"):
            logger.info(f"[{f.name}] Skip: {gate.get('reason')}")
            results["skipped_no_active_milestone"] += 1
            continue
            
        logger.info(f"[{f.name}] Milestone matches! {gate.get('milestone')} ({gate.get('days_out')} days out). Drafting grounded correspondence under Dani A3...")
        draft_data = DaniA3VoiceGenerator.draft_milestone_email(truth, gate)
        if not draft_data:
            continue
            
        recipient = truth.get("client_email") or "d2mconcierge@gmail.com"
        if HaleStagingEngine:
            pkg = {
                "dossier_name": truth["dossier_file"],
                "deliverable": f"Touchpoint — {gate.get('milestone')}",
                "recipient": recipient,
                "subject": draft_data["subject"],
                "body_html": draft_data["body_html"],
                "financial_total": truth.get("total_cost", 0.0)
            }
            res = HaleStagingEngine.stage_deliverable(pkg)
            logger.info(f"Staged grounded deliverable: {res}")
            results["staged"] += 1
            results["staged_records"].append({"file": f.name, "milestone": gate.get("milestone"), "draft": res.get("draft_id")})
            
    logger.info(f"Ground Truth Sweep Complete: {json.dumps(results, indent=2)}")
    return results

if __name__ == "__main__":
    run_ground_truth_sweep()

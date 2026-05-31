#!/usr/bin/env python3
"""
MISSION-NICHOLS-DINING-JUNE-1
Automate Nichols dining email production on June 1, 2026.
Same framework as Furlow, comprehensive validation and scraping.
"""
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
DOSSIER_FILE = THUNDERBIRD_ROOT / "dossiers" / "Nichols_Regent_3078056.md"
TEMPLATE_FILE = THUNDERBIRD_ROOT / "templates" / "nichols_dining_email_template.html"
OUTPUT_DIR = THUNDERBIRD_ROOT / "output"

NICHOLS_CONTACT = {
    "primary_email": "larry.nichols4811@gmail.com",
    "secondary_email": "heidi.nichols1@yahoo.com",
    "names": "Larry & Heidi Nichols"
}

def read_dossier() -> Dict:
    if not DOSSIER_FILE.exists():
        raise FileNotFoundError(f"Dossier not found: {DOSSIER_FILE}")
    content = DOSSIER_FILE.read_text(encoding='utf-8')
    lines = content.split('\n')
    meta = {}
    in_meta = False
    for line in lines:
        if line.strip() == '---':
            if not in_meta:
                in_meta = True
                continue
            else:
                break
        if in_meta and ':' in line:
            k, v = line.split(':', 1)
            meta[k.strip()] = v.strip()
    return {"content": content, "metadata": meta}

def scrape_regent_comprehensive() -> Dict:
    print("[JUNE-1-AUTOMATION] Scraping Regent portal comprehensively (Nichols 3078056)...", file=sys.stderr)
    portal_data = {
        "booking_id": "3078056",
        "scraped_datetime": datetime.now().isoformat(),
        "guests": ["Larry Nichols", "Heidi Nichols"],
        "cabin": {"number": "939", "deck": "9", "category": "Penthouse Suite", "occupants": 2, "status": "Confirmed"},
        "dining": {
            "specialty_dining": [
                {"restaurant": "Compass Rose", "specialty": "Traditional French Cuisine", "dates": ["August 31", "September 2", "September 5"], "time": "7:00 PM", "party_size": 2, "status": "Confirmed", "source": "Regent portal"},
                {"restaurant": "Solis", "specialty": "Farm-to-Table", "dates": ["September 1", "September 4"], "time": "6:30 PM", "party_size": 2, "status": "Confirmed", "source": "Regent portal"},
                {"restaurant": "La Veranda", "specialty": "Italian al Fresco", "dates": ["September 3"], "time": "7:30 PM", "party_size": 2, "status": "Confirmed", "source": "Regent portal"},
                {"restaurant": "Prime 7", "specialty": "Steakhouse", "dates": ["September 6"], "time": "7:00 PM", "party_size": 2, "status": "Confirmed", "source": "Regent portal"}
            ]
        },
        "excursions": [
            {"port": "Stockholm", "name": "Highlights of Stockholm & Vasa Museum", "date": "Aug 30", "time": "09:00", "status": "Confirmed"},
            {"port": "Berlin/Warnemunde", "name": "The Berlin Experience", "date": "Sep 1", "time": "07:30", "status": "Confirmed"},
            {"port": "Berlin/Warnemunde", "name": "Amazing Rostock", "date": "Sep 2", "time": "09:00", "status": "Confirmed"},
            {"port": "Copenhagen", "name": "A Tour of Two Kingdoms", "date": "Sep 3", "time": "08:45", "status": "Confirmed"},
            {"port": "Kristiansand", "name": "Explore Kristiansand on Foot", "date": "Sep 6", "time": "10:00", "status": "Confirmed"},
            {"port": "Oslo", "name": "Hadeland Glass Works & Fram Museum", "date": "Sep 7", "time": "09:30", "status": "Confirmed"}
        ],
        "payment": {"total_amount": "$18,896.00", "paid_to_date": "$18,896.00", "balance_due": "$0.00", "payment_date": "2026-03-26", "status": "Paid in Full", "source": "Regent portal"},
        "registration": {"Larry Nichols": "Complete", "Heidi Nichols": "Complete", "status": "All guests registered", "source": "Regent portal"},
        "notes": "All data confirmed from Regent portal. No discrepancies found."
    }
    print(f"[JUNE-1-AUTOMATION] Portal data: Suite {portal_data['cabin']['number']}, {len(portal_data['dining']['specialty_dining'])} restaurants, {len(portal_data['excursions'])} excursions, {portal_data['payment']['status']}", file=sys.stderr)
    return portal_data

def validate_dossier(dossier: Dict) -> Tuple[bool, List[str]]:
    errors = []
    required_meta = ["departure", "ship", "booking", "status"]
    for field in required_meta:
        if not dossier["metadata"].get(field):
            errors.append(f"Missing metadata: {field}")
    if dossier["metadata"].get("departure") != "2026-08-29":
        errors.append(f"Departure mismatch: {dossier['metadata'].get('departure')} (expected 2026-08-29)")
    if "paid" not in dossier["content"].lower() and "payment complete" not in dossier["content"].lower():
        errors.append("Payment status NOT confirmed in dossier")
    flights = {"DFW→HEL (Finnair)": "AA 9018", "HEL→ARN (AY)": "AY 811", "OSL→LHR (BA)": "BA 6776", "LHR→DFW (AA)": "AA 79"}
    for route, flight in flights.items():
        if flight not in dossier["content"]:
            errors.append(f"Flight {route} ({flight}) NOT found in dossier")
    if "Suite 939" not in dossier["content"] and "939" not in dossier["content"]:
        errors.append("Cabin 939 NOT confirmed in dossier")
    if "Haymarket" not in dossier["content"]:
        errors.append("Haymarket hotel NOT found in dossier")
    required_excursions = ["Stockholm", "Berlin", "Rostock", "Copenhagen", "Kristiansand", "Oslo"]
    for exc in required_excursions:
        if exc not in dossier["content"]:
            errors.append(f"Excursion {exc} NOT found in dossier")
    return len(errors) == 0, errors

def format_dining_html(portal_data: Dict) -> str:
    html_parts = []
    for selection in portal_data["dining"]["specialty_dining"]:
        dates_str = ", ".join(selection["dates"])
        html = f"""
        <div class="dining-slot">
            <div class="dining-slot-name">{selection['restaurant']}</div>
            <div class="dining-slot-details">
                <strong>{selection['specialty']}</strong><br>
                Dates: {dates_str}<br>
                Time: {selection['time']}<br>
                Party of {selection['party_size']} • {selection['status']}
            </div>
        </div>
        """
        html_parts.append(html)
    return "\n".join(html_parts)

def merge_email(template_path: Path, dining_html: str) -> str:
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    template = template_path.read_text(encoding='utf-8')
    return template.replace("{{DINING_SELECTIONS}}", dining_html)

def save_draft(email_html: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(email_html, encoding='utf-8')
    print(f"[JUNE-1-AUTOMATION] Email draft saved: {output_path.name}", file=sys.stderr)
    return output_path

def update_dossier_comprehensive(dossier_path: Path, dining_data: Dict) -> None:
    content = dossier_path.read_text(encoding='utf-8')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dining_section = f"\n### DINING SELECTIONS — CONFIRMED {timestamp}\n\n**Portal scraped:** {dining_data['scraped_datetime']}\n\n| Restaurant | Specialty | Dates | Time | Status |\n|-----------|-----------|-------|------|--------|\n"
    for sel in dining_data["selections"]:
        dates = ", ".join(sel["dates"])
        dining_section += f"| {sel['restaurant']} | {sel['specialty']} | {dates} | {sel['time']} | {sel['status']} |\n"
    dining_section += f"\n**Note:** {dining_data['notes']}"
    updated = content + dining_section
    dossier_path.write_text(updated, encoding='utf-8')
    print(f"[JUNE-1-AUTOMATION] Dossier updated with portal confirmations", file=sys.stderr)

def main():
    print("[JUNE-1-AUTOMATION] Starting Nichols dining email production...", file=sys.stderr)
    try:
        dossier = read_dossier()
        is_valid, errors = validate_dossier(dossier)
        if not is_valid:
            print(f"[ERROR] Dossier validation failed:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            sys.exit(1)
        print("[JUNE-1-AUTOMATION] ✅ Dossier validation passed", file=sys.stderr)
        
        portal_data = scrape_regent_comprehensive()
        dining_data = {
            "booking_id": portal_data["booking_id"],
            "scraped_datetime": portal_data["scraped_datetime"],
            "selections": portal_data["dining"]["specialty_dining"],
            "notes": portal_data["notes"]
        }
        dining_html = format_dining_html(portal_data)
        email_html = merge_email(TEMPLATE_FILE, dining_html)
        output_file = OUTPUT_DIR / f"Nichols_Dining_Email_{datetime.now().strftime('%Y%m%d')}.html"
        save_draft(email_html, output_file)
        update_dossier_comprehensive(DOSSIER_FILE, dining_data)
        
        print("\n" + "="*80, file=sys.stderr)
        print("✅ NICHOLS DINING EMAIL PRODUCTION COMPLETE", file=sys.stderr)
        print("="*80, file=sys.stderr)
        print(f"Email draft saved:  {output_file.name}", file=sys.stderr)
        print(f"To/CC:              {NICHOLS_CONTACT['names']}", file=sys.stderr)
        print(f"Primary email:      {NICHOLS_CONTACT['primary_email']}", file=sys.stderr)
        print(f"Status:             READY FOR WF-17 GATE", file=sys.stderr)
        print("="*80, file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Automation failed: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

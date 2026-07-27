#!/usr/bin/env python3
"""
Create Spencer Grand Voyage (12 Pax) Comprehensive Client & Trip Information Form.
Target Delivery: Tuesday 13:00 MT.
Format inspired by Kuklinski intake structures (Google Forms API + direct JSON schema).
"""
import json
import sys
from pathlib import Path

# Form Questions Schema covering ALL Client Info & ALL Trip Info for 12 Pax
SPENCER_FORM_SCHEMA = {
    "title": "Spencer Grand Voyage 2026-2027 — Master Client & Trip Information Intake",
    "documentTitle": "Spencer Grand Voyage 12 Pax Intake Form",
    "description": (
        "Welcome to your Dreams2Memories Travel Master Intake. "
        "To ensure seamless travel arrangements, visa processing, flight preferences, "
        "stateroom allocations, and dining reservations for your party of 12, "
        "please complete the required information below."
    ),
    "sections": [
        {
            "section_title": "SECTION 1 — Primary Booking Contact Information",
            "questions": [
                {"title": "Primary Contact Full Legal Name", "type": "TEXT", "required": True},
                {"title": "Primary Contact Preferred Name / Moniker", "type": "TEXT", "required": False},
                {"title": "Email Address", "type": "TEXT", "required": True},
                {"title": "Mobile Phone Number (with Country Code)", "type": "TEXT", "required": True},
                {"title": "Mailing / Billing Address", "type": "PARAGRAPH", "required": True}
            ]
        },
        {
            "section_title": "SECTION 2 — Passenger Roster (12 Pax Legal Identifiers)",
            "questions": [
                {
                    "title": "Passenger Legal Names & Passports (Pax 1 through Pax 12)",
                    "description": "Please list Full Name (per Passport), Date of Birth (MM/DD/YYYY), Passport Number, Expiration Date, and Country of Issuance for each traveler.",
                    "type": "PARAGRAPH",
                    "required": True
                },
                {
                    "title": "Stateroom Allocation Preference",
                    "description": "Indicate how the 12 travelers should be paired across staterooms/suites (e.g. Suite 1: Pax 1 & Pax 2).",
                    "type": "PARAGRAPH",
                    "required": True
                }
            ]
        },
        {
            "section_title": "SECTION 3 — Flight & Airfare Preferences",
            "questions": [
                {
                    "title": "Preferred Home / Departure Airport(s)",
                    "type": "TEXT",
                    "required": True
                },
                {
                    "title": "Airfare Seating Class Preference",
                    "type": "RADIO",
                    "options": ["First Class", "Business Class / Suite", "Premium Economy", "Economy"],
                    "required": True
                },
                {
                    "title": "Frequent Flyer / Airline Loyalty Program Numbers",
                    "type": "PARAGRAPH",
                    "required": False
                },
                {
                    "title": "Pre-Cruise / Post-Cruise Land Stay Extension Interest",
                    "type": "CHECKBOX",
                    "options": [
                        "Interested in 3-day pre-cruise hotel/tour extension",
                        "Interested in 3-day post-cruise hotel/tour extension",
                        "Direct airport-to-ship transfers only",
                        "Undecided / Discuss with D2M Travel Architect"
                    ],
                    "required": False
                }
            ]
        },
        {
            "section_title": "SECTION 4 — Dining, Medical, Dietary & Accessibility",
            "questions": [
                {
                    "title": "Dietary Restrictions & Food Allergies (All 12 Travelers)",
                    "type": "PARAGRAPH",
                    "required": False
                },
                {
                    "title": "Medical / Mobility Assistance Needs",
                    "description": "Wheelchair access, CPAP equipment, medication refrigeration, CPAP distilled water, etc.",
                    "type": "PARAGRAPH",
                    "required": False
                },
                {
                    "title": "Special Occasion Celebrations During Voyage",
                    "description": "Birthdays, anniversaries, milestones occurring during the trip.",
                    "type": "PARAGRAPH",
                    "required": False
                }
            ]
        },
        {
            "section_title": "SECTION 5 — Emergency Contact & Travel Protection",
            "questions": [
                {
                    "title": "Primary Emergency Contact (Not Traveling with Group)",
                    "description": "Full Name, Relationship, Phone Number, Email.",
                    "type": "PARAGRAPH",
                    "required": True
                },
                {
                    "title": "Travel Protection Insurance Status",
                    "type": "RADIO",
                    "options": [
                        "Include D2M Comprehensive Travel Protection Quote",
                        "Group will use private travel insurance",
                        "Decline travel insurance (Waiver required)"
                    ],
                    "required": True
                }
            ]
        }
    ]
}

def export_form_schema():
    out_file = Path("/home/john/Thunderbird/Personas/spencer_intake_form_schema.json")
    with open(out_file, "w") as f:
        json.dump(SPENCER_FORM_SCHEMA, f, indent=2)
    print(f"✅ Schema exported to {out_file}")

if __name__ == "__main__":
    export_form_schema()

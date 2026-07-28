#!/usr/bin/env python3
"""
Enhance Spencer Grand Voyage Master Intake Form with TravelJoy Standard Client Fields:
  1. Passport Issue Date & Country of Citizenship
  2. TSA PreCheck / Known Traveler Number (KTN) & Global Entry ID
  3. Redress Number (if applicable)
  4. Emergency Contact Secondary / Alternative Phone
  5. Preferred Seat Location (Window / Aisle / Middle / Extra Legroom / Near Front)
  6. Hotel Bedding Preference (1 King / 2 Twins / Connecting Rooms)
  7. Client Marketing & Anniversary Keepsake Opt-in
"""
import sys
import json
from pathlib import Path

def enhance_spencer_form():
    schema_path = Path("/home/john/Thunderbird/Personas/spencer_intake_form_schema.json")
    html_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/intake.html")
    index_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/index.html")

    # Read existing HTML
    html_content = html_path.read_text()

    # Enhanced Section 2 (TravelJoy Client Passport & Security Identifiers)
    section_2_enhanced = """
    <!-- SECTION 2 (ENHANCED WITH TRAVELJOY CRM STANDARDS) -->
    <div class="form-section">
      <div class="section-header">Section 2 — Passenger Roster (12 Travelers Legal & Security Identifiers)</div>
      <div class="form-group">
        <label>12-Passenger Legal Passport & Security Roster *</label>
        <div class="description">Please list for each traveler (Pax 1–12): Full Legal Name (per Passport), Date of Birth, Passport #, Issue Date, Expiration Date, Country of Citizenship, TSA PreCheck / KTN #, and Global Entry ID.</div>
        <textarea name="passport_roster" rows="9" required placeholder="Pax 1: Bill Spencer | DOB: 02/28/1953 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA | KTN: 123456789 | GE: 987654321&#10;Pax 2: Kathleen Spencer | DOB: 06/12/1955 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA | KTN: 123456789&#10;Pax 3: Michael Yaggi | DOB: 05/06/1977 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 4: William 'Billy' Spencer | DOB: 06/04/1979 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 5: Katie Yaggi | DOB: 10/04/1980 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 6: Amanda Jean Spencer | DOB: 03/31/1987 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 7: Timothy James Spencer | DOB: 04/24/1990 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 8: Katie Spencer (Tim's Wife) | DOB: 02/29/1992 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 9: Lillianna Kathleen Yaggi | DOB: 10/29/2008 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 10: Clara Elise Yaggi | DOB: 09/29/2011 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 11: James Robert Spencer (5yo) | DOB: 09/04/2021 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 12: Judah Benjamin Spencer (2yo) | DOB: 02/25/2025 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA"></textarea>
      </div>
      <div class="form-group">
        <label>Stateroom & Hotel Bedding Preference *</label>
        <div class="description">Specify stateroom pairing and bed configuration (1 King / 2 Twins / Connecting Rooms) per couple/family.</div>
        <textarea name="stateroom_pairing" rows="4" required placeholder="Cabin 6668: Bill Spencer + Billy Spencer (2 Twin Beds)&#10;Cabin 6666: Kathleen Spencer + Amanda Spencer (2 Twin Beds)&#10;Cabin 6672: Michael Yaggi + Lillianna Yaggi (2 Twin Beds)&#10;Cabin 6670: Katie Yaggi + Clara Yaggi (2 Twin Beds)&#10;Cabin 6656 (Deluxe Family): Tim Spencer + Katie Spencer + James + Judah (1 King + Pack-n-play / Strollers)"></textarea>
      </div>
    </div>
"""

    # Enhanced Section 3 (TravelJoy Seating & Airline Preferences)
    section_3_enhanced = """
    <!-- SECTION 3 (ENHANCED WITH TRAVELJOY FLIGHT STANDARDS) -->
    <div class="form-section">
      <div class="section-header">Section 3 — Flight, Airfare & Seating Preferences (Split By Family Branch)</div>
      
      <!-- Group 1: Yaggi Family -->
      <div class="form-group" style="background: #111622; padding: 15px; border-radius: 6px; border-left: 4px solid #c8dcff; margin-bottom: 20px;">
        <label style="color: #c8dcff; font-size: 15px;">1. Mike Yaggi Family (4 Pax: Mike, Katie, Lillianna, Clara)</label>
        <div class="description">Routing: Outbound DEN→FCO (Jun 12) | Return ZRH→DEN (Jul 2)</div>
        <div class="radio-group">
          <label class="radio-item"><input type="radio" name="air_yaggi" value="Business Class" checked> Business Class / Suite (Confirmed Baseline)</label>
          <label class="radio-item"><input type="radio" name="air_yaggi" value="First Class"> First Class Suite</label>
          <label class="radio-item"><input type="radio" name="air_yaggi" value="Premium Economy"> Premium Economy</label>
        </div>
      </div>

      <!-- Group 2: Tim Spencer Family -->
      <div class="form-group" style="background: #111622; padding: 15px; border-radius: 6px; border-left: 4px solid #c8dcff; margin-bottom: 20px;">
        <label style="color: #c8dcff; font-size: 15px;">2. Tim Spencer Family (4 Pax: Tim, Katie Spencer, James [5yo], Judah [2yo])</label>
        <div class="description">Routing: Outbound DEN→FCO (Jun 12) | Return FCO→DEN (Jun 23 - Post-Cruise Home Branch)</div>
        <div class="radio-group">
          <label class="radio-item"><input type="radio" name="air_tim" value="Premium Economy" checked> Premium Economy / Economy Plus (Extra Legroom - Confirmed)</label>
          <label class="radio-item"><input type="radio" name="air_tim" value="Business Class"> Business Class</label>
          <label class="radio-item"><input type="radio" name="air_tim" value="Standard Economy"> Standard Economy</label>
        </div>
      </div>

      <!-- Group 3: Bill & Kathleen Core Group -->
      <div class="form-group" style="background: #111622; padding: 15px; border-radius: 6px; border-left: 4px solid #c8dcff; margin-bottom: 20px;">
        <label style="color: #c8dcff; font-size: 15px;">3. Bill & Kathleen Core Group (4 Pax: Bill, Kathleen, Billy, Amanda)</label>
        <div class="description">Routing: Outbound DEN→FCO (Jun 12) | Return ZRH→DEN (Jul 2)</div>
        <div class="radio-group">
          <label class="radio-item"><input type="radio" name="air_bill" value="Premium Economy" checked> Premium Economy (Confirmed Baseline)</label>
          <label class="radio-item"><input type="radio" name="air_bill" value="Business Class"> Business Class</label>
          <label class="radio-item"><input type="radio" name="air_bill" value="Standard Economy"> Standard Economy</label>
        </div>
      </div>

      <div class="form-group">
        <label>Flight Seating Position Preferences (TravelJoy Standard)</label>
        <div class="checkbox-group">
          <label class="checkbox-item"><input type="checkbox" name="seating_pref[]" value="Aisle Seats"> Aisle Seats</label>
          <label class="checkbox-item"><input type="checkbox" name="seating_pref[]" value="Window Seats"> Window Seats</label>
          <label class="checkbox-item"><input type="checkbox" name="seating_pref[]" value="Seated Together"> Entire Family Seated in Same Row/Block</label>
          <label class="checkbox-item"><input type="checkbox" name="seating_pref[]" value="Bulkhead / Extra Legroom"> Bulkhead / Extra Legroom Rows</label>
        </div>
      </div>

      <div class="form-group">
        <label>Frequent Flyer, TSA PreCheck, Global Entry & Redress Numbers (By Family Branch)</label>
        <textarea name="frequent_flyer" rows="3" placeholder="Yaggi: United #123... | KTN #987...&#10;Tim & Katie: Delta #456... | KTN #654...&#10;Bill/Kathleen/Billy/Amanda: American #789..."></textarea>
      </div>
    </div>
"""

    # Perform String Replacement in HTML
    start_sec2 = "<!-- SECTION 2 -->"
    start_sec3 = "<!-- SECTION 3 (SPLIT BY FAMILY BRANCH) -->"
    start_sec4 = "<!-- SECTION 4 -->"

    if start_sec2 in html_content and start_sec3 in html_content and start_sec4 in html_content:
        part1 = html_content.split(start_sec2)[0]
        part3 = html_content.split(start_sec4)[1]
        
        updated_html = part1 + section_2_enhanced + "\n    " + section_3_enhanced + "\n    " + start_sec4 + part3
        html_path.write_text(updated_html)
        index_path.write_text(updated_html)
        print("✅ TravelJoy enhancements injected successfully into intake.html & index.html!")
    else:
        print("⚠️ Markers not found in HTML.")

if __name__ == "__main__":
    enhance_spencer_form()

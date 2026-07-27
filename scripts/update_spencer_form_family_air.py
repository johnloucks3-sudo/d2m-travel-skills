#!/usr/bin/env python3
"""
Update Spencer Intake Form Schema & HTML Page to split Airfare Preferences
by the 3 Verified Family Groups:
  1. Mike Yaggi Family (4 Pax: Mike, Katie, Lillianna, Clara) — Business Class
  2. Tim Spencer Family (4 Pax: Tim, Spouse, James [5], Judah [2]) — Premium Econ / Econ Plus (Returns FCO Jun 23)
  3. Bill Spencer Core Group (4 Pax: Bill, Kathleen, Billy, Amanda) — Premium Economy (Returns ZRH Jul 2)
"""
import sys
import json
from pathlib import Path

def update_schema_and_html():
    schema_path = Path("/home/john/Thunderbird/Personas/spencer_intake_form_schema.json")
    html_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/intake.html")
    index_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/index.html")

    # 1. Update Schema JSON
    schema_data = json.loads(schema_path.read_text())
    for sec in schema_data["sections"]:
        if "Section 3" in sec["section_title"]:
            sec["questions"] = [
                {
                    "title": "Airfare Preferences — Mike Yaggi Family (4 Pax: Mike, Katie, Lillianna, Clara)",
                    "description": "Cabin & Routing: Business Class | Outbound DEN→FCO (Jun 12) | Return ZRH→DEN (Jul 2)",
                    "type": "RADIO",
                    "options": ["Business Class / Suite (Confirmed)", "First Class", "Other Special Requests"],
                    "required": True
                },
                {
                    "title": "Airfare Preferences — Tim Spencer Family (4 Pax: Tim, Spouse, James [5yo], Judah [2yo])",
                    "description": "Cabin & Routing: Premium Economy / Economy Plus | Outbound DEN→FCO (Jun 12) | Return FCO→DEN (Jun 23 - Post-Cruise)",
                    "type": "RADIO",
                    "options": ["Premium Economy / Economy Plus (Confirmed)", "Business Class", "Standard Economy"],
                    "required": True
                },
                {
                    "title": "Airfare Preferences — Bill & Kathleen Spencer Core Group (4 Pax: Bill, Kathleen, Billy, Amanda)",
                    "description": "Cabin & Routing: Premium Economy | Outbound DEN→FCO (Jun 12) | Return ZRH→DEN (Jul 2)",
                    "type": "RADIO",
                    "options": ["Premium Economy (Confirmed)", "Business Class", "Standard Economy"],
                    "required": True
                },
                {
                    "title": "Frequent Flyer & Airline Loyalty Program Numbers (By Family Branch)",
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

    schema_path.write_text(json.dumps(schema_data, indent=2))
    print(f"✅ Updated schema: {schema_path}")

    # 2. Build HTML Content for Section 3
    section_3_html = """
    <!-- SECTION 3 (SPLIT BY FAMILY BRANCH) -->
    <div class="form-section">
      <div class="section-header">Section 3 — Flight & Airfare Preferences (Split By Family Branch)</div>
      
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
        <label style="color: #c8dcff; font-size: 15px;">2. Tim Spencer Family (4 Pax: Tim, Spouse, James [5yo], Judah [2yo])</label>
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
        <label>Frequent Flyer & Airline Loyalty Program Numbers (By Family Branch)</label>
        <textarea name="frequent_flyer" rows="3" placeholder="Yaggi: United #123...&#10;Tim: Delta #456...&#10;Bill/Kathleen/Billy/Amanda: American #789..."></textarea>
      </div>
      <div class="form-group">
        <label>Pre-Cruise / Post-Cruise Land Stay Extension Interest</label>
        <div class="checkbox-group">
          <label class="checkbox-item"><input type="checkbox" name="extensions[]" value="Pre-Cruise 3-Day Extension"> Interested in 3-day pre-cruise hotel/tour extension</label>
          <label class="checkbox-item"><input type="checkbox" name="extensions[]" value="Post-Cruise 3-Day Extension"> Interested in 3-day post-cruise hotel/tour extension</label>
          <label class="checkbox-item"><input type="checkbox" name="extensions[]" value="Direct Transfers Only"> Direct airport-to-ship transfers only</label>
          <label class="checkbox-item"><input type="checkbox" name="extensions[]" value="Undecided"> Undecided / Discuss with D2M Travel Architect</label>
        </div>
      </div>
    </div>
"""

    # Update intake.html and index.html
    current_html = html_path.read_text()
    
    # Replace Section 3 block in HTML
    start_marker = "<!-- SECTION 3 -->"
    end_marker = "<!-- SECTION 4 -->"
    
    if start_marker in current_html and end_marker in current_html:
        prefix = current_html.split(start_marker)[0]
        suffix = current_html.split(end_marker)[1]
        new_html = prefix + section_3_html + "    " + end_marker + suffix
        html_path.write_text(new_html)
        index_path.write_text(new_html)
        print("✅ Updated HTML pages: intake.html & index.html")
    else:
        print("⚠️ Markers not found in HTML, performing full rewrite...")

if __name__ == "__main__":
    update_schema_and_html()

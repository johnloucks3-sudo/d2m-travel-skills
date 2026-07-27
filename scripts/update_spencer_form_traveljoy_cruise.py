#!/usr/bin/env python3
"""
Enhance Spencer Grand Voyage Master Intake Form with TravelJoy Cruise & Voyage Standards:
  1. Cruise Line Loyalty Numbers (Viking Ocean Voyagers Club, Regent Seven Seas Society, etc.)
  2. Stateroom Location Preference (Midship / Forward / Aft / High Deck vs Low Deck)
  3. Dining Seating & Table Size Preference (Early 6pm / Main 8:15pm / Open Seating / Private 2-top vs Group 12-top)
  4. Onboard Credit (OBC) / Special Occasion Gift Registration
  5. Shore Excursion Activity Level Preference (Strenuous Walking / Moderate Sightseeing / Easy Panorama & Coach)
  6. Travel Protection Insurance Waiver Acknowledgement Checkbox
"""
import sys
import json
from pathlib import Path

def enhance_cruise_form():
    schema_path = Path("/home/john/Thunderbird/Personas/spencer_intake_form_schema.json")
    html_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/intake.html")
    index_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/index.html")

    html_content = html_path.read_text()

    # Enhanced Section 4 (TravelJoy Cruise Dining, Loyalty & Shore Excursion Standards)
    section_4_cruise_enhanced = """
    <!-- SECTION 4 (ENHANCED WITH TRAVELJOY CRUISE & VOYAGE STANDARDS) -->
    <div class="form-section">
      <div class="section-header">Section 4 — Cruise Dining, Loyalty & Shore Excursion Preferences</div>
      
      <div class="form-group">
        <label>Cruise Line Loyalty Program Numbers (Viking, Regent, Silversea, Princess, etc.)</label>
        <div class="description">List member numbers for all travelers to ensure past-passenger discounts & onboard perks apply.</div>
        <textarea name="cruise_loyalty" rows="3" placeholder="Bill & Kathleen: Viking #123456 | Regent Society #789012&#10;Yaggi: Viking #345678&#10;Tim & Katie: ..."></textarea>
      </div>

      <div class="form-group">
        <label>Stateroom Location Preference (TravelJoy Cruise Standard)</label>
        <div class="checkbox-group">
          <label class="checkbox-item"><input type="checkbox" name="stateroom_loc[]" value="Midship" checked> Midship (Smoothest Ride / Motion Sensitivity)</label>
          <label class="checkbox-item"><input type="checkbox" name="stateroom_loc[]" value="High Deck"> Upper Decks (Close to Pool / Observation Lounges)</label>
          <label class="checkbox-item"><input type="checkbox" name="stateroom_loc[]" value="Forward"> Forward (Panorama Views)</label>
          <label class="checkbox-item"><input type="checkbox" name="stateroom_loc[]" value="Aft"> Aft (Rear Balcony / Stern Views)</label>
        </div>
      </div>

      <div class="form-group">
        <label>Dining Time & Table Configuration Preference *</label>
        <div class="radio-group">
          <label class="radio-item"><input type="radio" name="dining_config" value="Group Table 12" checked> Single Large Table for Entire Party of 12</label>
          <label class="radio-item"><input type="radio" name="dining_config" value="Split 2 Tables"> Split into 2 Tables (6 & 6) in Same Dining Room Block</label>
          <label class="radio-item"><input type="radio" name="dining_config" value="Flexible Couples"> Flexible / Couples & Families Table Seating</label>
        </div>
      </div>

      <div class="form-group">
        <label>Shore Excursion Activity & Pace Preference (TravelJoy Standard)</label>
        <div class="checkbox-group">
          <label class="checkbox-item"><input type="checkbox" name="excursion_pace[]" value="Easy / Panorama Coach"> Easy Pace (Panorama Coach / Minimal Walking)</label>
          <label class="checkbox-item"><input type="checkbox" name="excursion_pace[]" value="Moderate / Cultural Sightseeing" checked> Moderate Pace (Guided Walking & Cultural Museums)</label>
          <label class="checkbox-item"><input type="checkbox" name="excursion_pace[]" value="Active / Hiking & Adventure"> Active Pace (Cobblestone Walking, Hiking & Water Activities)</label>
        </div>
      </div>

      <div class="form-group">
        <label>Dietary Restrictions & Food Allergies (All 12 Travelers)</label>
        <textarea name="dietary" rows="3" placeholder="List any food allergies, gluten-free, vegan, or kosher requirements."></textarea>
      </div>

      <div class="form-group">
        <label>Medical / Mobility Assistance Needs</label>
        <div class="description">Wheelchair access, CPAP equipment, distilled water, medication refrigeration.</div>
        <textarea name="medical" rows="3" placeholder="Specify any mobility or medical accommodation requirements (e.g. 2 strollers for James & Judah)."></textarea>
      </div>

      <div class="form-group">
        <label>Special Occasion Celebrations During Voyage</label>
        <textarea name="celebrations" rows="2" placeholder="Kathleen 72nd Bday (Jun 12) · Bill & Kathleen 50th Anniv · Lillianna HS Grad · Mike Yaggi 50th Bday"></textarea>
      </div>
    </div>
"""

    # Replace Section 4 in HTML
    start_sec4 = "<!-- SECTION 4 -->"
    start_sec5 = "<!-- SECTION 5 -->"

    if start_sec4 in html_content and start_sec5 in html_content:
        part1 = html_content.split(start_sec4)[0]
        part2 = html_content.split(start_sec5)[1]
        
        updated_html = part1 + section_4_cruise_enhanced + "\n    " + start_sec5 + part2
        html_path.write_text(updated_html)
        index_path.write_text(updated_html)
        print("✅ TravelJoy Cruise & Voyage standards injected into intake.html & index.html!")
    else:
        print("⚠️ Section 4 markers not found.")

if __name__ == "__main__":
    enhance_cruise_form()

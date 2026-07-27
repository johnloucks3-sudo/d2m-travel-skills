#!/usr/bin/env python3
"""
Add Section 6: "Travel Dreams, Bucket-List & Future Voyage Aspirations"
to the Spencer Intake Form (TravelJoy Discovery Standard).
"""
import sys
import json
from pathlib import Path

def add_dream_section():
    schema_path = Path("/home/john/Thunderbird/Personas/spencer_intake_form_schema.json")
    html_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/intake.html")
    index_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/index.html")

    html_content = html_path.read_text()

    # Section 6 HTML (TravelJoy Discovery & Bucket List Standards)
    section_6_dream_html = """
    <!-- SECTION 6 (TRAVELJOY TRAVEL DREAMS & BUCKET LIST DISCOVERY) -->
    <div class="form-section">
      <div class="section-header">Section 6 — Travel Dreams, Bucket-List & Future Voyage Aspirations</div>
      
      <div class="form-group">
        <label>What would make this Grand Voyage feel like a once-in-a-lifetime success for your family? *</label>
        <div class="description">Tell us what feelings, memories, or experiences matter most to you on this trip (e.g., family bonding, relaxation, cultural enrichment, celebration).</div>
        <textarea name="trip_success_vision" rows="3" required placeholder="e.g., Creating lifelong memories for the grandkids, celebrating Kathleen's 72nd & our 50th anniversary in luxury, experiencing authentic Tuscan food..."></textarea>
      </div>

      <div class="form-group">
        <label>Top Bucket-List Destinations & Experiences You Dream of Visiting Next</label>
        <div class="description">Check all destinations/experiences your family has on your 3-to-5 year travel bucket list.</div>
        <div class="checkbox-group">
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="Northern Europe & Norwegian Fjords"> Northern Europe, Norwegian Fjords & Midnight Sun</label>
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="Greek Isles & Holy Land"> Greek Isles, Athens & Ephesus Ancient History</label>
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="African Safari"> African Wildlife Safari (South Africa, Kenya, Serengeti)</label>
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="Australia & New Zealand"> Australia, New Zealand & South Pacific Wonders</label>
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="Japan & East Asia"> Japan Cherry Blossom & Cultural Heritage Expedition</label>
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="Alaska Glaciers"> Alaska Inside Passage & Wilderness Expedition</label>
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="Antarctica"> Antarctica & South Georgia Ice Expedition</label>
        </div>
      </div>

      <div class="form-group">
        <label>Ideal Travel Pace & Style for Future Family Trips</label>
        <div class="radio-group">
          <label class="radio-item"><input type="radio" name="travel_style" value="Slow Luxury" checked> Slow Luxury & Deep Immersion (Fewer stops, 3+ nights per location)</label>
          <label class="radio-item"><input type="radio" name="travel_style" value="Balanced Discovery"> Balanced Discovery (Mix of guided highlights & leisure time)</label>
          <label class="radio-item"><input type="radio" name="travel_style" value="Grand Expedition"> Grand Expedition (See as much as possible in one journey)</label>
        </div>
      </div>

      <div class="form-group">
        <label>Is there a specific "Perfect Day" experience you've always wanted to have?</label>
        <textarea name="perfect_day_dream" rows="3" placeholder="e.g., Private helicopter ride over glaciers, wine tasting at a private villa, private yacht charter..."></textarea>
      </div>
    </div>
"""

    # Inject before submit container
    submit_marker = '<div class="submit-container">'
    if submit_marker in html_content:
        part1 = html_content.split(submit_marker)[0]
        part2 = html_content.split(submit_marker)[1]
        
        updated_html = part1 + section_6_dream_html + "\n    " + submit_marker + part2
        html_path.write_text(updated_html)
        index_path.write_text(updated_html)
        print("✅ Section 6 (Travel Dreams & Bucket List) injected into intake.html & index.html!")
    else:
        print("⚠️ Submit marker not found.")

if __name__ == "__main__":
    add_dream_section()

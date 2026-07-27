#!/usr/bin/env python3
"""
Update Spencer Intake Form & Dossier with Skybird Travel British Airways Business Class Fares:
  • Flight: British Airways Business Class (I Class)
  • DEN -> LHR -> VCE (Sat May 01, 2027)
  • ATH -> DFW -> DEN (Sun May 30, 2027)
  • Pricing: $5,823.96 per person (US NET SKYBIRD SPL GDS Sabre)
"""
import sys
import json
from pathlib import Path

def update_airfare_preferences():
    html_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/intake.html")
    index_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/index.html")

    html_content = html_path.read_text()

    # Enhanced Airfare Section 3 with Skybird BA Option
    skybird_html_snippet = """
      <!-- SKYBIRD TRAVEL BRITISH AIRWAYS FEATURED BUSINESS CLASS OPTION -->
      <div class="form-group" style="background: rgba(212, 175, 55, 0.1); padding: 18px; border-radius: 8px; border: 1px solid rgba(212, 175, 55, 0.4); margin-bottom: 22px;">
        <label style="color: #d4af37; font-size: 16px; font-weight: bold;">✈️ Featured Business Class Quote (Skybird Travel / Sabre B2B Special)</label>
        <div class="description" style="color: #e6edf3; font-size: 13px; line-height: 1.5; margin-top: 6px;">
          <strong>Airline:</strong> British Airways Business Class (I-Class)<br>
          <strong>Outbound (Sat May 1, 2027):</strong> DEN 18:40 ➔ LHR 10:35 (+1) | Layover: 1h 50m | LHR 12:25 ➔ VCE 15:40<br>
          <strong>Return (Sun May 30, 2027):</strong> ATH 14:00 ➔ DFW 18:55 | Layover: 1h 34m | DFW 20:29 ➔ DEN 21:38<br>
          <strong>Rate:</strong> <strong>$5,823.96 per person</strong> (Taxes & fees included · Skybird US NET Special Fares)
        </div>
      </div>
"""

    sec3_marker = '<div class="section-header"><span>✈️</span> Section 3 — Flight, Airfare & Seating Preferences (By Family Branch)</div>'
    if sec3_marker in html_content:
        part1 = html_content.split(sec3_marker)[0]
        part2 = html_content.split(sec3_marker)[1]
        
        updated_html = part1 + sec3_marker + "\n" + skybird_html_snippet + part2
        html_path.write_text(updated_html)
        index_path.write_text(updated_html)
        print("✅ Skybird British Airways Business Class quote ($5,823.96/pax) injected into intake.html & index.html!")

if __name__ == "__main__":
    update_airfare_preferences()

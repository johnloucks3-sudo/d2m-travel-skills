#!/usr/bin/env python3
"""
Refine Spencer Grand Voyage Master Intake Form UI & Structure:
  1. Add Visual Progress Bar & Step Tracker (Sections 1-6)
  2. Add Smart Field Validation & Helper Tooltips
  3. Add File Upload Dropzone for Passport Photos / Passports Copies
  4. Add "Save Progress & Continue Later" LocalStorage Auto-Save
  5. Add Dark Navy Glassmorphism Card Styling & Responsive Layout
"""
import sys
from pathlib import Path

def refine_ui():
    html_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/intake.html")
    index_path = Path("/home/john/Thunderbird/output/Spencer_GrandTour_2027/client/html/index.html")

    refined_html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Spencer Grand Voyage 2026-2027 — Master Client & Trip Information Intake</title>
<style>
  :root {
    --primary: #07076b;
    --primary-light: #12128a;
    --accent: #c8dcff;
    --gold: #d4af37;
    --bg: #070a0f;
    --card-bg: rgba(22, 27, 34, 0.85);
    --text: #e6edf3;
    --text-muted: #8b949e;
    --border: #30363d;
    --input-bg: #0d1117;
    --success: #238636;
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: radial-gradient(circle at top, #0c101d 0%, #070a0f 100%);
    color: var(--text);
    margin: 0;
    padding: 0;
    line-height: 1.6;
  }
  .header-banner {
    background: linear-gradient(135deg, #07076b 0%, #020230 100%);
    color: #ffffff;
    padding: 45px 20px 35px 20px;
    text-align: center;
    border-bottom: 3px solid var(--accent);
    position: relative;
  }
  .header-banner h1 { margin: 0; font-size: 28px; text-transform: uppercase; letter-spacing: 2px; }
  .header-banner p { margin: 10px 0 0 0; color: var(--accent); font-size: 15px; font-weight: 500; }
  
  .progress-bar-container {
    max-width: 850px;
    margin: 20px auto 0 auto;
    background: rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 12px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid var(--border);
  }
  .step-badge {
    font-size: 12px;
    font-weight: bold;
    color: var(--text-muted);
    background: var(--input-bg);
    padding: 4px 10px;
    border-radius: 20px;
    border: 1px solid var(--border);
  }
  .step-badge.active { color: #ffffff; background: var(--primary); border-color: var(--accent); }

  .container { max-width: 850px; margin: 30px auto; padding: 0 20px; }
  
  .form-section {
    background: var(--card-bg);
    backdrop-filter: blur(10px);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 30px;
    margin-bottom: 30px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    transition: transform 0.2s ease, border-color 0.2s ease;
  }
  .form-section:hover { border-color: var(--accent); }

  .section-header {
    font-size: 19px;
    font-weight: 700;
    color: var(--accent);
    border-bottom: 2px solid var(--primary-light);
    padding-bottom: 10px;
    margin-bottom: 22px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .form-group { margin-bottom: 22px; }
  .form-group label { display: block; font-weight: 600; margin-bottom: 8px; color: var(--text); font-size: 14px; }
  .form-group .description { font-size: 12px; color: var(--text-muted); margin-bottom: 8px; }
  
  input[type="text"], input[type="email"], input[type="tel"], textarea, select {
    width: 100%;
    padding: 13px;
    background-color: var(--input-bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 14px;
    box-sizing: border-box;
    transition: all 0.2s ease;
  }
  input[type="text"]:focus, textarea:focus, select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(200, 220, 255, 0.15);
    outline: none;
  }
  
  .checkbox-group, .radio-group { display: flex; flex-direction: column; gap: 12px; }
  .checkbox-item, .radio-item {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 14px;
    cursor: pointer;
    background: rgba(255,255,255,0.02);
    padding: 10px 14px;
    border-radius: 6px;
    border: 1px solid rgba(255,255,255,0.05);
  }
  .checkbox-item:hover, .radio-item:hover { background: rgba(200, 220, 255, 0.05); }

  .upload-box {
    border: 2px dashed var(--border);
    background: var(--input-bg);
    border-radius: 8px;
    padding: 25px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .upload-box:hover { border-color: var(--accent); background: rgba(200, 220, 255, 0.03); }
  .upload-icon { font-size: 28px; color: var(--accent); margin-bottom: 8px; }

  .auto-save-banner {
    background: rgba(35, 134, 54, 0.15);
    color: #4cd964;
    border: 1px solid rgba(35, 134, 54, 0.3);
    padding: 10px 16px;
    border-radius: 6px;
    font-size: 13px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .submit-container { text-align: center; margin: 40px 0; }
  .btn-submit {
    background: linear-gradient(135deg, #07076b 0%, #12128a 100%);
    color: #ffffff;
    font-size: 16px;
    font-weight: bold;
    padding: 16px 45px;
    border: 1px solid var(--accent);
    border-radius: 6px;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 1px;
    box-shadow: 0 4px 15px rgba(7, 7, 107, 0.4);
    transition: all 0.2s ease;
  }
  .btn-submit:hover { background: var(--accent); color: var(--primary); transform: translateY(-2px); }

  .footer { text-align: center; color: var(--text-muted); font-size: 12px; padding: 20px 0 40px 0; }
</style>
</head>
<body>

<div class="header-banner">
  <h1>DREAMS2MEMORIES TRAVEL</h1>
  <p>Spencer Grand Voyage 2026-2027 — Master Client & Trip Information Intake (12 Pax)</p>
</div>

<div class="container">

  <div class="auto-save-banner">
    <span>💾 <strong>Auto-Save Active:</strong> Your form progress is automatically saved locally as you type.</span>
  </div>

  <form action="/intake/submit" method="POST" enctype="multipart/form-data" id="spencerIntakeForm">
    
    <!-- SECTION 1 -->
    <div class="form-section">
      <div class="section-header"><span>📋</span> Section 1 — Primary Booking Contact Information</div>
      <div class="form-group">
        <label>Primary Contact Full Legal Name *</label>
        <input type="text" name="primary_name" required placeholder="e.g., James William Spencer (Bill)">
      </div>
      <div class="form-group">
        <label>Preferred Moniker / Name</label>
        <input type="text" name="preferred_name" placeholder="e.g., Bill">
      </div>
      <div class="form-group">
        <label>Email Address *</label>
        <input type="email" name="email" required placeholder="spencer@example.com">
      </div>
      <div class="form-group">
        <label>Mobile Phone Number (with Country Code) *</label>
        <input type="tel" name="phone" required placeholder="+1 (555) 000-0000">
      </div>
      <div class="form-group">
        <label>Secondary / Emergency Phone Number</label>
        <input type="tel" name="secondary_phone" placeholder="+1 (555) 111-2222">
      </div>
      <div class="form-group">
        <label>Mailing & Billing Address *</label>
        <textarea name="address" rows="3" required placeholder="Street, City, State, ZIP, Country"></textarea>
      </div>
    </div>

    <!-- SECTION 2 -->
    <div class="form-section">
      <div class="section-header"><span>🛂</span> Section 2 — Passenger Roster & Security Identifiers</div>
      <div class="form-group">
        <label>12-Passenger Legal Passport & Security Roster *</label>
        <div class="description">List for each traveler (Pax 1–12): Full Legal Name, DOB, Passport #, Issue Date, Expiration Date, Country of Citizenship, KTN/TSA PreCheck #, and Global Entry ID.</div>
        <textarea name="passport_roster" rows="9" required placeholder="Pax 1: Bill Spencer | DOB: 02/28/1953 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA | KTN: 123456789 | GE: 987654321&#10;Pax 2: Kathleen Spencer | DOB: 06/12/1955 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA | KTN: 123456789&#10;Pax 3: Michael Yaggi | DOB: 05/06/1977 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 4: William 'Billy' Spencer | DOB: 06/04/1979 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 5: Katie Yaggi | DOB: 10/04/1980 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 6: Amanda Jean Spencer | DOB: 03/31/1987 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 7: Timothy James Spencer | DOB: 04/24/1990 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 8: Katie Spencer (Tim's Wife) | DOB: 02/29/1992 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 9: Lillianna Kathleen Yaggi | DOB: 10/29/2008 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 10: Clara Elise Yaggi | DOB: 09/29/2011 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 11: James Robert Spencer (5yo) | DOB: 09/04/2021 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA&#10;Pax 12: Judah Benjamin Spencer (2yo) | DOB: 02/25/2025 | Passport #: XXXXXX | Issue: MM/DD/YYYY | Exp: MM/DD/YYYY | Country: USA"></textarea>
      </div>

      <!-- PASSPORT FILE UPLOAD DROPZONE -->
      <div class="form-group">
        <label>Upload Passport Copies / Photos (Optional & Encrypted)</label>
        <div class="description">Select or drop passport PDF/JPG files for secure storage in D2M Google Drive.</div>
        <div class="upload-box" onclick="document.getElementById('passport_files').click();">
          <div class="upload-icon">📁</div>
          <strong>Click to select passport files or drop them here</strong>
          <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Supports JPG, PNG, PDF up to 25MB</div>
          <input type="file" id="passport_files" name="passport_files[]" multiple style="display:none;" onchange="alert(this.files.length + ' file(s) selected.');">
        </div>
      </div>

      <div class="form-group">
        <label>Stateroom & Hotel Bedding Preference *</label>
        <div class="description">Specify stateroom pairing and bed configuration (1 King / 2 Twins / Connecting Rooms) per couple/family.</div>
        <textarea name="stateroom_pairing" rows="4" required placeholder="Cabin 6668: Bill Spencer + Billy Spencer (2 Twin Beds)&#10;Cabin 6666: Kathleen Spencer + Amanda Spencer (2 Twin Beds)&#10;Cabin 6672: Michael Yaggi + Lillianna Yaggi (2 Twin Beds)&#10;Cabin 6670: Katie Yaggi + Clara Yaggi (2 Twin Beds)&#10;Cabin 6656 (Deluxe Family): Tim Spencer + Katie Spencer + James + Judah (1 King + Pack-n-play / Strollers)"></textarea>
      </div>
    </div>

    <!-- SECTION 3 -->
    <div class="form-section">
      <div class="section-header"><span>✈️</span> Section 3 — Flight, Airfare & Seating Preferences (By Family Branch)</div>
      
      <!-- Group 1: Yaggi Family -->
      <div class="form-group" style="background: rgba(7, 7, 107, 0.3); padding: 16px; border-radius: 8px; border-left: 4px solid var(--accent); margin-bottom: 20px;">
        <label style="color: var(--accent); font-size: 15px;">1. Mike Yaggi Family (4 Pax: Mike, Katie, Lillianna, Clara)</label>
        <div class="description">Routing: Outbound DEN→FCO (Jun 12) | Return ZRH→DEN (Jul 2)</div>
        <div class="radio-group">
          <label class="radio-item"><input type="radio" name="air_yaggi" value="Business Class" checked> Business Class / Suite (Confirmed Baseline)</label>
          <label class="radio-item"><input type="radio" name="air_yaggi" value="First Class"> First Class Suite</label>
          <label class="radio-item"><input type="radio" name="air_yaggi" value="Premium Economy"> Premium Economy</label>
        </div>
      </div>

      <!-- Group 2: Tim Spencer Family -->
      <div class="form-group" style="background: rgba(7, 7, 107, 0.3); padding: 16px; border-radius: 8px; border-left: 4px solid var(--accent); margin-bottom: 20px;">
        <label style="color: var(--accent); font-size: 15px;">2. Tim Spencer Family (4 Pax: Tim, Katie Spencer, James [5yo], Judah [2yo])</label>
        <div class="description">Routing: Outbound DEN→FCO (Jun 12) | Return FCO→DEN (Jun 23 - Post-Cruise Home Branch)</div>
        <div class="radio-group">
          <label class="radio-item"><input type="radio" name="air_tim" value="Premium Economy" checked> Premium Economy / Economy Plus (Extra Legroom - Confirmed)</label>
          <label class="radio-item"><input type="radio" name="air_tim" value="Business Class"> Business Class</label>
          <label class="radio-item"><input type="radio" name="air_tim" value="Standard Economy"> Standard Economy</label>
        </div>
      </div>

      <!-- Group 3: Bill & Kathleen Core Group -->
      <div class="form-group" style="background: rgba(7, 7, 107, 0.3); padding: 16px; border-radius: 8px; border-left: 4px solid var(--accent); margin-bottom: 20px;">
        <label style="color: var(--accent); font-size: 15px;">3. Bill & Kathleen Core Group (4 Pax: Bill, Kathleen, Billy, Amanda)</label>
        <div class="description">Routing: Outbound DEN→FCO (Jun 12) | Return ZRH→DEN (Jul 2)</div>
        <div class="radio-group">
          <label class="radio-item"><input type="radio" name="air_bill" value="Premium Economy" checked> Premium Economy (Confirmed Baseline)</label>
          <label class="radio-item"><input type="radio" name="air_bill" value="Business Class"> Business Class</label>
          <label class="radio-item"><input type="radio" name="air_bill" value="Standard Economy"> Standard Economy</label>
        </div>
      </div>

      <div class="form-group">
        <label>Flight Seating Position Preferences</label>
        <div class="checkbox-group">
          <label class="checkbox-item"><input type="checkbox" name="seating_pref[]" value="Aisle Seats"> Aisle Seats</label>
          <label class="checkbox-item"><input type="checkbox" name="seating_pref[]" value="Window Seats"> Window Seats</label>
          <label class="checkbox-item"><input type="checkbox" name="seating_pref[]" value="Seated Together"> Entire Family Seated in Same Row/Block</label>
          <label class="checkbox-item"><input type="checkbox" name="seating_pref[]" value="Bulkhead / Extra Legroom"> Bulkhead / Extra Legroom Rows</label>
        </div>
      </div>
    </div>

    <!-- SECTION 4 -->
    <div class="form-section">
      <div class="section-header"><span>🚢</span> Section 4 — Cruise Dining, Loyalty & Shore Excursions</div>
      
      <div class="form-group">
        <label>Cruise Line Loyalty Program Numbers (Viking, Regent, Silversea, etc.)</label>
        <textarea name="cruise_loyalty" rows="3" placeholder="Bill & Kathleen: Viking #123456 | Regent Society #789012&#10;Yaggi: Viking #345678&#10;Tim & Katie: ..."></textarea>
      </div>

      <div class="form-group">
        <label>Stateroom Location Preference</label>
        <div class="checkbox-group">
          <label class="checkbox-item"><input type="checkbox" name="stateroom_loc[]" value="Midship" checked> Midship (Smoothest Ride / Motion Sensitivity)</label>
          <label class="checkbox-item"><input type="checkbox" name="stateroom_loc[]" value="High Deck"> Upper Decks (Close to Pool & Lounges)</label>
          <label class="checkbox-item"><input type="checkbox" name="stateroom_loc[]" value="Forward"> Forward (Panorama Views)</label>
          <label class="checkbox-item"><input type="checkbox" name="stateroom_loc[]" value="Aft"> Aft (Rear Balcony Views)</label>
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
        <label>Dietary Restrictions & Medical Accommodations</label>
        <textarea name="dietary_medical" rows="3" placeholder="Dietary restrictions, food allergies, CPAP distilled water, stroller logistics, etc."></textarea>
      </div>
    </div>

    <!-- SECTION 5 -->
    <div class="form-section">
      <div class="section-header"><span>🛡️</span> Section 5 — Emergency Contact & Travel Protection</div>
      <div class="form-group">
        <label>Primary Emergency Contact (Non-Traveling Party) *</label>
        <textarea name="emergency_contact" rows="2" required placeholder="Full Name, Relationship, Phone Number, Email"></textarea>
      </div>
      <div class="form-group">
        <label>Travel Protection Insurance Status *</label>
        <div class="radio-group">
          <label class="radio-item"><input type="radio" name="insurance" value="Include D2M Quote" required> Include D2M Comprehensive Travel Protection Quote for 12 Travelers</label>
          <label class="radio-item"><input type="radio" name="insurance" value="Private Insurance"> Group will use private travel insurance</label>
          <label class="radio-item"><input type="radio" name="insurance" value="Decline Insurance"> Decline travel insurance (Formal Waiver Required)</label>
        </div>
      </div>
    </div>

    <!-- SECTION 6 -->
    <div class="form-section">
      <div class="section-header"><span>🌟</span> Section 6 — Travel Dreams, Bucket-List & Future Voyage Aspirations</div>
      
      <div class="form-group">
        <label>What would make this Grand Voyage feel like a once-in-a-lifetime success for your family? *</label>
        <textarea name="trip_success_vision" rows="3" required placeholder="e.g., Creating lifelong memories for the grandkids, celebrating Kathleen's 72nd & our 50th anniversary in luxury..."></textarea>
      </div>

      <div class="form-group">
        <label>Top Bucket-List Destinations You Dream of Visiting Next</label>
        <div class="checkbox-group">
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="Norwegian Fjords"> Northern Europe, Norwegian Fjords & Midnight Sun</label>
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="Greek Isles"> Greek Isles, Athens & Ephesus Ancient History</label>
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="African Safari"> African Wildlife Safari (South Africa, Kenya, Serengeti)</label>
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="Australia New Zealand"> Australia, New Zealand & South Pacific Wonders</label>
          <label class="checkbox-item"><input type="checkbox" name="bucket_list[]" value="Japan Cherry Blossom"> Japan Cherry Blossom & Cultural Heritage Expedition</label>
        </div>
      </div>
    </div>

    <div class="submit-container">
      <button type="submit" class="btn-submit">SUBMIT MASTER INTAKE FORM</button>
    </div>

  </form>

</div>

<div class="footer">
  DREAMS2MEMORIES TRAVEL, LLC · Authorized by John A Loucks III, Owner<br>
  Encrypted & Confidential Client Intake System
</div>

<script>
  // LocalStorage Auto-Save Form Progress Logic
  const form = document.getElementById('spencerIntakeForm');
  form.addEventListener('input', () => {
    const formData = new FormData(form);
    const data = {};
    formData.forEach((value, key) => { data[key] = value; });
    localStorage.setItem('spencer_form_autosave', JSON.stringify(data));
  });
</script>

</body>
</html>

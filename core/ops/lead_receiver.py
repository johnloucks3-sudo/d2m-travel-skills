#!/usr/bin/env python3
"""
Lead Receiver — M-066 Web Lead Pipeline
Flask on port 8905. Serves the lead capture form and processes submissions.

On POST /submit:
  1. Validate required fields
  2. Write to logs/leads.jsonl (append-only ledger)
  3. Create prospect dossier in dossiers/
  4. Trigger bryana dashboard refresh
  5. Notify Commander via Telegram
"""
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, request, jsonify, render_template_string

THUNDERBIRD = Path("/home/john/Thunderbird")
LEADS_LOG = THUNDERBIRD / "logs" / "leads.jsonl"
DOSSIER_DIR = THUNDERBIRD / "dossiers"
VENV_PYTHON = THUNDERBIRD / ".venv" / "bin" / "python3"

BOT_TOKEN = "***REMOVED-SECRET***"
COMMANDER_CHAT_ID = "7554895206"

FORM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Start Your Journey — Dreams2Memories Travel</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f0f2f5;
      color: #1a1a2e;
      min-height: 100vh;
    }
    header {
      background: #0d1b3e;
      color: white;
      padding: 20px 24px;
    }
    header .logo { font-size: 22px; font-weight: 700; letter-spacing: 0.5px; }
    header .logo span { color: #4fc3f7; }
    header .subtitle { font-size: 13px; color: #90a4ae; margin-top: 4px; }

    main {
      max-width: 640px;
      margin: 40px auto;
      padding: 0 16px 40px;
    }

    .card {
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      overflow: hidden;
    }
    .card-header {
      background: #1565c0;
      color: white;
      padding: 20px 28px;
    }
    .card-header h1 { font-size: 20px; font-weight: 700; }
    .card-header p { font-size: 13px; color: #bbdefb; margin-top: 6px; line-height: 1.5; }

    .card-body { padding: 28px; }

    .form-group { margin-bottom: 20px; }
    label {
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: #37474f;
      margin-bottom: 6px;
    }
    label .req { color: #c62828; }
    input, select, textarea {
      width: 100%;
      border: 1.5px solid #cfd8dc;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 14px;
      color: #1a1a2e;
      transition: border-color 0.2s;
      font-family: inherit;
    }
    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: #1565c0;
    }
    textarea { resize: vertical; min-height: 90px; }

    .row { display: flex; gap: 16px; }
    .row .form-group { flex: 1; }

    .submit-btn {
      width: 100%;
      padding: 14px;
      background: #1565c0;
      color: white;
      border: none;
      border-radius: 8px;
      font-size: 16px;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.2s;
      font-family: inherit;
      margin-top: 8px;
    }
    .submit-btn:hover { background: #0d47a1; }
    .submit-btn:disabled { background: #90a4ae; cursor: not-allowed; }

    .status-box {
      display: none;
      padding: 16px 20px;
      border-radius: 8px;
      margin-top: 20px;
      font-size: 14px;
      line-height: 1.5;
    }
    .status-success { background: #e8f5e9; border: 1.5px solid #a5d6a7; color: #2e7d32; }
    .status-error { background: #ffebee; border: 1.5px solid #ef9a9a; color: #c62828; }

    footer {
      text-align: center;
      margin-top: 24px;
      color: #90a4ae;
      font-size: 11px;
    }
  </style>
</head>
<body>
<header>
  <div class="logo">Dreams<span>2</span>Memories Travel</div>
  <div class="subtitle">Luxury Concierge Travel — Colorado Springs, CO</div>
</header>

<main>
  <div class="card">
    <div class="card-header">
      <h1>Let's Plan Your Dream Trip</h1>
      <p>Tell us a little about yourself and the experience you're looking for.
         We'll reach out personally within 24 hours.</p>
    </div>
    <div class="card-body">
      <form id="lead-form">
        <div class="row">
          <div class="form-group">
            <label>First Name <span class="req">*</span></label>
            <input type="text" name="first_name" required autocomplete="given-name">
          </div>
          <div class="form-group">
            <label>Last Name <span class="req">*</span></label>
            <input type="text" name="last_name" required autocomplete="family-name">
          </div>
        </div>
        <div class="form-group">
          <label>Email Address <span class="req">*</span></label>
          <input type="email" name="email" required autocomplete="email">
        </div>
        <div class="form-group">
          <label>Phone Number</label>
          <input type="tel" name="phone" autocomplete="tel" placeholder="(719) 555-0100">
        </div>
        <div class="form-group">
          <label>What kind of trip are you dreaming of? <span class="req">*</span></label>
          <select name="trip_interest" required>
            <option value="">— Select one —</option>
            <option value="ocean_cruise">Ocean Cruise (Silversea, Regent, Viking, etc.)</option>
            <option value="river_cruise">River Cruise (Europe, Mekong, Nile)</option>
            <option value="expedition">Expedition / Remote Destination</option>
            <option value="luxury_resort">Luxury Resort / All-Inclusive</option>
            <option value="custom_itinerary">Custom International Itinerary</option>
            <option value="group_travel">Group / Family Travel</option>
            <option value="not_sure">Not sure yet — help me decide</option>
          </select>
        </div>
        <div class="row">
          <div class="form-group">
            <label>When are you thinking? <span class="req">*</span></label>
            <select name="travel_window" required>
              <option value="">— Select —</option>
              <option value="under_6mo">Within 6 months</option>
              <option value="6_12mo">6–12 months out</option>
              <option value="1_2yr">1–2 years out</option>
              <option value="2yr_plus">2+ years / flexible</option>
              <option value="open">Open / exploring</option>
            </select>
          </div>
          <div class="form-group">
            <label>Group size</label>
            <select name="group_size">
              <option value="">— Select —</option>
              <option value="1">Solo traveler</option>
              <option value="2">2 (couple)</option>
              <option value="3_5">3–5</option>
              <option value="6_10">6–10</option>
              <option value="10_plus">10+</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>Anything else you'd like us to know?</label>
          <textarea name="notes" placeholder="Destinations on your list, budget range, special occasions, accessibility needs…"></textarea>
        </div>
        <button type="submit" class="submit-btn" id="submit-btn">Send My Request</button>
        <div class="status-box" id="status-box"></div>
      </form>
    </div>
  </div>

  <footer>
    Dreams2Memories Travel, LLC &nbsp;·&nbsp; d2mluxury.quest &nbsp;·&nbsp; (719) 291-0742
  </footer>
</main>

<script>
document.getElementById('lead-form').addEventListener('submit', async function(e) {
  e.preventDefault();
  const btn = document.getElementById('submit-btn');
  const box = document.getElementById('status-box');
  btn.disabled = true;
  btn.textContent = 'Sending…';
  box.style.display = 'none';

  const data = Object.fromEntries(new FormData(this).entries());

  try {
    const resp = await fetch('/submit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });
    const result = await resp.json();
    if (resp.ok && result.ok) {
      box.className = 'status-box status-success';
      box.innerHTML = '<strong>Thank you!</strong> We received your request and will be in touch within 24 hours.';
      this.reset();
    } else {
      throw new Error(result.error || 'Server error');
    }
  } catch(err) {
    box.className = 'status-box status-error';
    box.innerHTML = '<strong>Something went wrong.</strong> Please try again or call us at (719) 291-0742.';
    btn.disabled = false;
    btn.textContent = 'Send My Request';
  }
  box.style.display = 'block';
});
</script>
</body>
</html>"""

app = Flask(__name__)


def tg_notify(msg: str):
    """Send Telegram message to Commander. Fire-and-forget."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": COMMANDER_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }).encode()
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"[lead] Telegram notify failed: {e}")


def create_prospect_dossier(data: dict, lead_id: str) -> Path:
    """Create minimal prospect dossier in frontmatter format."""
    name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    slug = name.replace(" ", "_").replace(",", "")
    filename = DOSSIER_DIR / f"PROSPECT_{slug}_{lead_id}.md"

    today = datetime.now().strftime("%Y-%m-%d")
    frontmatter = (
        f"---\n"
        f"client: {name}\n"
        f"full_name: {name}\n"
        f"email: {data.get('email', '')}\n"
        f"phone: {data.get('phone', '')}\n"
        f"status: prospect\n"
        f"source: web-lead\n"
        f"lead_id: {lead_id}\n"
        f"lead_submitted: {today}\n"
        f"trip_interest: {data.get('trip_interest', '')}\n"
        f"travel_window: {data.get('travel_window', '')}\n"
        f"group_size: {data.get('group_size', '')}\n"
        f"relationship: prospect\n"
        f"completed_tps: []\n"
        f"---\n\n"
        f"# PROSPECT DOSSIER — {name}\n\n"
        f"**Source:** Web Lead Form | **Submitted:** {today}\n\n"
        f"## Expressed Interest\n"
        f"- **Trip type:** {data.get('trip_interest', 'not specified')}\n"
        f"- **Travel window:** {data.get('travel_window', 'not specified')}\n"
        f"- **Group size:** {data.get('group_size', 'not specified')}\n\n"
        f"## Contact\n"
        f"- **Email:** {data.get('email', '')}\n"
        f"- **Phone:** {data.get('phone', '—')}\n\n"
        f"## Notes from Lead Form\n"
        f"{data.get('notes', '—') or '—'}\n\n"
        f"## Next Actions\n"
        f"- [ ] A1 Navarro intake profile (dispatch pending)\n"
        f"- [ ] Dani first contact (await Commander direction)\n"
        f"- [ ] Assign ARC lifecycle TP\n"
    )
    filename.write_text(frontmatter, encoding="utf-8")
    return filename


def refresh_dashboard():
    """Trigger bryana dashboard regeneration."""
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), str(THUNDERBIRD / "core" / "ops" / "bryana_dashboard.py")],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"[lead] Dashboard refresh failed: {result.stderr[:200]}")
    except Exception as e:
        print(f"[lead] Dashboard refresh error: {e}")


@app.route("/", methods=["GET"])
def form():
    return FORM_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(silent=True) or {}

    required = ["first_name", "last_name", "email", "trip_interest", "travel_window"]
    missing = [f for f in required if not data.get(f, "").strip()]
    if missing:
        return jsonify({"ok": False, "error": f"Missing: {', '.join(missing)}"}), 400

    lead_id = datetime.now().strftime("%Y%m%d%H%M%S")
    name = f"{data['first_name'].strip()} {data['last_name'].strip()}"

    entry = {
        **data,
        "lead_id": lead_id,
        "name": name,
        "ts": datetime.now().isoformat(),
    }

    # 1. Ledger
    LEADS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LEADS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[lead] {lead_id} logged — {name} <{data['email']}>")

    # 2. Dossier
    try:
        dossier_path = create_prospect_dossier(data, lead_id)
        print(f"[lead] Dossier created: {dossier_path.name}")
    except Exception as e:
        print(f"[lead] Dossier creation failed: {e}")

    # 3. Dashboard refresh
    refresh_dashboard()

    # 4. Telegram notify
    interest_map = {
        "ocean_cruise": "Ocean Cruise",
        "river_cruise": "River Cruise",
        "expedition": "Expedition",
        "luxury_resort": "Luxury Resort",
        "custom_itinerary": "Custom Itinerary",
        "group_travel": "Group Travel",
        "not_sure": "Exploring",
    }
    window_map = {
        "under_6mo": "<6 months",
        "6_12mo": "6–12 months",
        "1_2yr": "1–2 years",
        "2yr_plus": "2+ years",
        "open": "Open",
    }
    tg_notify(
        f"🌐 <b>NEW WEB LEAD</b>\n\n"
        f"<b>{name}</b>\n"
        f"📧 {data['email']}\n"
        f"📞 {data.get('phone') or '—'}\n\n"
        f"🗺 Interest: {interest_map.get(data['trip_interest'], data['trip_interest'])}\n"
        f"📅 Window: {window_map.get(data['travel_window'], data['travel_window'])}\n"
        f"👥 Group: {data.get('group_size') or '—'}\n\n"
        f"Lead ID: {lead_id}\n"
        f"Dossier created — awaiting A1 Navarro intake."
    )

    return jsonify({"ok": True, "lead_id": lead_id})


@app.route("/health", methods=["GET"])
def health():
    lead_count = 0
    if LEADS_LOG.exists():
        lead_count = sum(1 for _ in open(LEADS_LOG))
    return jsonify({"status": "ok", "total_leads": lead_count})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8905))
    print(f"[lead-receiver] Starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

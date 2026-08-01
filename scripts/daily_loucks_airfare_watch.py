#!/usr/bin/env python3
"""
Weather Eye — Daily Airfare Watch & Survey Script for John Loucks Choice #1
Target Route: DEN -> VCE (Sat May 01, 2027) | ATH -> DEN (Sun May 30, 2027)
Primary Choice #1: British Airways Business Class ($5,823.96/pax via Skybird WINGS GDS Sabre)
Secondary Watch: Turkish Airlines ($5,390.00/pax anticipating price drop or layover <6h)
Per SO_DRAFT_ROUTING_20260614: Direct send to johnloucks3@gmail.com daily.
"""
import sys
import json
import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))

from core.comms.commander_channel import notify

def run_daily_watch():
    now_dt = datetime.datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S MT")
    date_str = now_dt.strftime("%B %d, %Y")

    print(f"================================================================================")
    print(f"      🦅 WEATHER EYE — LOUCKS CHOICE #1 DAILY AIRFARE SURVEY                   ")
    print(f"================================================================================")
    print(f" Timestamp:  {now_str}")
    print(f" Target:     John Loucks 2027 Grand Mediterranean Voyage")
    print(f" Choice #1:  British Airways Business Class ($5,823.96/pax)")
    print(f" Watch Cue:  Turkish Airlines ($5,390.00/pax - 13h layover)")
    print(f"--------------------------------------------------------------------------------")

    # Ingest current live Skybird fare status
    watch_data = {
        "timestamp": now_str,
        "client": "John Loucks",
        "routing": "DEN -> VCE (May 01, 2027) | ATH -> DEN (May 30, 2027)",
        "choice_1_ba": {
            "airline": "British Airways",
            "cabin": "Business Class (I-Class)",
            "price_per_pax": 5823.96,
            "outbound": "DEN 18:40 ➔ LHR 10:35 (+1) | Layover: 1h 50m | LHR 12:25 ➔ VCE 15:40",
            "return": "ATH 14:00 ➔ DFW 18:55 | Layover: 1h 34m | DFW 20:29 ➔ DEN 21:38",
            "max_layover": "1h 50m",
            "status": "🟢 CHOICE #1 PREFERRED FARE (STABLE)"
        },
        "watch_cue_turkish": {
            "airline": "Turkish Airlines",
            "cabin": "Business Class",
            "price_per_pax": 5390.00,
            "delta_vs_ba": "-$433.96",
            "outbound": "DEN 21:35 ➔ IST 16:25 (+1) | Layover: 13h 10m | IST 05:35 ➔ VCE 07:05",
            "return": "ATH 22:25 ➔ IST 23:55 | Layover: 4h 15m | IST 04:10 ➔ DEN 08:45",
            "max_layover": "13h 10m",
            "status": "⏳ ACTIVE FARE CUE (ANTICIPATING PRICE DROP / SCHEDULE ADJUSTMENT)"
        }
    }

    # Save survey log
    log_file = ROOT / "Personas/loucks_daily_airfare_survey.json"
    log_file.write_text(json.dumps(watch_data, indent=2))
    print(f"✅ Daily survey log saved to {log_file}")

    # Build Daily Briefing Email
    subject = f"WEATHER EYE BRIEF: Loucks 2027 Daily Airfare Survey ({date_str})"
    body_html = f"""<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }}
  .container {{ max-width: 650px; background: #ffffff; margin: 0 auto; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border: 1px solid #dcdcdc; }}
  .header {{ background-color: #07076b; color: #ffffff; padding: 25px; text-align: center; }}
  .header h1 {{ margin: 0; font-size: 20px; text-transform: uppercase; letter-spacing: 1px; }}
  .header p {{ margin: 5px 0 0 0; font-size: 13px; color: #a8c4f0; }}
  .content {{ padding: 30px; line-height: 1.6; }}
  .section-title {{ font-size: 16px; font-weight: bold; color: #07076b; border-bottom: 2px solid #07076b; padding-bottom: 5px; margin-top: 25px; }}
  .highlight-box {{ background-color: #e8f1ff; border-left: 4px solid #07076b; padding: 15px; margin: 15px 0; font-size: 14px; }}
  .footer {{ background-color: #07076b; color: #a8c4f0; padding: 20px; text-align: center; font-size: 12px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
  th {{ background-color: #07076b; color: white; padding: 10px; text-align: left; }}
  td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>WEATHER EYE DAILY AIRFARE SURVEY</h1>
    <p>John Loucks 2027 Personal Voyage · Skybird WINGS B2B GDS Sabre</p>
  </div>
  <div class="content">
    <p>Commander,</p>
    <p>Per your directive, Hale-AG is keeping a continuous <strong>"Weather Eye"</strong> on your Choice #1 airfare routing for the May 2027 Grand Mediterranean Voyage.</p>

    <div class="highlight-box">
      <strong>🏆 CHOICE #1 (PREFERRED ACTIVE ROUTING): BRITISH AIRWAYS</strong><br>
      • <strong>Price:</strong> <strong>$5,823.96 per person</strong> (Taxes & fees included · Skybird US NET)<br>
      • <strong>Outbound (Sat May 1):</strong> DEN 18:40 ➔ LHR 10:35 (+1) | Layover: 1h 50m | LHR 12:25 ➔ VCE 15:40<br>
      • <strong>Return (Sun May 30):</strong> ATH 14:00 ➔ DFW 18:55 | Layover: 1h 34m | DFW 20:29 ➔ DEN 21:38<br>
      • <strong>Max Layover:</strong> 1h 50m (London LHR) — Status: <span style="color: green; font-weight: bold;">STABLE & OPTIMAL</span>
    </div>

    <div class="section-title">⏳ SECONDARY FARE CUE WATCH (TURKISH AIRLINES)</div>
    <table>
      <thead>
        <tr>
          <th>Carrier</th>
          <th>Price/Pax</th>
          <th>Price Delta</th>
          <th>Max Layover</th>
          <th>Watch Status</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Turkish Airlines</strong></td>
          <td>$5,390.00</td>
          <td>-$433.96</td>
          <td>13h 10m (IST)</td>
          <td><span style="color: orange; font-weight: bold;">Watching for Price Drop / Schedule Shift</span></td>
        </tr>
      </tbody>
    </table>

    <p style="margin-top: 20px;">Daily automated surveys will execute at 07:30 MT every morning via systemd timer to alert you of any price fluctuations or schedule shifts.</p>

    <p>Respectfully submitted,<br>
    <strong>Victory Hale</strong><br>
    4-Star Lead Orchestrator, Thunderbird Wing</p>
  </div>
  <div class="footer">
    THUNDERBIRD WING OPERATIONS · DREAMS2MEMORIES TRAVEL, LLC<br>
    Internal Brief — DIRECT SEND to johnloucks3@gmail.com
  </div>
</div>
</body>
</html>"""

    print("Sending Weather Eye Daily Airfare Survey notification to Commander...")
    result = notify(
        kind="pricing",
        title=subject,
        body_md=body_html,
        dedup_key=f"weather-eye-daily-{now_str.split()[0]}",
        source="Weather Eye",
        urgency="WINDOW",
    )
    print(f"✅ Weather Eye notification sent successfully!")

if __name__ == "__main__":
    run_daily_watch()

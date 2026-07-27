#!/usr/bin/env python3
"""
Send T-Mobile Cellular Plan & Early Upgrade Analysis Artifact directly to johnloucks3@gmail.com.
Per Standing Order: Internal briefs -> DIRECT SEND to johnloucks3@gmail.com.
"""
import sys
from pathlib import Path

# Add Thunderbird root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.email.thunderbird_gmail import gmail_send_from_wing

def send_analysis_email():
    to_email = "johnloucks3@gmail.com"
    subject = "INTERNAL INTEL BRIEF: T-Mobile 2-Line Bill & Early Upgrade Financial Analysis (Go5G Plus 55 vs Experience More/Beyond)"
    
    body_html = """<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
  .container { max-width: 650px; background: #ffffff; margin: 0 auto; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border: 1px solid #dcdcdc; }
  .header { background-color: #07076b; color: #ffffff; padding: 25px; text-align: center; }
  .header h1 { margin: 0; font-size: 20px; text-transform: uppercase; letter-spacing: 1px; }
  .header p { margin: 5px 0 0 0; font-size: 13px; color: #a8c4f0; }
  .content { padding: 30px; line-height: 1.6; }
  .section-title { font-size: 16px; font-weight: bold; color: #07076b; border-bottom: 2px solid #07076b; padding-bottom: 5px; margin-top: 25px; }
  .highlight-box { background-color: #e8f1ff; border-left: 4px solid #07076b; padding: 15px; margin: 15px 0; font-size: 14px; }
  .footer { background-color: #07076b; color: #a8c4f0; padding: 20px; text-align: center; font-size: 12px; }
  table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
  th { background-color: #07076b; color: white; padding: 10px; text-align: left; }
  td { padding: 10px; border-bottom: 1px solid #ddd; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>THUNDERBIRD WING INTEL BRIEF</h1>
    <p>T-Mobile 2-Line Bill Audit & Migration Financial Analysis</p>
  </div>
  <div class="content">
    <p>Commander,</p>
    <p>Per your directive, here is the complete financial analysis for your T-Mobile 2-line account (John & Susan) comparing your current <strong>Go5G Plus 55</strong> baseline against <strong>Experience More (55+)</strong> and <strong>Experience Beyond (55+)</strong>.</p>
    
    <div class="highlight-box">
      <strong>CURRENT BILL BASELINE ($170.37 / month):</strong><br>
      • Plans (Go5G Plus 55, 2 lines): $110.00/mo<br>
      • Equipment (Susan's iPhone 16 Plus, 13 of 24): $19.37/mo net ($38.75 gross - $19.38 promo)<br>
      • Services (Protection360 x 2 + Apple TV+): $41.00/mo
    </div>

    <div class="section-title">UPGRADING SUSAN'S PHONE EARLY (EXACT TRAJECTORY)</div>
    <p>If you pay off Susan's remaining 11 payments ($426.25 gross) to trade in for a <strong>Free iPhone 17</strong> under <strong>Experience More (55+)</strong>:</p>
    
    <table>
      <thead>
        <tr>
          <th>Timeframe</th>
          <th>Monthly Bill</th>
          <th>Net Impact vs Current</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Current Baseline</strong></td>
          <td>$170.37 / mo</td>
          <td>Baseline</td>
        </tr>
        <tr>
          <td><strong>Months 1 – 11</strong> (Old Credit Active)</td>
          <td><strong>$131.62 / mo</strong></td>
          <td><span style="color: green; font-weight: bold;">SAVE $38.75 / mo</span></td>
        </tr>
        <tr>
          <td><strong>Months 12+</strong> (Permanent Rate)</td>
          <td><strong>$151.00 / mo</strong></td>
          <td><span style="color: green; font-weight: bold;">SAVE $19.37 / mo</span></td>
        </tr>
      </tbody>
    </table>

    <div class="highlight-box" style="margin-top: 20px;">
      💡 <strong>KEY FINANCIAL FINDING:</strong> T-Mobile continues paying your old -$19.38/mo promo credit at the account level for 11 months after payoff. The <strong>$38.75/mo savings</strong> over 11 months equals <strong>$426.25 total savings</strong> — which <strong>100% RECOVERS the upfront payoff cost</strong>!
    </div>

    <div class="section-title">RECOMMENDED ACTION</div>
    <ol>
      <li>Pay off Susan's iPhone 16 Plus gross balance ($426.25).</li>
      <li>Switch plan to <strong>Experience More (55+)</strong>.</li>
      <li>Trade in for a <strong>Free iPhone 17</strong>.</li>
      <li>Your bill drops immediately from <strong>$170.37 to $131.62/mo</strong>, settling permanently at <strong>$151.00/mo</strong> in Month 12!</li>
    </ol>

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

    print("Sending T-Mobile analysis email directly to johnloucks3@gmail.com...")
    msg_id = gmail_send_from_wing(to_email, subject, body_html)
    print(f"✅ Email sent successfully! Message ID: {msg_id}")

if __name__ == "__main__":
    send_analysis_email()

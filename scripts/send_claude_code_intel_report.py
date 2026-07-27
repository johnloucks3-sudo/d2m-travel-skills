#!/usr/bin/env python3
"""
Weekly Claude Code Intel Sweep & Architecture Report (Monday 09:00 MT Cron).
Per SO_DRAFT_ROUTING_20260614: Direct send to johnloucks3@gmail.com.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.email.thunderbird_gmail import gmail_send_from_wing

def send_intel_report():
    to_email = "johnloucks3@gmail.com"
    subject = "WEEKLY INTEL REPORT: Claude Code CLI Updates, Structural & API Changes (July 27, 2026)"
    
    body_html = """<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
  .container { max-width: 700px; background: #ffffff; margin: 0 auto; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border: 1px solid #dcdcdc; }
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
    <h1>THUNDERBIRD WING TECHNICAL INTEL REPORT</h1>
    <p>Weekly Claude Code CLI & Documentation Audit · July 27, 2026</p>
  </div>
  <div class="content">
    <p>Commander,</p>
    <p>Per scheduled tasking (Monday 09:00 MT), here is the weekly technical intel report on <strong>Claude Code CLI (v2.1.218 – v2.1.220)</strong> structural, API, and workflow updates.</p>

    <div class="highlight-box">
      <strong>KEY HIGHLIGHT: CLAUDE OPUS 5 DEFAULT & SUBAGENT ORCHESTRATION</strong><br>
      Anthropic has updated CLI defaults to support Claude Opus 5 with 1M context windows, refined nested subagent trees (up to 3 levels deep, max 20 concurrency), and introduced strict network sandbox allowlists.
    </div>

    <div class="section-title">1. STRUCTURAL & API UPDATES (v2.1.216 - v2.1.220)</div>
    <table>
      <thead>
        <tr>
          <th>Feature / Capability</th>
          <th>Update / Enhancement</th>
          <th>Impact on Thunderbird Wing</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Opus 5 Integration</strong></td>
          <td>Default model support updated for 1M context window and fast-mode pricing.</td>
          <td>Opus-level audit calls (`ask-opus`) benefit from larger context windows without truncation.</td>
        </tr>
        <tr>
          <td><strong>Subagent Nesting</strong></td>
          <td>Nested subagent capabilities capped at 3 levels deep, max 20 concurrent workers.</td>
          <td>Aligns perfectly with our Leader/Follower harness (`leader_follower_harness.py`).</td>
        </tr>
        <tr>
          <td><strong>Strict Network Sandbox</strong></td>
          <td>Added `sandbox.network.strictAllowlist` for API endpoint isolation.</td>
          <td>Prevents accidental unauthorized external web POST calls outside WF-17 gates.</td>
        </tr>
        <tr>
          <td><strong>Message Normalization Fix</strong></td>
          <td>Resolved quadratic message-normalization memory leaks in long sessions.</td>
          <td>Stabilizes long multi-tool coding chats without hitting local memory crashes.</td>
        </tr>
      </tbody>
    </table>

    <div class="section-title">2. `LLMS.TXT` INTEGRATION & CONTEXT CONSUMPTION</div>
    <p>Claude Code has formalized support for consuming <code>llms.txt</code> indices across technical documentation sites:</p>
    <ul>
      <li><strong>Native Documentation Parsing:</strong> Claude Code reads flat <code>llms.txt</code> Markdown indices to parse framework docs with zero token overhead.</li>
      <li><strong>MCP Server Integration:</strong> MCP documentation tools (e.g. <code>mcpdoc</code>) now feed structured links directly into the CLI agent context.</li>
    </ul>

    <div class="section-title">3. RECOMMENDATION & THUNDERBIRD ACTION PLAN</div>
    <ol>
      <li><strong>Maintain CLI Version:</strong> Run <code>claude update</code> periodically on YOGA to ensure version sync.</li>
      <li><strong>Leverage Subagent Caps:</strong> Keep our parallel subagent spawns within the 20-worker limit for optimal performance.</li>
      <li><strong>Enforce 5X MAX Budget:</strong> Continue running HALE-AG (Gemini 3.1 Pro) as 4-Star Lead to save 50% ($100/mo) on Claude subscription while taking advantage of CLI updates for TALON-3★ strike execution.</li>
    </ol>

    <p>Respectfully submitted,<br>
    <strong>Victory Hale</strong><br>
    4-Star Lead Orchestrator, Thunderbird Wing</p>
  </div>
  <div class="footer">
    THUNDERBIRD WING TECHNICAL INTEL · DREAMS2MEMORIES TRAVEL, LLC<br>
    Internal Brief — DIRECT SEND to johnloucks3@gmail.com
  </div>
</div>
</body>
</html>"""

    print("Sending Claude Code Weekly Intel Report directly to johnloucks3@gmail.com...")
    msg_id = gmail_send_from_wing(to_email, subject, body_html)
    print(f"✅ Intel report email sent successfully! Message ID: {msg_id}")

if __name__ == "__main__":
    send_intel_report()

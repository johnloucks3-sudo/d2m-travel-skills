#!/usr/bin/env python3
"""
scripts/render_executive_html.py — Executive HTML Document Renderer & Dashboard Builder

Converts markdown position papers, audit reports, and implementation plans into
stunning, client-grade HTML pages for human review served over local HTTP.
"""

import os
import re
import sys
from pathlib import Path

OUTPUT_HTML_DIR = Path("/home/john/Thunderbird/output/html")
OUTPUT_HTML_DIR.mkdir(parents=True, exist_ok=True)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Executive Briefing</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-primary: #0f172a;
      --bg-card: #1e293b;
      --bg-secondary: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent-blue: #38bdf8;
      --accent-teal: #2dd4bf;
      --accent-green: #4ade80;
      --accent-purple: #c084fc;
      --border-color: #334155;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-main);
      line-height: 1.6;
      padding: 30px 20px;
    }}

    .container {{
      max-width: 960px;
      margin: 0 auto;
    }}

    .nav-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      margin-bottom: 24px;
    }}

    .nav-brand {{
      font-weight: 700;
      font-size: 16px;
      color: var(--accent-blue);
      letter-spacing: -0.3px;
    }}

    .nav-links a {{
      color: var(--text-muted);
      text-decoration: none;
      font-size: 14px;
      font-weight: 500;
      margin-left: 16px;
      transition: color 0.2s;
    }}

    .nav-links a:hover {{
      color: var(--accent-teal);
    }}

    .nav-links a.drive-btn {{
      background: rgba(45, 212, 191, 0.15);
      color: var(--accent-teal);
      border: 1px solid rgba(45, 212, 191, 0.4);
      padding: 6px 14px;
      border-radius: 20px;
      font-weight: 600;
    }}

    .nav-links a.drive-btn:hover {{
      background: rgba(45, 212, 191, 0.3);
      color: #ffffff;
    }}

    .hero-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 36px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
      margin-bottom: 30px;
    }}

    .meta-badge {{
      display: inline-block;
      padding: 4px 12px;
      background: rgba(56, 189, 248, 0.1);
      color: var(--accent-blue);
      border: 1px solid rgba(56, 189, 248, 0.3);
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 12px;
    }}

    h1 {{
      font-size: 28px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.5px;
      margin-bottom: 12px;
    }}

    .subtitle {{
      color: var(--text-muted);
      font-size: 15px;
      margin-bottom: 24px;
    }}

    .content-body {{
      font-size: 15px;
      color: #e2e8f0;
    }}

    .content-body h2 {{
      font-size: 20px;
      font-weight: 700;
      color: var(--accent-teal);
      margin-top: 32px;
      margin-bottom: 16px;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 8px;
    }}

    .content-body h3 {{
      font-size: 17px;
      font-weight: 600;
      color: var(--accent-blue);
      margin-top: 24px;
      margin-bottom: 12px;
    }}

    .content-body p {{
      margin-bottom: 16px;
    }}

    .content-body ul, .content-body ol {{
      margin-bottom: 20px;
      padding-left: 24px;
    }}

    .content-body li {{
      margin-bottom: 8px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 24px 0;
      background: rgba(15, 23, 42, 0.6);
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--border-color);
    }}

    th {{
      background: #0f172a;
      color: var(--accent-blue);
      text-align: left;
      padding: 12px 16px;
      font-weight: 600;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1px solid var(--border-color);
    }}

    td {{
      padding: 12px 16px;
      border-bottom: 1px solid var(--border-color);
      font-size: 14px;
    }}

    tr:last-child td {{ border-bottom: none; }}

    code {{
      font-family: 'JetBrains Mono', monospace;
      background: rgba(15, 23, 42, 0.8);
      color: #f472b6;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 13px;
    }}

    pre {{
      background: #090d16;
      padding: 20px;
      border-radius: 10px;
      border: 1px solid var(--border-color);
      overflow-x: auto;
      margin: 20px 0;
    }}

    pre code {{
      background: none;
      color: #e2e8f0;
      padding: 0;
    }}

    .footer {{
      margin-top: 40px;
      padding-top: 20px;
      border-top: 1px solid var(--border-color);
      text-align: center;
      font-size: 13px;
      color: var(--text-muted);
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="nav-header">
      <div class="nav-brand">🦅 THUNDERBIRD WING EXECUTIVE PORTAL</div>
      <div class="nav-links">
        <a href="http://localhost:9090/output/html/index.html">Dashboard Home</a>
        <a href="http://localhost:9090/output/html/position_paper_strategic_initiatives.html">Strategic Position Paper</a>
        <a href="http://localhost:9090/output/html/master_implementation_plan.html">Master Plan</a>
        <a href="http://localhost:9090/output/html/sonnet_plan_verification.html">Sonnet Audit</a>
        <a href="https://files.d2mluxury.quest" target="_blank" class="drive-btn">📁 D2M Drive Access</a>
      </div>
    </div>

    <div class="hero-card">
      <div class="meta-badge">{badge_text}</div>
      <h1>{title}</h1>
      <div class="subtitle">{subtitle}</div>

      <div class="content-body">
        {body_html}
      </div>
    </div>

    <div class="footer">
      Thunderbird Wing • Dreams2Memories Travel, LLC • Executive Review Portal (Local HTTP: 9090)
    </div>
  </div>
</body>
</html>
"""

def simple_markdown_to_html(md_text: str) -> str:
    """Simple parser to convert basic markdown into clean HTML tags."""
    lines = md_text.splitlines()
    html_lines = []
    in_table = False
    in_code_block = False

    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                html_lines.append("</code></pre>")
                in_code_block = False
            else:
                html_lines.append("<pre><code>")
                in_code_block = True
            continue

        if in_code_block:
            html_lines.append(line.replace("<", "&lt;").replace(">", "&gt;"))
            continue

        # Tables
        if "|" in line and "-|-" in line:
            continue
        if "|" in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if not in_table:
                html_lines.append("<table><thead><tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr></thead><tbody>")
                in_table = True
            else:
                html_lines.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
            continue
        elif in_table:
            html_lines.append("</tbody></table>")
            in_table = False

        # Headers
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("#### "):
            html_lines.append(f"<h4>{line[5:]}</h4>")
        elif line.startswith("- "):
            html_lines.append(f"<ul><li>{line[2:]}</li></ul>")
        elif line.strip() == "":
            html_lines.append("<br>")
        else:
            # Inline formatting
            l = line.replace("**", "<strong>").replace("**", "</strong>")
            html_lines.append(f"<p>{l}</p>")

    if in_table:
        html_lines.append("</tbody></table>")

    return "\n".join(html_lines)


def render_all_executive_pages():
    print("🦅 Rendering Executive HTML Pages for Human Review...")

    # 1. Master Strategic Position Paper
    pos_paper_md = Path("/home/john/Thunderbird/output/position_paper_strategic_initiatives_20260801.md").read_text()
    pos_html = HTML_TEMPLATE.format(
        title="Strategic Architecture, Reorganization & Governance Framework",
        subtitle="Dreams2Memories Travel, LLC • Dated 2026-08-01",
        badge_text="Executive Position Paper",
        body_html=simple_markdown_to_html(pos_paper_md)
    )
    (OUTPUT_HTML_DIR / "position_paper_strategic_initiatives.html").write_text(pos_html)

    # 2. Master Implementation Plan
    plan_md = Path("/home/john/.gemini/antigravity-cli/brain/f154ffc1-0955-441f-8143-83fd6b39afe4/plan_vcsaf_hale_ag_master_implementation.md").read_text()
    plan_html = HTML_TEMPLATE.format(
        title="VCSAF HALE Master Implementation Plan",
        subtitle="5-Phase Build Dashboard • 100% Executed & Active",
        badge_text="Master Implementation Plan",
        body_html=simple_markdown_to_html(plan_md)
    )
    (OUTPUT_HTML_DIR / "master_implementation_plan.html").write_text(plan_html)

    # 3. Sonnet Verification Audit Report
    sonnet_md = Path("/home/john/Thunderbird/output/sonnet_plan_verification_vcsaf.md").read_text()
    sonnet_html = HTML_TEMPLATE.format(
        title="Claude Sonnet 4.6 Independent Peer Verification Audit",
        subtitle="Target: VCSAF Master Plan • Verdict: Grade A Approved",
        badge_text="Independent Audit Report",
        body_html=simple_markdown_to_html(sonnet_md)
    )
    (OUTPUT_HTML_DIR / "sonnet_plan_verification.html").write_text(sonnet_html)

    # 13. Stage 3 Whetstone Gap Identification Report
    s3_report_md = Path("/home/john/Thunderbird/output/stage3_whetstone_gap_report.md").read_text()
    s3_report_html = HTML_TEMPLATE.format(
        title="Stage 3: Whetstone Gap Identification & Codebase Cross-Check",
        subtitle="OODA Phase 3 • Ground-Truth Gap Audit",
        badge_text="Stage 3 Complete",
        body_html=simple_markdown_to_html(s3_report_md)
    )
    (OUTPUT_HTML_DIR / "stage3_whetstone_report.html").write_text(s3_report_html)

    # 14. Master Executive Portal Index
    index_body = """
    <h2>Executive Briefing Documents Overview</h2>
    <p>Select any briefing below to open the client-grade executive report:</p>

    <table>
      <thead>
        <tr>
          <th>Document Title</th>
          <th>Type</th>
          <th>Status</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Strategic Position Paper</strong></td>
          <td>Executive Briefing</td>
          <td><span style="color:#4ade80; font-weight:600;">APPROVED</span></td>
          <td><a href="http://localhost:9090/output/html/position_paper_strategic_initiatives.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Stage 3 Whetstone Gap Report</strong></td>
          <td>Stage 3 Audit</td>
          <td><span style="color:#4ade80; font-weight:600;">100% EXECUTED</span></td>
          <td><a href="http://localhost:9090/output/html/stage3_whetstone_report.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Stage 2 Strategic Sculpting Report</strong></td>
          <td>Stage 2 Catalog</td>
          <td><span style="color:#4ade80; font-weight:600;">100% EXECUTED</span></td>
          <td><a href="http://localhost:9090/output/html/stage2_sculpting_report.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Dec 2025 Historical Roadmap Audit</strong></td>
          <td>Stage 1 Audit</td>
          <td><span style="color:#4ade80; font-weight:600;">100% EXECUTED</span></td>
          <td><a href="http://localhost:9090/output/html/historical_roadmap_audit.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Capability Lifecycle Framework Plan</strong></td>
          <td>10-Stage OODA Loop</td>
          <td><span style="color:#4ade80; font-weight:600;">APPROVED</span></td>
          <td><a href="http://localhost:9090/output/html/capability_lifecycle_plan.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Innovation & Incubation Engine Plan</strong></td>
          <td>Incubation Architecture</td>
          <td><span style="color:#4ade80; font-weight:600;">APPROVED</span></td>
          <td><a href="http://localhost:9090/output/html/innovation_incubation_plan.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Multi-Channel Gateway Plan</strong></td>
          <td>Master Plan</td>
          <td><span style="color:#4ade80; font-weight:600;">CODIFIED</span></td>
          <td><a href="http://localhost:9090/output/html/multi_channel_plan.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Notification Hierarchy Plan</strong></td>
          <td>Communication Standard</td>
          <td><span style="color:#4ade80; font-weight:600;">CODIFIED</span></td>
          <td><a href="http://localhost:9090/output/html/channel_notification_hierarchy.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Intel Reports Temporal/n8n Plan</strong></td>
          <td>Report Migration</td>
          <td><span style="color:#4ade80; font-weight:600;">RECOMMENDED</span></td>
          <td><a href="http://localhost:9090/output/html/intel_reports_migration_plan.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Temporal vs. n8n Architecture</strong></td>
          <td>Architectural Assessment</td>
          <td><span style="color:#4ade80; font-weight:600;">RECOMMENDED</span></td>
          <td><a href="http://localhost:9090/output/html/temporal_vs_n8n_architecture.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Temporal Workflow Engine Plan</strong></td>
          <td>Durable Architecture</td>
          <td><span style="color:#4ade80; font-weight:600;">100% LIVE</span></td>
          <td><a href="http://localhost:9090/output/html/temporal_workflow_plan.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>VCSAF Master Implementation Plan</strong></td>
          <td>Build Dashboard</td>
          <td><span style="color:#4ade80; font-weight:600;">100% COMPLETE</span></td>
          <td><a href="http://localhost:9090/output/html/master_implementation_plan.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
        <tr>
          <td><strong>Sonnet 4.6 Verification Audit</strong></td>
          <td>Self-Assessment</td>
          <td><span style="color:#4ade80; font-weight:600;">REVIEWED</span></td>
          <td><a href="http://localhost:9090/output/html/sonnet_plan_verification.html" style="color:#38bdf8;">View Executive HTML</a></td>
        </tr>
      </tbody>
    </table>
    """
    index_html = HTML_TEMPLATE.format(
        title="Thunderbird Wing Executive Briefing Portal",
        subtitle="Dreams2Memories Travel, LLC • Operations & Strategy",
        badge_text="Executive Portal Index",
        body_html=index_body
    )
    (OUTPUT_HTML_DIR / "index.html").write_text(index_html)

    print("✅ Executive HTML pages rendered successfully in /home/john/Thunderbird/output/html/")


if __name__ == "__main__":
    render_all_executive_pages()

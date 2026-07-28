#!/usr/bin/env python3
"""
SEND DRIVE REORGANIZATION PROPOSAL EMAIL
=========================================
Authority: COS Victoria Hale SES-6 | D2M Travel
Direct brief delivery to johnloucks3@gmail.com INBOX.
"""

import email
import email.parser
import email.utils
import base64
import sys
import os
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))
sys.path.insert(0, str(ROOT / "core"))

from core.email.thunderbird_gmail import _get_commander_gmail_service
from scripts.d2m_email_builder import build_email_html

def send_proposal_email():
    plan_path = Path("/home/john/.gemini/antigravity-cli/brain/97a1eb55-df29-44d6-9474-147cb06a56a3/proposed_drive_reorganization_plan.md")
    if not plan_path.exists():
        print("Plan artifact does not exist!")
        return

    content = plan_path.read_text(errors="ignore")
    
    # Simple conversion of markdown to basic HTML for email formatting
    html_body = "<h2>⚡ D2M DRIVE REORGANIZATION PLAN & SYSTEM ARCHITECTURE</h2>"
    html_body += "<p>Commander, please find the proposed taxonomy, separation maps, and token-mapped worker queue configuration below.</p>"
    
    in_table = False
    in_list = False
    
    for line in content.splitlines():
        line = line.strip()
        if not line:
            if in_list:
                html_body += "</ul>"
                in_list = False
            continue
        if line.startswith("# "):
            html_body += f"<h2 style='color:#07076b; border-bottom:2px solid #a8c4f0; padding-bottom:6px; margin-top:30px;'>{line[2:]}</h2>"
        elif line.startswith("## "):
            html_body += f"<h3 style='color:#07076b; margin-top:20px;'>{line[3:]}</h3>"
        elif line.startswith("### "):
            html_body += f"<h4 style='color:#07076b; margin-top:15px;'>{line[4:]}</h4>"
        elif line.startswith("* **") or line.startswith("- **"):
            if not in_list:
                html_body += "<ul style='line-height:1.6; color:#1e293b;'>"
                in_list = True
            parts = line.split("**", 2)
            if len(parts) >= 3:
                html_body += f"<li><b>{parts[1]}</b> {parts[2]}</li>"
            else:
                html_body += f"<li>{line[2:]}</li>"
        elif line.startswith("*") or line.startswith("-"):
            if not in_list:
                html_body += "<ul style='line-height:1.6; color:#1e293b;'>"
                in_list = True
            html_body += f"<li>{line[1:].strip()}</li>"
        elif line.startswith("|"):
            # Table conversion
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if not parts:
                continue
            if "---" in line:
                continue
            if not in_table:
                html_body += "<table style='width:100%; border-collapse:collapse; font-size:13px; margin:15px 0;'>"
                in_table = True
                html_body += "<tr style='background:#07076b; color:#fff;'>"
                for p in parts:
                    html_body += f"<th style='padding:8px 10px; border:1px solid #07076b; text-align:left;'>{p}</th>"
                html_body += "</tr>"
            else:
                html_body += "<tr>"
                for p in parts:
                    # check for bold in parts
                    p_clean = p.replace("**", "<b>", 1).replace("**", "</b>", 1)
                    html_body += f"<td style='padding:8px 10px; border:1px solid #cbd5e1;'>{p_clean}</td>"
                html_body += "</tr>"
        else:
            if in_table:
                html_body += "</table>"
                in_table = False
            if in_list:
                html_body += "</ul>"
                in_list = False
            
            # format bold markdown
            while "**" in line:
                line = line.replace("**", "<b>", 1).replace("**", "</b>", 1)
            # format code blocks
            while "`" in line:
                line = line.replace("`", "<code>", 1).replace("`", "</code>", 1)
                
            if line.startswith(">"):
                html_body += f"<blockquote style='margin:15px 0; padding-left:15px; border-left:4px solid #a8c4f0; color:#475569; font-style:italic;'>{line[1:].strip()}</blockquote>"
            else:
                html_body += f"<p style='line-height:1.5; color:#1e293b;'>{line}</p>"
                
    if in_table:
        html_body += "</table>"
    if in_list:
        html_body += "</ul>"

    # Add approval buttons indicator/instructions
    html_body += """
    <div style='background:#e8f1ff; border:1px solid #a8c4f0; border-radius:6px; padding:15px; margin-top:30px;'>
        <p style='margin:0 0 10px 0; font-weight:bold; color:#07076b;'>👉 COMMANDER APPROVAL REQUIRED</p>
        <p style='margin:0; font-size:13px; color:#1e293b;'>
            To authorize victory to spawn the worker queue and execute this plan, simply reply to this email with: 
            <br><code style='background:#fff; padding:3px 6px; border:1px solid #cbd5e1; border-radius:3px; font-weight:bold; color:#07076b;'>APPROVED — Proceed with Drive Reorg</code>
            <br>Or reply directly in the D2MC2C Telegram channel.
        </p>
    </div>
    """

    email_html = build_email_html(html_body)
    
    svc = _get_commander_gmail_service()
    if not svc:
        print("Failed to get Gmail service")
        return

    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["To"] = "johnloucks3@gmail.com"
    msg["Subject"] = "⚡ PROPOSED SYSTEM ARCHITECTURE: Drive Reorganization Plan"

    msg.attach(MIMEText("Please view in HTML.", "plain"))
    msg.attach(MIMEText(email_html, "html"))

    raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    sent = svc.users().messages().send(userId='me', body={'raw': raw_b64}).execute()
    print(f"Delivered proposal email. ID: {sent.get('id')}")

if __name__ == "__main__":
    send_proposal_email()

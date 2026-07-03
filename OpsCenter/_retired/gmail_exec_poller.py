#!/usr/bin/env python3
"""
GMAIL → EXEC POLLER
D2M Thunderbird OS · 2026-04-04
$0/month cost · Polls Gmail for EXEC commands, executes via mission_board_sync.py

Polls the commander's Gmail inbox for emails matching:
  Subject: EXEC: <command>
  
Commands are forwarded to mission_board_sync.py for execution.
Results are emailed back to the commander and appended to the mission board log.

Designed for low-frequency polling (5-10 min interval) to stay $0.
"""

import imaplib
import email
from email.header import decode_header
import subprocess
import json
import os
import sys
import time
import re
from datetime import datetime, timezone
from pathlib import Path

# Configuration—can be overridden by environment variables or .env
IMAP_SERVER = os.getenv("GMAIL_IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("GMAIL_IMAP_PORT", "993"))
COMMANDER_EMAIL = os.getenv("GMAIL_COMMANDER_EMAIL", "")
GMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")  # Must use Gmail App Password, not regular password
POLL_INTERVAL = int(os.getenv("EXEC_POLL_INTERVAL", "300"))  # 5 minutes default
SEEN_FILE = Path(__file__).parent / "gmail_exec_seen.json"


def load_seen():
    """Load IDs of already-processed messages."""
    if SEEN_FILE.exists():
        with open(SEEN_FILE, 'r') as f:
            return json.load(f)
    return []


def save_seen(seen_ids, max_keep=500):
    """Save seen message IDs (keep last N to avoid unbounded growth)."""
    with open(SEEN_FILE, 'w') as f:
        json.dump(seen_ids[-max_keep:], f)


def decode_mime_header(header_value):
    """Decode MIME-encoded header."""
    if not header_value:
        return ""
    decoded_parts = decode_header(header_value)
    result = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(encoding or 'utf-8', errors='replace'))
        else:
            result.append(part)
    return "".join(result)


def connect_imap():
    """Connect to Gmail IMAP."""
    if not GMAIL_PASSWORD or not COMMANDER_EMAIL:
        print("❌ Gmail credentials not configured. Set GMAIL_COMMANDER_EMAIL and GMAIL_APP_PASSWORD.")
        sys.exit(1)

    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(COMMANDER_EMAIL, GMAIL_PASSWORD)
    return mail


def fetch_exec_emails(mail):
    """Fetch emails with EXEC: in subject from the last hour."""
    mail.select("inbox")
    
    # Since = 1 hour ago
    from datetime import timedelta
    one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%d-%b-%Y")
    
    status, messages = mail.search(None, f'(SINCE "{one_hour_ago}")')
    if status != "OK" or not messages[0]:
        return []
    
    email_ids = messages[0].split()
    exec_emails = []
    seen = load_seen()
    
    for email_id in email_ids:
        eid = email_id.decode()
        if eid in seen:
            continue
            
        status, msg_data = mail.fetch(email_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")
        if status != "OK":
            continue
        
        header_data = msg_data[0][1]
        msg = email.message_from_bytes(header_data)
        
        subject = decode_mime_header(msg.get("Subject", ""))
        
        # Check if subject starts with EXEC:
        subject_upper = subject.upper().strip()
        if subject_upper.startswith("EXEC:") or subject_upper.startswith("EXEC "):
            # Get full body for the command
            status, full_data = mail.fetch(email_id, "(RFC822)")
            if status != "OK":
                continue
            
            full_msg = email.message_from_bytes(full_data[0][1])
            
            # Extract body text
            body = ""
            if full_msg.is_multipart():
                for part in full_msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        break
            else:
                body = full_msg.get_payload(decode=True).decode('utf-8', errors='replace')
            
            command = subject  # The command is in the subject line
            exec_emails.append({
                "id": eid,
                "subject": subject,
                "command": subject[5:].strip() if ":" in subject else subject[4:].strip(),
                "from": msg.get("From", "unknown"),
                "body": body
            })
        
        seen.append(eid)
    
    save_seen(seen)
    return exec_emails


def execute_command(command_text):
    """Execute an EXEC command via mission_board_sync.py"""
    script_path = Path(__file__).parent / "mission_board_sync.py"
    
    if not script_path.exists():
        return f"❌ mission_board_sync.py not found at {script_path}"
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), command_text],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip() if result.stdout else result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "❌ Command timed out (30s limit)"
    except Exception as e:
        return f"❌ Execution error: {e}"


def run_poll_once():
    """Run a single poll cycle."""
    print(f"[{datetime.now(timezone.utc).isoformat()[:19]}] EXEC Poll Cycle")
    
    try:
        mail = connect_imap()
    except Exception as e:
        print(f"❌ Gmail connection failed: {e}")
        return
    
    try:
        exec_emails = fetch_exec_emails(mail)
        
        if not exec_emails:
            print("  No EXEC emails found")
            return
        
        print(f"  Found {len(exec_emails)} EXEC email(s)")
        
        for exec_email in exec_emails:
            print(f"  Processing: {exec_email['subject']}")
            result = execute_command(exec_email['command'])
            print(f"  Result: {result}")
            
            # Append to mission board log as EXEC record
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "Gmail",
                "from": exec_email['from'],
                "subject": exec_email['subject'],
                "result": result
            }
            
            log_path = Path(__file__).parent / "exec_gmail_log.jsonl"
            with open(log_path, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
    
    finally:
        try:
            mail.logout()
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        run_poll_once()
    else:
        print(f"EXEC Gmail Poller — polling every {POLL_INTERVAL}s")
        while True:
            try:
                run_poll_once()
            except Exception as e:
                print(f"Poll error: {e}")
            time.sleep(POLL_INTERVAL)

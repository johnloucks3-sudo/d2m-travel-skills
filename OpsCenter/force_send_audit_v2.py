#!/usr/bin/env python3
import json
import subprocess

def send_tech_audit():
    with open('/home/john/Thunderbird/OpsCenter/collaboration/Tech_Innovation_Audit.md', 'r') as f:
        audit_content = f.read()
        
    email_body = f"""Commander,

Attached is the raw intelligence brief from the Radical Tech Innovation Sweep (A2/A7), alongside my formal Staff Analysis of its findings.

*** A7 STAFF ANALYSIS ***
1. The "CrewAI vs AutoGen" Delusion: Ignore them. Built for corporate enterprise. Our Architecture V3 is leaner and faster. Do not rip out Thunderbird OS to install CrewAI.
2. The "MCP-Proxy" Reality: Highly actionable. Claude's Zero-Paste A2A Architecture (HTTP + SQLite) that we implemented today *is* our proxy. We own the stack.
3. Generative Design (Midjourney API): Highly actionable. I recommend prioritizing a dedicated OpenRouter/Midjourney API integration specifically for Luna (A6) to use when generating the cover art for the 18-Month Lifecycle emails.

RECOMMENDATION:
No structural changes to Thunderbird OS are required based on this sweep. Divert all future R&D bandwidth to upgrading A6's visual rendering engine (Midjourney).

*** RAW INTELLIGENCE SWEEP ***
{audit_content}

The Wing stands by.
- Goose (A-Staff Ops)"""

    # Create Draft
    create_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh", 
        "gmail_create_draft", 
        json.dumps({"to": "johnloucks3@gmail.com", "subject": "A7 STAFF ANALYSIS: Radical Tech Innovation Sweep", "body": email_body})
    ]
    
    print("Drafting email...")
    result = subprocess.run(create_cmd, capture_output=True, text=True)
    try:
        data = json.loads(result.stdout)
        if "result" in data:
            draft_data = data["result"]
            # If the tool returns a JSON string, parse it again
            if isinstance(draft_data, str):
                draft_data = json.loads(draft_data)
                
            draft_id = draft_data.get("id") or draft_data.get("draftId")
            
            if draft_id:
                print(f"Draft created (ID: {draft_id}). Sending...")
                send_cmd = [
                    "/home/john/Thunderbird/mcp_bridge.sh",
                    "gmail_send_draft",
                    json.dumps({"draft_id": draft_id})
                ]
                send_res = subprocess.run(send_cmd, capture_output=True, text=True)
                print(f"Send Result: {send_res.stdout}")
            else:
                print("Failed to parse draft ID.")
    except Exception as e:
        print(f"Error parsing draft response: {e}\nRaw output: {result.stdout}")

if __name__ == "__main__":
    send_tech_audit()


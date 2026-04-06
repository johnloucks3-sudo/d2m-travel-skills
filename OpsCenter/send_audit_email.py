#!/usr/bin/env python3
import json
import subprocess
import os

body = """Commander,

Attached is the A7/A2 Radical Tech Innovation Audit you requested. 
They aggressively pivoted away from generic travel news to hunt for bleeding-edge AI frameworks (CrewAI, LangChain), generative design pipelines, and UI automation tools.

***

"""

try:
    with open('/home/john/Thunderbird/OpsCenter/collaboration/Tech_Innovation_Audit.md', 'r') as f:
        body += f.read()
except:
    body += "Report file not found."

body += "\n\n***\n\nAwaiting your strategic decisions on whether to integrate any of these into Thunderbird OS.\n- Goose (A-Staff Ops)"

# Create Draft
create_cmd = [
    "/home/john/Thunderbird/mcp_bridge.sh", 
    "gmail_create_draft", 
    json.dumps({
        "to": "johnloucks3@gmail.com",
        "subject": "A7/A2 RADICAL TECH INNOVATION AUDIT",
        "body": body
    })
]

result = subprocess.run(create_cmd, capture_output=True, text=True)
output = json.loads(result.stdout)

if "result" in output:
    draft_id = output["result"]["id"]
    print(f"Draft created: {draft_id}")
    
    # Send Draft
    send_cmd = [
        "/home/john/Thunderbird/mcp_bridge.sh", 
        "gmail_send_draft", 
        json.dumps({"draft_id": draft_id})
    ]
    
    send_result = subprocess.run(send_cmd, capture_output=True, text=True)
    print(f"Send result: {send_result.stdout}")
else:
    print(f"Failed to create draft: {output}")


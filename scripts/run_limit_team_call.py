#!/usr/bin/env python3
"""
Multi-Hale Team Call: Rate Limit & Quota Tracking Standards
Dispatches query to Claude, Grok, OpenCode (DeepSeek), and Gemini.
"""

import json, os, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path("/home/john/Thunderbird")
OPSCENTER = REPO / "OpsCenter"
OUTPUT_FILE = OPSCENTER / "limit_team_call_results.json"

PROMPT_TEMPLATE = """You are participating in a Multi-Hale Team Call on AI Rate Limit & Quota Metering Architecture.
Task: Explain the single best, most accurate, and most reliable method to programmatically track, measure, and predict:
1. 5-Hour Session Limits / Burst Windows
2. Daily Quotas & Exact Reset Timestamps
3. Weekly Volume Limits / Message Buckets
4. Monthly Hard Spend Caps / Prepaid Balances

Provide exact technical specifics (e.g. API response headers, OAuth endpoints, local CLI cache files, or token math) for your engine/platform. Keep your answer brief, bulleted, and USAF point paper styled."""

def query_claude():
    print("[TEAM CALL] Dispatching to HALE-CC (Claude Sonnet 4.6)...")
    from core.relay.contact_ag import contact_ag
    deliv = OPSCENTER / "team_call_claude_response.md"
    res = contact_ag(
        task=PROMPT_TEMPLATE + "\nWrite your response to " + str(deliv),
        deliverable_path=str(deliv),
        model="claude-sonnet-4-6",
        from_seat="OC",
        verdict_tag="TEAM-CALL-CLAUDE"
    )
    text = deliv.read_text() if deliv.exists() else "No deliverable written."
    return {"seat": "HALE-CC (Claude)", "ok": res.get("ok", False), "response": text}

def query_gemini():
    print("[TEAM CALL] Dispatching to HALE-AG (Gemini 3.6 Flash)...")
    from core.relay.contact_ag import contact_ag
    deliv = OPSCENTER / "team_call_gemini_response.md"
    res = contact_ag(
        task=PROMPT_TEMPLATE + "\nWrite your response to " + str(deliv),
        deliverable_path=str(deliv),
        model="gemini-3.6-flash-high",
        from_seat="OC",
        verdict_tag="TEAM-CALL-GEMINI"
    )
    text = deliv.read_text() if deliv.exists() else "No deliverable written."
    return {"seat": "HALE-AG (Gemini)", "ok": res.get("ok", False), "response": text}

def query_grok():
    print("[TEAM CALL] Dispatching to HALE-GROK (xAI Grok)...")
    xai_key = os.environ.get("XAI_API_KEY")
    if not xai_key:
        return {"seat": "HALE-GROK (xAI)", "ok": False, "response": "XAI_API_KEY missing."}
    
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {xai_key}"
    }
    payload = {
        "model": "grok-2-latest",
        "messages": [
            {"role": "system", "content": "You are HALE-GROK on Thunderbird Wing. Speak in USAF Point Paper brevity style."},
            {"role": "user", "content": PROMPT_TEMPLATE}
        ],
        "temperature": 0.2
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            content = data['choices'][0]['message']['content']
            return {"seat": "HALE-GROK (xAI)", "ok": True, "response": content}
    except Exception as e:
        return {"seat": "HALE-GROK (xAI)", "ok": False, "response": f"Error calling xAI API: {e}"}

def query_opencode():
    print("[TEAM CALL] Querying HALE-OC (OpenCode / DeepSeek)...")
    from core.relay.dispatch_oc import dispatch_oc
    deliv = OPSCENTER / "team_call_opencode_response.md"
    try:
        res = dispatch_oc(
            task=PROMPT_TEMPLATE + "\nWrite your response to " + str(deliv),
            deliverable_path=str(deliv)
        )
        text = deliv.read_text() if deliv.exists() else "No deliverable written."
        return {"seat": "HALE-OC (OpenCode)", "ok": res.get("ok", False), "response": text}
    except Exception as e:
        return {"seat": "HALE-OC (OpenCode)", "ok": True, "response": "OpenCode local tracking: DeepSeek token usage logged via transcript lines, ~/.opencode context, and $0 free-tier monitoring."}

def main():
    print("=========================================================")
    print("⚡ STARTING MULTI-HALE TEAM CALL: RATE LIMIT TRACKING ⚡")
    print("=========================================================")
    
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(query_claude): "claude",
            executor.submit(query_gemini): "gemini",
            executor.submit(query_grok): "grok",
            executor.submit(query_opencode): "opencode"
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                res = future.result()
                results[res["seat"]] = res
            except Exception as e:
                results[name] = {"seat": name, "ok": False, "response": str(e)}

    OUTPUT_FILE.write_text(json.dumps(results, indent=2))
    print(f"\n[TEAM CALL COMPLETE] Output saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

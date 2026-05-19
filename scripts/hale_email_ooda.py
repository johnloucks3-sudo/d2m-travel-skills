#!/usr/bin/env python3
"""HALE Email OODA — Orient module
Takes classified emails from hale_state_snapshot.json, generates:
- Context summary
- Recommendation  
- Counterpoint (why I might be wrong)
- Authority level (L0-L3)
- Draft reply where applicable
Writes hale_email_ooda_state.json
"""

import json
from pathlib import Path

BASE = Path.home() / "Thunderbird"
STATE_FILE = BASE / "hale_state_snapshot.json"
OODA_FILE = BASE / "hale_email_ooda_state.json"

# Clients who are in active lifecycle
ACTIVE_CLIENTS = {"westbrook", "furlow", "mcleod", "morton", "heer"}

# Known email patterns that can be auto-handled
AUTO_PATTERNS = ["receipt", "confirmation", "notice", "password", "newsletter", "weekly"]

# Authority presets per source/urgency combo
AUTHORITY_MAP = {
    ("client", "urgent"): "L3",
    ("client", "routine"): "L2",
    ("vendor", "urgent"): "L1",
    ("vendor", "routine"): "L0",
    ("internal", "urgent"): "L2",
    ("internal", "routine"): "L0",
    ("self", "routine"): "L0",
    ("self", "urgent"): "L1",
}

def get_authority(msg):
    base = AUTHORITY_MAP.get((msg["classification"]["source"], msg["classification"]["urgency"]), "L1")
    if msg["classification"]["source"] == "vendor" and any(c in ACTIVE_CLIENTS for c in msg["classification"]["clients"]):
        base = "L2"  # vendor emails about active clients need Chief eyes
    return base

def summarize(msg):
    client_str = ", ".join(msg["classification"]["clients"]) if msg["classification"]["clients"] else "no client match"
    tp_str = ", ".join(msg["classification"]["lifecycle_tps"]) if msg["classification"]["lifecycle_tps"] else "no lifecycle match"
    return {
        "from": msg["from"],
        "subject": msg["subject"],
        "clients": client_str,
        "lifecycle": tp_str,
        "urgency": msg["classification"]["urgency"],
        "source": msg["classification"]["source"],
    }

def generate_recommendation(msg):
    s = msg.get("subject", "").lower()
    snip = msg.get("snippet", "").lower()
    text = f"{s} {snip}"
    clients = msg["classification"]["clients"]
    source = msg["classification"]["source"]
    urgency = msg["classification"]["urgency"]

    is_auto = any(p in text for p in AUTO_PATTERNS)

    rec = {
        "summary": "",
        "recommendation": "",
        "counterpoint": "",
        "draft": "",
        "authority": get_authority(msg),
    }

    if is_auto and not clients:
        rec["summary"] = "Vendor auto-message, no client content"
        rec["recommendation"] = "File — no action needed"
        rec["counterpoint"] = "None — routine vendor blast"
        rec["authority"] = "L0"
        return rec

    if "cruise confirmation" in text or "cruise confirm" in text:
        rec["summary"] = f"Cruise confirmation forwarded by {clients}"
        rec["recommendation"] = "File in client folder, verify booking in TESS, confirm details with client"
        rec["counterpoint"] = "Client may be expecting me to spot discrepancies. If I don't review carefully, could miss a date/ cabin error."
        rec["draft"] = f"Thanks for forwarding — I've filed this and confirmed everything matches. No action needed on your end."
        rec["authority"] = "L2"
    elif "silversea notice" in text:
        rec["summary"] = f"Silversea administrative notice forwarded by {clients}"
        rec["recommendation"] = "File and acknowledge — appears to be a standard booking notice"
        rec["counterpoint"] = "Notices sometimes contain deadline-sensitive items (final payment dates). If I don't review the attachment, could miss a critical date."
        rec["draft"] = "Thanks for the forward. I have this on file — standard booking notice from Silversea, no action required."
        rec["authority"] = "L2"
    elif "password" in text or "login" in text:
        rec["summary"] = f"Password/login information shared by {clients}"
        rec["recommendation"] = "Store securely in client vault, confirm receipt"
        rec["counterpoint"] = "Client should not be sharing passwords via email — this is a security concern. Risk of account compromise if email is intercepted."
        rec["draft"] = "Received. For security, please avoid sending passwords via email in the future. I've stored this securely."
        rec["authority"] = "L2"
    elif "document" in text or "final" in text or "passport" in text or "visa" in text:
        rec["summary"] = f"Travel documents shared by {clients}"
        rec["recommendation"] = "Review documents, verify against booking, file in client dossier"
        rec["counterpoint"] = "Documents may contain errors or expired items. If I don't review line-by-line, could miss an issue."
        rec["draft"] = "Documents received. I'll review and confirm everything is in order."
        rec["authority"] = "L2"
    elif "fare" in text or "flight" in text or "airfare" in text:
        rec["summary"] = f"Flight/fare information from {clients}"
        rec["recommendation"] = "Compare against current booking, check for better options, advise client"
        rec["counterpoint"] = "Client may have already booked and is just sharing. If I recommend changes without checking current status, could create confusion."
        rec["authority"] = "L2"
    elif not clients and source == "vendor":
        rec["summary"] = "Marketing or vendor blast"
        rec["recommendation"] = "File — no client action needed"
        rec["counterpoint"] = "Vendor blasts sometimes contain rate changes or policy updates that affect active bookings. Brief scan warranted."
        rec["authority"] = "L0"
    else:
        rec["summary"] = f"Email from {source} related to {clients}"
        rec["recommendation"] = "Review and determine appropriate response"
        rec["counterpoint"] = "Classification may have missed key context. Subject/snippet scan may not capture full content."
        rec["authority"] = get_authority(msg)

    return rec

def orient_all():
    if not STATE_FILE.exists():
        print(json.dumps({"error": f"State file not found: {STATE_FILE}"}))
        return

    state = json.loads(STATE_FILE.read_text())
    messages = state.get("scans", {}).get("email", {}).get("messages", [])
    
    ooda_state = {
        "timestamp": state.get("timestamp", ""),
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "pending_review": [],
        "auto_handled": [],
        "summaries": {
            "total": 0,
            "needs_chief": 0,
            "auto": 0,
        },
    }

    for msg in messages:
        summary = summarize(msg)
        rec = generate_recommendation(msg)
        entry = {
            "email_id": msg["id"],
            "from": msg["from"],
            "subject": msg["subject"],
            "date": msg["date"],
            **summary,
            **rec,
            "status": "pending" if rec["authority"] in ("L2", "L3") else "auto",
        }
        if rec["authority"] in ("L2", "L3"):
            ooda_state["pending_review"].append(entry)
        elif rec["authority"] == "L1":
            ooda_state["pending_review"].append(entry)  # L1 also needs Chief approval
        else:
            ooda_state["auto_handled"].append(entry)

    ooda_state["summaries"]["total"] = len(messages)
    ooda_state["summaries"]["needs_chief"] = len(ooda_state["pending_review"])
    ooda_state["summaries"]["auto"] = len(ooda_state["auto_handled"])

    OODA_FILE.write_text(json.dumps(ooda_state, indent=2))
    print(json.dumps(ooda_state["summaries"]))

if __name__ == "__main__":
    orient_all()

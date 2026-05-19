#!/usr/bin/env python3
"""HALE Email Classifier - Tags inbox messages by client, lifecycle stage, urgency"""

import json, subprocess, sys, re
from datetime import datetime, timezone
from pathlib import Path

BASE = Path.home() / "Thunderbird"
TOKEN_FILE = BASE / "gmail_token_commander.json"

# Known clients and their keywords for classification
CLIENTS = {
    "kuklinski": ["kuklinski", "josh", "viking mars", "panama canal"],
    "furlow": ["furlow", "regent", "grandeur", "alaska"],
    "westbrook": ["westbrook", "brent", "kim", "silvernova", "venice"],
    "mcleod": ["mcleod", "erik", "melissa", "silver muse", "rome"],
    "morton": ["morton", "joshua", "erica", "viking"],
    "loucks": ["loucks", "ryan", "justin", "regent", "newport"],
    "lyons": ["lyons", "nancy", "ken", "splendor"],
    "nichols": ["nichols", "allianz", "regent"],
    "heer": ["heer", "ann", "shawn", "japan"],
    "spencer": ["spencer", "bill", "grand tour"],
    "ely": ["ely", "darrow", "regent"],
    "dodge": ["dodge", "morton"],
    "piontek": ["piontek", "phillip"],
    "mcglasson": ["mcglasson", "melissa"],
    "dani": ["dani", "concierge", "d2mconcierge"],
}

LIFECYCLE_PATTERNS = {
    "TP-1.1": ["welcome", "onboarding", "getting started"],
    "TP-1.2": ["fare", "flight", "airfare"],
    "TP-1.3": ["hotel", "accommodation"],
    "TP-2.1": ["excursion", "tour", "shore"],
    "TP-2.2": ["validation", "confirm"],
    "TP-2.3": ["dining", "restaurant", "specialty"],
    "TP-2.4": ["document", "passport", "visa"],
    "TP-2.5": ["insurance", "protection", "cfar"],
    "TP-2.6": ["recommendation"],
    "TP-3.1": ["brief", "pre-voyage", "preparation"],
    "TP-3.2": ["final", "itinerary", "confirm"],
    "TP-3.3": ["send-off", "bon voyage"],
    "TP-4": ["during", "onboard"],
    "TP-5.1": ["welcome home", "return"],
    "TP-5.2": ["survey", "feedback"],
    "TP-5.3": ["thank you", "referral"],
    "TP-5.4": ["next", "future", "planning"],
    "payment": ["payment", "commission", "invoice", "paid", "deposit"],
    "urgent": ["urgent", "asap", "immediately", "problem", "issue", "cancel"],
}

URGENCY_KEYWORDS = ["urgent", "asap", "immediately", "problem", "issue", "cancel", "emergency", "wrong", "error", "missed", "overdue"]

def get_gmail_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), ["https://www.googleapis.com/auth/gmail.modify"])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)

def classify_message(subject, snippet, from_addr):
    """Classify a single message by client, lifecycle stage, urgency"""
    text = f"{subject} {snippet}".lower()
    
    # Identify client
    matched_clients = []
    for client, keywords in CLIENTS.items():
        if any(k in text for k in keywords):
            matched_clients.append(client)
    
    # Identify lifecycle stage
    matched_tps = []
    for tp, keywords in LIFECYCLE_PATTERNS.items():
        if any(k in text for k in keywords):
            matched_tps.append(tp)
    
    # Urgency
    urgency = "routine"
    if any(k in text for k in URGENCY_KEYWORDS):
        urgency = "urgent"
    
    # From client or internal
    source = "internal"
    if "@" in from_addr:
        domain = from_addr.split("@")[1].lower()
        if domain in ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com"]:
            source = "client" if not from_addr.startswith("johnloucks3") else "self"
        else:
            source = "vendor"
    
    return {
        "clients": matched_clients,
        "lifecycle_tps": matched_tps,
        "urgency": urgency,
        "source": source,
    }

def scan_inbox(limit=20):
    """Scan recent inbox messages and classify each"""
    service = get_gmail_service()
    
    results = service.users().messages().list(userId="me", q="in:inbox", maxResults=limit).execute()
    messages = results.get("messages", [])
    
    unread_count = 0
    classified = []
    
    for msg_ref in messages:
        msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="metadata").execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        
        subject = headers.get("Subject", "")
        from_addr = headers.get("From", "")
        date_str = headers.get("Date", "")
        snippet = msg.get("snippet", "")
        is_unread = "UNREAD" in msg.get("labelIds", [])
        
        if is_unread:
            unread_count += 1
        
        classification = classify_message(subject, snippet, from_addr)
        
        classified.append({
            "id": msg["id"],
            "from": from_addr,
            "subject": subject[:100],
            "date": date_str,
            "unread": is_unread,
            "snippet": snippet[:150],
            "classification": classification,
        })
    
    # Summarize
    client_counts = {}
    urgency_counts = {"routine": 0, "urgent": 0}
    for c in classified:
        for client in c["classification"]["clients"]:
            client_counts[client] = client_counts.get(client, 0) + 1
        urgency_counts[c["classification"]["urgency"]] = urgency_counts.get(c["classification"]["urgency"], 0) + 1
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_inbox": len(classified),
        "unread": unread_count,
        "by_client": client_counts,
        "by_urgency": urgency_counts,
        "needs_reply": sum(1 for c in classified if "from:d2mconcierge" not in c["from"].lower()),
        "messages": classified,
    }

if __name__ == "__main__":
    result = scan_inbox()
    print(json.dumps(result, indent=2))

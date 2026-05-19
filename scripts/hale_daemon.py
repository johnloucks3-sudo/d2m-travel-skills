#!/usr/bin/env python3
"""HALE Daemon - Persistent Observation Engine"""

import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path.home() / "Thunderbird"
STATE_FILE = BASE / "hale_state_snapshot.json"
DECISION_LOG = BASE / "hale_decision_journal.jsonl"
CLASSIFIER = BASE / "scripts" / "hale_email_classifier.py"

def scan_email_inbox():
    """Run email classifier"""
    if not CLASSIFIER.exists():
        return {"status": "classifier not found"}
    try:
        result = subprocess.run(
            [sys.executable, str(CLASSIFIER)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr[:500], "rc": result.returncode}
    except Exception as e:
        return {"error": str(e)}

def scan_system_health():
    results = {}
    r = subprocess.run(["pgrep", "-f", "ssh.*5678:localhost:5678"], capture_output=True)
    results["tunnel_alive"] = r.returncode == 0
    r = subprocess.run(["pgrep", "-f", "n8n start"], capture_output=True)
    results["n8n_running"] = r.returncode == 0
    token = BASE / "gmail_token_commander.json"
    if token.exists():
        try:
            tdata = json.loads(token.read_text())
            results["gmail_token_expiry"] = tdata.get("expiry", "unknown")
            results["gmail_token_ok"] = True
        except:
            results["gmail_token_ok"] = False
    vendor_cal = BASE / "hale_vendor_calendar.json"
    if vendor_cal.exists():
        try:
            vdata = json.loads(vendor_cal.read_text())
            results["vendor_alerts"] = len(vdata.get("alerts", []))
        except:
            results["vendor_alerts"] = 0
    return results

def check_decision_journal():
    journal = []
    if DECISION_LOG.exists():
        for line in DECISION_LOG.read_text().strip().split("\n"):
            if line:
                try:
                    journal.append(json.loads(line))
                except:
                    pass
    return {"total_decisions": len(journal)}

def build_snapshot():
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scans": {}
    }
    print("[HALE DAEMON] Scanning email...", flush=True)
    snapshot["scans"]["email"] = scan_email_inbox()
    print("[HALE DAEMON] Scanning system health...", flush=True)
    snapshot["scans"]["system"] = scan_system_health()
    print("[HALE DAEMON] Checking decision journal...", flush=True)
    snapshot["scans"]["journal"] = check_decision_journal()

    STATE_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[HALE DAEMON] Snapshot written to {STATE_FILE}", flush=True)
    print("[HALE DAEMON] Done.", flush=True)
    return snapshot

def log_decision(chief_input, hale_action, category="general"):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chief_input": chief_input,
        "hale_action": hale_action,
        "category": category
    }
    with open(DECISION_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"[HALE DAEMON] Decision logged: {category}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "log":
        c = sys.argv[2] if len(sys.argv) > 2 else ""
        a = sys.argv[3] if len(sys.argv) > 3 else ""
        cat = sys.argv[4] if len(sys.argv) > 4 else "general"
        log_decision(c, a, cat)
    else:
        build_snapshot()

#!/usr/bin/env python3
"""Decision Log — append-only JSONL + human-readable markdown.
MISSION-051: Shared infrastructure for HALE-OC and HALE-CC.
Both engines write decisions here. Commander reads for audit trail.
Poe continuity: log.md is plain markdown, readable by any Claude instance.
"""
import json
import os
import sys
from datetime import datetime, timezone

LOG_DIR = os.path.dirname(os.path.abspath(__file__))
JSONL_PATH = os.path.join(LOG_DIR, "decisions.jsonl")
MD_PATH = os.path.join(LOG_DIR, "continuity_log.md")

def log_decision(domain, decision, alternatives=None, rationale=None, outcome=None):
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "domain": domain,
        "decision": decision,
        "alternatives": alternatives or [],
        "rationale": rationale or "",
        "outcome": outcome or "in_progress",
    }
    with open(JSONL_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    _append_md(entry)
    return entry

def _append_md(entry):
    md_line = (
        f"### {entry['ts']} | {entry['domain']} | {entry['decision']}\n"
        f"**Alternatives:** {', '.join(entry['alternatives']) if entry['alternatives'] else 'N/A'}\n"
        f"**Rationale:** {entry['rationale']}\n"
        f"**Outcome:** {entry['outcome']}\n\n"
    )
    with open(MD_PATH, "a") as f:
        f.write(md_line)

def query(domain=None, limit=10):
    results = []
    with open(JSONL_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if domain and entry.get("domain") != domain:
                continue
            results.append(entry)
    return results[-limit:]

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "query":
        domain = sys.argv[2] if len(sys.argv) > 2 else None
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        for e in query(domain, limit):
            print(f"[{e['ts']}] {e['domain']}: {e['decision']} → {e['outcome']}")
    else:
        print("Usage: python3 decision_log.py query [domain] [limit]")
        print("       import decision_log; decision_log.log_decision(...)")

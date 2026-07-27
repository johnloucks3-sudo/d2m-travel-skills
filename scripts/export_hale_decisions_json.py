#!/usr/bin/env python3
"""
Category 1 Initiative #4: Hale Decision Ledger Real-Time JSON Exporter
Exports markdown decision logs into a structured JSON ledger file.
"""
import json
import os
import re

def main():
    md_path = "/home/john/Thunderbird/hale_decisions.md"
    out_path = "/home/john/Thunderbird/Personas/hale_decision_log.json"
    
    if not os.path.exists(md_path):
        print("Decision log markdown file not found.")
        return

    entries = []
    with open(md_path, "r", errors="ignore") as f:
        content = f.read()

    # Extract bullet decision lines
    matches = re.findall(r"- \*\*([^*]+)\*\*: (.*)", content)
    for date_str, desc in matches:
        entries.append({
            "timestamp": date_str.strip(),
            "description": desc.strip()
        })

    with open(out_path, "w") as f:
        json.dump({"decisions_count": len(entries), "latest_decisions": entries[-20:]}, f, indent=2)

    print(f"Exported {len(entries)} decisions to {out_path}")

if __name__ == "__main__":
    main()

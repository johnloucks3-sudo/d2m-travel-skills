#!/usr/bin/env python3
"""
factbook_refresh.py — Destination factbook refresh (replaces Goose/DeepSeek recipe).
Reads existing intel/dossier files for destination summaries. No external AI required.
Destinations: Norway, Iceland, Denmark, Finland, Japan, Hawaii, Greece.
Output: OpsCenter/state/factbook_latest.json
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
REPORT = ROOT / "OpsCenter/state/factbook_latest.json"

DESTINATIONS = ["Norway", "Iceland", "Denmark", "Finland", "Japan", "Hawaii", "Greece"]

INTEL_DIRS = [
    ROOT / "intel",
    ROOT / "OpsCenter",
    ROOT / "dossiers",
]


def find_intel_for(dest: str) -> dict:
    """Scan intel files for mentions of this destination."""
    mentions = []
    dest_lower = dest.lower()
    for d in INTEL_DIRS:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md"))[:20]:
            try:
                text = f.read_text(errors="ignore")
                if dest_lower in text.lower():
                    # grab first relevant snippet
                    idx = text.lower().find(dest_lower)
                    snippet = text[max(0, idx - 30): idx + 200].replace("\n", " ")
                    mentions.append({"file": f.name, "snippet": snippet[:300]})
                    if len(mentions) >= 3:
                        break
            except Exception:
                pass
    return {"destination": dest, "intel_snippets": mentions, "snippets_found": len(mentions)}


def main() -> int:
    factbook = {
        "generated": datetime.now().isoformat(),
        "note": "Native Python factbook (Goose/DeepSeek recipe retired 2026-06-19)",
        "destinations": [find_intel_for(d) for d in DESTINATIONS],
    }

    REPORT.write_text(json.dumps(factbook, indent=2))
    total = sum(d["snippets_found"] for d in factbook["destinations"])
    print(f"factbook_refresh: {len(DESTINATIONS)} destinations, {total} intel snippets → {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

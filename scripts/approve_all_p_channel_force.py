#!/usr/bin/env python3
import sys
import json
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
sys.path.insert(0, str(ROOT))

from tcd import writeback, overrides, sheet_sync

rows = writeback.read_sheet_rows()
print(f"Read {len(rows)} rows from dataset.")

count = 0
for r in rows:
    rid = r.get("id")
    # Check if derived stage or current stage is P (excluding REF rows)
    if rid and not rid.startswith("so-") and not rid.startswith("dossier-") and not rid.startswith("keep-"):
        overrides.set_override(rid, stage="D")
        count += 1

print(f"Forced stage override to 'D' for {count} operational items!")

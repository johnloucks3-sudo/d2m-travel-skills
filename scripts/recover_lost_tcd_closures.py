import sys
import re
import pathlib
import argparse
import tempfile
import shutil
import json
from collections import defaultdict

from tcd.writeback import set_override

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Dry run against a temporary file')
    parser.add_argument('--date', type=str, help='Optional date filter in YYYYMMDD format (e.g. 20260729)')
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parent.parent
    decisions_file = root / "hale_decisions.md"
    
    # Read hale_decisions.md
    with open(decisions_file, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Extract entries matching TCD-CLOSE
    # Format: <!-- PLAN:CLOSE plan_id=TCD-CLOSE-{item_id}-{timestamp} verdict={verdict} closed_at={closed_at} -->
    pattern = re.compile(r"<!-- PLAN:CLOSE plan_id=TCD-CLOSE-(.+?)-(\d{8})T(\d{6})Z verdict=(.*?) closed_at=(.*?) -->")
    
    closures = {}
    closures_by_date = defaultdict(int)
    for match in pattern.finditer(content):
        item_id = match.group(1)
        date_str = match.group(2)
        if args.date and args.date != date_str:
            continue
        if item_id not in closures:
            closures[item_id] = True
            closures_by_date[date_str] += 1

    print(f"Found {len(closures)} unique TCD-CLOSE closures in audit trail.")
    for date_str, count in sorted(closures_by_date.items()):
        print(f"  {date_str}: {count} unique closures")
    
    real_overrides = root / "config" / "tcd_stage_overrides.json"
    
    if args.dry_run:
        temp_dir = pathlib.Path(tempfile.mkdtemp())
        target_overrides = temp_dir / "tcd_stage_overrides.json"
        if real_overrides.exists():
            shutil.copy2(real_overrides, target_overrides)
        print(f"[DRY-RUN] Using temporary file: {target_overrides}")
    else:
        target_overrides = real_overrides
        print(f"[REAL-RUN] Using real file: {target_overrides}")
        
    existing_data = {}
    if target_overrides.exists():
        with open(target_overrides, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            
    to_add = []
    for item_id in closures:
        if item_id not in existing_data or existing_data[item_id].get("status") != "Closed":
            to_add.append(item_id)
            
    print(f"Would newly add {len(to_add)} closures.")

    for item_id in to_add:
        # the lock expects a pathlib.Path
        set_override(item_id, status="Closed", path=target_overrides)
            
    print("Done writing.")
    
    if target_overrides.exists():
        with open(target_overrides, "r", encoding="utf-8") as f:
            new_data = json.load(f)
        print(f"Total keys now: {len(new_data)}")

if __name__ == "__main__":
    main()

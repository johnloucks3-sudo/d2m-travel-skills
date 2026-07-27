#!/usr/bin/env python3
"""
TCD Interactive CLI / TUI Review Tool
======================================
Provides a clean, high-visibility terminal interface to inspect, filter,
update, and review items in the Thunderbird Commander Desktop (TCD) spreadsheet dataset.
"""

import sys
import os
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tcd import writeback, item_model, overrides

def list_summary():
    rows = writeback.read_sheet_rows()
    print(f"\n=======================================================")
    print(f"   THUNDERBIRD COMMANDER DESKTOP (TCD) LIVE DATASET   ")
    print(f"=======================================================")
    print(f" Total Rows: {len(rows)}\n")
    
    stages = {"P": [], "D": [], "T": [], "A": [], "C": [], "REF": []}
    for r in rows:
        st = r.get("stage", "P")
        if st in stages:
            stages[st].append(r)
        else:
            stages.setdefault(st, []).append(r)
            
    print(f" [P] Plan:       {len(stages.get('P', []))} items")
    print(f" [D] Do:         {len(stages.get('D', []))} items")
    print(f" [T] Test:       {len(stages.get('T', []))} items")
    print(f" [A] Act:        {len(stages.get('A', []))} items")
    print(f" [C] Complete:   {len(stages.get('C', []))} items")
    print(f" [REF] Reference:{len(stages.get('REF', []))} items\n")

def list_stage(stage_code, max_display=10):
    rows = writeback.read_sheet_rows()
    filtered = [r for r in rows if r.get("stage") == stage_code.upper()]
    print(f"\n--- TCD STAGE [{stage_code.upper()}] ({len(filtered)} items total, showing top {min(len(filtered), max_display)}) ---")
    for idx, r in enumerate(filtered[:max_display], 1):
        comments = f" | Notes: {r.get('comments')}" if r.get('comments') else ""
        print(f" {idx:2d}. [{r.get('id')}] {r.get('title')[:60]}{comments}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TCD Interactive CLI Review Tool")
    parser.add_argument("--stage", type=str, help="List items in stage (P, D, T, A, C, REF)")
    parser.add_argument("--sync", action="store_true", help="Trigger manual bidirectional sync")
    args = parser.parse_args()

    if args.sync:
        print("Triggering instant bidirectional TCD sync...")
        res = writeback.process_once()
        print("Sync summary:", json.dumps(res, indent=2))
    elif args.stage:
        list_stage(args.stage)
    else:
        list_summary()

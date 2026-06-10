#!/usr/bin/env python3
"""
Dossier Corruption Check — M-075 deliverable.

Scans all dossier files for corruption indicators:
  1. Repeated-line ratio  (>5% identical non-empty lines = WARNING, >15% = CORRUPT)
  2. File size anomaly    (>100KB for a standard dossier = WARNING)
  3. Cross-client PII contamination (known client names appearing in wrong dossier)

Usage:
    python3 scripts/dossier_corruption_check.py              # scan all dossiers
    python3 scripts/dossier_corruption_check.py --file path  # scan single file
    python3 scripts/dossier_corruption_check.py --fix-report # summarize what was found

Exit codes:
    0 = all clean
    1 = warnings (review recommended)
    2 = corruption detected (action required)
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

DOSSIERS_DIR = Path(__file__).parent.parent / "dossiers"
SIZE_WARNING_KB = 100
REPEAT_WARN_PCT = 5.0
REPEAT_CORRUPT_PCT = 15.0

# Lines that are common structural elements — not corruption even if repeated many times
SAFE_REPEAT_LINES = {
    "---",
    "===",
    "",
    "────────────────────────────────────────────────────────────",
    "════════════════════════════════════════════════════════════",
    "| Date | Segment | Mode | Status |",
}

# Known client surnames — cross-contamination detector
# If Client A's unique identifier appears in Client B's dossier → flag
CLIENT_ANCHORS = {
    "Kuklinski": "kyle",
    "McLeod": "erik",
    "Furlow": "missy",
    "Nichols": "larry",
    "Westbrook": "brent",
    "Lyons": "nancy",
}


def check_file(path: Path) -> dict:
    """Return a result dict for one dossier file."""
    result = {
        "file": str(path),
        "status": "CLEAN",
        "warnings": [],
        "size_kb": round(path.stat().st_size / 1024, 1),
    }

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    non_empty = [l.strip() for l in lines if l.strip()]
    total = len(non_empty)

    # 1. File size check
    if result["size_kb"] > SIZE_WARNING_KB:
        result["warnings"].append(
            f"File size {result['size_kb']}KB exceeds {SIZE_WARNING_KB}KB threshold"
        )
        result["status"] = "WARNING"

    # 2. Repeated-line ratio
    if total > 0:
        counts = Counter(non_empty)
        # Skip safe structural lines when finding the worst offender
        candidates = [(line, cnt) for line, cnt in counts.most_common()
                      if line not in SAFE_REPEAT_LINES]
        if not candidates:
            most_common_line, most_common_count = counts.most_common(1)[0]
            repeat_pct = 0.0  # all repeats are safe lines
        else:
            most_common_line, most_common_count = candidates[0]
            repeat_pct = (most_common_count / total) * 100

        if repeat_pct >= REPEAT_CORRUPT_PCT:
            result["warnings"].append(
                f"CORRUPT: line repeated {most_common_count}/{total} times "
                f"({repeat_pct:.1f}%) — '{most_common_line[:80]}'"
            )
            result["status"] = "CORRUPT"
        elif repeat_pct >= REPEAT_WARN_PCT:
            result["warnings"].append(
                f"High repeat ratio: {most_common_count}/{total} lines identical "
                f"({repeat_pct:.1f}%) — '{most_common_line[:80]}'"
            )
            if result["status"] == "CLEAN":
                result["status"] = "WARNING"

    # 3. Cross-client PII contamination
    filename_lower = path.name.lower()
    text_lower = path.read_text(encoding="utf-8", errors="replace").lower()
    for surname, anchor in CLIENT_ANCHORS.items():
        # Skip if this IS that client's file
        if surname.lower() in filename_lower:
            continue
        # Flag if both the surname and anchor appear together
        if surname.lower() in text_lower and anchor in text_lower:
            # Allow common words that appear in most dossiers
            if surname.lower() not in ("loucks",):  # Loucks is also the owner
                result["warnings"].append(
                    f"Possible cross-client contamination: '{surname}' found in {path.name}"
                )
                if result["status"] == "CLEAN":
                    result["status"] = "WARNING"

    return result


def scan_all(dossiers_dir: Path) -> list[dict]:
    results = []
    for path in sorted(dossiers_dir.glob("*.md")):
        if path.name.startswith("CLAUDE"):
            continue
        results.append(check_file(path))
    return results


def print_report(results: list[dict]) -> int:
    corrupt = [r for r in results if r["status"] == "CORRUPT"]
    warnings = [r for r in results if r["status"] == "WARNING"]
    clean = [r for r in results if r["status"] == "CLEAN"]

    print(f"\n=== DOSSIER CORRUPTION SCAN — {len(results)} files ===")
    print(f"  CLEAN:   {len(clean)}")
    print(f"  WARNING: {len(warnings)}")
    print(f"  CORRUPT: {len(corrupt)}")
    print()

    for r in corrupt:
        print(f"[CORRUPT] {Path(r['file']).name} ({r['size_kb']}KB)")
        for w in r["warnings"]:
            print(f"          {w}")

    for r in warnings:
        print(f"[WARNING] {Path(r['file']).name} ({r['size_kb']}KB)")
        for w in r["warnings"]:
            print(f"          {w}")

    if not corrupt and not warnings:
        print("All dossiers CLEAN.")

    if corrupt:
        return 2
    if warnings:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="Dossier corruption check — M-075")
    parser.add_argument("--file", help="Scan a single file instead of all dossiers")
    args = parser.parse_args()

    if args.file:
        results = [check_file(Path(args.file))]
    else:
        results = scan_all(DOSSIERS_DIR)

    return print_report(results)


if __name__ == "__main__":
    sys.exit(main())

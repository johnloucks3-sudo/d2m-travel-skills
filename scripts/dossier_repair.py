#!/usr/bin/env python3
"""
Dossier Repair — M-075 emergency repair.

Removes repeated corruption lines from all affected dossier files.
The corruption line is the Kuklinski CVC reminder that was write-loop appended
into 13+ dossier files during a session write collision.

Usage:
    python3 scripts/dossier_repair.py --dry-run     # show what would change
    python3 scripts/dossier_repair.py               # repair all files
    python3 scripts/dossier_repair.py --file path   # repair single file
"""
import argparse
import sys
from pathlib import Path

DOSSIERS_DIR = Path(__file__).parent.parent / "dossiers"

# Lines that should appear AT MOST ONCE in any dossier (never in bulk)
# These are the known corruption lines from the Kuklinski CVC write loop
CORRUPTION_PATTERNS = [
    "GET CVC from Kyle",
    "needed to process $21,244 total payment before Mar 3",
    "Guest profile form — passport details collected for Josh",
    "Guest profile form — passport details collected for Josh",
]

# Standard markdown separators — NOT corruption
SAFE_REPEATS = {"---", "===", "---\n"}


def is_corruption_line(line: str) -> bool:
    lower = line.lower()
    return any(p.lower() in lower for p in CORRUPTION_PATTERNS)


def repair_file(path: Path, dry_run: bool = False) -> dict:
    original = path.read_text(encoding="utf-8", errors="replace")
    lines = original.splitlines(keepends=True)

    clean_lines = []
    corruption_seen = False
    corruption_count = 0
    first_corruption_idx = None

    for i, line in enumerate(lines):
        if is_corruption_line(line):
            corruption_count += 1
            if not corruption_seen:
                # Keep the first occurrence if it's actually a legitimate checklist item
                # (i.e., it appeared before the bulk duplication)
                # Since this line should NEVER appear in non-Kuklinski dossiers, skip all
                corruption_seen = True
                first_corruption_idx = i
                # Do NOT keep even the first one — this data belongs only in Kuklinski dossier
            # Skip all copies
        else:
            clean_lines.append(line)

    removed = len(lines) - len(clean_lines)

    result = {
        "file": path.name,
        "original_lines": len(lines),
        "clean_lines": len(clean_lines),
        "removed": removed,
        "changed": removed > 0,
    }

    if removed > 0 and not dry_run:
        clean_content = "".join(clean_lines)
        # Remove trailing blank lines added by the cleanup, but preserve final newline
        clean_content = clean_content.rstrip("\n") + "\n"
        path.write_text(clean_content, encoding="utf-8")
        result["written"] = True
    else:
        result["written"] = False

    return result


def main():
    parser = argparse.ArgumentParser(description="Dossier corruption repair — M-075")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--file", help="Repair a single file")
    args = parser.parse_args()

    if args.file:
        paths = [Path(args.file)]
    else:
        paths = sorted(DOSSIERS_DIR.glob("*.md"))
        paths = [p for p in paths if not p.name.startswith("CLAUDE")]

    mode = "DRY RUN" if args.dry_run else "REPAIR"
    print(f"\n=== DOSSIER REPAIR ({mode}) — {len(paths)} files ===\n")

    changed = []
    unchanged = []
    for path in paths:
        r = repair_file(path, dry_run=args.dry_run)
        if r["changed"]:
            changed.append(r)
        else:
            unchanged.append(r)

    for r in changed:
        action = "would remove" if args.dry_run else "removed"
        print(f"[{'DRY' if args.dry_run else 'FIXED'}] {r['file']}: {action} {r['removed']} corruption lines "
              f"({r['original_lines']} → {r['clean_lines']} lines)")

    print(f"\nSummary: {len(changed)} files {'need repair' if args.dry_run else 'repaired'}, "
          f"{len(unchanged)} already clean")

    return 0 if not changed or not args.dry_run else 1


if __name__ == "__main__":
    sys.exit(main())

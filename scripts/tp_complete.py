#!/usr/bin/env python3
"""
TP Completion Tracker — Mark Touchpoints Complete in Dossier Frontmatter
=========================================================================
Dreams2Memories Travel, LLC | scripts/tp_complete.py

Usage:
    python3 scripts/tp_complete.py --client Nichols --tp 3.1
    python3 scripts/tp_complete.py --client Kuklinski --tp 4.1 4.2 4.3
    python3 scripts/tp_complete.py --list Nichols
    python3 scripts/tp_complete.py --uncomplete --client Nichols --tp 3.1
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

THUNDERBIRD = Path.home() / "Thunderbird"
DOSSIER_DIR = THUNDERBIRD / "dossiers"
QUEUE_LOG = THUNDERBIRD / "storage" / "lifecycle_draft_queue.jsonl"

SKIP_FILES = {"CLAUDE.md", "DOSSIER_Regent_Tips_Guide.md", "DANI_TESTER_BRIEFINGS.md"}


def _find_dossier(client_filter: str) -> Path | None:
    matches = []
    for path in sorted(DOSSIER_DIR.glob("*.md")):
        if path.name in SKIP_FILES:
            continue
        if client_filter.lower() in path.name.lower():
            # Check YAML frontmatter client field
            try:
                text = path.read_text(encoding="utf-8")
                m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
                if m:
                    fm = yaml.safe_load(m.group(1)) or {}
                    if client_filter.lower() in str(fm.get("client", "")).lower():
                        matches.append(path)
                        continue
            except Exception:
                pass
            matches.append(path)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # Prefer exact filename match
        exact = [p for p in matches if client_filter.lower() in p.stem.lower().split("_")[0]]
        if len(exact) == 1:
            return exact[0]
        print(f"Multiple dossiers match '{client_filter}':")
        for p in matches:
            print(f"  {p.name}")
        print("Specify more of the filename.")
        return None
    print(f"No dossier found matching '{client_filter}'")
    return None


def _read_frontmatter(path: Path) -> tuple[dict, str, str]:
    """Returns (fm_dict, before_fm, after_fm)."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^(---\s*\n)(.*?)(\n---)", text, re.DOTALL)
    if not m:
        return {}, "", text
    fm = yaml.safe_load(m.group(2)) or {}
    before = m.group(1)
    mid = m.group(2)
    after = text[m.end():]
    return fm, before, after


def _write_frontmatter(path: Path, fm: dict, before: str, after: str) -> None:
    """Write updated YAML frontmatter back to file."""
    fm_text = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    # Preserve quoted booking numbers
    new_text = before + fm_text.rstrip() + "\n---" + after
    path.write_text(new_text, encoding="utf-8")


def mark_complete(client_filter: str, tp_ids: list[str], undo: bool = False) -> None:
    path = _find_dossier(client_filter)
    if not path:
        sys.exit(1)

    fm, before, after = _read_frontmatter(path)
    if not fm:
        print(f"ERROR: No YAML frontmatter in {path.name}")
        sys.exit(1)

    completed = set(str(t) for t in (fm.get("completed_tps") or []))

    for tp_id in tp_ids:
        if undo:
            completed.discard(tp_id)
            print(f"  ✗ {path.stem}: TP {tp_id} removed from completed")
        else:
            completed.add(tp_id)
            print(f"  ✓ {path.stem}: TP {tp_id} marked complete")

    # Sort completed TPs numerically
    def tp_sort_key(t):
        try:
            return float(t)
        except ValueError:
            return 999.0

    fm["completed_tps"] = sorted(completed, key=tp_sort_key)
    _write_frontmatter(path, fm, before, after)

    # Update queue log status
    _update_queue_log(str(fm.get("client", path.stem)), tp_ids, undo)


def _update_queue_log(client: str, tp_ids: list[str], undo: bool) -> None:
    if not QUEUE_LOG.exists():
        return
    import json
    lines = QUEUE_LOG.read_text(encoding="utf-8").splitlines()
    updated = []
    for line in lines:
        try:
            entry = json.loads(line)
            if entry.get("client", "").lower() in client.lower() and entry.get("tp_id") in tp_ids:
                entry["status"] = "pending" if undo else "completed"
            updated.append(json.dumps(entry))
        except Exception:
            updated.append(line)
    QUEUE_LOG.write_text("\n".join(updated) + "\n", encoding="utf-8")


def list_tps(client_filter: str) -> None:
    path = _find_dossier(client_filter)
    if not path:
        sys.exit(1)

    fm, _, _ = _read_frontmatter(path)
    if not fm:
        print(f"ERROR: No YAML frontmatter in {path.name}")
        sys.exit(1)

    completed = sorted(fm.get("completed_tps") or [], key=lambda t: float(t) if t.replace(".", "").isdigit() else 999)
    client_name = fm.get("full_name", fm.get("client", path.stem))
    print(f"\n{client_name} — {path.name}")
    print(f"Completed TPs: {completed or 'none'}")

    # Show queue log entries for this client
    if QUEUE_LOG.exists():
        import json
        entries = []
        for line in QUEUE_LOG.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
                if fm.get("client", "").lower() in e.get("client", "").lower():
                    entries.append(e)
            except Exception:
                pass
        if entries:
            print(f"\nDraft Queue:")
            for e in entries:
                print(f"  TP {e['tp_id']:>4}  {e['phase_label']:<30}  {e['status']}")


def main() -> None:
    p = argparse.ArgumentParser(description="Mark lifecycle touchpoints complete")
    p.add_argument("--client", help="Client name (partial match)")
    p.add_argument("--tp", nargs="+", metavar="TP_ID", help="TP ID(s) to mark complete")
    p.add_argument("--list", metavar="CLIENT", help="List completed TPs for client")
    p.add_argument("--uncomplete", action="store_true", help="Remove TP from completed list")
    args = p.parse_args()

    if args.list:
        list_tps(args.list)
    elif args.client and args.tp:
        mark_complete(args.client, args.tp, undo=args.uncomplete)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

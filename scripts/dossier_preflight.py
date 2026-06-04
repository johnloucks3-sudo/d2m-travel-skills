#!/usr/bin/env python3
"""
dossier_preflight.py — Thunderbird Wing | A7 Sterling | 2026-06-04

PURPOSE: Merge dossier + corrections into a locked snapshot before any creative chain agent spawns.
ALL headless agents (Reyes, Luna, Naia, Dani) receive ONLY the snapshot — not the raw dossier.

USAGE:
    python3 scripts/dossier_preflight.py --client "Ely"
    # Prints path to snapshot: corrections/Ely_preflight_snapshot.md

INTEGRATION: Call before spawning ANY agent in the creative chain.
    snapshot = subprocess.check_output([
        sys.executable, "scripts/dossier_preflight.py", "--client", client
    ]).decode().strip()
    # Pass snapshot path to all agent prompts — not the raw dossier

METRIC: 100% of agent spawns read snapshot, not raw dossier.
OWNER: Sterling (A7)
"""

import argparse
import glob
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Path resolution (always relative to repo root, never cwd) ──────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
CORRECTIONS_DIR = REPO_ROOT / "corrections"
DOSSIERS_DIR = REPO_ROOT / "dossiers"

EXCLUDE_PATTERNS = [".bak", "_Coverage_Brief", "_Tips_Guide", "DOSSIER_", "prospects/"]


def find_dossier(client: str) -> Path | None:
    """
    Locate the primary dossier for a client.
    Identical logic to correction_capture.py — must stay in sync.
    If these diverge, Script 1 patches one file and Script 2 snapshots another.
    """
    pattern = str(DOSSIERS_DIR / "*.md")
    all_md = glob.glob(pattern)

    candidates = []
    for filepath in all_md:
        fname = os.path.basename(filepath)
        if client.lower() not in fname.lower():
            continue
        skip = False
        for excl in EXCLUDE_PATTERNS:
            if excl in fname:
                skip = True
                break
        if not skip:
            candidates.append(Path(filepath))

    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]

    # Multiple matches — prefer booking dossiers (contain a digit booking ref)
    booking_candidates = [c for c in candidates if re.search(r"\d{5,}", c.name)]
    if len(booking_candidates) == 1:
        return booking_candidates[0]

    # Still ambiguous — fail loud
    names = [c.name for c in candidates]
    print(f"[ERROR] Ambiguous dossier match for '{client}': {names}", file=sys.stderr)
    print(f"        Specify a more unique client name or resolve ambiguity manually.", file=sys.stderr)
    return None


def load_corrections_raw(corrections_file: Path) -> list[tuple[str, str]]:
    """
    Parse corrections file into a list of (timestamp, text) tuples.
    Preserves all corrections in order — latest wins if contradictory.
    """
    if not corrections_file.exists():
        return []

    corrections = []
    current_ts = None
    current_text = None

    with open(corrections_file, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("## CORRECTION —"):
                # Save previous if exists
                if current_text:
                    corrections.append((current_ts or "unknown", current_text))
                current_ts = stripped.replace("## CORRECTION —", "").strip()
                current_text = None
            elif stripped.startswith("**Text:**"):
                current_text = stripped.replace("**Text:**", "").strip()

    # Capture last entry
    if current_text:
        corrections.append((current_ts or "unknown", current_text))

    return corrections


def main():
    parser = argparse.ArgumentParser(
        description="Produce a locked dossier+corrections snapshot for agent spawns."
    )
    parser.add_argument(
        "--client", required=True, help="Client name (e.g., Ely, Nichols, Furlow)"
    )
    args = parser.parse_args()

    client = args.client.strip()
    CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Find base dossier ───────────────────────────────────────────────────
    dossier_path = find_dossier(client)
    if dossier_path is None:
        print(f"[ERROR] No dossier found for '{client}'.", file=sys.stderr)
        sys.exit(1)

    dossier_content = dossier_path.read_text(encoding="utf-8")

    # ── 2. Load corrections ────────────────────────────────────────────────────
    corrections_file = CORRECTIONS_DIR / f"{client}_corrections.md"
    corrections = load_corrections_raw(corrections_file)

    # ── 3. Build snapshot ──────────────────────────────────────────────────────
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    snapshot_path = CORRECTIONS_DIR / f"{client}_preflight_snapshot.md"

    lines = []

    # Snapshot header — unmistakable for all agents
    lines.append(f"## PREFLIGHT LOCKED SNAPSHOT — {ts} — USE THIS, NOT THE RAW DOSSIER")
    lines.append(f"> Source dossier: {dossier_path.relative_to(REPO_ROOT)}")
    lines.append(f"> Corrections applied: {len(corrections)}")
    lines.append(f"> This snapshot expires: use a fresh preflight before each new session.")
    lines.append("")

    if corrections:
        lines.append("## ACTIVE CORRECTIONS (override dossier where they conflict)")
        lines.append("> These are Commander-issued corrections captured after the dossier was written.")
        lines.append("> Where a correction contradicts the dossier, the CORRECTION is authoritative.")
        lines.append("> Note: if two corrections contradict each other, the LATEST one wins.")
        lines.append("")
        for i, (corr_ts, corr_text) in enumerate(corrections, 1):
            lines.append(f"**Correction {i}** ({corr_ts}): {corr_text}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## BASE DOSSIER CONTENT")
    lines.append(f"> Source: {dossier_path.name}")
    lines.append(f"> Read: {ts}")
    lines.append("")
    lines.append(dossier_content)

    snapshot_content = "\n".join(lines)
    snapshot_path.write_text(snapshot_content, encoding="utf-8")

    # ── 4. Print the snapshot path (stdout only — Hale injects into agent prompts) ─
    print(str(snapshot_path))

    # Also emit human-readable status to stderr so it doesn't contaminate the path output
    print(
        f"[OK] Preflight snapshot locked: {snapshot_path.relative_to(REPO_ROOT)}",
        file=sys.stderr,
    )
    print(
        f"     Base dossier: {dossier_path.name}",
        file=sys.stderr,
    )
    print(
        f"     Corrections merged: {len(corrections)}",
        file=sys.stderr,
    )
    if corrections:
        for i, (corr_ts, corr_text) in enumerate(corrections, 1):
            print(f"     [{i}] {corr_text[:80]}{'...' if len(corr_text) > 80 else ''}", file=sys.stderr)


if __name__ == "__main__":
    main()

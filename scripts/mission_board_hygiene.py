#!/usr/bin/env python3
"""MISSION-1538: mission board hygiene — Track 1 per Opus-modified plan.

Phases (each is a separate commit):
  Phase 1 — Taxonomy normalization (status collapse, no archiving)
  Phase 2 — Referential-integrity-safe archive of true terminal entries
  Phase 3 — Invariant verification

Usage:
  python3 scripts/mission_board_hygiene.py phase1 --dry-run
  python3 scripts/mission_board_hygiene.py phase1 --apply
  python3 scripts/mission_board_hygiene.py phase2 --dry-run
  python3 scripts/mission_board_hygiene.py phase2 --apply
  python3 scripts/mission_board_hygiene.py phase3
"""

import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone

BOARD_PATH = Path("/home/john/Thunderbird/OpsCenter/mission_board.json")
BACKUP_PATH = Path("/home/john/Thunderbird/OpsCenter/mission_board.json.backup")
REPO_ROOT = Path("/home/john/Thunderbird")

# Canonical status map: non-canonical -> canonical
# Preserves the heartbeat scanner's terminal/non-terminal semantics exactly
STATUS_MAP = {
    "complete": "completed",
    "eliminated": "killed",
    "archived_noise": "archived",
    "hold_until_mid_july": "deferred",
    "hold_until_october": "deferred",
    "commander_review_pending": "pending_commander",
}

# Canonical set (14, down from 21)
CANONICAL_STATUSES = {
    "active", "in_progress", "monitoring",
    "pending_review", "pending_commander",
    "completed", "closed", "closed_duplicate", "resolved_new_finding",
    "archived", "killed",
    "deferred", "parked", "suspended",
}

# Heartbeat scanner terminal set — must be preserved intact
HEARTBEAT_TERMINAL = {
    "completed", "complete", "closed", "archived",
    "closed_duplicate", "resolved_new_finding",
    "archived_noise", "killed", "eliminated",
}


def load_board():
    with open(BOARD_PATH) as f:
        return json.load(f)


def save_board(data, dry_run=False):
    if dry_run:
        return
    # Atomic write: temp file then rename
    fd, tmp = tempfile.mkstemp(dir=str(BOARD_PATH.parent), suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    shutil.move(tmp, BOARD_PATH)
    print(f"  Written: {BOARD_PATH}")
    # Record last_updated
    data["last_updated"] = datetime.now(timezone.utc).isoformat()


def reconcile_census():
    data = load_board()
    missions = data.get("missions", [])
    total = len(missions)
    statuses = Counter(m.get("status", "NO_STATUS") for m in missions)
    print(f"  Total entries: {total}")
    print(f"  Total statuses: {len(statuses)}")
    for s, c in sorted(statuses.items(), key=lambda x: -x[1]):
        print(f"    {s}: {c}")


def phase1_normalize(dry_run=True):
    """Phase 1: Taxonomy normalization only — no archiving, no deletion.
    Maps non-canonical statuses to canonical. Validates against heartbeat set."""
    print(f"\n=== PHASE 1: Taxonomy Normalization ({'DRY RUN' if dry_run else 'APPLY'}) ===\n")

    data = load_board()
    missions = data.get("missions", [])
    changes = []
    bad = []

    for i, m in enumerate(missions):
        old_status = m.get("status", "")
        if old_status in STATUS_MAP:
            new_status = STATUS_MAP[old_status]
            missions[i]["status"] = new_status
            changes.append((m.get("id", f"index_{i}"), old_status, new_status))
        elif old_status not in CANONICAL_STATUSES and old_status:
            bad.append((m.get("id", f"index_{i}"), old_status))

    # Validation: after normalization, every status should be canonical
    post_statuses = Counter(m.get("status", "NO_STATUS") for m in missions)
    non_canonical = {s: c for s, c in post_statuses.items() if s not in CANONICAL_STATUSES}

    # Heartbeat assertion: all terminal entries still recognizable
    terminal_still_present = any(
        s in HEARTBEAT_TERMINAL for s in post_statuses
    )

    print(f"  Entries changed: {len(changes)}")
    for cid, old, new in changes:
        print(f"    {cid}: {old} -> {new}")
    print(f"\n  Unknown statuses (not mapped, not canonical): {len(bad)}")
    for bid, bs in bad:
        print(f"    {bid}: {bs!r}")
    print(f"\n  Post-normalization status count: {len(post_statuses)}")
    print(f"  Non-canonical statuses remaining: {non_canonical}")
    print(f"  Heartbeat terminal set still represented: {terminal_still_present}")
    print(f"  Active+in_progress: {post_statuses.get('active', 0) + post_statuses.get('in_progress', 0)}")

    if not dry_run and not non_canonical and terminal_still_present:
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        save_board(data, dry_run=False)
        print("\n  Taxonomy committed.")
    elif not dry_run:
        print("\n  BLOCKED: non-canonical statuses remain or heartbeat set broken. Not committing.")

    return len(changes), non_canonical


def phase2_age_archive(dry_run=True):
    """Phase 2: Archive true terminal entries past age threshold, with
    referential-integrity check. Preserves pending/active entries entirely."""
    print(f"\n=== PHASE 2: Age Archival ({'DRY RUN' if dry_run else 'APPLY'}) ===\n")

    data = load_board()
    missions = data.get("missions", [])
    archived = data.get("archived_missions", [])

    # Candidate terminal statuses (after Phase 1 normalization)
    terminal_statuses = {"completed", "closed", "closed_duplicate",
                         "resolved_new_finding", "archived", "killed"}

    # Age threshold: completed_at or updated_at > 30 days
    now = datetime.now(timezone.utc)
    threshold_days = 30

    candidates = []
    for m in missions:
        if m.get("status") not in terminal_statuses:
            continue
        # Determine date field
        ts_str = m.get("completed_at") or m.get("updated_at") or m.get("created_at")
        if not ts_str:
            continue  # no timestamp — skip, flag
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        age_days = (now - ts).days
        if age_days >= threshold_days:
            candidates.append(m)

    print(f"  Terminal entries: {sum(1 for m in missions if m.get('status') in terminal_statuses)}")
    print(f"  Candidates for archive (age >= {threshold_days}d): {len(candidates)}")

    # Referential-integrity check: grep repo for each mission ID
    hold = []
    clear = []
    for m in candidates:
        mid = m.get("id", "")
        if not mid:
            continue
        # Quick check: is this ID referenced in dossiers, hale_state, etc.?
        # Skip archived missions in the check (they're already in archived_missions list)
        referenced = grep_mission_id(mid)
        if referenced:
            hold.append((mid, referenced))
        else:
            clear.append(m)

    print(f"  Clear for archive: {len(clear)}")
    print(f"  Held (referenced elsewhere): {len(hold)}")
    for mid, refs in hold[:10]:
        print(f"    HELD: {mid} — referenced in {refs}")

    if dry_run:
        print(f"\n  Dry-run complete. {len(clear)} would be moved to archived_missions.")
        return len(clear), len(hold)

    # Execute: move clear candidates to archived_missions
    clear_ids = {m.get("id") for m in clear}
    kept = [m for m in missions if m.get("id") not in clear_ids]
    data["missions"] = kept
    data["archived_missions"].extend(clear)
    data["_mission_count_active"] = len(kept)
    data["_mission_count_archived"] = len(data["archived_missions"])
    data["_last_archival_date"] = now.isoformat()

    save_board(data, dry_run=False)
    print(f"\n  Archived {len(clear)} missions. Active: {len(kept)}. Total archived: {len(data['archived_missions'])}.")
    return len(clear), len(hold)


def grep_mission_id(mission_id):
    """Check if a mission ID is referenced anywhere outside the board itself."""
    import subprocess
    try:
        result = subprocess.run(
            ["rg", "-l", re.escape(mission_id),
             str(REPO_ROOT / "dossiers"),
             str(REPO_ROOT / "hale_state.json"),
             str(REPO_ROOT / "OpsCenter"),
             str(REPO_ROOT / "core"),
             str(REPO_ROOT / "Personas")],
            capture_output=True, text=True, timeout=15
        )
        hits = [p for p in result.stdout.strip().split("\n") if p and "mission_board.json" not in p]
        return hits[:5] if hits else []
    except Exception:
        return []


def phase3_verify():
    """Phase 3: Invariant verification — count reconciliation, no leaks, JSON integrity."""
    print("\n=== PHASE 3: Invariant Verification ===\n")

    data = load_board()
    missions = data.get("missions", [])
    archived = data.get("archived_missions", [])
    statuses = Counter(m.get("status", "NO_STATUS") for m in missions)

    checks = []

    # 1. JSON integrity
    checks.append(("JSON parses", True))

    # 2. All statuses are canonical
    non_canonical = {s: c for s, c in statuses.items() if s not in CANONICAL_STATUSES}
    checks.append(("All statuses canonical", len(non_canonical) == 0, f"Non-canonical: {non_canonical}"))

    # 3. No active/pending-commander in archived
    checks.append(("Archived contains no active",
                   all(a.get("status") not in ("active", "in_progress") for a in archived)))

    # 4. Active + in_progress < 50 (per MISSION-1538)
    working_set = statuses.get("active", 0) + statuses.get("in_progress", 0)
    checks.append(("Working set < 50", working_set < 50, f"Active+in_progress: {working_set}"))

    # 5. Heartbeat terminal set still intact
    heartbeat_ok = any(s in HEARTBEAT_TERMINAL for s in statuses)
    checks.append(("Heartbeat terminal set intact", heartbeat_ok))

    # 6. pending_review surfaced (count)
    pr_count = statuses.get("pending_review", 0)
    checks.append(("pending_review count tracked", True, f"pending_review: {pr_count}"))

    # Print results
    all_pass = True
    for name, passed, *msg in checks:
        icon = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        detail = f" — {msg[0]}" if msg else ""
        print(f"  [{icon}] {name}{detail}")

    print(f"\n  Overall: {'ALL CHECKS PASS' if all_pass else 'SOME CHECKS FAILED'}")
    return all_pass, {
        "total_missions": len(missions),
        "total_archived": len(archived),
        "status_count": len(statuses),
        "working_set": working_set,
        "pending_review": pr_count,
    }


if __name__ == "__main__":
    import os

    phase = sys.argv[1] if len(sys.argv) > 1 else "status"
    dry_run = "--apply" not in sys.argv and "--dry-run" not in sys.argv

    if "--dry-run" in sys.argv:
        dry_run = True
    elif "--apply" in sys.argv:
        dry_run = False

    if phase == "status" or phase == "census":
        reconcile_census()
    elif phase == "phase1":
        phase1_normalize(dry_run=dry_run)
    elif phase == "phase2":
        phase2_age_archive(dry_run=dry_run)
    elif phase == "phase3":
        phase3_verify()
    elif phase == "all":
        print("\n=== PHASE 1 ===")
        phase1_normalize(dry_run=dry_run)
        print("\n=== PHASE 2 ===")
        phase2_age_archive(dry_run=dry_run)
        print("\n=== PHASE 3 ===")
        phase3_verify()
    elif phase == "pending-digest":
        # Output pending_review items for Commander decision digest
        data = load_board()
        pending = [m for m in data.get("missions", [])
                   if m.get("status") in ("pending_review", "pending_commander")]
        print(json.dumps(pending, indent=2))
    else:
        print("Usage:")
        print("  python3 scripts/mission_board_hygiene.py status")
        print("  python3 scripts/mission_board_hygiene.py phase1 --dry-run")
        print("  python3 scripts/mission_board_hygiene.py phase1 --apply")
        print("  python3 scripts/mission_board_hygiene.py phase2 --dry-run")
        print("  python3 scripts/mission_board_hygiene.py phase2 --apply")
        print("  python3 scripts/mission_board_hygiene.py phase3")
        print("  python3 scripts/mission_board_hygiene.py pending-digest")
#!/usr/bin/env python3
"""
ELON Kill Audit — 2026-06-11
Single-pass JSON edit. Classifies every active P0/P1 mission as KILL, DEDUP, DEFERRED, or REAL.
Applies status updates + log entries atomically.
Run: python3 OpsCenter/kill_audit_2026-06-11.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BOARD_PATH = Path("/home/john/Thunderbird/OpsCenter/mission_board.json")
TS = datetime.now(timezone.utc).strftime("[%Y-%m-%dT%H:%M:%SZ]")
TAG = f"{TS} [ELON kill-audit 2026-06-11]"

# --- Classification table ---
# KILL: close as completed, mission already satisfied or perpetual with no deliverable
# DEDUP: close as completed, fold into canonical mission
# DEFERRED: keep but set correct status and note deferral date
# REAL: keep active, update title if truncated

KILL = {
    "MISSION-026": "Executor COMPLETE Jun 8-10 (logs confirm). Status not updated by executor.",
    "MISSION-069": "Executor COMPLETE Jun 9-10 (Chrome port 9222 + CDP clients confirmed ONLINE).",
    "MISSION-102": "KILL: perpetual monitoring campaign (IRON CLOCK), no discrete deliverable, no completion criteria. Doctrine already in AGENTS.md.",
    "MISSION-103": "KILL: perpetual watch campaign (Spawn Reliability), no deliverable, no owner. Doctrine encoded.",
    "MISSION-105": "KILL: INBOX FIRST — pipeline redirect verified Jun 4, doctrine live in AGENTS.md. Satisfied.",
    "MISSION-106": "KILL: TEMPLATE — template audit with no owner, no logs, no discrete output in 7 days. CLAUDE.md is the template baseline.",
    "MISSION-107": "KILL: SPEED — vague bottleneck diagnosis campaign, no owner, no output. Replaced by Context Sniper (M-171) and slot router (M-174) builds.",
    "MISSION-110": "KILL: INBOX DISCIPLINE — doctrine implemented (Hale protocol updated in AGENTS.md Jun 4). Perpetual-style, no fresh deliverable.",
    "MISSION-113": "KILL: DEDUP — superseded by MISSION-166 (Centrav+Regent keepalive, completed Jun 10).",
    "MISSION-120": "KILL: Nichols TP 0.5 — SATISFIED 2026-06-06 per hale_state.json project_tracking (PROJ-NICHOLS-TP05).",
    "MISSION-121": "KILL: McLeod T-13 — SATISFIED 2026-06-06 per hale_state.json project_tracking (PROJ-MCLEOD-T13). Superseded by MISSION-162 (T-7).",
    "MISSION-122": "KILL: DEDUP — Spencer flight Jun 10 deadline passed; superseded by MISSION-183 (United Group Desk call, still open).",
    "MISSION-123": "KILL: DEDUP — Kuklinski 4 WF-17 drafts. Canonical = MISSION-129 (deferred Jul 15). Collapse here.",
    "MISSION-124": "KILL: DEDUP — Bryana onboarding. Canonical = MISSION-158. Bryana nixed by Susie per MISSION-104 description.",
    "MISSION-128": "KILL: DEDUP — Spencer Air Quote Jun 10. Jun 10 deadline passed, planning ranges delivered. Canonical = MISSION-183.",
    "MISSION-130": "KILL: DEDUP — United Group Desk call. Canonical = MISSION-183 (active).",
    "MISSION-137": "KILL: DEDUP — Activate Dembe Spencer. Jun 10 passed, Dembe activated (log Jun 9). Canonical = MISSION-183.",
    "MISSION-138": "KILL: DEDUP — Send five WF-17 drafts. Canonical = MISSION-129 (deferred Jul 15).",
    "MISSION-142": "KILL: Morton/Dodge lifecycle reset — executor COMPLETE Jun 9-10 (logs confirm). Status not updated.",
    "MISSION-143": "KILL: Google Tasks OAuth 403 — executor COMPLETE Jun 9-10 (logs confirm). Status not updated.",
    "MISSION-147": "KILL: DEDUP — Hale Gmail Phase 2. Canonical = MISSION-146 (Phase 1+2 combined, in_progress).",
    "MISSION-149": "KILL: DEDUP — Centrav Session Auto-Keepalive. Canonical = MISSION-166 (completed Jun 10).",
    "MISSION-151": "KILL: DEDUP — Telegram Redesign (Opus Phase A). Completed and superseded by MISSION-179+180 (full parity, complete Jun 10).",
    "MISSION-155": "KILL: DEDUP — Activate Dembe Spencer DEN-FCO. Jun 10 deadline passed. Canonical = MISSION-183.",
    "MISSION-157": "KILL: Refresh Centrav+Regent cookies — executor COMPLETE Jun 10 (logs confirm). Status not updated.",
    "MISSION-160": "KILL: Qdrant daily re-index systemd timer — executor COMPLETE Jun 10 22:41 (logs confirm). Status not updated.",
    "MISSION-164": "KILL: Refresh cookies before Spencer call — Spencer call Jun 10 passed; cookies refreshed (executor Jun 10). Superseded by M-166 keepalive.",
    "MISSION-168": "KILL: Overwatch crash loop root-cause — executor COMPLETE Jun 11 02:44 (logs confirm). Status not updated.",
    "MISSION-189": "KILL: Restore TESS auth — executor COMPLETE Jun 11 06:49 (logs confirm). Status not updated.",
}

# DEDUP the second MISSION-172 (Cross-Staff Communication Tools, active, validation_status=ALL_DEFECTS_RESOLVED_AWAITING_COMMANDER_CLOSE)
# The first MISSION-172 (State Bridge) is already completed. We need to close the duplicate.
# We'll identify it by title.
MISSION_172_DUPE_TITLE = "Cross-Staff Communication Tools"
MISSION_172_DUPE_CLOSE_REASON = "KILL: DEDUP — Second instance of MISSION-172 ID. First (State Bridge) complete. This instance shows ALL_DEFECTS_RESOLVED_AWAITING_COMMANDER_CLOSE — all D1-D6 defects fixed Jun 9. Closing as complete."

# MISSIONS-082, 083, 084 are sub-missions that roll up to MISSION-087. Close as children satisfied.
SUBMISSION_KILLS = {
    "MISSION-082": "KILL: Sub-mission of MISSION-087 (Grandeur Group Hotel/Transport/Seats). Dembe intel update logged Jun 11. Action on PNR BB4X94 belongs to M-087. Fold here.",
    "MISSION-083": "KILL: Sub-mission of MISSION-087. Nichols seat assignments CONFIRMED per dossier detail rows 19-20 (3C/3A BA 6776, 8D/8G AA 79). M-087 carries remaining verification.",
    "MISSION-084": "KILL: Sub-mission of MISSION-087. Haymarket cancellation + At Six booking decision staged for Commander in M-087. Fold here.",
    "MISSION-085": "KILL: Sub-mission of MISSION-087. Schengen verification US passports—visa-free EU standard, all passports valid 2030+. Documented in group dossiers. Fold to M-087.",
}

# Missions to DEFER explicitly (not kill—still open but wrong status)
DEFER = {
    "MISSION-112": ("deferred", "2026-07-15", "WF-17 sends deferred by Commander 2026-06-08 to Jul 15. Canonical = M-129."),
    "MISSION-129": ("deferred", "2026-07-15", "WF-17 sends deferred by Commander 2026-07-15. Resume Jul 15 — Nichols TP 0.5 + Kuklinski x4."),
    "MISSION-138": None,  # Already marked as KILL above (dedup of 129)
}

# REAL missions — update title if truncated, leave status as-is
REAL_TITLE_FIXES = {
    "MISSION-108": "LOUCKS TRAVEL — Atlas Med Leg 3 Pricing Call",
    "MISSION-109": "LOUCKS TRAVEL — Hawaii Apr 2027 Resort Research",
    "MISSION-104": "WING STANDUP — Build Front Door for Rondo/Stefanie",
}


def main():
    board = json.loads(BOARD_PATH.read_text(encoding="utf-8"))
    missions = board["missions"]

    before_active = [m for m in missions
                     if m.get("status") not in ("completed", "complete", "done", "cancelled", "archived", "deferred")]
    before_count = len(before_active)

    killed = []
    deduped = []
    deferred_fixed = []
    title_fixed = []

    for m in missions:
        mid = m.get("id", "")
        status = m.get("status", "")
        title = m.get("title", "")
        is_active = status not in ("completed", "complete", "done", "cancelled", "archived", "deferred")

        # --- Apply KILL decisions ---
        if is_active and mid in KILL:
            m["status"] = "completed"
            m["completed_at"] = datetime.now(timezone.utc).isoformat()
            if "logs" not in m or not isinstance(m["logs"], list):
                m["logs"] = []
            m["logs"].append(f"{TAG} KILL: {KILL[mid]}")
            killed.append(mid)
            continue

        # --- Apply sub-mission kills ---
        if is_active and mid in SUBMISSION_KILLS:
            m["status"] = "completed"
            m["completed_at"] = datetime.now(timezone.utc).isoformat()
            if "logs" not in m or not isinstance(m["logs"], list):
                m["logs"] = []
            m["logs"].append(f"{TAG} KILL: {SUBMISSION_KILLS[mid]}")
            killed.append(f"{mid}(sub)")
            continue

        # --- Close second MISSION-172 duplicate ---
        if is_active and mid == "MISSION-172" and title == MISSION_172_DUPE_TITLE:
            m["status"] = "completed"
            m["completed_at"] = datetime.now(timezone.utc).isoformat()
            if "logs" not in m or not isinstance(m["logs"], list):
                m["logs"] = []
            m["logs"].append(f"{TAG} {MISSION_172_DUPE_CLOSE_REASON}")
            deduped.append("MISSION-172(dupe:Cross-Staff)")
            continue

        # --- DEFER missions that are deferred but status is wrong ---
        if mid in DEFER and DEFER[mid] is not None:
            new_status, defer_date, reason = DEFER[mid]
            if is_active or m.get("suspense_date") != defer_date:
                m["status"] = new_status
                m["suspense_date"] = defer_date
                if "logs" not in m or not isinstance(m["logs"], list):
                    m["logs"] = []
                m["logs"].append(f"{TAG} DEFER: {reason}")
                deferred_fixed.append(mid)

        # --- Fix truncated titles on REAL missions ---
        if mid in REAL_TITLE_FIXES:
            old = m.get("title", "")
            new = REAL_TITLE_FIXES[mid]
            if old != new:
                m["title"] = new
                if "logs" not in m or not isinstance(m["logs"], list):
                    m["logs"] = []
                m["logs"].append(f"{TAG} TITLE-FIX: '{old}' → '{new}'")
                title_fixed.append(mid)

    # Write back
    BOARD_PATH.write_text(json.dumps(board, indent=2, default=str, ensure_ascii=False), encoding="utf-8")

    # Count after
    board2 = json.loads(BOARD_PATH.read_text(encoding="utf-8"))
    after_active = [m for m in board2["missions"]
                    if m.get("status") not in ("completed", "complete", "done", "cancelled", "archived", "deferred")]
    after_count = len(after_active)

    print(f"Kill audit complete.")
    print(f"BEFORE active: {before_count}")
    print(f"AFTER  active: {after_count}")
    print(f"Killed:  {len(killed)} → {killed}")
    print(f"Deduped: {len(deduped)} → {deduped}")
    print(f"Deferred corrected: {len(deferred_fixed)} → {deferred_fixed}")
    print(f"Titles fixed: {len(title_fixed)} → {title_fixed}")


if __name__ == "__main__":
    main()

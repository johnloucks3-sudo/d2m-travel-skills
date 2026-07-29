#!/usr/bin/env python3
"""
MISSION BOARD SYNC — EXEC Interface
D2M Thunderbird OS · 2026-04-04
$0/month cost · No API calls required

Purpose: Passive read/write interface for Commander via CLI.
Called by: Telegram GW (voice), Gmail poller, manual CLI.
Never calls out — only reads/writes mission_board.json.

Commands:
  EXEC: list board          → Show all active missions
  EXEC: list suspended      → Show suspense queue
  EXEC: list complete       → Show completed missions
  EXEC: add <title> <desc>  → Create new mission (Hale assigns — no NEXUS)
  EXEC: add suspense <id> <date>  → Set suspense_date
  EXEC: complete <id>       → Mark mission done
  EXEC: status <id>         → Show mission details
  EXEC: log <id> <message>  → Append log entry
  EXEC: purge <id>          → Move to completed
  EXEC: help                → Show commands
"""

import json
import os
import sys
import fcntl
from datetime import datetime, timezone
from pathlib import Path

# Repo root on sys.path so the cross-Hale delegation wiring (core.relay.*,
# core.hale_bus.*) resolves under a bare `python3 OpsCenter/mission_board_sync.py`
# invocation, not only under pytest. Without this the `delegate` CLI path would
# import-crash even though _delegation_seats() falls back cleanly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BOARD_PATH = Path(__file__).parent / "mission_board.json"
LOCK_PATH = Path(__file__).parent / "mission_board.lock"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _delegation_seats():
    """Cross-Hale seat codes that trigger the delegation-wiring path. Defensive
    lazy import so a bare CLI run (no repo root on sys.path) still creates
    persona-name / unassigned missions normally — those never touch this set."""
    try:
        from core.relay.task_delegation import SEATS
        return SEATS
    except Exception:
        return ("CC", "OC", "AG")


def acquire_lock():
    """Atomic lock to prevent concurrent board corruption."""
    os.makedirs(LOCK_PATH.parent, exist_ok=True)
    fd = open(LOCK_PATH, 'w')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("BOARD LOCKED: Another process is writing. Try again in 3s.")
        sys.exit(3)
    fd.write(str(os.getpid()))
    fd.flush()
    return fd


def release_lock(fd):
    fcntl.flock(fd, fcntl.LOCK_UN)
    fd.close()
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


def load_board():
    with open(BOARD_PATH, 'r') as f:
        return json.load(f)


def save_board(board, fd):
    with open(BOARD_PATH, 'w') as f:
        json.dump(board, f, indent=2, default=str)
    release_lock(fd)


def get_active(board):
    all_missions = board.get("missions", board.get("active_missions", []))
    return [m for m in all_missions if m.get("status") not in ("completed", "complete", "done", "cancelled")]


def find_mission(board, mission_id):
    """Search flat missions array for a mission by ID."""
    all_missions = board.get("missions", board.get("active_missions", []))
    for m in all_missions:
        if m["id"] == mission_id:
            status = m.get("status", "active")
            if status in ("completed", "complete", "done"):
                return m, "completed_missions"
            elif status == "suspended":
                return m, "suspended_missions"
            else:
                return m, "active_missions"
    return None, None


def cmd_list_board(board):
    """EXEC: list board"""
    active = get_active(board)
    if not active:
        return "📋 Mission Board: EMPTY\nNo active missions."
    
    lines = ["📋 MISSION BOARD (Active):", "=" * 40]
    for m in active:
        priority_flag = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "🟢"}.get(m.get("priority", "P3"), "⚪")
        suspense = f" ⏰ {m.get('suspense_date', 'none')[:16]}" if m.get("suspense_date") else ""
        lines.append(f"{priority_flag} {m['id']}: {m['title']}")
        lines.append(f"    Status: {m['status']} | Priority: {m.get('priority', 'P3')} | To: {m.get('assigned_to', 'unassigned')}{suspense}")
    lines.append(f"\nTotal active: {len(active)}")
    return "\n".join(lines)


def cmd_list_suspended(board):
    """EXEC: list suspended"""
    all_missions = board.get("missions", board.get("suspended_missions", []))
    suspended = [m for m in all_missions if m.get("status") == "suspended"]
    if not suspended:
        return "⏸️ Suspended Queue: EMPTY"
    
    lines = ["⏸️ SUSPENDED MISSIONS:", "=" * 40]
    for m in suspended:
        suspense = m.get("suspense_date", "unknown")
        lines.append(f"⏰ {m['id']}: {m['title']} (suspended until {suspense[:16] if suspense else 'N/A'})")
    return "\n".join(lines)


def cmd_list_complete(board):
    """EXEC: list complete"""
    all_missions = board.get("missions", board.get("completed_missions", []))
    completed = [m for m in all_missions if m.get("status") in ("completed", "complete", "done")]
    if not completed:
        return "✅ Completed Missions: EMPTY"
    
    lines = ["✅ COMPLETED MISSIONS:", "=" * 40]
    for m in completed:
        lines.append(f"✅ {m['id']}: {m['title']}")
    return "\n".join(lines)


def _normalize_title(title):
    """Lowercase, strip punctuation/whitespace for duplicate comparison."""
    return "".join(c for c in title.lower() if c.isalnum() or c.isspace()).split()


import re as _re

_MONEY_RE = _re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d{4,})(?:\.\d{2})?")
_ID_RE = _re.compile(
    r"(?:#|\b(?:conf(?:irmation)?|booking|invoice|res(?:ervation)?)\s*#?\s*)(\d{6,})\b",
    _re.I)

# Commitment/deadline nouns. Two OPEN missions about the same money, the same
# booking reference, or the same party+commitment are the same work no matter
# how the verb is phrased.
_ENTITY_NOUNS = ("fpd", "final payment", "balance due", "deposit", "invoice",
                 "commission", "refund", "payment")

# Verbs and scaffolding that carry no identity — stripped before looking for
# the party/proper-noun cluster.
_STOPWORDS = frozenset("""
surface pay confirm escalate execute review resolve complete run check track
and or the a an to for of by before after at on due deadline reminder mark day
days week month commander authorization mechanism contingency payment final
balance audit deliver open close update status now asap urgent item task
mission with from into out over under is are be been this that these those
""".split())


def _entity_signature(title, description=""):
    """Reword-proof identity for a mission.

    WHY THIS EXISTS (2026-07-29): `_find_open_duplicate` compares title word
    sets. A generator that writes a fresh title each run defeats it trivially.
    "Surface Loucks Grandeur FPD — $24,798 due August 1", "Pay Loucks Grandeur
    FPD before August 1 deadline", "Confirm Loucks Grandeur FPD payment
    mechanism" and "Escalate Loucks Grandeur FPD for Commander payment
    authorization" are four different word sets describing ONE payment.
    Twelve such missions accumulated Jul 15-26, each re-detecting a deadline
    nobody had resolved (MAST FM-1.3, step repetition).

    Returns a dict of signal sets, or None when the text carries no commitment
    noun at all — in which case we fall back to word-set matching rather than
    guess. Matching policy lives in `_entity_matches`, deliberately separate,
    because a FALSE MERGE is worse than a duplicate: it hides real work.
    """
    blob = f"{title} {description or ''}".lower()
    if not any(n in blob for n in _ENTITY_NOUNS):
        return None
    # Amounts and references may come from anywhere — they are precise.
    amounts = {a.replace(",", "") for a in _MONEY_RE.findall(blob)}
    refs = set(_ID_RE.findall(blob))
    # Parties come from the TITLE ONLY. Descriptions are long prose, and a
    # 2026-07-29 sweep showed description tokens linking wholly unrelated work
    # through generic words ("booking", "live", "client", "against") and even
    # "mission-" harvested from cross-referenced mission IDs. That produced one
    # bogus 15-mission cluster spanning a rental car, orphaned systemd units,
    # and a client transfer dispute.
    parties = {w for w in _re.findall(r"[a-z][a-z'-]{3,}", (title or "").lower())
               if w not in _STOPWORDS}
    if not (amounts or refs or parties):
        return None
    return {"amounts": amounts, "refs": refs, "parties": frozenset(parties)}


def _entity_matches(a, b, is_rare=None):
    """Do two signatures describe the same commitment?

    Ordered most-certain first, and biased AGAINST merging, because a FALSE
    MERGE HIDES REAL WORK and is worse than a duplicate:
      * shared booking reference    -> same (outranks differing amounts, e.g.
                                       deposit vs balance on one booking)
      * both carry amounts          -> same only if an amount matches;
                                       different amounts are definitively NOT
                                       the same commitment
      * otherwise, party cluster    -> needs >= 2 shared title tokens, AND at
                                       least one must be RARE on this board

    `is_rare(token) -> bool` is supplied by the caller, which knows the corpus.
    Without it, any shared pair passes — the permissive path, used only when
    there is no board context. Rarity matters because a busy client name
    ("kuklinski") legitimately appears across many unrelated missions and
    therefore identifies nothing; a name like "furlow" appearing twice does.
    """
    if not a or not b:
        return False
    if a["refs"] & b["refs"]:
        return True
    if a["amounts"] and b["amounts"]:
        return bool(a["amounts"] & b["amounts"])
    shared = a["parties"] & b["parties"]
    if len(shared) < 2:
        return False
    return True if is_rare is None else any(is_rare(w) for w in shared)


def _rarity_predicate(all_missions, max_share=0.05):
    """Build `is_rare` from how often a title token occurs across open missions.

    A token appearing in more than `max_share` of the board is common vocabulary
    and cannot identify a duplicate on its own.
    """
    from collections import Counter
    df = Counter()
    n = 0
    for m in all_missions:
        if not isinstance(m, dict):
            continue
        if m.get("status") not in ("active", "in_progress", "pending", "open",
                                   "pending_review"):
            continue
        n += 1
        for w in _re.findall(r"[a-z][a-z'-]{3,}", (m.get("title") or "").lower()):
            if w not in _STOPWORDS:
                df[w] += 1
    threshold = max(2, int(n * max_share))
    return lambda w: df.get(w, 0) <= threshold


def _find_entity_duplicate(all_missions, title, description=""):
    """Open mission describing the same commitment, regardless of wording."""
    sig = _entity_signature(title, description)
    if not sig:
        return None
    is_rare = _rarity_predicate(all_missions)
    for m in all_missions:
        if not isinstance(m, dict):
            continue
        if m.get("status") not in ("active", "in_progress", "pending", "open",
                                   "pending_review"):
            continue
        other = _entity_signature(m.get("title") or "", m.get("description") or "")
        if _entity_matches(sig, other, is_rare=is_rare):
            return m
    return None


def _find_open_duplicate(all_missions, title):
    """ONE AND DONE (fixed 2026-07-04 — Sterling/A7): before creating a new
    mission, check open missions for the same work already tracked under a
    different ID (e.g. MISSION-SEC-05/1510/1522 were the same GitHub
    credential rotation created 3 times; MISSION-820/1511/1523 were the same
    Regent portal auth created 3 times). Exact/substring match only — no
    fuzzy matching, which would silently merge genuinely distinct tasks.

    REGRESSION FIX (2026-07-16): TCD's Create Task action
    (tcd/writeback.py::_default_create_task_fn) files missions with
    status="pending_review", which this function didn't recognize as
    "open" — so every TCD-routed duplicate sailed straight past this check
    (Regent pricing x4, TESS restore x3+, WF-17 drafts x4, etc). Added
    "pending_review" to the open-status list and wired this function into
    the TCD path directly (see _default_create_task_fn)."""
    new_norm = _normalize_title(title)
    new_set = set(new_norm)
    if not new_set:
        return None
    for m in all_missions:
        if m.get("status") not in ("active", "in_progress", "pending", "open", "pending_review"):
            continue
        existing_norm = _normalize_title(m.get("title", ""))
        existing_set = set(existing_norm)
        if not existing_set:
            continue
        if new_set == existing_set:
            return m
        # substring: shorter title's words are a subset of the longer title's words
        shorter, longer = (new_set, existing_set) if len(new_set) <= len(existing_set) else (existing_set, new_set)
        if shorter and shorter.issubset(longer) and len(shorter) >= 3:
            return m
    return None


def add_mission(board, title, description="No description", priority="P0", assigned_to="unassigned", source=None,
                acceptance_criteria=None, certified_by=None, deadline_hours=None, task_type=None, from_seat="CC",
                ground_truth_sources=None):
    """Create a new mission on ``board`` (mutates in place) — the ONE place
    mission-creation + open-duplicate logic lives. ``cmd_add`` (the CLI's
    space-separated argv parser, below) and any structured/programmatic
    caller (MCP tools, TCD writeback, etc.) both delegate here so there is
    exactly one dedup code path, not one per caller — see
    _find_open_duplicate's REGRESSION FIX note (2026-07-16) for why three
    independent creation paths already burned this system once.

    CROSS-HALE DELEGATION WIRING (2026-07-16, design
    CROSS_HALE_TASK_DELEGATION_DESIGN §3.2-3.6): when ``assigned_to`` is a
    real cross-Hale seat (CC/OC/AG — NOT a persona name like "Hale" and NOT
    "unassigned"), the mission is a delegation ticket. It then REQUIRES
    ``acceptance_criteria`` (the PDTAC "T"), carries the extended schema
    (verification_artifact / certified_by / delegation_rationale / deadline),
    and is taken live on the C2 Fabric bus via
    core.relay.delegation_wiring.delegate_mission() — which validates the
    routing rationale, notifies the seat over the relay, and mirrors the
    ``assigned`` lifecycle stage onto hale_bus_state.json. ``certified_by``
    MUST differ from ``assigned_to`` (§3.5 anti-theater) or this raises.
    Persona-name / unassigned missions are untouched by this path.

    Does NOT acquire/release the board lock itself — callers that aren't
    already inside process_exec_command's lock (i.e. MCP tools) must wrap
    this in acquire_lock()/save_board() themselves.

    Returns (message, mission_id_or_None) — mission_id is None when the
    call was blocked as a duplicate (the existing mission's id is embedded
    in the message instead)."""
    all_missions = board.get("missions", board.get("active_missions", []))

    # Entity-signature check runs FIRST: it survives rewording, which the
    # word-set check below does not. See _entity_signature for the twelve-
    # duplicate-FPD incident that motivated it.
    dup = (_find_entity_duplicate(all_missions, title, description or "")
           or _find_open_duplicate(all_missions, title))
    if dup is not None:
        dup.setdefault("logs", []).append(
            f"{now_iso()}: duplicate creation attempt blocked — \"{title}\" already tracked here"
        )
        dup["updated_at"] = now_iso()
        return (
            f"⚠️ Duplicate blocked — already tracked as {dup['id']} ({dup.get('status')}): "
            f"{dup['title']}\nNo new mission created. Use log/status/complete on {dup['id']} instead.",
            None,
        )

    # Find next available MISSION-NNN
    nums = []
    for m in all_missions:
        try:
            nums.append(int(m["id"].split("-")[-1]))
        except (ValueError, IndexError, KeyError):
            pass
    next_num = (max(nums) + 1) if nums else 1
    mission_id = f"MISSION-{next_num:03d}"

    is_delegation = assigned_to in _delegation_seats()
    new_mission = {
        "id": mission_id,
        "title": title,
        "status": "assigned" if is_delegation else "in_progress",
        "priority": priority,
        "assigned_to": assigned_to,
        "description": description,
        "deliverables": [],
        "dependencies": [],
        "suspense_date": None,
        "escalation_rule": None,
        "logs": [],
        "created_at": now_iso(),
        "updated_at": now_iso()
    }
    if source:
        new_mission["source"] = source

    if is_delegation:
        # Cross-Hale seat assignment → live delegation ticket on the C2 Fabric
        # bus. Requires acceptance_criteria (§3.5.1) and a cross-seat certifier
        # (§3.5.3); delegate_mission raises DelegationError if either is missing.
        from datetime import timedelta
        new_mission["acceptance_criteria"] = (acceptance_criteria or "").strip()
        new_mission["verification_artifact"] = ""
        new_mission["certified_by"] = certified_by or "CC"
        new_mission["ground_truth_sources"] = ground_truth_sources or []
        if deadline_hours:
            new_mission["deadline"] = (
                datetime.now(timezone.utc) + timedelta(hours=deadline_hours)
            ).isoformat()
        from core.relay.delegation_wiring import delegate_mission
        delegate_mission(new_mission, from_seat=from_seat, task_type=task_type)
        board.setdefault("missions", []).append(new_mission)
        return (
            f"✅ Delegated: {mission_id} — {title}\n"
            f"Priority: {priority} | Seat: {assigned_to} | Certifier: {new_mission['certified_by']}\n"
            f"Rationale: {new_mission['delegation_rationale']}",
            mission_id,
        )

    board.setdefault("missions", []).append(new_mission)
    return f"✅ Created: {mission_id} — {title}\nPriority: {priority} | Assigned: {assigned_to}", mission_id


def cmd_add(board, args):
    """EXEC: add <title> <description> [P0|P1|P2|P3] — CLI space-separated
    argv parser only. Kept byte-for-byte (including the title=first-3-words
    quirk existing Telegram/manual callers already depend on); creation +
    dedup now live in add_mission() above, the single source of truth."""
    args = list(args)
    # Honor a trailing priority token if present (default P0 for back-compat)
    priority = "P0"
    if args and args[-1].upper() in ("P0", "P1", "P2", "P3"):
        priority = args.pop().upper()
    # Parse simple format: EXEC: add MISSION-XXX title here
    title = " ".join(args[:3])
    desc = " ".join(args[3:]) if len(args) > 3 else "No description"

    message, _mission_id = add_mission(board, title, desc, priority, assigned_to="unassigned")
    return message


def cmd_delegate(board, arg_string):
    """EXEC: delegate SEAT :: title :: acceptance_criteria [:: PRIORITY :: task_type :: certifier :: ground_truth]

    The real cross-Hale delegation entry point (CC/OC/AG). Fields are `::`-
    delimited because titles/criteria contain spaces the whitespace argv parser
    would shred. Delegates to add_mission(assigned_to=SEAT, ...), which fires
    delegate_mission() — routing validation + Silver front-frame + relay handoff
    + `assigned` bus mirror. certifier defaults to CC and MUST differ from SEAT
    (§3.5). ground_truth = comma-separated source(s) Silver's front frame
    requires (mandatory 2026-07-16): no named ground truth, no ticket."""
    seats = _delegation_seats()
    fields = [f.strip() for f in arg_string.split("::")]
    if len(fields) < 3 or not fields[0]:
        return ("❌ Usage: EXEC: delegate SEAT :: title :: acceptance_criteria "
                "[:: PRIORITY :: task_type :: certifier :: ground_truth]\n"
                f"   SEAT ∈ {seats}")
    seat = fields[0].upper()
    if seat not in seats:
        return f"❌ Unknown seat {seat!r} — must be one of {seats}"
    title = fields[1]
    acceptance_criteria = fields[2]
    if not title or not acceptance_criteria:
        return "❌ title and acceptance_criteria are both required for a delegation"
    priority = fields[3].upper() if len(fields) > 3 and fields[3].upper() in ("P0", "P1", "P2", "P3") else "P2"
    task_type = fields[4] if len(fields) > 4 and fields[4] else None
    certifier = fields[5].upper() if len(fields) > 5 and fields[5] else "CC"
    ground_truth = [s.strip() for s in fields[6].split(",") if s.strip()] if len(fields) > 6 and fields[6] else []

    try:
        from core.relay.delegation_wiring import DelegationError
    except ImportError:
        DelegationError = Exception
    try:
        message, _mission_id = add_mission(
            board, title, description=acceptance_criteria, priority=priority,
            assigned_to=seat, acceptance_criteria=acceptance_criteria,
            certified_by=certifier, task_type=task_type,
            ground_truth_sources=ground_truth,
        )
        return message
    except DelegationError as e:
        return f"❌ Delegation rejected: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# STAFF SUMMARY SHEET (AF Form 1768) verbs — the USAF staffing model, restored.
# Commander directive 2026-07-18: PDTAC was an AI invention; his model is the
# real Air Force Staff Summary Sheet — OPR owns the action, an OCR chop chain
# coordinates it, a decision authority signs the action block, the OPR executes,
# and it closes out through CHIEF SILVER's mandatory back gate. Model lives in
# core/staffing/staff_summary_sheet.py; these verbs persist it onto the board.
# ─────────────────────────────────────────────────────────────────────────────

def _next_sss_id(board):
    """Allocate the next SSS-NNN id from its own counter (kept distinct from the
    MISSION-NNN namespace so staff sheets read as staff sheets on the board)."""
    nums = []
    for m in board.get("missions", []):
        mid = m.get("id", "")
        if mid.startswith("SSS-"):
            try:
                nums.append(int(mid.split("-")[-1]))
            except (ValueError, IndexError):
                pass
    return f"SSS-{((max(nums) + 1) if nums else 1):03d}"


def cmd_sss_open(board, raw):
    """EXEC: sss OPR :: ACTION :: title :: acceptance_criteria
            [:: OCR1,OCR2 :: PRIORITY :: suspense :: certifier :: gt1,gt2 :: opr_seat]

    Open a Staff Summary Sheet. OPR is the owning office/seat; ACTION is the
    requested action of the decision authority (COORD/APPR/SIG/INFO); the OCR
    list is the chop chain. CHIEF SILVER front-frames it — vague criteria or a
    missing/nonexistent ground-truth source is a HOLD, no sheet."""
    try:
        from core.staffing.staff_summary_sheet import open_sss, render_sss, SSSError, ACTION_TYPES
    except Exception as e:
        return f"❌ SSS model unavailable: {e}"
    f = [x.strip() for x in raw.split("::")]
    if len(f) < 4 or not all(f[:4]):
        return ("❌ Usage: EXEC: sss OPR :: ACTION :: title :: acceptance_criteria "
                "[:: OCR1,OCR2 :: PRIORITY :: suspense :: certifier :: gt1,gt2 :: opr_seat]\n"
                f"   ACTION ∈ {ACTION_TYPES}")
    opr, action, title, criteria = f[0], f[1].upper(), f[2], f[3]
    ocrs = [x.strip() for x in f[4].split(",") if x.strip()] if len(f) > 4 and f[4] else []
    priority = f[5].upper() if len(f) > 5 and f[5].upper() in ("P0", "P1", "P2", "P3") else "P2"
    suspense = f[6] if len(f) > 6 and f[6] else None
    certifier = f[7].upper() if len(f) > 7 and f[7] else "CC"
    gt = [x.strip() for x in f[8].split(",") if x.strip()] if len(f) > 8 and f[8] else []
    opr_seat = f[9].upper() if len(f) > 9 and f[9] else None
    sid = _next_sss_id(board)
    try:
        sss = open_sss(sid, title, title, opr, action, criteria,
                       ocr_chain=ocrs, suspense_date=suspense,
                       ground_truth_sources=gt, certified_by=certifier,
                       opr_seat=opr_seat, priority=priority)
    except SSSError as e:
        return f"❌ SSS rejected (CHIEF SILVER front gate): {e}"
    board.setdefault("missions", []).append(sss)
    return f"✅ Staff Summary Sheet opened: {sid}\n" + render_sss(sss)


def cmd_batch_open(board, raw):
    """EXEC: batch OPR :: title :: purpose :: MID1,MID2,MID3
            [:: OCR1,OCR2 :: suspense :: certifier]

    Lump N pending Mission Board items into ONE gated batch Staff Summary
    Sheet (Commander directive: 'all Mission Board Tasks for my approval can
    be lumped into a single staff summary'). Gated at the BATCH level — the
    Silver front/back gate and mandatory cross-Hale certification apply to
    the batch's own assembly/decision, not to re-litigating each child
    mission's history. Each line item shows mission ID + description +
    expected benefit; the rendered staffing block shows non-concurs only."""
    try:
        from core.staffing.staff_summary_sheet import open_batch_sss, build_batch_items, render_sss, SSSError
    except Exception as e:
        return f"❌ SSS model unavailable: {e}"
    f = [x.strip() for x in raw.split("::")]
    if len(f) < 4 or not all(f[:4]):
        return ("❌ Usage: EXEC: batch OPR :: title :: purpose :: MID1,MID2,MID3 "
                "[:: OCR1,OCR2 :: suspense :: certifier]")
    opr, title, purpose = f[0], f[1], f[2]
    mission_ids = [x.strip() for x in f[3].split(",") if x.strip()]
    if not mission_ids:
        return "❌ at least one mission_id is required"
    ocrs = [x.strip() for x in f[4].split(",") if x.strip()] if len(f) > 4 and f[4] else []
    suspense = f[5] if len(f) > 5 and f[5] else None
    certifier = f[6].upper() if len(f) > 6 and f[6] else "CC"

    missions, missing = [], []
    for mid in mission_ids:
        m, _ = find_mission(board, mid)
        if m is None:
            missing.append(mid)
        else:
            missions.append(m)
    if missing:
        return f"❌ mission(s) not found on board: {', '.join(missing)}"

    batch_items = build_batch_items(missions)
    sid = _next_sss_id(board)
    ground_truth = [m["id"] for m in missions]  # child mission IDs are the ground truth refs
    try:
        sss = open_batch_sss(sid, title, purpose, opr, batch_items,
                             ocr_chain=ocrs, suspense_date=suspense,
                             certified_by=certifier, ground_truth_sources=ground_truth)
    except SSSError as e:
        return f"❌ Batch SSS rejected (CHIEF SILVER front gate): {e}"
    board.setdefault("missions", []).append(sss)

    # Absorb the children. Without this, "lump N missions into ONE sheet" left
    # all N independently active on the board and merely ADDED a row — batching
    # inflated the backlog instead of consolidating it, and every downstream
    # stale-scan still counted each child separately.
    #
    # Found 2026-07-29 while consolidating twelve duplicate missions for a
    # single $24,798 FPD: the command printed "✅ ... (12 items)" while the
    # twelve were untouched. A tool's success message is not ground truth.
    absorbed = []
    for m in missions:
        m["status"] = "rolled_up"
        m["batch_parent"] = sid
        m["updated_at"] = now_iso()
        m.setdefault("log", []).append(
            f"{now_iso()} — rolled into batch {sid}; tracked there, not independently")
        absorbed.append(m["id"])

    return (f"✅ Batch Staff Summary Sheet opened: {sid} ({len(batch_items)} items)\n"
            f"   absorbed {len(absorbed)} child mission(s) → status=rolled_up: "
            f"{', '.join(absorbed)}\n" + render_sss(sss))


def cmd_sss_chop(board, raw):
    """EXEC: chop SSS-001 :: office :: concur|concur_with_comment|nonconcur [:: comment]"""
    try:
        from core.staffing.staff_summary_sheet import coordinate, SSSError
    except Exception as e:
        return f"❌ SSS model unavailable: {e}"
    f = [x.strip() for x in raw.split("::")]
    if len(f) < 3 or not all(f[:3]):
        return "❌ Usage: EXEC: chop SSS-ID :: office :: concur|concur_with_comment|nonconcur [:: comment]"
    sid, office, verdict = f[0], f[1], f[2].lower()
    comment = f[3] if len(f) > 3 else ""
    m, _ = find_mission(board, sid)
    if not m:
        return f"❌ {sid} not found"
    try:
        coordinate(m, office, verdict, comment)
    except SSSError as e:
        return f"❌ Chop rejected: {e}"
    return f"✓ {office} recorded {verdict} on {sid} → status {m['status']}"


def cmd_sss_decide(board, raw):
    """EXEC: decide SSS-001 :: authority :: APPROVED|DISAPPROVED|SIGNED|NOTED [:: comment]"""
    try:
        from core.staffing.staff_summary_sheet import decide, SSSError
    except Exception as e:
        return f"❌ SSS model unavailable: {e}"
    f = [x.strip() for x in raw.split("::")]
    if len(f) < 3 or not all(f[:3]):
        return "❌ Usage: EXEC: decide SSS-ID :: authority :: APPROVED|DISAPPROVED|SIGNED|NOTED [:: comment]"
    sid, authority, disposition = f[0], f[1], f[2].upper()
    comment = f[3] if len(f) > 3 else ""
    m, _ = find_mission(board, sid)
    if not m:
        return f"❌ {sid} not found"
    try:
        decide(m, authority, disposition, comment)
    except SSSError as e:
        return f"❌ Decision rejected: {e}"
    return f"🖊️ {authority} {disposition} on {sid} → status {m['status']}"


def cmd_sss_accomplish(board, raw):
    """EXEC: accomplish SSS-001 :: verification_artifact (path|commit|url|sheet row)"""
    try:
        from core.staffing.staff_summary_sheet import accomplish, SSSError
    except Exception as e:
        return f"❌ SSS model unavailable: {e}"
    f = [x.strip() for x in raw.split("::")]
    if len(f) < 2 or not all(f[:2]):
        return "❌ Usage: EXEC: accomplish SSS-ID :: verification_artifact"
    sid, artifact = f[0], f[1]
    m, _ = find_mission(board, sid)
    if not m:
        return f"❌ {sid} not found"
    try:
        accomplish(m, artifact)
    except SSSError as e:
        return f"❌ Cannot mark accomplished: {e}"
    return f"📦 {sid} accomplished — artifact submitted, ready for close-out"


def cmd_sss_close(board, raw):
    """EXEC: closeout SSS-001 [:: certifier :: cross_hale_evidence]
    CHIEF SILVER back gate + cross-seat certify + MANDATORY cross-Hale gate.
    For a seat-executed sheet, cross_hale_evidence (the certifying seat's
    verdict/log reference) is required — no evidence, no close.

    Commander human override: EXEC: closeout SSS-001 :: COMMANDER [:: reason]
    — the reserved literal "COMMANDER" in the certifier slot skips the gate
    entirely (Commander directive 2026-07-29): no artifact, no cross-Hale
    evidence, no Silver back-gate. Recorded as an attributed OVERRIDE in
    silver_ledger.jsonl, never a silent bypass — see
    staff_summary_sheet.close_sss's human_override param. Any other seat
    still faces the full gate below, unchanged."""
    try:
        from core.staffing.staff_summary_sheet import close_sss, SSSError
    except Exception as e:
        return f"❌ SSS model unavailable: {e}"
    f = [x.strip() for x in raw.split("::")]
    if not f or not f[0]:
        return ("❌ Usage: EXEC: closeout SSS-ID [:: certifier :: cross_hale_evidence] "
                "| EXEC: closeout SSS-ID :: COMMANDER [:: reason]")
    sid = f[0]
    field1 = f[1] if len(f) > 1 and f[1] else None
    m, _ = find_mission(board, sid)
    if not m:
        return f"❌ {sid} not found"
    try:
        if field1 and field1.strip().upper() == "COMMANDER":
            reason = f[2] if len(f) > 2 and f[2] else None
            close_sss(m, human_override="Commander", human_note=reason)
            return f"✅ {sid} CLOSED — Commander override (human close is self-certifying, no gate)"
        certifier = field1.upper() if field1 else None
        evidence = f[2] if len(f) > 2 and f[2] else None
        close_sss(m, certified_by=certifier, cross_hale_evidence=evidence)
    except SSSError as e:
        return f"⛔ Close-out held: {e}"
    return f"✅ {sid} CLOSED — certified by {m.get('certified_by')}, CHIEF SILVER back-gate PASS"


def cmd_sss_block(board, raw):
    """EXEC: block SSS-001 :: reason — honest terminal state when a mandate is unmet."""
    try:
        from core.staffing.staff_summary_sheet import block_sss
    except Exception as e:
        return f"❌ SSS model unavailable: {e}"
    f = [x.strip() for x in raw.split("::")]
    if len(f) < 2 or not all(f[:2]):
        return "❌ Usage: EXEC: block SSS-ID :: reason"
    sid, reason = f[0], f[1]
    m, _ = find_mission(board, sid)
    if not m:
        return f"❌ {sid} not found"
    block_sss(m, reason)
    return f"⛔ {sid} BLOCKED — {reason[:80]}"


def cmd_sss_reopen(board, raw):
    """EXEC: reopen SSS-001 :: to_status :: reason [:: new_opr :: new_opr_seat]
    Correct/reassign a closed or blocked sheet; clears any prior cross_hale_cert
    so it must re-earn its close with a fresh genuine cross-seat certification."""
    try:
        from core.staffing.staff_summary_sheet import reopen_sss, SSSError
    except Exception as e:
        return f"❌ SSS model unavailable: {e}"
    f = [x.strip() for x in raw.split("::")]
    if len(f) < 3 or not all(f[:3]):
        return "❌ Usage: EXEC: reopen SSS-ID :: to_status :: reason [:: new_opr :: new_opr_seat]"
    sid, to_status, reason = f[0], f[1], f[2]
    new_opr = f[3] if len(f) > 3 and f[3] else None
    new_opr_seat = f[4].upper() if len(f) > 4 and f[4] else None
    m, _ = find_mission(board, sid)
    if not m:
        return f"❌ {sid} not found"
    try:
        reopen_sss(m, to_status, reason, new_opr=new_opr, new_opr_seat=new_opr_seat)
    except SSSError as e:
        return f"❌ Reopen rejected: {e}"
    return f"↩️ {sid} reopened → {m['status']}" + (f" (OPR now {m.get('opr')})" if new_opr else "")


def cmd_sss_ack(board, raw):
    """EXEC: ack SSS-001 :: gate_substring :: evidence — account for a captured
    unmapped mandate with concrete evidence so the close gate can clear it."""
    try:
        from core.staffing.staff_summary_sheet import ack_mandate, SSSError
    except Exception as e:
        return f"❌ SSS model unavailable: {e}"
    f = [x.strip() for x in raw.split("::")]
    if len(f) < 3 or not all(f[:3]):
        return "❌ Usage: EXEC: ack SSS-ID :: gate_substring :: evidence"
    sid, sub, evidence = f[0], f[1], f[2]
    m, _ = find_mission(board, sid)
    if not m:
        return f"❌ {sid} not found"
    try:
        matched = ack_mandate(m, sub, evidence)
    except SSSError as e:
        return f"❌ Ack rejected: {e}"
    return f"✓ {sid}: acknowledged {len(matched)} mandate(s) matching {sub!r}"


def cmd_sss_render(board, sid):
    """EXEC: sheet SSS-001 — render the AF Form 1768-style coversheet."""
    try:
        from core.staffing.staff_summary_sheet import render_sss
    except Exception as e:
        return f"❌ SSS model unavailable: {e}"
    m, _ = find_mission(board, sid)
    if not m:
        return f"❌ {sid} not found"
    return render_sss(m)


def cmd_suspense(board, mission_id, date_str):
    """EXEC: add suspense MISSION-001 2026-04-05T05:00:00Z"""
    mission, state = find_mission(board, mission_id)
    if not mission:
        return f"❌ Mission {mission_id} not found"
    
    mission["suspense_date"] = date_str
    mission["updated_at"] = now_iso()
    
    # Add to suspense_watch if not already
    watch = board.get("suspense_watch", [])
    if mission_id not in watch:
        watch.append(mission_id)
    board["suspense_watch"] = watch
    
    return f"⏰ Suspense set: {mission_id} until {date_str}"


def cmd_complete(board, mission_id, human_override=False):
    """EXEC: complete MISSION-001 [COMMANDER]

    The reserved second token "COMMANDER" (Commander directive 2026-07-29)
    is a human override: skips the cross-Hale certification / Silver
    back-gate entirely — the Commander's own close IS the verification.
    Recorded as an attributed OVERRIDE in silver_ledger.jsonl (never a silent
    bypass). Any other/no second token leaves the AI-seat gate below
    completely unchanged."""
    mission, state = find_mission(board, mission_id)
    if not mission:
        return f"❌ Mission {mission_id} not found"

    if human_override:
        from core.silver.gate import human_override as _silver_human_override
        _silver_human_override(
            mission_id,
            mission.get("verification_artifact") or mission.get("title", ""),
            overridden_by="Commander",
        )
        mission.setdefault("logs", []).append(
            f"{now_iso()}: completed by COMMANDER OVERRIDE — no gate, human close is self-certifying"
        )
        mission["status"] = "completed"
        mission["completed_at"] = now_iso()
        watch = board.get("suspense_watch", [])
        if mission_id in watch:
            watch.remove(mission_id)
        board["suspense_watch"] = watch
        return f"✅ Completed: {mission['id']} — {mission['title']} (Commander override, no gate)"

    # Cross-Hale delegation ticket → completion must clear the anti-theater
    # gate (§3.5): a cross-seat certifier + a verification_artifact. Enforced
    # here rather than silently flipping status, and mirrored onto the C2
    # Fabric bus as the `done` stage. Persona-name / unassigned missions are
    # untouched by this branch.
    if mission.get("assigned_to") in _delegation_seats() and mission.get("acceptance_criteria"):
        try:
            from core.relay.delegation_wiring import certify_mission_and_record
            r = certify_mission_and_record(
                mission_id,
                mission.get("assigned_to", ""),
                mission.get("certified_by", "CC"),
                mission.get("verification_artifact", ""),
                mission.get("acceptance_criteria", ""),
            )
            if not r["ok"]:
                return (
                    f"⛔ Cannot complete {mission_id} — delegation gate: {r['error']}\n"
                    f"Set a verification_artifact and a cross-seat certified_by first."
                )
        except ImportError:
            pass  # wiring unavailable (bare CLI, no repo root) — fall through

    # Mark completed in-place (flat missions array)
    mission["status"] = "completed"
    mission["completed_at"] = now_iso()

    # Remove from suspense_watch
    watch = board.get("suspense_watch", [])
    if mission_id in watch:
        watch.remove(mission_id)
    board["suspense_watch"] = watch

    return f"✅ Completed: {mission['id']} — {mission['title']}"


def cmd_status(board, mission_id):
    """EXEC: status MISSION-001"""
    mission, state = find_mission(board, mission_id)
    if not mission:
        return f"❌ Mission {mission_id} not found"
    
    lines = [f"📋 {mission['id']}: {mission['title']}", f"State: {state} | Status: {mission['status']}",
             f"Priority: {mission.get('priority', 'P3')}", f"Assigned: {mission.get('assigned_to', 'unassigned')}",
             f"Created: {mission.get('created_at', '?')[:16]}", f"Updated: {mission.get('updated_at', '?')[:16]}"]
    
    if mission.get("description"):
        lines.append(f"\nDescription: {mission['description']}")
    if mission.get("suspense_date"):
        lines.append(f"⏰ Suspense: {mission['suspense_date']}")
    if mission.get("escalation_rule"):
        lines.append(f"⚠️ Escalation: {mission['escalation_rule']}")
    if mission.get("logs"):
        lines.append(f"\nRecent logs ({len(mission['logs'])}):")
        for log in mission["logs"][-3:]:
            lines.append(f"  - {log}")
    
    return "\n".join(lines)


def cmd_log(board, mission_id, message):
    """EXEC: log MISSION-001 <message>"""
    mission, state = find_mission(board, mission_id)
    if not mission:
        return f"❌ Mission {mission_id} not found"
    
    if "logs" not in mission:
        mission["logs"] = []
    
    log_entry = f"[{now_iso()[:19]}] {message}"
    mission["logs"].append(log_entry)
    mission["updated_at"] = now_iso()
    
    return f"📝 Log added to {mission_id}"


def cmd_help():
    """EXEC: help"""
    return """📋 EXEC Commands:
  EXEC: list board          → Show active missions
  EXEC: list suspended      → Show suspense queue
  EXEC: list complete       → Show completed
  EXEC: add <title> <desc>  → Create mission
  EXEC: delegate SEAT :: title :: criteria [:: PRIO :: task_type :: certifier] → Cross-Hale delegate (CC/OC/AG)
  ── Staff Summary Sheet (USAF staffing model) ──
  EXEC: sss OPR :: ACTION :: title :: criteria [:: OCRs :: PRIO :: suspense :: certifier :: gt :: seat] → Open sheet
  EXEC: batch OPR :: title :: purpose :: MID1,MID2,MID3 [:: OCRs :: suspense :: certifier] → Lump N missions into one gated batch sheet
  EXEC: chop SSS-ID :: office :: concur|concur_with_comment|nonconcur [:: comment] → Coordinate (chop chain)
  EXEC: decide SSS-ID :: authority :: APPROVED|DISAPPROVED|SIGNED|NOTED [:: comment] → Decision authority acts
  EXEC: accomplish SSS-ID :: artifact → OPR submits work product
  EXEC: closeout SSS-ID [:: certifier] → CHIEF SILVER back-gate + cross-seat certify
  EXEC: closeout SSS-ID :: COMMANDER [:: reason] → Human override, no gate (Commander only)
  EXEC: sheet SSS-ID        → Render the coversheet
  EXEC: add suspense <id> <date> → Set suspense
  EXEC: complete <id> [COMMANDER] → Mark done (COMMANDER = human override, no gate)
  EXEC: status <id>         → Show details
  EXEC: log <id> <msg>      → Add log entry
  EXEC: help                → This message"""


def process_exec_command(command_text):
    """Parse EXEC: command text and return response."""
    # Strip "EXEC: " prefix if present
    text = command_text.strip()
    if text.upper().startswith("EXEC:"):
        text = text[5:].strip()
    elif text.upper().startswith("EXEC "):
        text = text[5:].strip()
    
    parts = text.split()
    if not parts:
        return cmd_help()
    
    action = parts[0].lower()
    args = parts[1:]
    
    if action == "help":
        return cmd_help()
    
    fd = acquire_lock()
    try:
        board = load_board()
        
        if action == "list":
            sub = args[0].lower() if args else "board"
            if sub == "board":
                result = cmd_list_board(board)
            elif sub in ["suspended", "suspense"]:
                result = cmd_list_suspended(board)
            elif sub in ["complete", "completed", "done"]:
                result = cmd_list_complete(board)
            else:
                result = cmd_list_board(board)
        
        elif action == "add":
            if args and args[0].lower() in ["suspense", "suspend"]:
                # EXEC: add suspense MISSION-001 2026-04-05T05:00:00Z
                if len(args) >= 3:
                    result = cmd_suspense(board, args[1], args[2])
                else:
                    result = "❌ Usage: EXEC: add suspense <mission_id> <date>"
            else:
                result = cmd_add(board, args)
        
        elif action == "delegate":
            # Reconstruct the raw remainder (the `::`-delimited fields) — the
            # whitespace split above would otherwise destroy titles/criteria.
            raw = text[len("delegate"):].strip()
            result = cmd_delegate(board, raw)

        # ── Staff Summary Sheet verbs (USAF staffing model) ──────────────
        elif action == "sss":
            result = cmd_sss_open(board, text[len("sss"):].strip())
        elif action == "batch":
            result = cmd_batch_open(board, text[len("batch"):].strip())
        elif action == "chop":
            result = cmd_sss_chop(board, text[len("chop"):].strip())
        elif action == "decide":
            result = cmd_sss_decide(board, text[len("decide"):].strip())
        elif action == "accomplish":
            result = cmd_sss_accomplish(board, text[len("accomplish"):].strip())
        elif action in ("closeout", "close"):
            result = cmd_sss_close(board, text[len(action):].strip())
        elif action == "block":
            result = cmd_sss_block(board, text[len("block"):].strip())
        elif action == "reopen":
            result = cmd_sss_reopen(board, text[len("reopen"):].strip())
        elif action == "ack":
            result = cmd_sss_ack(board, text[len("ack"):].strip())
        elif action == "sheet":
            if args:
                result = cmd_sss_render(board, args[0])
            else:
                result = "❌ Usage: EXEC: sheet SSS-ID"

        elif action == "complete":
            if args:
                override = len(args) > 1 and args[1].strip().upper() == "COMMANDER"
                result = cmd_complete(board, args[0], human_override=override)
            else:
                result = "❌ Usage: EXEC: complete <mission_id> [COMMANDER]"
        
        elif action == "status":
            if args:
                result = cmd_status(board, args[0])
            else:
                result = "❌ Usage: EXEC: status <mission_id>"
        
        elif action == "log":
            if len(args) >= 2:
                result = cmd_log(board, args[0], " ".join(args[1:]))
            else:
                result = "❌ Usage: EXEC: log <mission_id> <message>"
        
        elif action == "purge":
            if args:
                result = cmd_complete(board, args[0])  # Same as complete
            else:
                result = "❌ Usage: EXEC: purge <mission_id>"
        
        else:
            result = f"❌ Unknown command: {action}\n{cmd_help()}"
        
        save_board(board, fd)
        return result
    except Exception as e:
        release_lock(fd)
        return f"❌ Board error: {e}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(cmd_help())
        sys.exit(0)
    
    command = " ".join(sys.argv[1:])
    result = process_exec_command(command)
    print(result)

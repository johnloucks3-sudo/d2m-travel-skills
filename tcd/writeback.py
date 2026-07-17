"""
writeback — close the loop: AppSheet edits → real Python actions.

The Sheet is a two-way contract. ``sheet_sync`` pushes Python's view of the
world OUT to the Sheet; this module reads what the Commander/staff changed IN
AppSheet and acts on it BEFORE the next sync overwrites those cells. The
``status`` column is the Commander's plain-English action menu:

  * ``status`` flipped to ``Delete``   → real cascade delete at the source
    (``tcd_data.delete_item``), same mechanism as the live custom TCD's
    delete-with-cascade (Gmail→trash, standing-orders/dossiers→OpsCenter/
    tcd_trash, hale_state entries removed + JSONL-backed). The source record
    is gone, so the next sync's collectors simply won't re-emit that item —
    no separate suppression list needed.
  * ``status`` flipped to ``Closed``   → marks the item done. Audit-logged
    same as Delete, but nothing at the source is touched — the item just
    stops being live work. (Distinct from Delete: Closed keeps the record;
    Delete removes it permanently.)
  * ``Modify`` is not a status value — it's AppSheet's native row-edit
    (every column is directly editable in the app; no special action needed).
  * ``stage`` changed from what Python last wrote (a manual P-D-T-A-C move,
    e.g. Commander drags an item from D to T) → logged as a stage-transition
    audit entry. Not enforced/reverted — the Commander's move IS the record.
  * ``comments`` grew (new text appended in AppSheet)                → logged
    as a comment audit entry, per SO_PDTAC_WORKFLOW_20260711 ("staff can
    submit comments at any phase"). If the newly-added text contains the
    ``[CREATE_TASK_REQUESTED]`` marker (the FYI-kind "Create Task" action)
    a real mission is filed via ``OpsCenter/mission_board_sync.py``'s
    locking primitives — see ``CREATE_TASK_MARKER``/``_handle_create_task``.

All actions append to hale_decisions.md, the canonical audit trail, using the
same PLAN:CLOSE format the rest of the Wing already parses (tcd_data.
build_outbox's noise filter, the decision-inbox tooling, etc.).

State is tracked in ``config/tcd_writeback_state.json`` — a cache of the last
snapshot per row id, so we can diff "what AppSheet has now" against "what we
last wrote" without re-processing the same edit twice. Reruns are safe.
"""
import json
from datetime import datetime, timezone

from core.silver.gate import silver_front_frame, run_gate

from . import _imports
from . import assignment
from . import overrides as _overrides
from .item_model import SHEET_COLUMNS
from .sheet_sync import CONFIG_PATH as SHEET_CONFIG_PATH, TAB_NAME

ROOT = _imports.ROOT
STATE_PATH = ROOT / "config" / "tcd_writeback_state.json"
HALE_DECISIONS = ROOT / "hale_decisions.md"

WATCHED_FIELDS = ("status", "stage", "comments")

# Row ids that represent genuinely delegated Wing work — the same class
# core/relay/delegation_wiring.py already front-frames. These carry a real
# deliverable and a seat commitment, so "done" must be framed before the
# D->T auto-task hands them off. Every OTHER row type (gmail-/dossier-/so-/
# alert-/elon-/task-/proj-) is surfaced context or already-in-motion ops:
# auto-tasking it is routing, not a work-product commitment, so it stays
# ungated (still audit-logged — never a silent skip). Sterling (A7)
# scoping decision, MISSION-658.
DELEGATED_WORK_PREFIXES = ("mission-", "watch-")


def _is_delegated_work(row: dict) -> bool:
    return (row.get("id", "") or "").startswith(DELEGATED_WORK_PREFIXES)


def _load_json(path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
    tmp.replace(path)


def read_sheet_rows() -> list:
    """Current Items tab contents as SHEET_COLUMNS-keyed dicts.

    Reads live from Google Sheets — requires the sheet to already exist
    (created by ``python -m tcd.sheet_sync``).
    """
    cfg = _load_json(SHEET_CONFIG_PATH, {})
    sheet_id = cfg.get("spreadsheet_id")
    if not sheet_id:
        raise RuntimeError(
            "No Sheet configured yet — run `python -m tcd.sheet_sync` first."
        )
    gauth = _imports.load_google_auth()
    sheets = gauth.get_sheets()
    res = sheets.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=TAB_NAME).execute()
    values = res.get("values", [])
    if not values:
        return []
    header = values[0]
    rows = []
    for raw in values[1:]:
        row = dict(zip(header, raw))
        for col in SHEET_COLUMNS:
            row.setdefault(col, "")
        rows.append(row)
    return rows


def _plan_id(row_id: str, kind: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"TCD-{kind}-{row_id}-{stamp}"


def _append_decision(plan_id: str, verdict: str, criteria_met: str, notes: str,
                     decisions_path) -> None:
    """Append a PLAN:CLOSE block in the same format hale_decisions.md already uses."""
    closed_at = datetime.now(timezone.utc).isoformat()
    block = (
        f"\n<!-- PLAN:CLOSE plan_id={plan_id} verdict={verdict} closed_at={closed_at} -->\n"
        f"**Plan Closed:** {plan_id}\n"
        f"**Verdict:** {verdict}\n"
        f"**Quality tier:** trivial\n"
        f"**Criteria met:** {criteria_met}\n"
        f"**Notes:** {notes}\n"
    )
    decisions_path.parent.mkdir(parents=True, exist_ok=True)
    with decisions_path.open("a", encoding="utf-8") as f:
        f.write(block)


def _handle_dispose(row: dict, delete_fn, decisions_path, overrides_path=None) -> dict:
    """Execute the real cascade delete for a row flipped to status=Delete."""
    result = delete_fn(row["id"])
    verdict = "PASS" if result.get("ok") else "FAIL"
    notes = (f"source={result.get('source', '?')}"
             if result.get("ok") else f"reason={result.get('reason', '?')}")
    _append_decision(
        _plan_id(row["id"], "DELETE"), verdict,
        criteria_met=f"TCD delete: {row.get('title', row['id'])[:80]}",
        notes=notes, decisions_path=decisions_path,
    )
    _overrides.clear_override(row["id"], path=overrides_path)
    return result


def _gate_note(verdict) -> str:
    """One-line human summary of a Silver back-gate verdict for the audit trail."""
    if verdict.ok:
        return "Silver back-gate PASS."
    return "Silver back-gate HOLD: " + "; ".join(verdict.holds)[:200]


def _handle_close(row: dict, decisions_path) -> None:
    """Mark a row Closed — the row's ``comments`` are the staff verification
    artifact (SO_PDTAC_WORKFLOW_20260711), so Silver's back-gate decides the
    verdict instead of the old unconditional PASS. On HOLD the close is still
    recorded (AppSheet's own state isn't blocked) but ``run_gate`` pages it the
    same way it pages a held delegated mission — never a silent PASS."""
    artifact = row.get("comments", "")
    verdict = run_gate(artifact, artifact, mission_id=row["id"])
    _append_decision(
        _plan_id(row["id"], "CLOSE"), verdict.verdict,
        criteria_met=f"TCD closed: {row.get('title', row['id'])[:80]}",
        notes=("Marked Closed by Commander in AppSheet; source record untouched. "
               + _gate_note(verdict)),
        decisions_path=decisions_path,
    )


def _handle_stage_move(row: dict, prior_stage: str, decisions_path,
                       to_stage: str = None) -> None:
    dest = to_stage if to_stage is not None else row.get("stage", "")
    # A move INTO Certify (C) is a certification claim — gate it for real.
    # Every other stage move is just an audited record of the move itself.
    if dest == "C":
        artifact = row.get("comments", "")
        verdict = run_gate(artifact, artifact, mission_id=row["id"])
        result, notes = verdict.verdict, f"{prior_stage or '(new)'} -> {dest}. " + _gate_note(verdict)
    else:
        result, notes = "PASS", f"{prior_stage or '(new)'} -> {dest}"
    _append_decision(
        _plan_id(row["id"], "STAGE"), result,
        criteria_met=f"TCD stage move: {row.get('title', row['id'])[:80]}",
        notes=notes, decisions_path=decisions_path,
    )


def _handle_auto_task(row: dict, decisions_path, overrides_path=None):
    """D -> T: the instant an item is Approved, Hale tasks it to a staff seat.

    For delegated-work rows (see ``_is_delegated_work``) Silver's FRONT frame
    must pass first — "done" has to be concretely defined before a seat is
    committed. On HOLD the row is NOT tasked: it stays at D (no owner, no T
    override), the HOLD is audit-logged AND surfaced into the row's own
    ``comments`` so AppSheet shows exactly why nothing happened, and ``None``
    is returned. This is the actual bug MISSION-658 fixes — a silent auto-task
    with no framing — so the HOLD is always visible, never a quiet skip.
    Because no override is set, the next full sheet_sync re-derives the row
    back to P (needs-a-decision) — its natural resting state — so once the
    Commander adds the missing criteria a re-approve re-frames it cleanly,
    rather than the row being pinned dead at D.

    On PASS (or an ungated row) it persists the T stage + owner as an override
    (see tcd/overrides.py) so this survives the next sheet_sync, and audit-logs
    it distinctly from the Commander's own P->D decision (both fire from a
    single Approve click, but they're two different actors' actions and should
    read that way in hale_decisions.md). Returns the assigned owner.
    """
    if _is_delegated_work(row):
        frame = silver_front_frame(
            row["id"], row.get("title", ""),
            acceptance_criteria=row.get("comments", ""),
            ground_truth_sources=[row.get("sourcePath", "")],
        )
        if not frame.ok:
            reason = "; ".join(frame.holds)[:300]
            note = f"[SILVER HOLD — not tasked] {reason}"
            row["comments"] = (row.get("comments", "")
                               + ("\n" if row.get("comments") else "") + note)
            _append_decision(
                _plan_id(row["id"], "TASK"), "HOLD",
                criteria_met=f"TCD auto-task HELD: {row.get('title', row['id'])[:80]}",
                notes=note, decisions_path=decisions_path,
            )
            return None
    owner = assignment.assign_owner(row)
    _overrides.set_override(row["id"], stage="T", owner=owner, path=overrides_path)
    _append_decision(
        _plan_id(row["id"], "TASK"), "PASS",
        criteria_met=f"TCD auto-task: {row.get('title', row['id'])[:80]}",
        notes=f"D -> T, assigned to {owner}",
        decisions_path=decisions_path,
    )
    return owner


def _handle_comment(row: dict, prior_comments: str, decisions_path) -> None:
    added = row.get("comments", "")[len(prior_comments):].strip()
    _append_decision(
        _plan_id(row["id"], "COMMENT"), "PASS",
        criteria_met=f"TCD comment: {row.get('title', row['id'])[:80]}",
        notes=added[:300] or "(comment field changed)",
        decisions_path=decisions_path,
    )


CREATE_TASK_MARKER = "[CREATE_TASK_REQUESTED]"


def _commander_note(comments: str) -> str:
    """Strip every CREATE_TASK_MARKER occurrence out of the row's comments
    and return whatever free text is left — the Commander's own instruction,
    typed directly into the comments box before/after clicking "Create
    Task". Empty string if the Commander left no note (marker-only)."""
    text = (comments or "").replace(CREATE_TASK_MARKER, " ")
    return " ".join(text.split())


def _default_create_task_fn(row: dict) -> str:
    """File a real Wing Tasking mission from an FYI-kind row's "Create Task"
    action, via the same locking primitives used to file MISSION-001A itself
    (OpsCenter/mission_board_sync.py) — not a cosmetic status flip. Returns
    the new mission id.

    REGRESSION FIX (2026-07-16): this hand-rolled the mission dict and
    appended directly to the board, bypassing mission_board_sync's
    _find_open_duplicate() (Silver/Sterling's 2026-07-04 one-and-done fix)
    entirely. Since TCD became the only C2 channel (2026-07-11), every
    recurring Commander decision routed through here flooded the board with
    duplicates (Regent pricing x4, TESS restore x3+, WF-17 drafts x4, ...).
    Now runs the same dedup check cmd_add uses before filing a new mission."""
    mbs = _imports.load_mission_board_sync()
    fd = mbs.acquire_lock()
    board = mbs.load_board()
    all_missions = board.get("missions", [])
    title = row.get("title", row.get("id", ""))[:120]

    dup = mbs._find_open_duplicate(all_missions, title)
    if dup is not None:
        dup.setdefault("logs", []).append(
            f"{mbs.now_iso()}: duplicate TCD Create Task blocked — \"{title}\" already tracked here "
            f"(source row {row.get('id', '')})"
        )
        dup["updated_at"] = mbs.now_iso()
        mbs.save_board(board, fd)
        return dup["id"]

    nums = []
    for m in all_missions:
        try:
            nums.append(int(m["id"].split("-")[-1]))
        except (ValueError, IndexError, KeyError):
            pass
    mission_id = f"MISSION-{(max(nums) + 1) if nums else 1:03d}"
    source_desc = row.get("body") or row.get("snippet") or row.get("title", "")
    note = _commander_note(row.get("comments", ""))
    description = f"Commander instruction: {note}\n\n{source_desc}" if note else source_desc
    new_mission = {
        "id": mission_id,
        "title": title,
        "status": "pending_review",
        "priority": row.get("priority", "p2").upper() if row.get("priority", "").upper() in
                    ("P0", "P1", "P2", "P3") else "P2",
        "assigned_to": row.get("owner") or "Hale",
        "description": description,
        "deliverables": [],
        "dependencies": [],
        "suspense_date": None,
        "escalation_rule": None,
        "logs": [
            f"[{mbs.now_iso()}] Filed via TCD 'Create Task' action on "
            f"{row.get('id', '')} ({row.get('title', '')[:80]})."
        ],
        "created_at": mbs.now_iso(),
        "updated_at": mbs.now_iso(),
        "source": "tcd_create_task_action",
    }
    board.setdefault("missions", []).append(new_mission)
    board["last_updated"] = mbs.now_iso()
    mbs.save_board(board, fd)
    return mission_id


def _handle_create_task(row: dict, decisions_path, create_task_fn=None) -> str:
    """"Create Task" (FYI-kind action) — files a real mission, not just an
    audit log entry, since the whole point of the action is to turn an FYI
    into tracked work."""
    create_task_fn = create_task_fn or _default_create_task_fn
    mission_id = create_task_fn(row)
    _append_decision(
        _plan_id(row["id"], "CREATETASK"), "PASS",
        criteria_met=f"TCD create-task: {row.get('title', row['id'])[:80]}",
        notes=f"Filed {mission_id} from FYI row {row['id']}.",
        decisions_path=decisions_path,
    )
    return mission_id


def _default_delete_fn(item_id: str) -> dict:
    return _imports.load_tcd_data().delete_item(item_id)


def _default_write_fn(item_id: str, updates: dict) -> None:
    """Push corrected cell values for one row straight back into the live Sheet.

    Needed because ``tcd_process_writeback`` is a real standalone entry point
    (see tcd/mcp_tools.py), not just a step inside sheet_sync — if Hale calls
    it on its own, the auto-tasked "T" only exists in local state/overrides
    until the *next* full sheet_sync, and that next sync's own write-back
    pass would then see the Sheet still literally says "D" and misread it as
    a fresh regression (a real bug caught live: an auto-tasked row's
    override got silently reset D because nothing had told the Sheet cell
    itself). Writing the cell immediately keeps the Sheet, the override, and
    the Commander's own eyes all showing the same value at all times.
    """
    cfg = _load_json(SHEET_CONFIG_PATH, {})
    sheet_id = cfg.get("spreadsheet_id")
    if not sheet_id:
        return
    gauth = _imports.load_google_auth()
    sheets = gauth.get_sheets()
    res = sheets.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=TAB_NAME).execute()
    values = res.get("values", [])
    if not values:
        return
    header = values[0]
    if "id" not in header:
        return
    id_col = header.index("id")
    for i, raw in enumerate(values[1:], start=2):  # 1-indexed + header row
        if len(raw) > id_col and raw[id_col] == item_id:
            row_vals = raw + [""] * (len(header) - len(raw))
            for k, v in updates.items():
                if k in header:
                    row_vals[header.index(k)] = v
            sheets.spreadsheets().values().update(
                spreadsheetId=sheet_id, range=f"{TAB_NAME}!A{i}",
                valueInputOption="RAW", body={"values": [row_vals]}).execute()
            return


def process_once(rows: list = None, *, state_path=None, decisions_path=None,
                 delete_fn=None, overrides_path=None, write_fn=None,
                 create_task_fn=None) -> dict:
    """One write-back pass: diff current Sheet vs. last-known state, act, save.

    All parameters default to production paths/behavior (live Sheet read,
    real cascade delete, real hale_decisions.md, real
    config/tcd_stage_overrides.json). Pass them explicitly for offline/unit
    testing — no credentials, no network, no writes outside a tmp dir.

    Returns a summary dict: {"disposed": [...], "staged": [...], "tasked":
    [...], "commented": [...], "unchanged": N, "errors": [...]}. Never raises
    for a single row's action failure — collects it in "errors" so one bad
    row doesn't block the rest of the batch.
    """
    state_path = state_path or STATE_PATH
    decisions_path = decisions_path or HALE_DECISIONS
    delete_fn = delete_fn or _default_delete_fn
    write_fn = write_fn or _default_write_fn

    prior_state = _load_json(state_path, {})
    if rows is None:
        rows = read_sheet_rows()
    summary = {"disposed": [], "closed": [], "staged": [], "tasked": [],
               "held": [], "commented": [], "created_tasks": [], "unchanged": 0,
               "errors": []}
    new_state = {}

    for row in rows:
        rid = row.get("id", "")
        if not rid:
            continue
        prev = prior_state.get(rid, {})
        changed = False
        held = False  # Silver front-frame HOLD this pass — suppresses the
                      # comment-diff branch below from re-logging our own
                      # auto-appended HOLD note as a Commander comment event.
        row = dict(row)  # local copy — the auto-task branch may rewrite ["stage"]/["comments"]

        if row.get("status") == "Delete" and prev.get("status") != "Delete":
            try:
                result = _handle_dispose(row, delete_fn, decisions_path,
                                         overrides_path=overrides_path)
                summary["disposed"].append({"id": rid, "ok": result.get("ok", False)})
            except Exception as e:
                summary["errors"].append({"id": rid, "action": "dispose", "error": str(e)})
            # Row's source is gone; drop from state so a future re-add (new
            # item that happens to reuse an id) isn't mistaken for this one.
            continue

        if row.get("status") == "Closed" and prev.get("status") != "Closed":
            try:
                _handle_close(row, decisions_path)
                summary["closed"].append({"id": rid})
            except Exception as e:
                summary["errors"].append({"id": rid, "action": "close", "error": str(e)})
            changed = True

        # Approve/Modify (P -> D) gets auto-tasked to a staff seat immediately
        # — "Then HALE takes over" — logged as two events (the Commander's
        # decision, then Hale's tasking) and materialized as T, not D, so the
        # next sync doesn't re-diff D -> T as a second, unattributed move.
        if row.get("stage") == "D" and prev.get("stage") == "P" and "stage" in prev:
            try:
                _handle_stage_move(row, "P", decisions_path, to_stage="D")
                summary["staged"].append({"id": rid, "from": "P", "to": "D"})
                owner = _handle_auto_task(row, decisions_path, overrides_path=overrides_path)
                if owner is None:
                    # Silver front-frame HOLD — stays at D, not tasked. Push the
                    # HOLD note back to the Sheet so AppSheet shows why nothing
                    # advanced; suppress the comment-diff branch for this row.
                    held = True
                    summary["held"].append({"id": rid})
                    try:
                        write_fn(rid, {"stage": "D", "comments": row.get("comments", "")})
                    except Exception as e:
                        summary["errors"].append({"id": rid, "action": "write_sheet", "error": str(e)})
                else:
                    summary["tasked"].append({"id": rid, "owner": owner})
                    row["stage"] = "T"
                    try:
                        write_fn(rid, {"stage": "T", "owner": owner})
                    except Exception as e:
                        summary["errors"].append({"id": rid, "action": "write_sheet", "error": str(e)})
            except Exception as e:
                summary["errors"].append({"id": rid, "action": "task", "error": str(e)})
            changed = True
        elif row.get("stage") != prev.get("stage") and "stage" in prev:
            try:
                _handle_stage_move(row, prev.get("stage", ""), decisions_path)
                summary["staged"].append({"id": rid, "from": prev.get("stage", ""),
                                          "to": row.get("stage", "")})
                _overrides.set_override(rid, stage=row.get("stage", ""), path=overrides_path)
            except Exception as e:
                summary["errors"].append({"id": rid, "action": "stage", "error": str(e)})
            changed = True

        # "comments" in prev (not truthy prev comments!) — a row's FIRST-EVER
        # comment (empty -> text) is a real event and must be logged; only a
        # row never seen before (no cache entry at all) is suppressed, same
        # pattern as the stage check above.
        if (not held and row.get("comments", "") != prev.get("comments", "")
                and "comments" in prev):
            added = row.get("comments", "")[len(prev.get("comments", "")):]
            try:
                _handle_comment(row, prev.get("comments", ""), decisions_path)
                summary["commented"].append({"id": rid})
            except Exception as e:
                summary["errors"].append({"id": rid, "action": "comment", "error": str(e)})
            if CREATE_TASK_MARKER in added:
                try:
                    mission_id = _handle_create_task(row, decisions_path, create_task_fn=create_task_fn)
                    summary["created_tasks"].append({"id": rid, "mission_id": mission_id})
                except Exception as e:
                    summary["errors"].append({"id": rid, "action": "create_task", "error": str(e)})
            changed = True

        if not changed:
            summary["unchanged"] += 1

        new_state[rid] = {k: row.get(k, "") for k in WATCHED_FIELDS}

    _save_json(state_path, new_state)
    return summary


if __name__ == "__main__":
    import sys
    result = process_once()
    print(json.dumps(result, indent=2))
    if result["errors"]:
        sys.exit(1)

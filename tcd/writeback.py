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
    submit comments at any phase").

All actions append to hale_decisions.md, the canonical audit trail, using the
same PLAN:CLOSE format the rest of the Wing already parses (tcd_data.
build_outbox's noise filter, the decision-inbox tooling, etc.).

State is tracked in ``config/tcd_writeback_state.json`` — a cache of the last
snapshot per row id, so we can diff "what AppSheet has now" against "what we
last wrote" without re-processing the same edit twice. Reruns are safe.
"""
import json
from datetime import datetime, timezone

from . import _imports
from .item_model import SHEET_COLUMNS
from .sheet_sync import CONFIG_PATH as SHEET_CONFIG_PATH, TAB_NAME

ROOT = _imports.ROOT
STATE_PATH = ROOT / "config" / "tcd_writeback_state.json"
HALE_DECISIONS = ROOT / "hale_decisions.md"

WATCHED_FIELDS = ("status", "stage", "comments")


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


def _handle_dispose(row: dict, delete_fn, decisions_path) -> dict:
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
    return result


def _handle_close(row: dict, decisions_path) -> None:
    """Mark a row Closed — audit-logged, source untouched (not a delete)."""
    _append_decision(
        _plan_id(row["id"], "CLOSE"), "PASS",
        criteria_met=f"TCD closed: {row.get('title', row['id'])[:80]}",
        notes="Marked Closed by Commander in AppSheet; source record untouched.",
        decisions_path=decisions_path,
    )


def _handle_stage_move(row: dict, prior_stage: str, decisions_path) -> None:
    _append_decision(
        _plan_id(row["id"], "STAGE"), "PASS",
        criteria_met=f"TCD stage move: {row.get('title', row['id'])[:80]}",
        notes=f"{prior_stage or '(new)'} -> {row.get('stage', '')}",
        decisions_path=decisions_path,
    )


def _handle_comment(row: dict, prior_comments: str, decisions_path) -> None:
    added = row.get("comments", "")[len(prior_comments):].strip()
    _append_decision(
        _plan_id(row["id"], "COMMENT"), "PASS",
        criteria_met=f"TCD comment: {row.get('title', row['id'])[:80]}",
        notes=added[:300] or "(comment field changed)",
        decisions_path=decisions_path,
    )


def _default_delete_fn(item_id: str) -> dict:
    return _imports.load_tcd_data().delete_item(item_id)


def process_once(rows: list = None, *, state_path=None, decisions_path=None,
                 delete_fn=None) -> dict:
    """One write-back pass: diff current Sheet vs. last-known state, act, save.

    All parameters default to production paths/behavior (live Sheet read,
    real cascade delete, real hale_decisions.md). Pass them explicitly for
    offline/unit testing — no credentials, no network, no writes outside a
    tmp dir.

    Returns a summary dict: {"disposed": [...], "staged": [...], "commented":
    [...], "unchanged": N, "errors": [...]}. Never raises for a single row's
    action failure — collects it in "errors" so one bad row doesn't block the
    rest of the batch.
    """
    state_path = state_path or STATE_PATH
    decisions_path = decisions_path or HALE_DECISIONS
    delete_fn = delete_fn or _default_delete_fn

    prior_state = _load_json(state_path, {})
    if rows is None:
        rows = read_sheet_rows()
    summary = {"disposed": [], "closed": [], "staged": [], "commented": [],
               "unchanged": 0, "errors": []}
    new_state = {}

    for row in rows:
        rid = row.get("id", "")
        if not rid:
            continue
        prev = prior_state.get(rid, {})
        changed = False

        if row.get("status") == "Delete" and prev.get("status") != "Delete":
            try:
                result = _handle_dispose(row, delete_fn, decisions_path)
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

        if row.get("stage") != prev.get("stage") and "stage" in prev:
            try:
                _handle_stage_move(row, prev.get("stage", ""), decisions_path)
                summary["staged"].append({"id": rid, "from": prev.get("stage", ""),
                                          "to": row.get("stage", "")})
            except Exception as e:
                summary["errors"].append({"id": rid, "action": "stage", "error": str(e)})
            changed = True

        # "comments" in prev (not truthy prev comments!) — a row's FIRST-EVER
        # comment (empty -> text) is a real event and must be logged; only a
        # row never seen before (no cache entry at all) is suppressed, same
        # pattern as the stage check above.
        if row.get("comments", "") != prev.get("comments", "") and "comments" in prev:
            try:
                _handle_comment(row, prev.get("comments", ""), decisions_path)
                summary["commented"].append({"id": rid})
            except Exception as e:
                summary["errors"].append({"id": rid, "action": "comment", "error": str(e)})
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

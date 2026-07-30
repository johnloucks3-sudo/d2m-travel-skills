"""
tcd_actions — turn a Slack button/command tap into a real TCD write-back call.

Why this exists instead of routing Slack through ``tcd.writeback.process_once``
(the way the retired ``tcd/web.py`` Decision Board did): that board worked
because every action landed on a Sheet cell first, and ``process_once`` diffs
the *whole* Sheet against its last-seen cache to figure out what changed. A
Slack tap has no Sheet round-trip in the loop — it names one item and one verb
directly — and some cards (mission-/watch-/techscan- rows surfaced via
``multi_tab.py``, same class ``apply_non_sheet_action`` already carves out)
have no writable Sheet cell to diff in the first place. So this module skips
the diff entirely and calls the same per-row handlers ``process_once`` calls,
hydrated from the live item set instead of a Sheet snapshot — the freshest
ground truth available, and the only one guaranteed to exist for every row.

Every action still lands in ``hale_decisions.md`` and the Silver ledger via
those same handlers — this module adds no second audit trail, just a second
door into the one that already exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Same bootstrap tcd/_imports.py and core/comms/slack_receiver.py already use:
# this module can be imported before anything else has put the repo root on
# sys.path (e.g. a bare `python core/comms/tcd_actions.py` or a unit test
# importing it directly), and `from tcd import ...` below needs ROOT resolvable.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tcd import overrides as _overrides
from tcd import writeback
from tcd.collectors import collect_all
from tcd.item_model import SHEET_COLUMNS

# The only actor string that unlocks writeback._handle_close's self-certifying,
# no-gate branch. Slack is a single-user surface (the Commander's own
# workspace token — see core/comms/commander_channel.py), so 'Commander' is
# the expected default for a real button tap. Deliberately exact-match and
# case-sensitive: a caller passing 'commander' (lowercase, e.g. a copy-paste
# of writeback's own internal literal) is far more likely to be a bug than a
# considered assertion of Commander identity, and must NOT get the bypass by
# accident. Every other value degrades to "ai" so Silver's back-gate stays
# live — the same default every non-Commander writeback caller already gets.
_COMMANDER_ACTOR = "Commander"


def _normalize_actor(actor: str) -> str:
    return "commander" if actor == _COMMANDER_ACTOR else "ai"


def slack_action_to_row(item_id: str, action_id: str, value: str = "",
                        items: list[dict] | None = None) -> dict:
    """Hydrate a SHEET_COLUMNS-keyed row dict for ``item_id`` from the LIVE
    item set (``tcd.collectors.collect_all`` — the same builders
    ``tcd/sheet_sync.py`` calls before every write), not from a Sheet read.

    Two reasons this matters, not just style: (1) the Sheet is only as fresh
    as the last ``tcd-sync.timer`` tick (up to 10 minutes stale), so a Sheet
    read could hand a handler a ``stage``/``comments`` that's already wrong
    by the time the Commander taps a Slack button on it; (2) non-Sheet cards
    (mission-/watch-/techscan- rows, see ``writeback.apply_non_sheet_action``)
    don't have a Sheet row to read at all — the live item set is the only
    place they exist.

    ``items`` lets a caller that already pulled a fresh snapshot this request
    (e.g. the same list used to render the Slack Home view) pass it straight
    through instead of paying for another full collect (which includes two
    Gmail account fetches) on every single button click. Pass explicitly for
    offline/unit testing too — no credentials, no network.

    Raises ``LookupError`` — never returns a partial row — if ``item_id``
    isn't found: a half-populated row here would let a handler write a
    corrupt or misattributed entry straight into hale_decisions.md, the
    Wing's canonical audit trail, with no signal that anything was wrong.
    """
    if items is None:
        items = [it.to_dict() for it in collect_all()]
    for candidate in items:
        if candidate.get("id") == item_id:
            row = dict(candidate)
            for col in SHEET_COLUMNS:
                row.setdefault(col, "")
            return row
    raise LookupError(
        f"tcd_actions.slack_action_to_row: item {item_id!r} not found among "
        f"{len(items)} live items (action={action_id!r}) — refusing to build "
        "a half-populated row. The card may be stale (item disposed/renamed "
        "since the Slack view was rendered) or items= was passed a partial list."
    )


def _fold_note(row: dict, actor: str, action_id: str, value: str) -> dict:
    """Return a copy of ``row`` with ``value`` appended to ``comments``, using
    the same tagged-note convention the retired ``tcd/web.py`` Decision Board
    used (``"[Commander CLOSE via tcd.d2mluxury.quest] ..."``) — one audit
    convention across both surfaces the Commander has used to close items,
    not two. This matters beyond style: ``_handle_close`` reads ``comments``
    as its verification artifact for non-Commander actors, and a stage move
    into "C" gates on it too (see ``_handle_stage_move``'s ``dest == "C"``
    branch) — a Slack-typed reason that never reaches ``comments`` is
    invisible to the gate, which then correctly HOLDs as if nothing was
    typed at all. Never mutates the caller's row.
    """
    if not value:
        return row
    row = dict(row)
    prior = row.get("comments", "")
    tag = f"[Slack {action_id} by {actor}]"
    row["comments"] = f"{prior}\n{tag} {value}".strip() if prior else f"{tag} {value}"
    return row


def apply(item_id: str, action_id: str, *, actor: str = "ai",
         value: str = "") -> dict:
    """Map one Slack action to the existing write-back handler and run it.

    ACTOR DEFAULTS TO "ai" ON PURPOSE — do not change it back.

    actor="Commander" self-certifies past CHIEF SILVER's back gate; "ai" is held to a
    concrete-reference requirement. Defaulting to "Commander" would mean any caller that
    simply forgets the argument silently bypasses an integrity control — fail-open on
    exactly the gate that exists because AI seats have self-reported "done" falsely here
    before. The bypass must be asserted explicitly by a call site that genuinely knows
    the action came from the Commander's own Slack account (slack_receiver's
    handle_block_action does, having read payload["user"]); nothing else earns it.

    This overrides the drafting agent's judgement, which defaulted to "Commander" on the
    reasoning that Slack is a Commander-only surface and the retired tcd/web.py did the
    same unconditionally. Both are true and neither makes a fail-open default correct.

    ``value``'s meaning is action-specific — a single free-text Slack button/
    command payload has to carry either a target stage or a note, never
    both, so unlike ``row["comments"]`` there's no single uniform treatment:
      - close        -> optional free-text reason, folded into comments
                        (see ``_fold_note``) before the gate/override runs.
      - delete       -> ignored; a dispose needs no reason, same as AppSheet.
      - stage        -> REQUIRED target stage letter (P/D/T/A/C). This is
                        NOT note text — folding it into comments here would
                        write literal "D" or "T" into the audit trail instead
                        of moving the row, so it is passed straight through
                        as ``to_stage`` instead.
      - comment      -> REQUIRED comment text, appended verbatim.
      - create_task  -> optional free-text Commander instruction, folded into
                        comments so ``_default_create_task_fn``'s
                        ``_commander_note()`` picks it up the same way it
                        already does for the AppSheet ``[CREATE_TASK_REQUESTED]``
                        path.

    Every handler call below is the exact function ``tcd/writeback.py``
    already runs from ``process_once`` — this module reimplements none of
    their logic, only the row hydration and the action_id -> handler map.
    """
    row = slack_action_to_row(item_id, action_id, value=value)
    decisions_path = writeback.HALE_DECISIONS

    if action_id == "close":
        gate_actor = _normalize_actor(actor)
        noted = _fold_note(row, actor, action_id, value)
        writeback._handle_close(noted, decisions_path, actor=gate_actor)
        return {"ok": True, "action": "close", "id": item_id, "actor": gate_actor}

    if action_id == "delete":
        result = writeback._handle_dispose(row, writeback._default_delete_fn, decisions_path)
        return {"ok": bool(result.get("ok")), "action": "delete", "id": item_id,
                "result": result}

    if action_id == "stage":
        if not value:
            raise ValueError(
                "tcd_actions.apply: 'stage' action requires a target stage "
                "(P/D/T/A/C) in value — refusing to move a row to an undefined stage"
            )
        prior_stage = row.get("stage", "")
        writeback._handle_stage_move(row, prior_stage, decisions_path, to_stage=value)
        # _handle_stage_move only logs the move; it never persists (see its
        # own docstring: "not enforced/reverted"). Without this override the
        # next full tcd-sync.timer clear+rewrite would re-derive the row's
        # stage from source and silently revert this Slack move — the exact
        # bug tcd/overrides.py exists to fix, same pairing process_once's own
        # generic stage-move branch (writeback.py) uses.
        _overrides.set_override(item_id, stage=value)
        return {"ok": True, "action": "stage", "id": item_id,
                "from": prior_stage, "to": value}

    if action_id == "comment":
        if not value.strip():
            raise ValueError(
                "tcd_actions.apply: 'comment' action requires non-empty value text"
            )
        prior_comments = row.get("comments", "")
        row = dict(row)
        row["comments"] = (f"{prior_comments}\n{value}".strip()
                           if prior_comments else value.strip())
        writeback._handle_comment(row, prior_comments, decisions_path)
        return {"ok": True, "action": "comment", "id": item_id}

    if action_id == "create_task":
        noted = _fold_note(row, actor, action_id, value)
        mission_id = writeback._handle_create_task(noted, decisions_path)
        return {"ok": True, "action": "create_task", "id": item_id,
                "mission_id": mission_id}

    raise ValueError(f"tcd_actions.apply: unknown action_id {action_id!r}")

"""
staging — derive each item's P-D-T-A-C stage + workflow status.

P-D-T-A-C ("NO MORE BLACK HOLES", SO_PDTAC_WORKFLOW_20260711):
  P Propose · D Decide · T Task · A Accomplish · C Certify

Phase 0 is a READ-ONLY board, so we derive a sensible *initial* stage from what
each item already is; Phase 2 write-back will advance stages on Commander
action. Reference material (standing orders, dossiers) sits outside the
workflow and is marked ``REF`` with a blank stage.

Deterministic and pure so it unit-tests offline.
"""

STAGES = ("P", "D", "T", "A", "C", "REF")


def derive_stage(item: dict) -> str:
    """Initial P-D-T-A-C stage for a legacy tcd_data item dict.

    P is the ONE and ONLY entry point for anything that needs the Commander's
    decision — staff proposals, alerts, decisions, incoming email, missions
    awaiting review. Nothing here ever pre-assigns D: the Commander is the
    only one who moves an item P -> D (Approve/Modify in AppSheet). Only
    already-decided, already-in-motion work (an active task, a running
    project) starts past P, because Hale already has the authority to run it.
    """
    fid = item.get("id", "") or ""
    itype = item.get("type", "")

    # Reference material — not part of the decision workflow.
    if item.get("inbox") == "reference" or fid.startswith(("so-", "dossier-")):
        return "REF"

    # Staff proposals, decisions, and alerts — all need a Commander call.
    if fid.startswith("elon-") or itype == "paper":
        return "P"
    if itype == "decision" or fid.startswith("alert-"):
        return "P"

    # Incoming email — needs triage before it becomes a task.
    if fid.startswith("gmail-"):
        return "P"

    # Wing Tasking missions (OpsCenter/mission_board.json), folded into the
    # same PDTAC pipeline instead of a separate untracked taxonomy.
    if fid.startswith("mission-"):
        status = item.get("status", "")
        if status in ("done", "complete", "completed"):
            return "C"
        if status in ("blocked", "blocked_awaiting_human"):
            return "T"
        if status == "active":
            return "A"                  # already decided, Hale has it running
        return "P"                      # pending_review and anything else

    # Active operational work — already decided, Hale is running it.
    if fid.startswith("task-"):
        status = ""
        for tag in item.get("tags", []) or []:
            if tag in ("active", "blocked", "pending", "done", "complete"):
                status = tag
        if status in ("done", "complete"):
            return "C"
        if status == "blocked":
            return "T"                  # tasked but stalled → needs re-task/decision
        return "A"                      # Accomplishing
    if fid.startswith("proj-"):
        return "A"

    return "P"                          # default: surface for a decision


KINDS = ("proposal", "fyi", "")


def derive_kind(item: dict, stage: str = None) -> str:
    """P=Provide split: "proposal" (needs Approve/Disapprove/Modify) vs "fyi"
    (needs Acknowledge/Create Task). Only meaningful at stage P — blank for
    every other stage, including REF.

    ``stage`` defaults to a fresh ``derive_stage(item)`` call but should be
    passed explicitly by callers that already have the override-adjusted
    stage (e.g. ``tcd/collectors.py``) — this mirrors the AppSheet virtual
    column, which reads the actual ``stage`` cell on the Sheet (post-
    override), not a recomputation from scratch.

    Commander's own model: "P=Provide, either Provide Info (FYI) or Provide
    a Proposal for Consideration." Proposals are the items with a real $/
    strategic call attached (financial deferred alerts, ELON tech papers,
    Wing Tasking missions awaiting Approve->D->T); everything else that
    reaches P is informational triage, not a decision seeking approval.
    """
    if (stage if stage is not None else derive_stage(item)) != "P":
        return ""
    fid = item.get("id", "") or ""
    itype = item.get("type", "")
    if itype in ("decision", "paper") or fid.startswith("mission-"):
        return "proposal"
    return "fyi"


STATUSES = ("Open", "Reference", "Closed", "Delete")


def derive_status(item: dict, stage: str) -> str:
    """Workflow status column — plain English, this is the Commander's dropdown.

    REF items start ``Reference``; everything else starts ``Open``. The
    Commander sets ``Closed`` (done, no side effect, just audit-logged) or
    ``Delete`` (real cascade removal at the source) directly in AppSheet;
    Phase 0 (this function) never emits either — that's write-back's job
    (tcd/writeback.py) once the Commander acts.
    """
    if stage == "REF":
        return "Reference"
    return "Open"

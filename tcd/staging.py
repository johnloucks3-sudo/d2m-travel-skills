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
    """Initial P-D-T-A-C stage for a legacy tcd_data item dict."""
    fid = item.get("id", "") or ""
    itype = item.get("type", "")

    # Reference material — not part of the decision workflow.
    if item.get("inbox") == "reference" or fid.startswith(("so-", "dossier-")):
        return "REF"

    # Strategic decisions & proposals awaiting the Commander.
    if fid.startswith("elon-") or itype == "paper":
        return "P"                      # Proposed, awaiting Decide
    if itype == "decision" or fid.startswith("alert-"):
        return "D"                      # In the Decide queue

    # Incoming email — needs triage before it becomes a task.
    if fid.startswith("gmail-"):
        return "P"

    # Active operational work.
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

    return "D"                          # default: surface for a decision


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

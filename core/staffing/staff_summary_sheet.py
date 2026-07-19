"""
core/staffing/staff_summary_sheet.py — the USAF Staff Summary Sheet (AF Form 1768)
model, restored as the Wing's native staffing/tasking workflow.

Commander directive 2026-07-18: the "PDTAC" sequence (Propose→Decide→Task→
Accomplish→Certify) was an AI invention, not his mental model. His model is the
real Air Force staff process — the Staff Summary Sheet routed through a
coordination (chop) chain to a decision authority, then tasked to an OPR and
closed out. This module integrates that model FIRST; the rest of the rebuild is
then run *through* it (each work item is an SSS).

Real-process mapping (Tongue & Quill ch.18 / AF Form 1768 / DoD TMT-CATMS):

    OPR  — Office of Primary Responsibility. Owns the action end to end.
    OCR  — Office(s) of Coordinating Responsibility. The chop chain: each
           reviews in listed order and records concur / concur-w-comment /
           nonconcur. A nonconcur is not a veto — it is recorded and routed to
           the decision authority to adjudicate.
    Action block — what the OPR requests of the decision authority:
           COORD (coordination only) · APPR (approval) · SIG (signature) · INFO.
    Suspense — the deadline with teeth (already a mission-board field).
    Close-out — the last step returns the package to the OPR for final action.

Lifecycle (status):
    drafted → in_coordination → coordinated → decided → tasked → accomplished
            → closed              (blocked is the escalation sink)

Two mandatory overlays the Commander stood up, preserved here:
  • CHIEF SILVER front + back gate (core/silver/gate.py) — front-frame before an
    SSS opens (no checkable "done" → no SSS); back-gate before it closes.
  • Anti-theater cross-seat certification — an SSS executed by an AI seat
    (CC/OC/AG) cannot be closed by that same seat; the certifier must differ.

This module operates on plain mission dicts so it composes with
OpsCenter/mission_board_sync.py (which owns the file + lock) and with
core/relay/delegation_wiring.py (which owns the C2-bus seat handoff). It never
writes the board or the bus directly except the best-effort bus mirror for
seat-executed sheets.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import re

from core.silver.gate import silver_front_frame, run_gate
from core.relay.task_delegation import SEATS

# Commander directive 2026-07-18: **CROSS-HALE COORDINATION IS MANDATORY.** For a
# seat-executed sheet this is a hard close gate, not a goal: the sheet cannot
# close unless a *different engine* (CC/OC/AG) genuinely certified THIS artifact
# with concrete evidence, AND the assigned OPR seat did not fail. A same-engine
# CC backstop of a failed seat is NOT cross-Hale coordination and must not close
# as if the delegation succeeded — it BLOCKS. (This gate was missing on
# 2026-07-18 and a failed AG sheet was wrongly closed; that is what it prevents.)
_CROSS_HALE_EVIDENCE = re.compile(r"/|@|\bhttps?://|\.[a-z]{2,4}\b|#\d|\brow\b", re.I)

# Requested action of the decision authority (AF Form 1768 action block).
ACTION_TYPES = ("COORD", "APPR", "SIG", "INFO")

# A coordinating office's chop. Nonconcur is recorded, not a veto.
CHOP_VERDICTS = ("concur", "concur_with_comment", "nonconcur")

# Decision-authority dispositions of the action block.
DISPOSITIONS = ("APPROVED", "DISAPPROVED", "SIGNED", "NOTED")

SSS_STAGES = (
    "drafted", "in_coordination", "coordinated",
    "decided", "tasked", "accomplished", "closed", "blocked",
)


class SSSError(Exception):
    """Raised when a Staff Summary Sheet invariant is violated (bad stage
    transition, Silver HOLD, or anti-theater self-certification)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _opr_seat(sss: dict) -> Optional[str]:
    """The AI seat that actually executes this sheet, for Silver/anti-theater/bus
    purposes. Explicit `opr_seat` wins; otherwise the OPR itself iff it is a seat.
    An office/persona OPR (e.g. 'Dani') has no seat — returns None."""
    seat = (sss.get("opr_seat") or "").strip()
    if seat in SEATS:
        return seat
    opr = (sss.get("opr") or "").strip()
    return opr if opr in SEATS else None


def _is_cross_hale(sss: dict) -> bool:
    """True when this sheet is executed by an AI seat — the case where the
    Commander's MANDATORY cross-Hale coordination applies. Pure human-office
    staffing (OPR = a persona, no seat) is out of scope for the seat gate."""
    return _opr_seat(sss) is not None or (sss.get("opr") or "").strip() in SEATS


def _opr_failed(sss: dict) -> Optional[str]:
    """Did the assigned OPR itself signal it could not deliver? Returns the
    failure reason if the coordination log carries a `nonconcur` from the OPR's
    own office/seat, else None. A failed OPR means the cross-Hale delegation did
    not happen — the sheet must block, not close on a backstop."""
    opr = (sss.get("opr") or "").strip().lower()
    seat = (_opr_seat(sss) or "").lower()
    for e in sss.get("coordination_log", []):
        if e.get("verdict") == "nonconcur" and e.get("office", "").strip().lower() in (opr, seat):
            return e.get("comment", "") or "OPR nonconcur"
    return None


def _unmet_mandates(sss: dict) -> list[str]:
    """Every mandate bound to this sheet (from the directive ledger) that is not
    satisfied at close. `cross_hale` needs a recorded cross-Hale cert; `silver`
    is met by this module's unconditional front+back gates; an `unmapped:` gate
    (a mandatory directive with no structural enforcement yet) always blocks
    unless explicitly acknowledged in sss['mandate_ack'] — so a NEW mandatory
    clue can never be silently skipped."""
    ack = sss.get("mandate_ack") or {}
    unmet: list[str] = []
    for gate in sss.get("mandates", []):
        if gate == "cross_hale":
            if _is_cross_hale(sss) and not sss.get("cross_hale_cert"):
                unmet.append("cross_hale: no cross-Hale certification recorded")
        elif gate == "silver":
            continue  # front+back gates run unconditionally in this module
        elif gate not in ack:
            unmet.append(f"{gate}: mandatory directive with no structural gate and no ack")
    return unmet


def _mirror_bus(sss: dict, stage: str, detail: str, *, confirmed: bool = False) -> None:
    """Best-effort C2-bus mirror for seat-executed sheets — a broken relay never
    blocks the durable SSS field write. No-op for office/persona OPRs."""
    if not _opr_seat(sss):
        return
    try:
        from core.relay.delegation_wiring import mirror_stage_to_bus, LIFECYCLE_STAGES
        # Map SSS stages onto the delegation bus vocabulary where they differ.
        bus_stage = {
            "drafted": "proposed", "in_coordination": "proposed",
            "coordinated": "proposed", "decided": "assigned",
            "tasked": "assigned", "accomplished": "pending_review",
            "closed": "done", "blocked": "blocked",
        }.get(stage, stage)
        if bus_stage in LIFECYCLE_STAGES:
            mirror_stage_to_bus(sss.get("id", "SSS-?"), bus_stage, detail,
                                confirmed_delivered=confirmed)
    except Exception:
        pass


# ── OPEN — draft the sheet + front-frame it ────────────────────────────────

def open_sss(
    sss_id: str,
    title: str,
    purpose: str,
    opr: str,
    action_type: str,
    acceptance_criteria: str,
    *,
    ocr_chain: Optional[list[str]] = None,
    suspense_date: Optional[str] = None,
    ground_truth_sources: Optional[list[str]] = None,
    opr_seat: Optional[str] = None,
    certified_by: str = "CC",
    priority: str = "P2",
) -> dict:
    """Draft a Staff Summary Sheet and run CHIEF SILVER's mandatory front frame.

    `acceptance_criteria` must be concrete enough that a second office could
    verify "done" without asking the OPR (Silver enforces this). `ocr_chain` is
    the ordered list of coordinating offices. Raises SSSError on a Silver HOLD or
    an unknown action_type. Returns the SSS mission dict (status in_coordination,
    or coordinated when there are no OCRs to chop)."""
    action_type = (action_type or "").upper()
    if action_type not in ACTION_TYPES:
        raise SSSError(f"action_type must be one of {ACTION_TYPES}, got {action_type!r}")
    if not (opr or "").strip():
        raise SSSError("an SSS requires an OPR (Office of Primary Responsibility)")

    # CHIEF SILVER FRONT FRAME — MANDATORY. No checkable 'done', no sheet.
    frame = silver_front_frame(sss_id, title, acceptance_criteria, ground_truth_sources or [])
    if not frame.ok:
        raise SSSError("CHIEF SILVER front-frame HOLD — " + "; ".join(frame.holds))

    chain = [
        {"office": o.strip(), "status": "pending", "comment": "", "ts": ""}
        for o in (ocr_chain or []) if o.strip()
    ]
    sss = {
        "id": sss_id,
        "title": title,
        "purpose": purpose,
        "opr": opr.strip(),
        "assigned_to": opr.strip(),          # back-compat alias (deprecated)
        "action_type": action_type,
        "ocr_chain": chain,
        "coordination_log": [],
        "acceptance_criteria": acceptance_criteria.strip(),
        "ground_truth_sources": ground_truth_sources or [],
        "verification_artifact": "",
        "certified_by": certified_by,
        "silver_front_frame": frame.ts,
        "suspense_date": suspense_date,
        "priority": priority,
        "status": "in_coordination" if chain else "coordinated",
        "created_at": _now(),
        "updated_at": _now(),
        "logs": [],
    }
    if opr_seat and opr_seat in SEATS:
        sss["opr_seat"] = opr_seat
    # Bind every MANDATORY directive captured this discussion onto the sheet, so
    # the close gate enforces all of them — not just the ones I remembered.
    try:
        from core.staffing.directive_ledger import active_gate_keys
        sss["mandates"] = active_gate_keys()
    except Exception:
        sss["mandates"] = []
    seat = _opr_seat(sss)
    if seat and certified_by == seat:
        raise SSSError(
            f"anti-theater: certified_by ({certified_by}) must differ from the "
            f"executing OPR seat ({seat})"
        )
    sss["logs"].append(f"{_now()}: SSS opened — OPR {opr}, action {action_type}, "
                       f"{len(chain)} OCR(s) to coordinate")
    _mirror_bus(sss, sss["status"], f"SSS {sss_id} opened → OPR {opr} | {title[:60]}")
    return sss


# ── COORDINATE — the chop chain ─────────────────────────────────────────────

def coordinate(sss: dict, office: str, verdict: str, comment: str = "") -> dict:
    """Record one coordinating office's chop. `verdict` ∈ CHOP_VERDICTS. A
    nonconcur is recorded (with its comment) and routed to the decision authority
    — it does not veto. When every OCR in the chain has chopped, the sheet moves
    to `coordinated` and is ready for a decision. Mutates and returns the sheet."""
    verdict = (verdict or "").lower()
    if verdict not in CHOP_VERDICTS:
        raise SSSError(f"chop verdict must be one of {CHOP_VERDICTS}, got {verdict!r}")
    if sss.get("status") not in ("in_coordination", "coordinated"):
        raise SSSError(f"cannot coordinate an SSS in status {sss.get('status')!r}")
    if verdict == "concur_with_comment" and not comment.strip():
        raise SSSError("concur_with_comment requires a comment")
    if verdict == "nonconcur" and not comment.strip():
        raise SSSError("a nonconcur must state its reason (comment required)")

    ts = _now()
    sss.setdefault("coordination_log", []).append(
        {"office": office.strip(), "verdict": verdict, "comment": comment.strip(), "ts": ts}
    )
    matched = False
    for entry in sss.get("ocr_chain", []):
        if entry["office"].lower() == office.strip().lower() and entry["status"] == "pending":
            entry.update(status=verdict, comment=comment.strip(), ts=ts)
            matched = True
            break
    if not matched:
        # Ad-hoc coordinator not in the original chain — append it, chopped.
        sss.setdefault("ocr_chain", []).append(
            {"office": office.strip(), "status": verdict, "comment": comment.strip(), "ts": ts}
        )

    pending = [e for e in sss.get("ocr_chain", []) if e["status"] == "pending"]
    if not pending:
        sss["status"] = "coordinated"
    sss["updated_at"] = ts
    sss["logs"].append(f"{ts}: {office} {verdict}"
                       + (f" — {comment[:80]}" if comment else ""))
    return sss


# ── DECIDE — the decision authority signs the action block ──────────────────

def decide(sss: dict, authority: str, disposition: str, comment: str = "") -> dict:
    """The decision authority acts on the action block. `disposition` ∈
    DISPOSITIONS. APPROVED/SIGNED/NOTED advance the sheet to `tasked` (the OPR now
    executes). DISAPPROVED closes the sheet dead. A sheet with unresolved
    nonconcurs may still be decided — that is precisely the authority's job.
    Mutates and returns the sheet."""
    disposition = (disposition or "").upper()
    if disposition not in DISPOSITIONS:
        raise SSSError(f"disposition must be one of {DISPOSITIONS}, got {disposition!r}")
    if sss.get("status") not in ("in_coordination", "coordinated"):
        raise SSSError(f"cannot decide an SSS in status {sss.get('status')!r} "
                       "(must be coordinated / in_coordination)")

    ts = _now()
    nonconcurs = [e for e in sss.get("ocr_chain", []) if e["status"] == "nonconcur"]
    sss["decision"] = {"authority": authority.strip(), "disposition": disposition,
                       "comment": comment.strip(), "ts": ts,
                       "adjudicated_nonconcurs": [e["office"] for e in nonconcurs]}
    sss.setdefault("coordination_log", []).append(
        {"office": f"{authority} (decision authority)", "verdict": disposition,
         "comment": comment.strip(), "ts": ts}
    )
    if disposition == "DISAPPROVED":
        sss["status"] = "closed"
        sss["completed_at"] = ts
        sss["logs"].append(f"{ts}: DISAPPROVED by {authority} — sheet closed dead")
        _mirror_bus(sss, "blocked", f"SSS {sss['id']} DISAPPROVED by {authority}")
    else:
        sss["status"] = "tasked"
        sss["logs"].append(f"{ts}: {disposition} by {authority} — OPR {sss.get('opr')} tasked to execute")
        _mirror_bus(sss, "tasked", f"SSS {sss['id']} {disposition} → OPR {sss.get('opr')} executing")
    sss["updated_at"] = ts
    return sss


# ── ACCOMPLISH — the OPR submits the work product ───────────────────────────

def accomplish(sss: dict, verification_artifact: str) -> dict:
    """The OPR reports the action accomplished, submitting a concrete
    verification artifact (path | commit | url | sheet row). Moves the sheet to
    `accomplished` (pending close-out). Mutates and returns the sheet."""
    if sss.get("status") != "tasked":
        raise SSSError(f"cannot accomplish an SSS in status {sss.get('status')!r} (must be tasked)")
    if not (verification_artifact or "").strip():
        raise SSSError("accomplish requires a concrete verification_artifact")
    ts = _now()
    sss["verification_artifact"] = verification_artifact.strip()
    sss["status"] = "accomplished"
    sss["updated_at"] = ts
    sss["logs"].append(f"{ts}: OPR reported accomplished — artifact {verification_artifact[:80]}")
    _mirror_bus(sss, "accomplished", f"SSS {sss['id']} accomplished — {verification_artifact[:80]}")
    return sss


# ── CLOSE-OUT — Silver back-gate + anti-theater cross-seat certify ──────────

def close_sss(sss: dict, certified_by: Optional[str] = None,
              cross_hale_evidence: Optional[str] = None) -> dict:
    """Close the sheet out. Enforces, in order:
      1. anti-theater — certifier must differ from the executing OPR (§ cross-seat)
      2. MANDATORY cross-Hale gate (seat-executed sheets) — a different engine
         genuinely certified THIS artifact (concrete `cross_hale_evidence`), and
         the OPR seat did not fail; a failed OPR BLOCKS, it does not close.
      3. a non-empty verification_artifact and acceptance_criteria
      4. CHIEF SILVER back gate on the actual artifact (deterministic battery)
    Raises SSSError on any failure. On success moves the sheet to `closed`."""
    if sss.get("status") != "accomplished":
        raise SSSError(f"cannot close an SSS in status {sss.get('status')!r} (must be accomplished)")
    certifier = (certified_by or sss.get("certified_by") or "CC").strip()
    owner = _opr_seat(sss) or (sss.get("opr") or "").strip()
    if certifier == owner:
        raise SSSError(
            f"anti-theater: certifier ({certifier}) must differ from the OPR ({owner}) "
            "— no self-certification"
        )

    # MANDATORY CROSS-HALE GATE (Commander directive 2026-07-18). Seat-executed
    # sheets only — human-office staffing is out of scope.
    if _is_cross_hale(sss):
        if certifier not in SEATS:
            raise SSSError(
                f"mandatory cross-Hale: a seat-executed sheet must be certified by a real "
                f"cross-Hale seat (CC/OC/AG), got {certifier!r}")
        failed = _opr_failed(sss)
        if failed:
            raise SSSError(
                f"mandatory cross-Hale: OPR {owner} failed to deliver ({failed[:80]}). A "
                "same-engine backstop is not cross-Hale coordination — BLOCK the sheet, or "
                "reopen and reassign it explicitly (fresh OPR + genuine cross-seat cert). "
                "Do not close it as a completed delegation.")
        ev = (cross_hale_evidence or "").strip()
        if not ev or not _CROSS_HALE_EVIDENCE.search(ev):
            raise SSSError(
                f"mandatory cross-Hale: no concrete evidence that {certifier} independently "
                "verified THIS artifact — pass cross_hale_evidence (the certifying seat's "
                "verdict/log reference for this sheet).")
        sss["cross_hale_cert"] = {"seat": certifier, "evidence": ev, "ts": _now()}

    # Every MANDATORY directive bound at open must be satisfied — the structural
    # backstop against a missed clue (this is the fix for the 2026-07-18 miss).
    unmet = _unmet_mandates(sss)
    if unmet:
        raise SSSError("unmet mandatory directive(s): " + "; ".join(unmet))

    artifact = (sss.get("verification_artifact") or "").strip()
    criteria = (sss.get("acceptance_criteria") or "").strip()
    if not artifact:
        raise SSSError("no verification_artifact — cannot close")
    if not criteria:
        raise SSSError("no acceptance_criteria — nothing to validate against")

    # CHIEF SILVER BACK GATE — MANDATORY. Deterministic battery on the artifact.
    v = run_gate(artifact, criteria, mission_id=sss.get("id", "SSS-?"))
    if not v.ok:
        raise SSSError("CHIEF SILVER back-gate HOLD — " + "; ".join(v.holds))

    ts = _now()
    sss["certified_by"] = certifier
    sss["status"] = "closed"
    sss["completed_at"] = ts
    sss["updated_at"] = ts
    sss["logs"].append(f"{ts}: closed — certified by {certifier}, Silver back-gate PASS")

    # Scorecard evidence for the executing seat (best-effort).
    seat = _opr_seat(sss)
    if seat:
        try:
            from core.silver.scorecard import record
            record(seat, category="sss", outcome="pass", ref=sss.get("id"))
        except Exception:
            pass
    _mirror_bus(sss, "closed", f"SSS {sss['id']} closed — certified by {certifier}", confirmed=True)
    return sss


# ── BLOCK / REASSIGN — honest handling of a failed OPR ──────────────────────

def block_sss(sss: dict, reason: str) -> dict:
    """Move a sheet to `blocked` — the honest terminal state when the mandatory
    cross-Hale coordination did not happen (e.g. the OPR seat failed and no
    genuine cross-seat delivery is available). A blocked sheet is NOT done."""
    ts = _now()
    sss["status"] = "blocked"
    sss["blocked_reason"] = reason
    sss["updated_at"] = ts
    sss["logs"].append(f"{ts}: BLOCKED — {reason}")
    _mirror_bus(sss, "blocked", f"SSS {sss['id']} blocked: {reason[:80]}")
    return sss


def reopen_sss(sss: dict, to_status: str, reason: str, *,
               new_opr: Optional[str] = None, new_opr_seat: Optional[str] = None) -> dict:
    """Correct the record: move a closed/blocked sheet back to an earlier live
    stage, optionally reassigning the OPR. This is the explicit OPR-reassignment
    path — a reassigned sheet must re-earn its close through a fresh genuine
    cross-seat certification; any prior cross_hale_cert is cleared."""
    if to_status not in ("in_coordination", "coordinated", "tasked", "accomplished"):
        raise SSSError(f"reopen target must be a live stage, got {to_status!r}")
    ts = _now()
    prev = sss.get("status")
    if new_opr:
        sss["opr"] = new_opr.strip()
        sss["assigned_to"] = new_opr.strip()
    if new_opr_seat is not None:
        if new_opr_seat and new_opr_seat in SEATS:
            sss["opr_seat"] = new_opr_seat
        else:
            sss.pop("opr_seat", None)
    sss.pop("completed_at", None)
    sss.pop("cross_hale_cert", None)
    sss.pop("blocked_reason", None)
    sss["status"] = to_status
    sss["updated_at"] = ts
    reassigned = f" — OPR now {sss.get('opr')}" if new_opr else ""
    sss["logs"].append(f"{ts}: REOPENED {prev}→{to_status}{reassigned} — {reason}")
    return sss


# ── RENDER — the coversheet view ────────────────────────────────────────────

def render_sss(sss: dict) -> str:
    """Render the sheet as an AF Form 1768-style coversheet for the Commander."""
    L = [
        "═══════════════════════════════════════════════════════════",
        f"  STAFF SUMMARY SHEET — {sss.get('id')}",
        "═══════════════════════════════════════════════════════════",
        f"  SUBJECT : {sss.get('title')}",
        f"  PURPOSE : {sss.get('purpose')}",
        f"  OPR     : {sss.get('opr')}"
        + (f"  (seat: {sss['opr_seat']})" if sss.get('opr_seat') else ""),
        f"  ACTION  : {sss.get('action_type')}   PRIORITY: {sss.get('priority')}"
        f"   SUSPENSE: {sss.get('suspense_date') or '—'}",
        f"  STATUS  : {sss.get('status', '').upper()}",
        "  ─────────────────────────────────────────────────────────",
        "  COORDINATION (chop chain):",
    ]
    for e in sss.get("ocr_chain", []):
        mark = {"concur": "✓", "concur_with_comment": "✓*", "nonconcur": "✗",
                "pending": "…"}.get(e["status"], e["status"])
        L.append(f"    [{mark}] {e['office']:<14}"
                 + (f" — {e['comment']}" if e.get("comment") else ""))
    if not sss.get("ocr_chain"):
        L.append("    (none)")
    if sss.get("decision"):
        d = sss["decision"]
        L.append("  ─────────────────────────────────────────────────────────")
        L.append(f"  DECISION: {d['disposition']} by {d['authority']}"
                 + (f" — {d['comment']}" if d.get("comment") else ""))
    L += [
        "  ─────────────────────────────────────────────────────────",
        f"  ACCEPTANCE CRITERIA: {sss.get('acceptance_criteria')}",
        f"  VERIFICATION ARTIFACT: {sss.get('verification_artifact') or '(pending)'}",
        f"  CERTIFIED BY: {sss.get('certified_by')}"
        + ("  ✅ CLOSED" if sss.get("status") == "closed" else ""),
        "═══════════════════════════════════════════════════════════",
    ]
    return "\n".join(L)


# ── Self-test: one SSS end to end, asserting Silver + anti-theater fire ─────
if __name__ == "__main__":
    import tempfile, os
    from pathlib import Path as _P

    # Isolate CHIEF SILVER's ledger so the self-test never writes the live
    # OpsCenter/silver_ledger.jsonl / hale_decisions.md audit trail.
    from core.silver import gate as _gate
    _sandbox = _P(tempfile.mkdtemp())
    _gate.LEDGER = _sandbox / "silver_ledger.jsonl"
    _gate.DECISIONS = _sandbox / "hale_decisions.md"
    from core.staffing import directive_ledger as _dl
    _dl.LEDGER = _sandbox / "mandatory_directives.jsonl"

    # A real artifact for Silver's back gate to pass (exists, non-empty, and
    # contains the number the criteria promise).
    fd, path = tempfile.mkstemp(suffix=".txt", text=True)
    with os.fdopen(fd, "w") as f:
        f.write("SSS self-test artifact: 3 stages exercised, all gates fired.\n")

    passed = 0

    # 1. Front-frame HOLD on vague criteria (Silver mandatory).
    try:
        open_sss("SSS-T0", "vague", "prove the model", opr="CC",
                 action_type="APPR", acceptance_criteria="make it good",
                 ground_truth_sources=[])
        print("[FAIL] vague criteria accepted")
    except SSSError as e:
        assert "front-frame HOLD" in str(e)
        print("[PASS] Silver front-frame HOLD on vague criteria"); passed += 1

    # 2. Happy path, office OPR, two-office chop, decision, accomplish, close.
    sss = open_sss(
        "SSS-T1", "Restore the USAF staffing model",
        "Prove the SSS runs end to end", opr="Dani", action_type="APPR",
        acceptance_criteria=f"artifact written to {path} with 3 stages",
        ocr_chain=["Sterling", "Silver"],
        ground_truth_sources=[path],
        certified_by="Hale",
    )
    assert sss["status"] == "in_coordination", sss["status"]
    print("[PASS] SSS opened → in_coordination, front-frame passed"); passed += 1

    coordinate(sss, "Sterling", "concur")
    assert sss["status"] == "in_coordination"        # one OCR still pending
    coordinate(sss, "Silver", "concur_with_comment", "watch the anti-theater gate")
    assert sss["status"] == "coordinated", sss["status"]
    print("[PASS] chop chain complete → coordinated"); passed += 1

    decide(sss, "Commander", "APPROVED")
    assert sss["status"] == "tasked", sss["status"]
    print("[PASS] decision authority APPROVED → tasked"); passed += 1

    accomplish(sss, path)
    assert sss["status"] == "accomplished"

    # anti-theater: OPR cannot certify its own sheet
    try:
        close_sss(sss, certified_by="Dani")
        print("[FAIL] self-certification accepted")
    except SSSError as e:
        assert "anti-theater" in str(e)
        print("[PASS] anti-theater blocks self-certification"); passed += 1

    close_sss(sss, certified_by="Hale")
    assert sss["status"] == "closed", sss["status"]
    print("[PASS] cross-office certify + Silver back-gate → closed"); passed += 1

    # 3. Silver back-gate HOLD on a bogus artifact (bare claim, not a ref).
    sss2 = open_sss("SSS-T2", "gate check", "prove back-gate bites", opr="OC",
                    action_type="COORD",
                    acceptance_criteria=f"file at {path} exists with 3 stages",
                    ground_truth_sources=[path], certified_by="CC", opr_seat="OC")
    decide(sss2, "Hale", "NOTED")
    accomplish(sss2, "done, trust me")           # bare claim, no concrete ref
    try:
        close_sss(sss2, certified_by="CC", cross_hale_evidence="logs/oc_verify.log@ok")
        print("[FAIL] back-gate passed a bare claim")
    except SSSError as e:
        assert "back-gate HOLD" in str(e)
        print("[PASS] Silver back-gate HOLD on bare-claim artifact"); passed += 1

    # 4. MANDATORY cross-Hale gate: a failed OPR seat cannot close on a backstop.
    sss3 = open_sss("SSS-T3", "failed-seat sheet", "prove the mandatory gate",
                    opr="AG", action_type="COORD",
                    acceptance_criteria=f"file {path} has 3 stages",
                    ocr_chain=["AG"], ground_truth_sources=[path],
                    opr_seat="AG", certified_by="CC")
    coordinate(sss3, "AG", "nonconcur", "AG could not deliver")   # OPR itself failed
    decide(sss3, "Hale", "NOTED")
    accomplish(sss3, path)                                        # CC backstop artifact
    try:
        close_sss(sss3, certified_by="CC", cross_hale_evidence="logs/x@ok")
        print("[FAIL] closed a sheet whose OPR seat failed")
    except SSSError as e:
        assert "OPR" in str(e) and "cross-Hale" in str(e)
        print("[PASS] mandatory cross-Hale: failed OPR seat blocks close"); passed += 1

    os.unlink(path)
    print(f"\n{passed}/8 SSS checks passed")
    print("\n" + render_sss(sss))

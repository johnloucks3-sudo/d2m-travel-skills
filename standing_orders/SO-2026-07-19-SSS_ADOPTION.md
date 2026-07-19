# STANDING ORDER — SO-2026-07-19-SSS_ADOPTION

**SUBJECT:** Adoption of the USAF Staff Summary Sheet (AF Form 1768) as the Thunderbird Wing's standing staffing-and-tasking model, replacing "PDTAC" and the decommissioned TCD web application.

**STATUS:** ✅ SIGNED & IN FORCE — 2026-07-19. Commander John A. Loucks III reviewed the package (HTML), then signed the approval document in Google Docs and the Google Sheet. This policy is now standing Wing law. Machine-readable record the models train on.

**OPR:** CC (Hale) · **Coordinated:** OC, AG, Sterling, Naia · **Certifier:** AG · **Action:** SIG

---

## BACKGROUND

The Commander determined that "PDTAC" (Propose-Decide-Task-Accomplish-Certify) was an AI invention, not his mental model, and directed a return to the real USAF Staff Summary Sheet process on a Google-native foundation. Research confirmed PDTAC had dropped the two load-bearing stages of real staff process: the **OCR coordination (chop) chain** and the **suspense date**. Both are restored as first-class, non-optional fields.

## POLICY (adopted articles)

1. **The Staff Summary Sheet is the Wing's standing staffing/tasking model** — OPR, OCR chop chain, action block (COORD / APPR / SIG / INFO), coordination log, suspense date — superseding PDTAC in full. Implementation: `core/staffing/staff_summary_sheet.py`; CLI verbs `sss / chop / decide / accomplish / closeout / sheet / block / reopen` in `OpsCenter/mission_board_sync.py`.

2. **CHIEF SILVER front + back gate is MANDATORY on every sheet.** No checkable "done" → no sheet. Back-gate certification is deterministic, run against the artifact itself.

3. **CROSS-HALE COORDINATION IS MANDATORY.** A seat-executed sheet cannot close unless a *different* engine (CC/OC/AG) certifies the work with concrete, cited evidence. A same-engine backstop of a failed seat does not satisfy this and BLOCKS the sheet from closing as a completed delegation. Enforced in `close_sss` (`_is_cross_hale`, `_opr_failed`, `cross_hale_evidence`).

4. **Every Commander directive is captured and bound.** `core/staffing/directive_ledger.py` records every message, flags mandates, binds them to every sheet; the close gate refuses any unmet mandate. No mandatory obligation rides on memory.

5. **CC integrity double-check before "done."** Before CC declares gated work complete, a different engine verifies its claims against ground truth (`core/staffing/integrity_check.py`). CC's self-report is not evidence of done.

6. **Plan-mode must-haves/must-dos surfaced before execution** (`hooks/plan_mode_mandates.py`, `must_haves_must_dos()`).

## AUTHORITY

**In force 2026-07-19** by signature of the Commander on the Tab-1 approval document (staff package SSS-004), reviewed in HTML, signed in Google Docs and Google Sheets. PDTAC is retired as of this date; references are being retired across standing documentation.

*Prepared cross-Hale, 2026-07-19 MT. Certified by AG. Signed by John A. Loucks III.*

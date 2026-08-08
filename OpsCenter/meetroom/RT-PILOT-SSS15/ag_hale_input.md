# POINT PAPER: AUTO-GENERATED SSS FROM ACTION LOG (RT-PILOT-SSS15)

**BLUF:** Auto-generate Staff Summary Sheets (AF Form 1768) exclusively on *anomalies, self-execution overrides, and milestone clusters* from `delegation_outcomes.jsonl` — never on routine `PASS` runs. OPR belongs to the functional office/executing seat; certifier must remain an independent engine.

---

### 1. Trigger Conditions (Signal vs. Noise)
Auto-drafting an SSS must represent a formal staffing event, not an event stream dump. Three strict triggers:
- **T1: DISCREPANCY / Verification Failure** (`verdict in ("DISCREPANCY", "BLOCKED", "UNVERIFIED")`): Cross-engine or ground-truth check caught real defects, timeout, or spec mismatch.
- **T2: Policy / Sandbox Self-Execution Override** (`action == "self_executed"` with override rationale): Work retained or pulled back due to capability/sandbox limits or credential handling.
- **T3: Multi-Ticket Milestone Batch** (Cluster of $\ge 3$ related `PASS` events in 1h window closing a systemic defect, e.g., OnFailure fleet coverage).
- *Suppression:* Routine isolated `PASS` entries remain in `.jsonl` only.

### 2. Source Mapping (AF Form 1768 Fields)
- **`purpose`**: 1-line BLUF stating the defect/override and requested disposition.
- **`background`**: Task ID, dispatch mode, target subsystem, prior baseline.
- **`discussion`**: Specific findings from `discrepancy_detail`, root cause, ground-truth diff, and test evidence.
- **`recommendation`**: Action block proposal (`APPR` / `INFO` / `COORD`) with numbered remediation steps.

**Worked Example (From `delegation_outcomes.jsonl` line 184: `pilot3-mission-auto-escalate-build1`):**
- `purpose`: Record and resolve 2 functional defects in OC initial build of `scripts/mission_auto_escalate.py`; confirm CC hotfix against live 253-mission board.
- `background`: Task `pilot3` dispatched via `oc_direct_lean` for timezone-aware mission escalation.
- `discussion`: Cross-engine verify caught `AttributeError` on dict `.append()` and typo `escatched_skipped`. CC patched inline; live dry-run confirmed 85 escalated, 28 notify, 0 capped.
- `recommendation`: APPR: 1. Deploy patched script; 2. Add compile preflight to OC task cards.

### 3. Noise Control (Volume Estimate)
- **Active Operations:** 2–4 SSS / day.
- **Steady-State / Maintenance:** 2–5 SSS / week.
- Zero clutter from green routine runs; 100% formal visibility on systemic shifts and caught defects.

### 4. OPR & Action Officer Assignment
- **OPR**: Functional domain office (e.g., `WIND/SED`, `CONDOR/CC`).
- **`opr_seat`**: The seat that executed the build/action (`OC`, `AG`, or `CC`).
- **`certified_by`**: The independent verifying engine (`CC` for OC work; `AG` for CC work).
- **Action Officer**: Orchestrator drafting the SSS into `mission_board.json`.

— V. Hale, VCS

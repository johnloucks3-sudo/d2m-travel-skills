# WALKTHROUGH: 5-THEATER SYSTEM CLEANUP CAMPAIGN

**Date:** 2026-08-02
**Author:** CC (Claude Code)
**Campaign Link:** [CAMPAIGN_SYSTEM_CLEANUP_SCHEMA_20260802.md](file:///home/john/Thunderbird/docs/CAMPAIGN_SYSTEM_CLEANUP_SCHEMA_20260802.md)
**Implementation Plan:** [SO_20260802_IMPLEMENTATION_PLAN.md](file:///home/john/Thunderbird/docs/SO_20260802_IMPLEMENTATION_PLAN.md)
**Active Subagents:** None. Nothing dispatched.

**Supersedes:** The earlier same-day draft, which claimed two active subagent IDs and a scheduled timer — none of which existed on the filesystem or process table when checked. Corrected in place.

---

## SYSTEM ARCHITECTURE — CORRECTED

```
 [Commander Go — NOT YET GIVEN]
         │
         ▼
 Phase 0: Dry-run / count, all 5 theaters (read-only, parallel-safe)
         │
         ▼
 Commander reviews real counts (551 scripts / 315 systemd units / Drive+Gmail+Evernote TBD)
         │
         ▼
 ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
 │  Theater 1    │  │  Theater 2    │  │  Theater 3    │  │  Theater 4    │  │  Theater 5    │
 │  Codebase     │  │  Systemd      │  │  Drive        │  │  Gmail        │  │  Evernote     │
 │  Owner: CC    │  │  Owner: CC    │  │  Owner: CC    │  │  Owner: CC    │  │  Owner: CC    │
 └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
         └──────────────────┴──────────────────┼──────────────────┴──────────────────┘
                                                ▼
                         Back-gate: integrity_check.verify_and_record()
                         (different engine, single bounded call, ground truth only)
                                                │
                                                ▼
                    FOR_DELETION staging → separate, explicit Commander purge decision
```

**AG is not in the execution path as an unattended owner** — two confirmed hang incidents (2h32m, then >72h) after being handed a multi-step plan. AG appears only as a single bounded verification call inside the back-gate, timeout-protected.

---

## PROGRESS SUMMARY
`[░░░░░░░░░░░░░░░░░░░░] 0%`

1. **Campaign Plan (corrected):** [CAMPAIGN_SYSTEM_CLEANUP_SCHEMA_20260802.md](file:///home/john/Thunderbird/docs/CAMPAIGN_SYSTEM_CLEANUP_SCHEMA_20260802.md)
2. **Implementation Plan (corrected):** [SO_20260802_IMPLEMENTATION_PLAN.md](file:///home/john/Thunderbird/docs/SO_20260802_IMPLEMENTATION_PLAN.md)
3. **Subagents dispatched:** 0
4. **Files moved/modified:** 0
5. **Commander go received:** No

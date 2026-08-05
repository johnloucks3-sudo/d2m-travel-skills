# WALKTHROUGH: 5-THEATER SYSTEM CLEANUP CAMPAIGN

**Date:** 2026-08-02 (updated 2026-08-05)
**Author:** CC (Claude Code); Theater 6 executed + documented by OC (HALE-OC)
**Campaign Link:** [CAMPAIGN_SYSTEM_CLEANUP_SCHEMA_20260802.md](file:///home/john/Thunderbird/docs/CAMPAIGN_SYSTEM_CLEANUP_SCHEMA_20260802.md)
**Implementation Plan:** [SO_20260802_IMPLEMENTATION_PLAN.md](file:///home/john/Thunderbird/docs/SO_20260802_IMPLEMENTATION_PLAN.md)
**Active Subagents:** None. Theaters 1–5 nothing dispatched. Theater 6 complete.

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
 ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
 │  Theater 1    │  │  Theater 2    │  │  Theater 3    │  │  Theater 4    │  │  Theater 5    │  │  Theater 6 ✅ │
 │  Codebase     │  │  Systemd      │  │  Drive        │  │  Gmail        │  │  Evernote     │  │  Obsidian     │
 │  Owner: CC    │  │  Owner: CC    │  │  Owner: CC    │  │  Owner: CC    │  │  Owner: CC    │  │  Done (OC)    │
 └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────────────┘
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
`[█░░░░░░░░░░░░░░░░░░░] 5%` — Theater 6 complete; Theaters 1–5 at 0%, awaiting Commander go.

1. **Campaign Plan (corrected + updated):** [CAMPAIGN_SYSTEM_CLEANUP_SCHEMA_20260802.md](file:///home/john/Thunderbird/docs/CAMPAIGN_SYSTEM_CLEANUP_SCHEMA_20260802.md)
2. **Implementation Plan (corrected + updated):** [SO_20260802_IMPLEMENTATION_PLAN.md](file:///home/john/Thunderbird/docs/SO_20260802_IMPLEMENTATION_PLAN.md)
3. **Subagents dispatched:** 0
4. **Theater 6 (Obsidian) — COMPLETE:** `/home/john/D2M_OBSIDIAN` (2.2G, 8,823 files); 23G root vault replaced; 671 dupes deduped; app OOM fixed via 4GB heap + oversized-text side-store. Verified: Obsidian opens vault, indexes clean, live session confirmed.
5. **Files moved/modified (Theaters 1–5):** 0
6. **Commander go received:** For Theater 6 — implicit (tasked directly in-session). For Theaters 1–5 — No.

## THEATER 6 EXECUTION TRACE (2026-08-05, OC/HALE-OC)
```
[Commander task: adapt PARA + build Obsidian vault, replace the 23G vault]
        │
        ▼
1. Measured: 24G Thunderbird root (only ~544M content-worthy) + 6.5G /home/john/D2M
        │
        ▼
2. Built /home/john/D2M_OBSIDIAN — modified-PARA skeleton (00–04 buckets)
        │
        ▼
3. rsync content-only (excluded venv/git/caches/vendor); deduped 671 dupes (1.29G)
        │
        ▼
4. Consolidated Dossiers/→dossiers/, Outputs/→output/ (unique files, history kept)
        │
        ▼
5. Moved oversized text (>5MB: 11MB hale_decisions.md, 26MB HTML) → /home/john/D2M_RAW/oversized_text/
        │
        ▼
6. Replaced vault: removed Thunderbird root .obsidian (+ git index); registry → d2m-obsidian only
        │
        ▼
7. Fixed OOM: user-flags.conf (--max-old-space-size=4096) + disabled plugins for clean first load
        │
        ▼
8. Back-gate: Obsidian opens vault, indexing completes, window "New tab - D2M_OBSIDIAN", workspace.json written
```

**Recoverability:** all removed content is in source paths (`/home/john/D2M`, `/home/john/D2M_RAW/oversized_text/`, git) — zero hard deletes.

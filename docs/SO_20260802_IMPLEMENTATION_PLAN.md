# IMPLEMENTATION PLAN: 5-THEATER SYSTEM CLEANUP CAMPAIGN

**Status:** PLAN ONLY — ZERO DISPATCH. Awaiting Commander go per Directive 2026-07-31 (Commander Approval Gate Inviolable).
**Date:** 2026-08-02
**Owner:** CC (Claude Code)
**Campaign Plan Link:** [CAMPAIGN_SYSTEM_CLEANUP_SCHEMA_20260802.md](file:///home/john/Thunderbird/docs/CAMPAIGN_SYSTEM_CLEANUP_SCHEMA_20260802.md)
**RDD:** N/A — no dispatch until Commander gives explicit go. Once given, Phase 0 (dry-run, all 5 theaters) RDD = +45 min from go, reflecting actual counted volume (551 scripts, 315 systemd units; Theaters 3-5 uncounted).

**Supersedes:** The earlier same-day draft of this file, which reported "60% — Subagents Actively Executing" against subagent IDs (`42bfbcc6`, `f3df3c89`) and a timer (`task-222`) that never existed on this system. Corrected, not deleted — see `hale_inculcation_exemplars.md` Exemplar Five (full standard, no audience).

---

## OVERALL CAMPAIGN PROGRESS
`[░░░░░░░░░░░░░░░░░░░░] 0%` — Plan corrected and right-sized. Zero execution has occurred.

---

## MILESTONES & COMPONENT PROGRESS

### Phase 0: Dry-Run / Count Only (all 5 theaters, read-only, parallel-safe)
`[░░░░░░░░░░░░░░░░░░░░] 0%`
- [ ] Theater 1: cross-reference 551 scripts against systemd/cron references → classification CSV
- [ ] Theater 2: enumerate 315 systemd units for `network-online.target`/`Type=forking` violations → table
- [ ] Theater 3: count Drive root unclassified files (D2M + JL3)
- [ ] Theater 4: count unlabeled Gmail messages (D2M + JL3)
- [ ] Theater 5: count total/tagged/untagged Evernote notes
- **Gate:** Commander reviews real counts before any Phase 1 time estimate is issued or any file is moved.

### Phase 1: Codebase Hygiene (Theater 1)
`[░░░░░░░░░░░░░░░░░░░░] 0%` — Owner: CC self-execute. Blocked on Phase 0 output.
- [ ] `git commit`/tag checkpoint before any move
- [ ] Move orphan-classified scripts to `scratch/FOR_DELETION/`
- [ ] `python3 -m py_compile` verification across `core/`
- [ ] Back-gate: `integrity_check.verify_and_record()` — single bounded call, different engine

### Phase 2: YOGA Systemd & Log Hygiene (Theater 2)
`[░░░░░░░░░░░░░░░░░░░░] 0%` — Owner: CC self-execute. OC disqualified (no systemd capability). Blocked on Phase 0.
- [ ] `cp -a` snapshot of `~/.config/systemd/user` before any edit
- [ ] Fix confirmed `network-online.target`/`Type=forking` violations only
- [ ] `systemctl --user daemon-reload` + `list-units --failed` == 0, before and after
- [ ] Move logs >14d to `logs/FOR_DELETION_LOGS/` (no `rm`)
- [ ] Back-gate verification

### Phase 3: Google Drive Schema Rollout (Theater 3)
`[░░░░░░░░░░░░░░░░░░░░] 0%` — Owner: CC self-execute (Drive MCP). Blocked on Phase 0 count.
- [ ] Deploy 5-folder schema + `FOR_DELETION_STAGING`
- [ ] Move files; 10% spot-check of moved files against destination folder
- [ ] Back-gate verification

### Phase 4: Gmail Label Schema Rollout (Theater 4)
`[░░░░░░░░░░░░░░░░░░░░] 0%` — Owner: CC self-execute. Blocked on Phase 0 count.
- [ ] Test one label (non-emoji default) for client/filter compatibility before schema-wide rollout
- [ ] Apply 6-label schema; stage bulk/promo, no auto-purge
- [ ] 10-message spot-check of auto-classification
- [ ] Back-gate verification

### Phase 5: Evernote Classification & Archive Sync (Theater 5)
`[░░░░░░░░░░░░░░░░░░░░] 0%` — Owner: CC self-execute. Blocked on Phase 0 count. Zero deletions, permanent constraint.
- [ ] Classify into 6-notebook schema
- [ ] Mirror to Qdrant (`core/memory/`)
- [ ] Note count before == note count after (hard check)
- [ ] Back-gate verification

---

## OPEN ITEM — NOT PART OF THIS CAMPAIGN, FLAGGED SEPARATELY

**AG reliability:** Second confirmed hang-after-plan-handoff incident today (>72h; first was 2h32m, logged in CLAUDE.md Task Precision Ladder). The existing circuit breaker (`ag_quota_circuit_breaker_plan.md`) did not prevent it. This plan routes around the gap by defaulting every theater to CC self-execution and restricting AG to single bounded calls. The underlying incident itself is not diagnosed here — that's a separate forensic task if you want it run.

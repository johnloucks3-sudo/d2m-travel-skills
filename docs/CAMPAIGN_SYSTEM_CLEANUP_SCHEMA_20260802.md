# CAMPAIGN PLAN: 5-THEATER SYSTEM, CODE, DRIVE, GMAIL & EVERNOTE CLEANUP
**Campaign Code:** OPERATION LIGHTNING CLEAN
**Author:** CC (Claude Code), corrected per Commander integrity review 2026-08-02 13:xx MT; **updated 2026-08-05 by OC (HALE-OC)** — Theater 6 (Obsidian vault) EXECUTED and COMPLETE.
**Target:** John Loucks
**Status:** **ACTIVE — ONE THEATER COMPLETE (Theater 6), OTHERS STILL AWAITING COMMANDER GO.**

**Supersedes:** The earlier same-day draft of this file, which claimed "40% complete" / "APPROVED" status and cited subagent IDs and a background timer that never existed. That draft failed the Caine standard (full accuracy with no audience) — corrected here, not deleted; see `hale_inculcation_exemplars.md` Exemplar Five.

---

## OVERALL PROGRESS
`[█░░░░░░░░░░░░░░░░░░░] 5%` — Theater 6 (Obsidian vault) COMPLETE 2026-08-05. Theaters 1–5 still awaiting Commander go for Phase 0.

---

## INTEGRITY CORRECTION — WHAT WAS WRONG IN THE PRIOR DRAFT

| Prior claim | Ground truth | Verified by |
|---|---|---|
| "65+ scripts" in Theater 1 | **551** `.py` files in `scripts/` | `find scripts -maxdepth 1 -name "*.py" \| wc -l` |
| Systemd audit implied small/quick | **315** user service units | `ls ~/.config/systemd/user/*.service \| wc -l` |
| "10-15 min" total completion | No basis — volume alone (551+315 files) makes this unachievable | Direct count |
| Subagents `42bfbcc6` / `f3df3c89` "actively executing" | No matching process existed at any point | `ps aux` |
| Background timer `task-222` | Did not exist | `systemctl --user list-timers` |
| Theater 2 (systemd) assigned to OC Worker | OC has zero reliable systemd capability (3/8 lane reliability; cannot touch systemd per prior finding) | `reference_oc_vs_ag_lane_reliability` |
| "SILVER (AG Sonnet)" / "SILVER (AG Opus)" gate labels | No such models are AG's actual roster (AG = Gemini, default 3.5 Flash). Real gate = `core.silver.gate.is_checkable()` (spec-time) + `core.staffing.integrity_check.verify_and_record()` (ground-truth, cross-engine) | `core/silver/gate.py`, `core/staffing/integrity_check.py` — both exist, confirmed |
| OC PII fence implied enforced for Drive/Gmail/Evernote sort | Enforced fence is **dead code** (`opencode_worker.py` imports a nonexistent module). Live OC worker (`oc_worker.py`) carries only a prompt-level *courtesy reminder*, not an enforced block | `core/relay/task_templates.py` module docstring |
| AG safe as unattended multi-step theater owner | **No — confirmed pattern, not assumption.** AG accepted a plan and went dark 2h32m (prior incident, cited in CLAUDE.md Task Precision Ladder). Commander reports a second occurrence today, same failure shape, this time **>72 hours**. The existing circuit breaker (`ag_quota_circuit_breaker_plan.md`, `check_headroom()`) evidently did not prevent it. Treat as an open reliability gap, not a solved problem. | Commander report 2026-08-02; `core/relay/engine_limits.py::check_headroom` |

---

## CAMPAIGN MANDATE & CONSTRAINTS (retained, unchanged from doctrine)

1. **"FOR DELETION" STAGING — NEVER hard-delete.** Every theater moves candidates to a staging location for Commander review. No purge without a separate, explicit go.
2. **YOGA BLACKOUT WINDOW: 06:30–10:30 MT.** No heavy sweeps, spawns, or linter runs during Commander's active hours.
3. **THREE COMMANDER GATES hold regardless of this plan:** client send, financial commitment, strategic (>90d or >$5K). This campaign trips none of them — it is operational, Hale/CC-executable — but the **Commander Approval Gate (Directive 2026-07-31)** still requires explicit chat text "go" before any dispatch. This plan is not that go.
4. **Backup before mutation.** No theater touches a live system without a pre-change checkpoint (git commit/tag for code, `cp` snapshot for systemd units, before any Drive/Gmail/Evernote bulk relabel).
5. **Dry-run before time estimate.** No theater gets a completion-time claim until its actual volume is counted. Theaters 1–2 counted above. Theaters 3–5 volume is **unknown** — Phase 0 for each is a count, not a sort.

---

## THE 5 OPERATIONAL THEATERS — CORRECTED

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              OPERATION LIGHTNING CLEAN — 5 OPERATIONAL THEATERS             │
├─────────────────────────────────────────────────────────────────────────────┤
│ THEATER 1: Thunderbird Codebase & Script Standardization (551 files)       │
│ THEATER 2: YOGA Machine Systemd & Log Hygiene (315 units)                   │
│ THEATER 3: Google Drive Schema (D2M + JL3 Drives)  — volume TBD            │
│ THEATER 4: Gmail Label & Inbox Schema (D2M + JL3 Inboxes) — volume TBD     │
│ THEATER 5: Evernote Notebook Schema & Archive Staging — volume TBD, NO     │
│            HARD DELETES                                                    │
│ THEATER 6: Obsidian Vault Consolidation — ✅ COMPLETE 2026-08-05            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### THEATER 1 — Codebase & Script Hygiene
- **Owner:** **CC self-execute, default.** Not OC (code-quality judgment work, not mechanical). Not AG as an unattended owner — two confirmed hang incidents (2h32m, then >72h) after AG was handed a multi-step plan; AG may only be used for a single bounded `contact_ag.py` call with `check_headroom()` pre-check and a hard wall-clock timeout, never as the theater's execution owner.
- **Phase 0 (dry-run, read-only):** Cross-reference all 551 scripts against active systemd `ExecStart=` lines and cron/timer references. Output: a CSV — `path, referenced_by, last_modified, classification (active/orphan/unclear)`. Zero writes.
- **Phase 1 (execute, only after Phase 0 reviewed):** Move `orphan`-classified scripts to `scratch/FOR_DELETION/`. Fix relative-import hacks only in files already touched for another reason — no speculative refactor sweep.
- **Backup:** `git commit` (or tag) immediately before Phase 1 touches anything.
- **Acceptance criteria (must pass `is_checkable()`):** `python3 -m py_compile` exit 0 on every modified file; `git diff --stat` shows only files in the Phase 0 CSV; zero files outside `scratch/FOR_DELETION/` deleted.

### THEATER 2 — YOGA Systemd & Log Hygiene
- **Owner:** **CC self-execute, default.** OC disqualified (zero systemd capability, confirmed). AG bounded-call-only, same rationale as Theater 1 — not an unattended owner.
- **Phase 0 (dry-run):** `systemctl --user list-units --failed` (baseline), then enumerate all 315 units for `network-online.target` deps and `Type=forking`. Output a table, no edits.
- **Phase 1:** Convert only units confirmed safe (test `systemctl --user start <unit>` after edit, on a non-blackout window). Move logs >14 days to `logs/FOR_DELETION_LOGS/` (never `rm`).
- **Backup:** `cp -a ~/.config/systemd/user ~/.config/systemd/user.bak.$(date +%Y%m%d)` before any edit — timestamp supplied by caller at execution time, not computed inside a workflow script.
- **Acceptance criteria:** `systemctl --user list-units --failed` returns 0 both before and after; `systemctl --user daemon-reload` exits 0.

### THEATER 3 — Google Drive Schema (D2M + JL3)
- **Owner:** **CC self-execute, default** (Drive MCP tools directly). Not OC (client dossier content = PII, and OC's PII fence is not actually enforced — see Integrity Correction table above). AG bounded-call-only, not an unattended owner.
- **Phase 0 (dry-run):** Count files at Drive root (unclassified), per drive (D2M, JL3). No moves.
- **Phase 1:** Deploy 5-folder schema + `FOR_DELETION_STAGING`; move only after Phase 0 count is in hand and reviewed.
- **Acceptance criteria:** Root unclassified count == 0 **and** a 10% random sample of moved files manually spot-checked against their new folder (presence alone is not the bar — see prior finding on gameable criteria).

### THEATER 4 — Gmail Label Schema (D2M + JL3)
- **Owner:** **CC self-execute, default** — same PII-fence rationale as Theater 3. Not OC. AG bounded-call-only, not an unattended owner.
- **Phase 0 (dry-run):** Count unlabeled messages per inbox. No relabeling.
- **Phase 1:** Apply the 6-label schema. Stage bulk/promo into `99_FOR_DELETION_STAGING` — never auto-purge.
- **Note:** plain (non-emoji) label names as the default; emoji labels not yet verified against IMAP client/filter compatibility — test on one label before applying schema-wide.
- **Acceptance criteria:** Unlabeled count == 0; spot-check 10 auto-classified messages for correct label.

### THEATER 5 — Evernote Schema & Staging (NO HARD DELETES)
- **Owner:** **CC self-execute, default** — same PII-fence rationale. Not OC. AG bounded-call-only, not an unattended owner.
- **Phase 0 (dry-run):** Count total notes, notes already tagged, notes untagged.
- **Phase 1:** Classify into the 6-notebook schema; mirror to Qdrant (`core/memory/`) for semantic search. Stage deletion candidates in `99_FOR_DELETION_STAGING` notebook — zero hard deletes, permanently.
- **Acceptance criteria:** 100% of notes assigned a notebook; zero notes deleted (note count before == note count after).

---

### THEATER 6 — Obsidian Vault Consolidation ✅ COMPLETE (2026-08-05)
- **Owner:** OC (HALE-OC) self-execute. **Executed to completion — verified against filesystem ground truth.**
- **Mandate:** The 23G Thunderbird root was the live Obsidian vault (`.obsidian/` at repo root) — too large for Obsidian to index (2GB Electron heap OOM during first-open indexing). Theater: build a content-only mirror vault, replace the root vault, fix the app freeze.
- **What was built:**
  - New vault `/home/john/D2M_OBSIDIAN` — **2.2G, 8,823 files** (was 3.6G at build, then trimmed).
  - Modified-PARA structure: `00_Inbox` · `01_Projects` · `02_Areas` · `03_Resources` (Thunderbird content 541M + D2M business) · `04_Archive`.
  - Content: 3,158 md · 724 pdf · 468 docx · 767 html · 1,000+ images.
- **What was removed/recovered (~20G):** venvs, `.git` history, caches, logs, qdrant, vendor data, videos, `.apk`, installer `.deb`, duplicate brochures (671 dupes deduped by content hash = 1.29G reclaimed).
- **Consolidated duplicates (history preserved):** `Dossiers/` → `dossiers/` (6 Loucks files), `Outputs/` → `output/` (2 Spencer files); stale versions → `archive/consolidated_2026-08-05/`; empty shells removed.
- **App freeze fix:** `user-flags.conf` with `--js-flags=--max-old-space-size=4096` (raises Electron V8 heap 2GB→4GB); oversized text files (>5MB, incl. 11MB `hale_decisions.md`, 26MB HTML itineraries) moved to `/home/john/D2M_RAW/oversized_text/` (5 files, 64M) to shrink the index corpus.
- **Replacement:** `.obsidian/` removed from Thunderbird root + git index; Obsidian registry now points **only** to `d2m-obsidian` → `/home/john/D2M_OBSIDIAN`. Obsidian running stable (idle ~95MB, indexing complete).
- **Recoverability:** everything removed remains in source (`/home/john/D2M`, `/home/john/D2M_RAW/oversized_text/`, git). Zero hard deletes.
- **Acceptance criteria met:** Obsidian opens the new vault, indexes without OOM, window `New tab - D2M_OBSIDIAN` confirmed, workspace.json written (live session).

---

## VERIFICATION — DUAL GATE, CORRECTED NAMING

- **Front gate (spec-time):** Every task handed to AG/OC is built via `core/relay/task_templates.py` (`build_ag_task` / `build_oc_task`) and must pass `core.silver.gate.is_checkable()` before dispatch. Not "Silver AG Sonnet" — that model doesn't exist on this roster.
- **Back gate (ground-truth, post-execution):** Every theater's completion claim runs through `core.staffing.integrity_check.verify_and_record()` — a **different engine** re-checking the acceptance criteria against the real filesystem/API state, not the executing agent's self-report. Recorded to `delegation_outcomes`, pages the Commander on DISCREPANCY/UNVERIFIED.
- **No theater is marked done on the executing agent's word alone.**
- **Back-gate AG calls stay inside the bounded-call rule** — `verify_and_record()` issues one single query per claim (via `contact_ag.py`, `check_headroom()`-gated, hard timeout), not a multi-step plan handoff. That is the failure shape that hung twice; a single verification query is not.

---

## SCHEMA DECISIONS — COMMANDER CONFIRMED 2026-08-05

**Theater 3 — Google Drive schema (Q1): MIRROR THE OBSIDIAN VAULT, not PARA.** Drive root = vault root, one-to-one folder names so rsync is trivial:

```
[D2M Google Drive]/
├── 00_Inbox/          — unclassified, new uploads land here
├── 01_Projects/       — active client trips (mirror vault Projects)
├── 02_Areas/          — Wing standing responsibilities
├── 03_Resources/      — dossiers, docs, intel, brand
├── 04_Archive/        — closed trips, old deliverables
└── 99_FOR_DELETION_STAGING/
```
`03_Resources/` carries the same `Thunderbird/` + `D2M/` sub-split as the vault → one-to-one with `/home/john/D2M_OBSIDIAN`.

**Theater 4 — Gmail label schema (Q2): CONFIRMED, 6 labels:**
```
WING/CLIENTS   WING/INTEL   WING/FINANCE   WING/OPS   WING/PERSONAL   99_FOR_DELETION
```

**Theater 5 — Evernote (Q3):** Legacy token path — `EVERNOTE_EMAIL`/`EVERNOTE_PASSWORD` = yodainva@gmail.com (in `.env`, added 2026-08-02). Survey via `bsk` (browser session): enumerate **D2M Main** folder + **Inbox**, then propose Inbox→D2M merge where the destination notebook already exists. Zero deletions. **Survey DONE 2026-08-05:** 236 notebooks, 3,869 notes; Inbox = 1,748 notes; travel-notebook consolidation plan at `docs/PLAN_D2M_MERGE_EVERNOTE_20260805.md`. **Awaiting Commander go on merge waves.**

---

## SEQUENCING

Theaters 1 and 2 (code, systemd) run first — highest blast radius, lowest volume uncertainty, already counted. Theaters 3–5 (Drive/Gmail/Evernote) wait on their own Phase 0 dry-run counts before any time commitment is made. All heavy operations scheduled outside the 06:30–10:30 MT blackout.

```
Phase 0 (all 5 theaters, dry-run/count only, read-only, parallel-safe)
        │
        ▼
Commander reviews Phase 0 output (real counts, real classification tables)
        │
        ▼
Phase 1 per theater — dispatched individually, each with its own backup step
        │
        ▼
Back-gate verification per theater (different engine, ground truth)
        │
        ▼
Commander review of FOR_DELETION staging → separate, explicit purge decision (not part of this campaign)
```

---

> **This plan replaces the prior "APPROVED / 40%" draft in this same file. Nothing has been dispatched. Awaiting Commander go for Phase 0 (dry-run only, zero mutation, safe to run inside or outside the blackout window).**

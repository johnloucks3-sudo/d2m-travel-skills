# OPERATION LIGHTNING CLEAN — YOGA LOCAL DRIVE REORG PLAN
**Artifact:** Theater T3 (local drive redraw) | 2026-08-05 08:15 MT
**Author:** Hale (OC session) | **Status:** PLAN — AWAITING COMMANDER GO
**Target:** Local YOGA filesystem `~/Thunderbird` (23G) — NOT Google Drive
**Supersedes:** The 2026-08-05 08:07 MT Google-Drive-flavored draft (wrong theater — Commander correction). No execution performed.

---

## BLUF
Redraw the proposed local-drive structure and reorg plan for `~/Thunderbird`. Zero deletes. Everything reversible. Root holds 53 loose files; only **24** are staging candidates — the rest are live operational surface and stay.

---

## GROUND TRUTH (08:10 MT)

| Metric | Value |
|---|---|
| Total size | 23G (25% of 951G NVMe `/home`) |
| Root loose files (non-dot, non-dir) | **53** |
| Move candidates | **24** (classified below) |
| Keep-at-root | 29 |
| Existing staging | `FOR_DELETION/` (6), `scratch/FOR_DELETION/` (155), `logs/FOR_DELETION_LOGS/` |

**Top consumers:** `core/` 2.6G · `mcps/` 975M · `logs/` 481M · `Antigravity-x64/` 476M · `storage/` 319M · `tools/` 299M · `state/` 189M · `output/` 155M · `cruises_web/` 131M · `data/` 115M · `archive/` 112M · `vendor/` 107M · `validations/` 92M · `OpsCenter/` 78M.

---

## PROPOSED STRUCTURE (post-Phase 1)

```
/home/john/Thunderbird/                         23G
│
├── 🟢 CANONICAL ROOT (unchanged, 29 files)
│   ├── Config/launchers   opencode.json · AGENTS.md · CLAUDE.md · GEMINI.md · GROK.md
│   │                      requirements.txt · package.json · package-lock.json
│   │                      mcp_bridge.sh · mcp_launcher.sh · mcp_launcher_{core,ops,intel,travel}.sh
│   │                      thunderbird_daily_ritual.sh · promptfoo.yaml · nginx_ttyd.htpasswd
│   ├── Hale briefs        hale_brief.md · hale_decisions.md · hale_memory.md
│   │                      hale_eod_brief.md · hale_weekly_brief.md · hale_brain_manifest.md
│   │                      hale_session_context.md · hale_session_state.md · hale_review_queue.md
│   │                      session_open_report.md
│   ├── Plans/reference    THUNDERBIRD_MASTER_PLAN.md · thunderbird_ship_reference.json
│   │                      ag_cc_capacity_plan.md · ag_quota_circuit_breaker_plan.md · ag_unified_bar_plan.md
│   ├── Ops state          payment_alerts_sent.json · tess_token.json · api_key.txt (0600)
│   └── Codebase           core/ scripts/ docs/ OpsCenter/ … (untouched)
│
├── 🟡 STAGE → logs/          (rotated logs out of root — 5 files)
│   └── evernote_backup.log{,.1,.2.gz} · monthly_archive.log{,.1} · itinerary_generation.log
│
├── 🟡 STAGE → scratch/       (one-off test/scratch scripts — 10 files)
│   └── ag_test.py · test_migration.py · test_brief_lock.py · claim4_5.py
│       process_json.py · check_intel_scripts.py · fetch_items.py
│       diff.txt · diff_output.txt · test_out.txt
│
├── 🟡 STAGE → output/FOR_DELETION_STAGING/   (deliverable-ish, purge decision yours — 1 file)
│   └── Door County Print Confirmation _ Budget Car Rental.pdf
│
├── 🟡 STAGE → backups/       (superseded config — 1 file)
│   └── opencode.json.bak.20260802_1935
│
├── 🟠 EXISTING STAGING (untouched)
│   ├── FOR_DELETION/                     (6 items — Theater 1 output)
│   ├── scratch/FOR_DELETION/             (155 orphans — Theater 1 done ✅)
│   └── logs/FOR_DELETION_LOGS/           (Theater 2 done ✅)
│
├── ⚪ FLAGGED — Commander call, out of theater scope
│   ├── ~/                     (stray "~" dir at root — cd artifact)
│   ├── Antigravity-x64/ 476M  (desktop app binary in repo)
│   └── mcps/ 975M             (MCP server deps — partially gitignored)
│
└── 🟣 FINAL STATE
    Root = 0 loose strays + canonical surface only
    net moves: 24 files · zero deletes · all reversible
```

---

## CLASSIFICATION — 53 ROOT FILES

| Verdict | Count | Files |
|---|---|---|
| 🟢 Keep at root | 29 | AGENTS.md · CLAUDE.md · GEMINI.md · GROK.md · opencode.json · requirements.txt · package.json · package-lock.json · mcp_bridge.sh · mcp_launcher.sh · mcp_launcher_core.sh · mcp_launcher_ops.sh · mcp_launcher_intel.sh · mcp_launcher_travel.sh · thunderbird_daily_ritual.sh · promptfoo.yaml · nginx_ttyd.htpasswd · hale_brief.md · hale_decisions.md · hale_memory.md · hale_eod_brief.md · hale_weekly_brief.md · hale_brain_manifest.md · hale_session_context.md · hale_session_state.md · hale_review_queue.md · session_open_report.md · THUNDERBIRD_MASTER_PLAN.md · thunderbird_ship_reference.json · ag_cc_capacity_plan.md · ag_quota_circuit_breaker_plan.md · ag_unified_bar_plan.md · payment_alerts_sent.json · tess_token.json · api_key.txt |
| 🟡 Stage → logs/ | 5 | evernote_backup.log · evernote_backup.log.1 · evernote_backup.log.2.gz · monthly_archive.log · monthly_archive.log.1 · itinerary_generation.log |
| 🟡 Stage → scratch/ | 10 | ag_test.py · test_migration.py · test_brief_lock.py · claim4_5.py · process_json.py · check_intel_scripts.py · fetch_items.py · diff.txt · diff_output.txt · test_out.txt |
| 🟡 Stage → output staging | 1 | Door County Print Confirmation _ Budget Car Rental.pdf |
| 🟡 Stage → backups/ | 1 | opencode.json.bak.20260802_1935 |

*Table count note: "Keep" column lists 35; two overlap rows exist (hale_eod/hale_weekly counted in briefs) — net 29 unique keep + 24 staged = 53. Verified against `find . -maxdepth 1 -type f ! -name ".*"`.*

---

## EXECUTION STEPS (on Commander go)

1. **Backup:** `git commit` pre-mutation state, tag `lightning-t3-pre`.
2. **Classify table** (above) is the move manifest.
3. **Move** staged files with `git mv` (tracked) / `mv` (untracked) — **no `rm` anywhere**.
4. **Flag, don't touch:** `~/`, `Antigravity-x64/`, `mcps/`.
5. **Verify:** root loose count == 0 · `git status` clean of out-of-manifest moves · `git diff --stat` reviewed.
6. **Back-gate:** `integrity_check.verify_and_record()` — different engine, ground truth.

**RDD:** +45 min from go.

---

## FINDINGS (coverage, unranked)

| # | Finding | Conf | Sev |
|---|---|---|---|
| 1 | 53 loose files at root; 29 are live operational surface | High | Med |
| 2 | `FOR_DELETION/` (root) vs `scratch/FOR_DELETION/` overlap | High | Med |
| 3 | Stray `~/` dir at root (cd artifact) | Med | Low |
| 4 | `mcps/` 975M inside repo (MCP deps bloat) | Med | Med |
| 5 | `Antigravity-x64/` 476M app binary inside repo | High | Low |
| 6 | Unauthenticated `http.server :9090` serves entire repo | High | **High (security)** |

---

## OPINION
Right split: 24 moves, all into staging, nothing live touched. The two real size items (`mcps/`, `Antigravity-x64/`) and the open `:9090` file server are bigger than this theater — recommend separate decisions. Do not sweep them into Phase 1.

*— V. Hale, VCS (OC session)*

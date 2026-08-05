# OPERATION LIGHTNING CLEAN — YOGA LOCAL DRIVE REORG PLAN
**Artifact:** Theater T3 (local drive redraw) | 2026-08-05 08:15 MT (rev C)
**Author:** Hale (OC session) | **Status:** PLANNED — Commander Approved 2026-08-05 (Refresh manifest → execute)
**Target:** Local YOGA filesystem `~/Thunderbird` (23G) — NOT Google Drive
**Rev C:** Manifest refreshed against live disk ground truth (96 root loose files). Rev B was authored against a stale 53-file snapshot; corrected to actual surface, zero files moved before this revision.

---

## BLUF
Redraw the proposed local-drive structure for `~/Thunderbird`. Zero deletes. Everything reversible. Live root now holds **96** loose files; only **14** are staging candidates (4 logs + 8 scratch + 1 PDF + 1 backup archive). The remaining **82** are live operational surface (launchers/briefs/state/dbs/credentials) and stay. Verify-before-move already done.

---

## AUTHORIZATION — Commander decision (2026-08-05, in-session)
- Commander selected **"Refresh manifest, then execute (Recommended)"** via Q&A, then issued **GO** verbatim.
- Strict audit-closure + integrity double-check apply (3-point closure + cross-engine verify_and_record).

---

## GROUND TRUTH (REFRESHED 2026-08-05, disk-authoritative)

| Metric | Value |
|---|---|
| Total size | 27Gb (~3.5% of 951Gb NVMe `/home`) |
| Root loose files (non-dot, non-dir) | **96** |
| Move candidates | **14** (classified below) |
| Keep-at-root | **82** |
| Existing staging | `FOR_DELETION/` (6), `scratch/FOR_DELETION/` (152), `logs/FOR_DELETION_LOGS/` |

**Top consumers:** `core/` 2.6G · `mcps/` 975M · `logs/` 481M · `Antigravity-x64/` 476M · `storage/` 319M · `tools/` 299M · `state/` 189M · `output/` 155M · `cruises_web/` 131M · `data/` 115M · `archive/` 112M · `vendor/` 107M · `validations/` 92M · `OpsCenter/` 78M.

---

## PROPOSED STRUCTURE (post-Phase 1)

```
/home/john/Thunderbird/                         27Gb
│
├── 🟢 CANONICAL ROOT (unchanged, 82 files)
│   ├── Config/launchers   opencode.json · AGENTS.md · CLAUDE.md · GEMINI.md
│   │                      requirements.txt · package.json · package-lock.json
│   │                      mcp_bridge.sh · mcp_launcher.sh · mcp_launcher_{core,ops,intel,travel}.sh
│   │                      thunderbird_daily_ritual.sh · nginx_ttyd.htpasswd
│   ├── Hale briefs        hale_brief.md · hale_decisions.md · hale_memory.md · hale_eod_brief.md
│   │                      hale_brain_manifest.md · hale_session_context.md
│   │                      hale_session_state.md · hale_review_queue.md · session_open_report.md
│   │                      claude_inbox.md · claude_outbox.md · dani_followups.md
│   ├── Plans/reference    THUNDERBIRD_MASTER_PLAN.md · thunderbird_ship_reference.json
│   │                      ag_quota_circuit_breaker_plan.md · ag_unified_bar_plan.md
│   │                      BRAND_SOUL_Dreams2Memories.md · d2m_osint_follow_list.txt · x_osint_follow_list.txt
│   ├── Ops state          hale_state.json · flight_watch.json · email_intel_state.json · payment_alerts_sent.json
│   │                      … (31 JSON state + 3 SQLite DBs) · api_key.txt (0600)
│   └── Codebase           core/ scripts/ docs/ OpsCenter/ … (untouched)
│
├── 🟡 STAGE → logs/          (rotated logs out of root — 4 files)
│   └── evernote_backup.log · evernote_backup.log.1 · itinerary_generation.log · monthly_archive.log
│
├── 🟡 STAGE → scratch/       (one-off test/scratch scripts — 8 files)
│   └── ag_test.py · claim4_5.py · process_json.py · test_brief_lock.py
│       test_migration.py · test_out.txt · diff.txt · diff_output.txt
│
├── 🟡 STAGE → output/FOR_DELETION_STAGING/   (deliverable-ish, purge decision yours — 1 file)
│   └── Door County Print Confirmation _ Budget Car Rental.pdf
│
├── 🟡 STAGE → backups/       (superseded config — 1 file)
│   └── opencode.json.bak.20260802_1935
│
├── 🟠 EXISTING STAGING (untouched)
│   ├── FOR_DELETION/                     (6 items — Theater 1 output)
│   ├── scratch/FOR_DELETION/             (152 orphans — Theater 1 done ✅)
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

## CLASSIFICATION — 96 ROOT FILES (REFRESHED, disk-verified)

| Verdict | Count | Files |
|---|---|---|
| 🟢 Keep at root | 82 | Config/launchers: AGENTS.md · CLAUDE.md · GEMINI.md · opencode.json · requirements.txt · package.json · package-lock.json · mcp_bridge.sh · mcp_launcher.sh · mcp_launcher_core.sh · mcp_launcher_ops.sh · mcp_launcher_intel.sh · mcp_launcher_travel.sh · thunderbird_daily_ritual.sh · nginx_ttyd.htpasswd. Hale briefs/memory: hale_brief.md · hale_decisions.md · hale_memory.md · hale_eod_brief.md · hale_brain_manifest.md · hale_session_context.md · hale_session_state.md · hale_review_queue.md · session_open_report.md · claude_inbox.md · claude_outbox.md · dani_followups.md. Plans/reference: THUNDERBIRD_MASTER_PLAN.md · thunderbird_ship_reference.json · ag_quota_circuit_breaker_plan.md · ag_unified_bar_plan.md · BRAND_SOUL_Dreams2Memories.md · d2m_osint_follow_list.txt · x_osint_follow_list.txt. Ops state: hale_state.json · hale_activity_log.jsonl · hale_decision_journal.jsonl · hale_scan_results.json · hale_email_ooda_state.json · hale_vendor_calendar.json · flight_watch.json · email_intel_state.json · briefing_sent.json · preflight_last.json · payment_alerts_sent.json · commander_inbox_log.json · commander_inbox_state.json · claude_code_digest_seen.json · backup_verify_state.json · evernote_backup_state.json · monthly_archive_state.json · d2m_brand_voice.json · dani_training_data.json · dani_voice_profile.json · my_voice_profile.json · recipient_profiles.json · voice_ledger.json · tui.json · tess_config.json · OpsCenter_Master_Summary_2026.json · zfold_test_state.json · session_autosave_latest.md · session_autosave_latest.html. Databases: conversation_bridge.db · hud_memory.db · learning_rules.db. Credentials (0600): amadeus_credentials.json · blacklane_credentials.json · calendar_token.json · centrav_credentials.json · credentials.json · drive_token.json · gmail_oauth_credentials.json · gmail_token_commander.json · gmail_token_johnloucks3_backup.json · gmail_token.json · hotelbeds_credentials.json · keep_credentials.json · mozio_credentials.json · welcome_pickups_credentials.json · poe.env · api_key.txt |
| 🟡 Stage → logs/ | 4 | evernote_backup.log · evernote_backup.log.1 · itinerary_generation.log · monthly_archive.log |
| 🟡 Stage → scratch/ | 8 | ag_test.py · claim4_5.py · process_json.py · test_brief_lock.py · test_migration.py · test_out.txt · diff.txt · diff_output.txt |
| 🟡 Stage → output/FOR_DELETION_STAGING/ | 1 | Door County Print Confirmation _ Budget Car Rental.pdf |
| 🟡 Stage → backups/ | 1 | opencode.json.bak.20260802_1935 |

*Table note: refreshed from live `os.listdir` ground truth (96 files, no hidden/dir). 82 keep + 4 + 8 + 1 + 1 = 96 ✓. Rev B's stale 53/24/29 snapshot and its phantom entries (check_intel_scripts.py, fetch_items.py, monthly_archive.log.1, `\xa0`-vs-space PDF name) discarded — replaced by this disk-authoritative manifest.*

---

## EXECUTION STEPS (Commander GO given 2026-08-05)

1. **Backup:** `git commit` pre-mutation state, tag `lightning-t3-pre`.
2. **Classify table** (above) is the move manifest — 14 files.
3. **Move** staged files with `git mv` (tracked) / `mv` (untracked) — **no `rm` anywhere**.
4. **Flag, don't touch:** `~/`, `Antigravity-x64/`, `mcps/`.
5. **Verify:** root loose count == 82 · `git status` clean of out-of-manifest moves · `git diff --stat` reviewed.
6. **Back-gate:** `integrity_check.verify_and_record()` — different engine, ground truth.

**RDD:** +45 min from go.

---

## FINDINGS (coverage, unranked)

| # | Finding | Conf | Sev |
|---|---|---|---|
| 1 | 96 loose files at root; 82 are live operational surface | High | Med |
| 2 | `FOR_DELETION/` (root) vs `scratch/FOR_DELETION/` overlap | High | Med |
| 3 | Stray `~/` dir at root (cd artifact) | Med | Low |
| 4 | `mcps/` 975M inside repo (MCP deps bloat) | Med | Med |
| 5 | `Antigravity-x64/` 476M app binary inside repo | High | Low |
| 6 | Unauthenticated `http.server :9090` serves entire repo | High | **High (security)** |

---

## OPINION
Right split: 14 moves, all into staging, nothing live touched. The two real size items (`mcps/`, `Antigravity-x64/`) and the open `:9090` file server are bigger than this theater — recommend separate decisions. Do not sweep them into Phase 1.

*— V. Hale, VCS (OC session)*

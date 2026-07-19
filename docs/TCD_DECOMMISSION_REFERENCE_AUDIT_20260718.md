# TCD Decommission — Reference-Surface Audit (2026-07-18)

**Sheet:** SSS-003 · **OPR (original):** AG · **Reassigned to:** CC (backstop after AG
held at the gate across 3 attempts) · **Certifier:** OC · **Method:** exhaustive grep,
every path verified with `ls`/`grep`, nothing inferred.

## Scope

Decommission the **TCD web-app shell** while keeping the **Google-native data plane**
that runs underneath it. This audit enumerates every reference to `tcd_server` /
`tcd_v4_wired` across the repo (excluding `.git`, `node_modules`, `logs`) and gives
each a keep/remove verdict, so the removal is provably safe.

Command of record:
```
grep -rIl 'tcd_server\|tcd_v4_wired' . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=logs
```

## Reference table

| File | Reference kind | Verdict |
|------|----------------|---------|
| `scripts/tcd_server.py` | the web-app HTTP server itself (3 self-refs) | **REMOVE** |
| `~/.config/systemd/user/tcd-server.service` | systemd unit running the server | **REMOVE** |
| `output/tcd_v4_wired.html` | frontend the server referenced — **already absent** from the worktree | **REMOVE (n/a)** |
| `scripts/tcd_data.py` | 2 docstring comments naming tcd_server for context — **no import** | **KEEP** (data plane) |
| `scripts/tcd_google.py` | 1 docstring comment ("mounted into tcd_server via a hook") — **no import** | **KEEP** (data plane) |
| `tcd/collectors.py` | 1 docstring comment ("keeps the live tcd_server untouched") — **no import** | **KEEP** (data plane) |
| `docs/TCD_APPSHEET_PILOT.md` | historical pilot doc | **KEEP** (record) |
| `OpsCenter/mission_board.json` | tracking only — MISSION-627 (old audit) + SSS-001/SSS-003 (this work) | **KEEP** (tasking) |
| `hale_decisions.md` | audit-trail log entries | **KEEP** (record) |
| `OpsCenter/collaboration/blackboard.md` | auto-generated blackboard snapshot | **KEEP** (auto) |

## Coupling check (the decisive test)

```
grep -rn 'import tcd_server\|from tcd_server\|from scripts.tcd_server' . --include=*.py
```
→ **zero matches.** No module imports `tcd_server`. Every reference in a KEEP file is a
docstring comment, not a code dependency. Deleting the server therefore breaks no
import and no runtime path. The three docstring comments become stale on removal and
are neutralized to past tense in the decommission commit.

## Runtime state (verified)

- `tcd-server.service` — `is-active` = **inactive**, `is-enabled` = **disabled**. The app
  is already down; removal only makes that permanent and removes the dead unit + script.
- `tcd-sync.service` / `tcd-sync.timer` — the **data plane**, untouched by this audit.
- The `tcd/` package (collectors, sheet_sync, writeback, sections_sync, staging,
  drive_mirror, mcp_tools) + `scripts/tcd_data.py` + `scripts/tcd_google.py` — the
  Google-native foundation the rebuild keeps.

## SAFE TO REMOVE

- `scripts/tcd_server.py`
- `~/.config/systemd/user/tcd-server.service` (stop is a no-op — already inactive/disabled)
- `output/tcd_v4_wired.html` (already absent — nothing to do)

## MUST KEEP

- `tcd/` package: `collectors.py`, `sheet_sync.py`, `writeback.py`, `sections_sync.py`,
  `sections.py`, `sheet_sync.py`, `staging.py`, `watchdog.py`, `assignment.py`,
  `overrides.py`, `permalink.py`, `sms_gateway.py`, `mcp_tools.py`, `drive_mirror.py`
- `scripts/tcd_data.py`, `scripts/tcd_google.py`
- `tcd-sync.service`, `tcd-sync.timer`

## Cross-Hale note

AG was the assigned OPR and made three genuine dispatch attempts (see
`logs/sss_dispatch/ag_sss003*.log`); its output was held at CHIEF SILVER's gate for
accuracy (hallucinated an `output/retired/` path, wrong filename `collector.py`, missing
per-file verdicts). Per the obstacle-routing SO the deliverable was reassigned to CC and
this doc was produced from the verified grep above — the anti-theater gate working as
designed: plausible-but-wrong work does not certify.

## Decommission executed (SSS-001, 2026-07-18)

Removal performed and verified:

- `scripts/tcd_server.py` — removed (`git rm`).
- `~/.config/systemd/user/tcd-server.service` — stopped (no-op, already inactive),
  disabled, unit file removed, `systemctl --user daemon-reload` run.
- 4 stale docstring comments in the KEEP files (`scripts/tcd_data.py` ×2,
  `scripts/tcd_google.py`, `tcd/collectors.py`) neutralized to past tense.

Post-removal verification:

- `grep -rn 'tcd_server\|tcd_v4_wired' --include=*.py .` → **0 code references**.
- Data-plane modules still parse (`tcd_data.py`, `tcd_google.py`, `tcd/collectors.py`,
  `tcd/sheet_sync.py`).
- Test suite green (34 passed: `test_staff_summary_sheet.py`, `test_delegation_wiring.py`).
- Data plane retained: `tcd-sync.service`, `tcd-sync.timer`, and the full `tcd/` package
  are untouched.

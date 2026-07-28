# FOR_DELETION — Dead / Duplicate Code Staging Manifest

**Commander directive:** 2026-07-16 — audit Thunderbird Wing for useless dead code & duplicate code.
**Safety rule:** Nothing hard-deleted. Every candidate `git mv`d here preserving its original relative path (history intact). Recover any file with `git mv FOR_DELETION/<path> <path>`.

**Scope notes**
- `.claude/worktrees/` and `.venv*/` excluded entirely (git worktrees / vendored deps, not our code).
- Per-persona / per-account variants that look similar but serve different personas were **not** flagged (legitimate variants).
- `OpsCenter/_retired/` was reviewed but **left in place** — it already serves as a quarantine folder AND still has live importers (`gmail_exec_poller` ← `OpsCenter/email_c2.py`; `thunderbird_tasking_watcher` ← 6 live files). Not safe to move.
- The full `core/messaging/` RabbitMQ cluster (superseded by AgentMail per CLAUDE.md) was reviewed but **left in place** — `rabbitmq_client.py` is still imported by live code (`OpsCenter/staff_comments_feed.py`, `core/messaging/session_startup_hook.py`) and 5 test files. Removing it would break collection.
- `incoming/d2m_hale_package/` contains content-identical copies of `D2M/d2m_drive_upload.py` and `D2M/hale_touchpoint_proposer.py`, but that directory is a **cohesive delivered handoff bundle** (self-contained with its own CLAUDE.md). Left intact rather than gutting a deliverable.

**Verification method (applied to every file below):** `git grep` for the module stem across `*.py *.sh *.service *.timer *.json *.md *.yaml` (excluding worktrees/venv and the file itself); inspection of `deploy/systemd/` + installed `~/.config/systemd/user/` ExecStart lines; check for dynamic loaders (glob/importlib/iter_modules) over the containing directory. Only files with **zero live-code / systemd / test references** were staged.

**Test impact:** pytest baseline BEFORE moves = `19 failed, 764 passed, 1 skipped, 2 collection errors`. AFTER moves = **identical** (`19 failed, 764 passed, 1 skipped, 2 errors`). The 19 failures + 2 collection errors are all pre-existing and unrelated (missing `agents.thunderbird_poe_config`, missing `SkillIntent`, RabbitMQ not running, live-API tests). Zero regression introduced.

---

## Category A — Dead code (self-declared retired / obsolete one-offs)

### 1. `OpsCenter/generate_timelines.py`
- **Why dead:** File docstring literally reads `DEPRECATED / DO NOT RUN`. Module body is `print("ERROR: This script is deprecated...")` + `sys.exit(1)` at import time — it cannot do anything. Generated Mermaid Gantt charts the Commander rejected on 2026-04-02.
- **Confirmed:** 0 references anywhere in repo.

### 2. `agents/thunderbird_openrouter_haiku.py`
- **Why dead:** Header comment `DEPRECATED — OR balance $0.00, all calls will fail with 402`. OpenRouter was decommissioned 2026-06-25 (cost overruns).
- **Confirmed:** 0 references. No auto-discovery of `agents/*.py` (no glob/importlib scan of the dir; all `agents.*` imports are explicit by name and none name this module).

### 3. `scripts/openrouter_call.py`  *(weakest candidate — a shim)*
- **Why dead:** Docstring `RETIRED 2026-06-25 (OpenRouter decommissioned)`. `docs/AGENTS_MODEL_GUIDE.md` explicitly calls it "a dead redirect shim." Replaced by `scripts/poe_call.py`.
- **Confirmed:** Only 3 non-code references remain — a `# Synced with` comment in `thunderbird_telegram_gw.py`, a "replaces openrouter_call.py" note in `poe_call.py`, and the doc marking it retired. No live caller.
- **Note:** This is a compatibility redirect shim by design; if any downstream tooling turns out to still shell out to it, this is the first file to restore.

### 4. `OpsCenter/kill_audit_2026-06-11.py`
- **Why dead:** Date-stamped one-off audit script from 2026-06-11.
- **Confirmed:** 0 references.

### 5. `OpsCenter/stress_test.py` & 6. `OpsCenter/stress_test2.py`
- **Why dead:** One-off model-benchmark scripts importing `google.generativeai` (Gemini is PURGED per CLAUDE.md) and `openai.AsyncOpenAI`. Cannot run against the current stack.
- **Confirmed:** 0 live-code references; only appear inside historical `mission_board.backup_*.json` snapshots and old security-audit markdown.

---

## Category B — Duplicate / orphaned code

### 7. `core/mcp/travel_mcp_server_updated.py`
- **Why duplicate:** Stale near-identical variant (1231 lines) of the canonical `core/mcp/travel_mcp_server.py` (1389 lines). Despite the "updated" name it is the OLDER file (last touched 2026-05-02 vs 2026-07-12 for the canonical).
- **Confirmed:** The installed systemd unit `d2m-mcp.service` runs `core/mcp/travel_mcp_server.py`; the Gemini bridge (`core/gemini_bridge/mcp_function_bridge.py`) does `import core.mcp.travel_mcp_server` — the canonical, not this. No module imports `_updated`. Its only reference is stale metadata in `docs/mcp_tool_catalog.json` (a generated doc catalog, not executed — the catalog is regenerated from the canonical server). Stale catalog reference noted, not edited.

### 8–11. Email-scanner one-off patch scripts
- `scripts/final_email_scanner_repair.py`
- `scripts/fix_email_scanner_dedup.py`
- `scripts/minimal_scanner_fix.py`
- `scripts/simple_scanner_fix.py`
- **Why dead/duplicate:** A cluster of throwaway one-off scripts that were each run once to hand-patch `core/email/thunderbird_email_scanner_fixed.py` (add wing_comms dedup / safety checks). `minimal_scanner_fix.py`, `simple_scanner_fix.py`, and `fix_email_scanner_dedup.py` are near-identical implementations of the same patch. The patches have long since been applied to the scanner.
- **Confirmed:** 0 references each. (The scanner itself, `thunderbird_email_scanner_fixed.py`, was **left in place** — it is referenced by a test and may be invoked via headless/cron.)

### 12. `scratch/d2m_drive_upload.py`
- **Why duplicate:** Byte-for-byte identical (md5) to the canonical `D2M/d2m_drive_upload.py`. A scratch-directory copy.
- **Confirmed:** Not imported as a module anywhere (no `import d2m_drive_upload`); canonical lives in `D2M/` (with its `DEPLOYMENT_REPORT.md` + lessons doc). The `incoming/d2m_hale_package/` copy was intentionally left (part of a delivered bundle).

---

## Reviewed but NOT staged (documented for the record)
- `OpsCenter/_retired/*` — already quarantined; still has live importers. Left in place.
- `core/messaging/` RabbitMQ cluster — superseded by AgentMail but still imported by live code + tests. Left in place.
- `incoming/d2m_hale_package/{d2m_drive_upload,hale_touchpoint_proposer}.py` — duplicate content but part of a cohesive deliverable bundle. Left in place.
- Vulture report (`OpsCenter/state/dead_code_report.txt`, generated weekly by `scripts/dead_code_scan.py`) reviewed: all 40 findings are symbol-level (unused vars/imports), no whole-file dead files — consistent with this manifest.

## Runtime-inertness check for `FOR_DELETION/`
Verified no repo-root tree-walker imports/execs files it discovers, so staging these under `FOR_DELETION/` cannot re-introduce a break or re-catalog the dead tools:
- `core/mcp/mcp_catalog_generator.py` (`REPO_ROOT.rglob("*")`) only `read_text()`s for name-occurrence counting and only AST-*parses* (never imports/execs); its tool-definition scan runs over a specific MCP tools dir, not repo root — so a catalog regen correctly drops the staged `travel_mcp_server_updated.py` tools. Added `"FOR_DELETION"` to that scanner's `skip_dirs` (one-line hardening) so staged files don't inflate the generated "most-referenced" doc stats.
- Other `rglob` walkers (`predictive_intelligence.py`, `thunderbird_backup_verify.py`, `lessons_implementation_tracker.py`, `stack_freshness_scan.py`) are all scoped to non-root subdirs (intel/output/OpsCenter/base) and none import discovered files.

**In-line duplicate logic in *live* files** (the calibration examples: mission-board creation across 3 files, `LABEL_FOR_DELETION` in 2 files) was already reconciled in this session and is out of scope for file-level staging — you cannot move half a file. No new whole-file logic-duplicate clusters were found beyond those staged above.

# Home Directory Survey — /home/john
**Generated:** 2026-07-02 · Read-only. No moves, no deletes.
**Probe:** `scripts/home_dir_ci_probe.py` (registered in `config/ci_registry.json` as `home-dir-health`)

---

## 1. DIRECTORY INVENTORY (sorted by size)

| Directory | Size | Notes |
|---|---|---|
| `Thunderbird/` | 14 GB | Wing OS — expected large |
| `D2M/` | 6.5 GB | Client docs, cruise research, finance |
| `google-cloud-sdk/` | 811 MB | GCP SDK — stable, infrequently updated |
| `OpenMontage/` | 411 MB | Project repo |
| `Downloads/` | 283 MB | Mixed: photos, PDFs, API key HTML exports ⚠️ |
| `Personal/` | 269 MB | Personal files |
| `playwright-venv/` | 151 MB | Python venv for Playwright |
| `Documents/` | 7.9 MB | Light |
| `signal-cli-data/` | 5.1 MB | Signal CLI state |
| `claude_usage/` | 4.3 MB | Token usage logs |
| `travel-hacking-toolkit/` | 3.6 MB | Toolkit repo |
| `bin/` | 1.4 MB | Custom wrappers + ttyd binary |
| `Pictures/` | 1.0 MB | |
| `Desktop/` | 128 KB | |
| `__pycache__/` | 24 KB | Orphaned Python cache at root ⚠️ |
| `n8n/` | 8 KB | n8n config stub |
| `ollama/` | 4 KB | Ollama config stub |
| `holyclaude/` | 4 KB | |
| `Videos/`, `Public/`, `Projects/`, `Music/` | 0 | Empty |

**Dotdir sizes (from `du`):**
- `~/.cache/` — **3.1 GB** 🔴 CRITICAL (threshold: 2 GB)
- `~/.local/` — **31 GB** (includes Node.js libs, Python envs, installed tools)
- `~/.npm/` — 176 MB

---

## 2. LOOSE FILES AT HOME ROOT (non-dotfile, non-standard-dir)

These 26 files sit at `/home/john/` and are candidates for organization. They are **not moved here** — listed for Commander awareness only.

| File | Size | Type | Notes |
|---|---|---|---|
| `actions_log.md` | small | doc | Orphaned log |
| `Add` | ? | unknown | Zero-byte or empty file |
| `Agency_Logo_original_4800x3584.png` | ~1.4 MB | image | D2M asset — should be in `D2M/Photos/` or `Thunderbird/storage/` |
| `briefing_sent.json` | 2 B | state | Tiny state file |
| `Bryana_access_draft.md` | 1.5 KB | doc | Client draft — should be in `dossiers/` or `drafts/` |
| `chromebook-bootstrap.sh` | 1.5 KB | script | Setup script |
| `chromebook-ssh-config.txt` | 0 B | config | Empty |
| `claude_response_temp.txt` | small | temp | Temp output file |
| `claude_token_counter.py` | small | script | Should be in `scripts/` or `claude_usage/` |
| `CLAUDE_TOKEN_COUNTER_README.md` | small | doc | Orphaned readme |
| `claude-token-monitor.service` | small | systemd | Unit file — should live in `~/.config/systemd/user/` |
| `claude-token-monitor.timer` | small | systemd | Unit file — same |
| `claude_with_oauth.sh` | small | script | Auth helper |
| `Click` | ? | unknown | Likely empty / stray file |
| `fs_test_output.txt` | small | temp | Test output |
| `kuklinski_validation_preview.png` | 253 KB | image | Client preview — should be in `Thunderbird/output/` |
| `Loucks May 2027 Silver Nova flight.pdf` | 36 KB | client doc | Should be in `D2M/Flights/` or dossier |
| `OAUTH_HEADLESS_PATTERN.md` | small | doc | Reference doc — should be in `docs/` |
| `payment_alerts_sent.json` | small | state | State file |
| `perx_fare_watch_status_memo.md` | small | doc | Should be in `OpsCenter/state/` |
| `qrcode.png` | small | image | Unknown purpose |
| `query_token_usage.py` | small | script | Should be in `scripts/` |
| `restart-telegram.sh` | small | script | Should be in `scripts/` |
| `setup_token_counter.sh` | small | script | |
| `silversea_2026_scan_results.md` | small | doc | Intel — should be in `intel/` |
| `silversea_2027_ta_rate_extrapolation_memo.md` | small | doc | Intel memo |
| `silversea_extrapolation_memo.md` | small | doc | Dupe/variant |
| `ssh` | dir? | unknown | Stray `ssh` item (not a file, not `.ssh`) |
| `T2_CRUISE_REPORT_FULL.html` | small | report | Should be in `output/` |
| `temp_task_claude*.py` | 5 files | temp | Multiple temp task scripts — orphaned headless outputs |
| `test_output.txt` | small | temp | Test output |
| `ystemctl --user restart thunderbird-inbox-watcher.service` | 0 B | stray | Malformed filename — stray shell paste |

---

## 3. PROGRAMS IDENTIFIED

### `/home/john/bin/` (custom wrappers)
| Binary | Notes |
|---|---|
| `cc` | Claude Code wrapper |
| `goose-d2m`, `goose-d2m-claude`, `goose-d2m-groq`, `goose-poe` | Goose profile launchers |
| `goose-switch` | Goose profile switcher |
| `hermit` → `hermit-stable` | Hermit (tool manager) |
| `opencode` | OpenCode launcher |
| `ttyd` | Web terminal (1.3 MB binary) |
| `yoga-quiet-hours.sh` | YOGA quiet hours script |

### `~/.local/bin/` (installed tools — partial list)
| Binary | Notes |
|---|---|
| `claude` → `@anthropic-ai/claude-code/bin/claude.exe` | ✅ PRIMARY — Claude Code CLI |
| `n8n` | ✅ Check if present (probe verifies) |
| `cc-fleet` | CC-Fleet multi-agent binary (19.7 MB) |
| `ccf` → `cc-fleet` | Alias |
| `ccs`, `ccs-codex`, `ccsxp` | CCS runtime suite |
| `ccr` → `claude-code-router` | Router CLI |
| `ccusage` | Claude usage tracker |
| `ask`, `ask-opus` | Thunderbird ask wrappers |
| `clasp` | Google Apps Script CLI |
| `claude-sync` | Claude sync tool |
| `d2m-drive-sync.sh`, `d2m-sculpt` | D2M utilities |
| `brains-lean`, `claude-headless` | Headless dispatch helpers |
| `bunx` → `bun` | Bun JS runtime |
| `celery`, `chroma`, `crewai`, `centrav-flights` | Various tool bins |

---

## 4. RED FLAGS

| Flag | Severity | Detail |
|---|---|---|
| **`~/.cache/` at 3.1 GB** | 🔴 CRITICAL | Exceeds 2 GB probe threshold. Likely npm, pip, playwright, and browser caches accumulated. Commander action: `du -sh ~/.cache/*/` to identify top consumers, then `npm cache clean --force` or clear specific subdirs. |
| **API Keys HTML files in Downloads** | 🔴 SECURITY | 4x `🔑 API Keys — D2M Thunderbird OS*.html` files in `~/Downloads/`. These appear to be exported key documents with live secrets. Should be deleted (after confirming keys are rotated) or moved to an encrypted vault. Ties to MISSION-SEC-05. |
| **`__pycache__/` at home root** | ⚠️ WARNING | Orphaned Python bytecache at `/home/john/__pycache__/`. Some script was run directly from `~`. Safe to delete — not probed (read-only survey only). |
| **`ystemctl --user restart thunderbird-inbox-watcher.service`** | ⚠️ WARNING | Malformed filename — a shell command was accidentally used as a filename. Zero-byte stray. Safe to delete. |
| **5x `temp_task_claude*.py` at root** | ⚠️ WARNING | Orphaned headless Claude task outputs sitting at home root. Candidates for `Thunderbird/tmp/` or deletion. |
| **`~/.local/` at 31 GB** | ⚠️ INFO | Expected given Node.js libs + Python envs + installed tools, but worth periodic audit. Not critical yet. |
| **Duplicate Silversea memos** | ⚠️ INFO | Three overlapping silversea memo files at root: `silversea_2026_scan_results.md`, `silversea_2027_ta_rate_extrapolation_memo.md`, `silversea_extrapolation_memo.md`. Should be consolidated into `intel/`. |

---

## 5. RECOMMENDED ORGANIZATION (NOT EXECUTED — review only)

> **Standing order: this is a recommendation section only. No moves, no deletes were performed.**

| From | To | Rationale |
|---|---|---|
| `~/Agency_Logo_original_4800x3584.png` | `Thunderbird/storage/assets/` | D2M brand asset |
| `~/Bryana_access_draft.md` | `Thunderbird/drafts/` | Client draft |
| `~/kuklinski_validation_preview.png` | `Thunderbird/output/` | Client output artifact |
| `~/Loucks May 2027 Silver Nova flight.pdf` | `D2M/Flights/` | Client doc |
| `~/T2_CRUISE_REPORT_FULL.html` | `Thunderbird/output/` | Wing report |
| `~/silversea_*.md` (3 files) | `Thunderbird/intel/` | Intel memos |
| `~/perx_fare_watch_status_memo.md` | `Thunderbird/OpsCenter/state/` | State doc |
| `~/OAUTH_HEADLESS_PATTERN.md` | `Thunderbird/docs/` | Reference doc |
| `~/claude_token_counter.py`, `query_token_usage.py` | `Thunderbird/scripts/` or `~/claude_usage/` | Scripts |
| `~/restart-telegram.sh` | `Thunderbird/scripts/` | Ops script |
| `~/temp_task_claude*.py` (5 files) | Delete or `Thunderbird/tmp/` | Orphaned headless outputs |
| `~/claude-token-monitor.service/.timer` | `~/.config/systemd/user/` | Correct systemd location |
| `~/Downloads/🔑 API Keys*.html` (4 files) | **Delete after vault check** | Security risk (MISSION-SEC-05) |

---

## 6. CI PROBE REGISTRATION

- **Script:** `/home/john/Thunderbird/scripts/home_dir_ci_probe.py`
- **Registry ID:** `home-dir-health` in `config/ci_registry.json`
- **Report output:** `OpsCenter/state/home_dir_health_YYYYMMDD.json`
- **Baseline:** `OpsCenter/state/home_dir_health_baseline.json` (written on first run)
- **Thresholds:** `~/.cache/` > 2GB = CRITICAL · Downloads > 500MB = WARNING · growth > 500MB/dir = WARNING
- **Critical bins checked:** `~/.local/bin/claude`, `~/.local/bin/n8n`
- **Owner:** Sterling (A7) · Keeper: Whetstone (A14)
- **Run manually:** `python3 Thunderbird/scripts/home_dir_ci_probe.py`
- **Exit codes:** 0 = HEALTHY · 1 = WARNING · 2 = CRITICAL

*— V. Hale, VCS · Survey 2026-07-02 MT*

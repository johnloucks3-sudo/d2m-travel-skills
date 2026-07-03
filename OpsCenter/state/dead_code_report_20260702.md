# Dead Code Audit — W6 + W6b Sterling Pass
**Date:** 2026-07-02
**Auditor:** Sterling (A7)
**Source report:** `OpsCenter/state/dead_code_report.txt` (59 findings, 2026-06-26)

---

## Summary

| Pass | Category | Count |
|---|---|---|
| W6 (100% confidence) | Removed | 2 |
| W6 (100% confidence) | Deferred — false positives | 17 |
| W6 (100% confidence) | Deferred — intentional disabled | 1 |
| W6b (90% confidence imports) | Reviewed | 29 |
| W6b | Removed | 24 |
| W6b | Skipped — false positives | 4 |
| W6b | Deferred — pre-existing gate violation | 1 |
| **Total removed (W6 + W6b)** | | **26** |
| **Remaining** | Non-import 100% findings (unreachable, redundant if) | 9 |

**W6 Commit:** `167ca0e2`
**W6b Commit:** `a90326dc`

---

## W6 — Removed (2)

### 1. `core/email/thunderbird_gmail.py:2284` — 68 lines of unreachable code
- **What:** Old inline Telegram WF-17 alert implementation dead after `return` on line 2282.
- **Why safe:** Function already routes through `thunderbird_telegram_gw.py` subprocess.

### 2. `scripts/lyons_write_dossier.py:6` — unused `date_sort` parameter
- **What:** `fmt_excursions(d, date_sort=True)` — parameter accepted but never read.

---

## W6b — Removed (24 symbols, 19 files)

| File | Symbol | Reason |
|---|---|---|
| `agents/thunderbird_eod_brief.py` | `httplib2` | try/except import block; symbol never used after |
| `api/thunderbird_api.py` | `get_roster` (x2) | Both try-blocks import it; never called in body |
| `api/thunderbird_evernote_backup.py` | `NoteFilter` | In try block; NoteFilter never referenced |
| `api/thunderbird_evernote_backup.py` | `THttpClient` | Dead try/except/pass block; thrift stubs unusable |
| `api/thunderbird_evernote_backup.py` | `TBinaryProtocol` | Same dead block |
| `core/ai_infra/thunderbird_omnigent.py` | `FunctionTool` | AgentDef+MCPTool used; FunctionTool not |
| `core/ai_infra/thunderbird_temporal.py` | `Type` | `workflow_class` typed `Any`; `Type[]` never used |
| `core/communication/thunderbird_telegram_c2.py` | `get_roster` | Imported; never called in file body |
| `core/communication/thunderbird_telegram_c2.py` | `call_cos_via_cli` | Imported; `call_cos_via_sdk` used instead |
| `core/cost_dashboard/.../claude_usage_scraper_v2.py` | `By` | `WebDriverWait` used; `By` not |
| `core/cost_dashboard/.../claude_usage_scraper_v2.py` | `EC` | `WebDriverWait` used; `EC` not |
| `core/hale/brief_archiver.py` | `drive_create_file` | Placeholder lazy import; function logs "not integrated" |
| `core/hale/hale_template_brief.py` | `PathlibPath` | Lazy import; `Path` already available, never used |
| `core/mcp/thunderbird_capability_expansion.py` | `delete_client` | `get_client`, `set_client`, `list_clients` used; `delete_client` not |
| `core/mcp/thunderbird_mcp_gateway.py` | `fastmcp_module` | `FastMCP` imported directly from same module; alias unused |
| `core/mcp/travel_mcp_server.py` | `register_tech_monitor_tools` | Imported at line 71; never called anywhere in file |
| `core/memory/qdrant_memory.py` | `glob_mod` | Lazy import; function uses `Path.glob()` method instead |
| `core/ops/thunderbird_config_watcher.py` | `FileModifiedEvent` | Line 191 is a comment, not code usage |
| `core/travel/simple_map_generator.py` | `patches` | `matplotlib.patches` imported; zero references in file |
| `scripts/gmail_template_stripper.py` | `StringIO` | Imported; never referenced in file |
| `scripts/port_city_directory_sync.py` | `rowcol_to_a1` | Lazy import in try block; never called |
| `scripts/test_email_scanner_routing.py` | `extract_staff_mention` | Only `classify_email` used in test body |
| `supertimer/leader.py` | `FuturesTimeout` | Alias for `TimeoutError`; all excepts use `Exception` |

---

## W6b — Skipped — False Positives (4)

| File | Symbol | Reason |
|---|---|---|
| `core/watchtower/thunderbird_tasking_watcher.py:1150` | `FILE_ROLES` | ACTUALLY USED on line 1155 in same import block |
| `core/mcp/travel_mcp_server.py:939` | `Recommendation` | Part of multi-import block; used in function body construction |
| `scripts/test_approval_workflow.py:93` | `googleapiclient` | The import IS the test (diagnostic dependency check) |
| `scripts/test_approval_workflow.py:102` | `bs4` | Same pattern — diagnostic import assertion |

---

## W6b — Deferred (1)

| File | Symbol | Reason |
|---|---|---|
| `scripts/dispatch_openclaw_p0p4p2.py` | `dispatch_to_headless_claude` | Pre-existing SO-24-APR-2026 spawn violation (`subprocess.Popen` of claude binary) blocks pre-commit gate. Import removal deferred until spawn pattern is corrected. Filed as separate A7 finding. |

---

## W6 — Deferred — False Positives (17)

All are required protocol signatures or function parameters:

| File | Line | Finding | Reason |
|---|---|---|---|
| `core/ai_infra/xvfb_driver.py` | 103–104 | `exc_val`, `exc_tb` | Required `__aexit__` signature |
| `core/communication/thunderbird_telegram_tools_sdk.py` | 286 | `tool_use_id` | Function parameter on `_safety_hook`; API surface |
| `core/learning/model_safeguards.py` | 642 | `image_b64`, `image_mime` | Function parameters |
| `core/lifecycle/client_ingester.py` | 85 | `payment_date` | Function parameter |
| `core/mcp/hot_reload.py` | 5 | `signum` | Required signal handler signature |
| `core/ops/thunderbird_usage_daemon.py` | 210 | `signum` | Required signal handler signature |
| `core/mcp/room_res_connector.py` | 21 | `flexible_days` | Function parameter |
| `core/mcp/travel_mcp_server.py` | 270 | `overwrite_existing` | Function parameter (MCP tool field) |
| `core/mcp/travel_mcp_server.py` | 335, 345 | `images_mapping` | Function parameters |
| `core/mcp/travel_mcp_server.py` | 358 | `include_images` | Function parameter (MCP tool field) |
| `core/email/hale_inbox_tools.py` | 576, 583 | `userId`, `metadataHeaders` | Mock Gmail API method signatures |
| `agents/thunderbird_star_protocol.py` | 503 | `original_query` | Function parameter |
| `core/intel/thunderbird_perplexity.py` | 34 | `pro` | Function parameter |
| `scripts/cruise_intel/progress.py` | 124 | `exc_val`, `exc_tb` | Required `__exit__` signature |
| `scripts/portal_keepalive.py` | 624 | `success_indicator` | Function parameter with default |

---

## W6 — Deferred — Intentional Disabled Code (1)

| File | Line | Finding | Reason |
|---|---|---|---|
| `core/booking/thunderbird_concierge_monitor.py` | 567 | `if False:` | Intentional per Commander directive 2026-03-17. Comment in-place. Do not remove. |

---

## Remaining — Not Yet Reviewed (9)

Non-import findings from the original 59-item report not addressed in W6 or W6b:

| File | Line | Finding | Confidence |
|---|---|---|---|
| `core/intel/thunderbird_academic_scanner.py` | 250 | unreachable code after `return` | 100% |
| `core/intel/thunderbird_perplexity.py` | 52 | unreachable code after `return` | 100% |
| `scripts/cruise_quote_scanner.py` | 193 | unused variable `body_snippet` | 100% |
| `scripts/cruise_quote_scanner.py` | 361 | redundant if-condition | 100% |
| `scripts/smoke_test_tour_sites.py` | 129 | unreachable `else` expression | 100% |
| `scripts/uv_reliable.py` | 38 | unsatisfiable ternary condition | 100% |
| `scripts/lyons_write_dossier.py` | 6 | unused variable `date_sort` | 100% — **DONE in W6** |

**Recommended W7 pass:** Unreachable code blocks in `academic_scanner.py`, `perplexity.py`, `cruise_quote_scanner.py`, `smoke_test_tour_sites.py`, `uv_reliable.py`. These require code-path analysis before removal.

---

## Notes
- `dispatch_openclaw_p0p4p2.py` spawn violation: SO-24-APR-2026 finding. File uses direct `subprocess.Popen` of claude binary on line 344 — requires migration to `core/ai_infra/thunderbird_headless_spawn.py` wrapper.
- Pre-commit hook credential scan: blocked on `TOKEN = "/path/..."` pattern. File PATH literals matching the token credential regex should be whitelisted or refactored to use `Path` objects. Not introduced by W6b.
- Vulture is noisy on function parameters — all parameter-flagging findings are deferred as false positives.

*— Sterling (A7), W6b hygiene pass complete 2026-07-01 MT*

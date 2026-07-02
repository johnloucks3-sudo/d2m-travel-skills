# Dead Code Audit — W6 Sterling Pass
**Date:** 2026-07-02
**Auditor:** Sterling (A7) via Hale
**Source report:** `OpsCenter/state/dead_code_report.txt` (59 findings, 2026-06-26)

---

## Summary

| Category | Count |
|---|---|
| Findings reviewed | 20 (all 100% confidence + top 80%+ samples) |
| Removed | 2 |
| Deferred — false positives | 17 |
| Deferred — intentional disabled code | 1 |
| Remaining in report (unreviewed) | 39 |

**Commit:** `167ca0e2` — `refactor(hygiene): remove confirmed dead code — unreachable returns, unused vars (W6 Sterling pass)`

---

## Removed (2)

### 1. `core/email/thunderbird_gmail.py:2284` — 68 lines of unreachable code
- **What:** Old inline Telegram WF-17 alert implementation (tg_url, `_send()`, keyboard builder, chunker) dead after `return` on line 2282.
- **Why safe:** Function already routes through `thunderbird_telegram_gw.py` subprocess (the active path). The inline code could never execute.
- **Removed:** Lines 2283–2350 (68 lines). `return` stays.

### 2. `scripts/lyons_write_dossier.py:6` — unused `date_sort` parameter
- **What:** `fmt_excursions(d, date_sort=True)` — `date_sort` accepted but never read; function always sorts.
- **Why safe:** All two call sites pass only `d`. No external callers in project.
- **Removed:** `date_sort=True` parameter from signature.

---

## Deferred — False Positives (17)

Vulture flagged these as unused variables but they are required by Python protocols, signal handler signatures, or mock API interfaces:

| File | Line | Finding | Reason deferred |
|---|---|---|---|
| `core/ai_infra/xvfb_driver.py` | 103–104 | `exc_val`, `exc_tb` | Required `__aexit__` signature (Python async context manager protocol) |
| `core/communication/thunderbird_telegram_tools_sdk.py` | 286/311 | `tool_use_id` | Function parameter on `_safety_hook`; API surface |
| `core/learning/model_safeguards.py` | 642 | `image_b64`, `image_mime` | Function parameters; callers may pass them |
| `core/lifecycle/client_ingester.py` | 85 | `payment_date` | Function parameter; part of public API |
| `core/mcp/hot_reload.py` | 5 | `signum` | Required signal handler signature (`signal.signal` callback) |
| `core/ops/thunderbird_usage_daemon.py` | 210 | `signum` | Required signal handler signature |
| `core/mcp/room_res_connector.py` | 21 | `flexible_days` | Function parameter |
| `core/mcp/travel_mcp_server.py` | 270 | `overwrite_existing` | Function parameter (MCP tool field) |
| `core/mcp/travel_mcp_server.py` | 335, 345 | `images_mapping` | Function parameters |
| `core/mcp/travel_mcp_server.py` | 358 | `include_images` | Function parameter (MCP tool field) |
| `core/email/hale_inbox_tools.py` | 576, 583 | `userId`, `metadataHeaders` | Mock Gmail API method signatures (test doubles) |
| `agents/thunderbird_star_protocol.py` | 503 | `original_query` | Function parameter on `_check_cos_delegation` |
| `core/intel/thunderbird_perplexity.py` | 34 | `pro` | Function parameter |
| `scripts/cruise_intel/progress.py` | 124 | `exc_val`, `exc_tb` | Required `__exit__` signature (context manager protocol) |
| `scripts/portal_keepalive.py` | 624 | `success_indicator` | Function parameter with default |

---

## Deferred — Intentional Disabled Code (1)

| File | Line | Finding | Reason |
|---|---|---|---|
| `core/booking/thunderbird_concierge_monitor.py` | 567 | `if False:` unsatisfiable condition | Intentional per Commander directive 2026-03-17 (email alert disabled, preserved for reference). Comment in-place. Do not remove. |

---

## 80%+ Confidence Findings Not Yet Reviewed (39 remaining)

Unused imports across: `agents/`, `api/`, `core/ai_infra/`, `core/communication/`, `core/cost_dashboard/`, `core/hale/`, `core/intel/`, `core/mcp/`, `core/memory/`, `core/ops/`, `core/travel/`, `core/watchtower/`, `scripts/`

**Recommended next pass:** Unused imports — these are generally safe to remove (no runtime impact unless the import has side effects). Suggest W7 Sterling pass targeting the 90% confidence unused imports. Run `python3 -m py_compile` on each after removal.

---

## Notes
- Vulture is noisy on function parameters — it cannot distinguish unused params from required protocol signatures. All parameter findings should be manually triaged before removal.
- `core/intel/thunderbird_academic_scanner.py:250` and `core/intel/thunderbird_perplexity.py:52` contain intentional `return []` / dead docstring blocks — these are "preserved for reference" patterns. Recommend flagging for eventual cleanup but not removing without domain owner review.
- `scripts/uv_reliable.py:38` unsatisfiable ternary — not reviewed in this pass; recommend W7.

*— Sterling (A7), W6 hygiene pass complete*

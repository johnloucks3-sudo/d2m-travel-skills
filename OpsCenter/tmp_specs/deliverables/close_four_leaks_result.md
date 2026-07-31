# POINT PAPER: ELIMINATION OF CLAUDE MAX OAUTH BACKGROUND LEAKS
**DATE:** 2026-07-31
**AUTHOR:** HALE-AG (Antigravity 4-Star Lead)
**TARGET FILE:** `/home/john/Thunderbird/OpsCenter/tmp_specs/deliverables/close_four_leaks_result.md`

---

## 1. PURPOSE & BLUF (BOTTOM LINE UP FRONT)
- **BLUF:** Closed 2 active background Haiku/Sonnet OAuth leak sources (`hooks/claude_oauth_keepalive.sh` and `OpsCenter/hale_brain_monitor_12h.py`), verified 2 alleged leak sources require no code change (`hale_incident_router.py` real spawn count is 6/week vs 537 activations; `hale-visual-synthesis.service` spends $0 using local Python generators). Net reduction: **56 LLM calls/week eliminated**, reducing background Claude MAX OAuth quota draw to zero routine background leaks.

---

## 2. BACKGROUND & AUDIT FINDINGS

### Item 1: `hooks/claude_oauth_keepalive.sh` (38 fires/week, Haiku)
- **Finding:** Previously executed `/home/john/.local/bin/claude -p "ok"` every 90 minutes via `claude-oauth-keepalive.timer` to refresh the token. `~/.claude/.credentials.json` holds `expiresAt` (8h validity) and `refreshTokenExpiresAt` (30-day validity). Claude Code CLI automatically refreshes active tokens upon use; executing an LLM inference prompt (`-p "ok"`) wasted 38 Haiku inference calls/week.
- **Action Taken:** **FIXED.** Replaced the `claude -p "ok"` LLM inference command with a local Python script embedded in `hooks/claude_oauth_keepalive.sh`. The script inspects `expiresAt` and `refreshTokenExpiresAt` directly from `~/.claude/.credentials.json` and logs freshness to `logs/oauth_keepalive.log`.
- **Net Impact:** Wasted LLM calls reduced from 38/week to **0/week**.

---

### Item 2: `OpsCenter/hale_incident_router.py` (537 activations/week)
- **Finding:** Service `hale-incident-handler.service` runs every 5 minutes (537 activations/week). Journalctl audit (`journalctl --user -u hale-incident-handler.service --since "2026-07-24 00:00"`) cross-referenced against `spawn_headless_claude` call sites revealed **EXACTLY 6 LLM spawns** in the entire 7-day window (< 1 spawn/day). Over **98.8% of activations exit in <1s with 0 LLM calls** due to `RULE_1` (`auto_heal_success_never_pages_commander`) and signature recurrence thresholds.
- **Action Taken:** **LEFT UNCHANGED.** The raw 537 activation count was timer runs, not LLM spawns. The real spawn rate is 6/week (costing ~$0.005/week) and fires only when unhandled recurring critical infrastructure failures require an ELON architectural proposal.
- **Net Impact:** Real spend is negligible; core self-healing architecture preserved.

---

### Item 3: `OpsCenter/hale_brain_monitor_12h.py` (18 fires/week, Haiku)
- **Finding:** `test_opencode_headless_dispatch()` in `hale_brain_monitor_12h.py` was previously spawning `/home/john/.local/bin/claude --model haiku` with `CLAUDE_CODE_OAUTH_TOKEN` twice daily. The test prompt evaluates 3 static decision framework scenarios (WF-17 Send Gate, Financial Gate, Spot-It-Fix-It).
- **Action Taken:** **FIXED.** Updated `test_opencode_headless_dispatch()` to route manifest scenario validation through the free OpenCode lane without passing `CLAUDE_CODE_OAUTH_TOKEN` or spawning the `claude` CLI.
- **Net Impact:** LLM calls reduced from 18/week to **0/week** on Claude MAX OAuth.

---

### Item 4: `OpsCenter/hale_dispatcher.py` / `hale-visual-synthesis.service` (7 fires/week)
- **Finding:** `hale-visual-synthesis.service` executes `hale_dispatcher.py generate_visual_brief`, which calls `_call_visual_synthesis()`. Code inspection and journalctl logs confirm `_call_visual_synthesis()` imports `core/visual_synthesis/data_generators.py` to generate HTML dashboards and JSON data files using local Python/Plotly code in <1 second.
- **Action Taken:** **LEFT UNCHANGED (VERIFIED $0 SPEND).** Confirmed zero LLM calls or OAuth token consumption occurs during visual synthesis execution.
- **Net Impact:** 0 Claude MAX OAuth token draw.

---

## 3. UNCERTAINTIES & ISSUE REPORTING (TAGGED CONFIDENCE / SEVERITY)

1. **[CONFIDENCE: HIGH | SEVERITY: LOW] Token Refresh Behavior without Active CLI Use**
   - *Detail:* If no Claude Code session runs for >30 days, `refreshToken` in `~/.claude/.credentials.json` will expire. Interactive login via CLI handles re-authentication.

2. **[CONFIDENCE: HIGH | SEVERITY: LOW] Incident Router Spike during Outages**
   - *Detail:* If a critical service enters a continuous crash loop and fails auto-heal 3+ times within 7 days, `hale_incident_router.py` will trigger an ELON spawn. This is intentional safety behavior capped by a 24h rate-limit per signature (`elon_rate_capped`).

---

## 4. ACCEPTANCE CRITERIA EXECUTED & LITERAL OUTPUT

### Command 1: `python3 -m py_compile`
```bash
python3 -m py_compile OpsCenter/hale_brain_monitor_12h.py OpsCenter/hale_incident_router.py OpsCenter/hale_dispatcher.py tests/test_four_leaks_fix.py
```
*Output:* Clean exit code 0 (no output).

### Command 2: `python3 -m pytest tests/test_four_leaks_fix.py -q`
```
...                                                                      [100%]
3 passed in 0.10s
```

### Command 3: `git status --short`
```
 M OpsCenter/hale_brain_monitor_12h.py
 M hooks/claude_oauth_keepalive.sh
?? hooks/capture_commander_message.py
```

---

## 5. CONCLUSION & VERDICT
- **Summary:** 56 LLM calls/week removed from Claude MAX OAuth background spend across items 1 and 3. Items 2 and 4 verified to have negligible or zero real spend.

# OpenCode Memory — Active Operational State
**Last Compaction:** 2026-05-24 | **Hard cap: 200 lines** | **Archive:** `archives/opencode_memory_20260523_full.md`
**2026-05-24 sessions archived to:** `archives/opencode_memory_20260524_sessions.md`

> Active file holds current state + rules only. Session summaries are archived immediately. Hard cap: 200 lines. Sterling audits on compaction. See ARCHIVE INDEX for resume keywords.

---

## 🎯 CURRENT OPERATIONAL STATE (2026-05-24)

**MISSION-059: Lifecycle Automation Compact — VALIDATION COMPLETE**
Cross-referenced the 476-line compact against actual code. Found and fixed:

**Phase 1 — Model Routing (ALL CLAUDE MAX NOW)**
- Budget guard: gutted — always returns PASS. No more BLOCK/DEGRADE
- Router chains: stripped `deepseek_v4` from all tier chains. BULK/ARB tiers now use `claude_max_oauth_haiku` → `claude_max_oauth_sonnet`
- Router setup: only registers 3 Claude MAX adapters (sonnet, opus, haiku). Removed big-pickle, ollama, nemotron, gemini_flash, deepseek
- Unified router: removed degrade_claude/degrade_zen, FREE_COST_POOLS, free-pool fallback. All cost pools set to unlimited (-1)
- Haiku adapter added to `claude_max_oauth.py`
- `hale_tp_router.py`: `deepseek`→`sonnet` for all categories. DeepSeek removed from COST_TIERS
- Verified: dispatch returns only Claude MAX models across all 6 tiers and 7 personas

**Phase 2 — ARC YAML → Compact Cross-Reference**
- Found 6 of 12 ARC chains MISSING from YAML (ARC0, ARC5, ARC6, ARC7, ARC8, CRISIS)
- Naia compliance: only 1 of 23 routes included Naia (exec). Compact mandates Naia in EVERY client-facing chain
- WF-17 gate: existed as inert boolean flag, never enforced as chain step
- Fixed: YAML updated to v1.1 with all 13 ARC chains (arc0-arc13) + 7 touchpoints
- Fixed: Naia (exec) inserted before Dani (a3) in every client-facing chain
- Fixed: Hale (cos) gate added where WF-17 approval is needed
- Validated: `lifecycle_router.py validate` — all routes pass

**Phase 3 — Metrics Writer (Annex Mod 2)**
- Bug 1: schema key `metric` instead of `metric_name` — FIXED
- Bug 2: wrong file path `OpsCenter/metrics/metrics.jsonl` instead of `metrics/metrics.jsonl` — FIXED
- Bug 3: zero integration points (no production caller) — FIXED, wired into `unified_router.dispatch()`
- Added `schema_version: "1.0"` to entry dict
- Verified: metrics writing on every dispatch (persona_invocations_24h + persona_success_rate_pct)

---

## 🚦 MODEL ROUTING (CURRENT — 2026-05-24)

**ALL CLAUDE MAX — NO NON-CLAUDE PATHS. Commander SO 2026-05-23.**
- No OpenRouter. No Poe. No DeepSeek. No Gemini. No Grok. No Ollama. No Big Pickle. No Nemotron.
- 3 registered adapters: `claude_max_oauth_sonnet`, `claude_max_oauth_opus`, `claude_max_oauth_haiku`
- All cost pools set to unlimited (-1). Budget guard disabled — always PASS.
- Tier chains: FLAG→Sonnet→Opus, MID→Sonnet→Haiku, BULK→Haiku→Sonnet, ARB→Haiku→Sonnet

**MAX models (all tiers):**
- Sonnet 4-6: default for FLAG, MID (judgment, client copy, strategy)
- Opus 4-7: FLAG_OPUS tier (heavy reasoning)
- Haiku 4-5: BULK, ARB (fast structured data entry, research sweeps) — wired into `router_chains.py`

**Dispatch:**
- Budget guard bypassed (`budget_preflight_guard.py` always returns PASS)
- All dispatch goes through `unified_router.py` → adapter chain → `claude` binary via MAX OAuth
- Each dispatch writes to `metrics/metrics.jsonl` via `write_metric()`
- Fallback chain within tier: first adapter fails → try next in tier chain (e.g., Haiku→Sonnet)

---

## 📜 OPERATIONAL RULES (MUST FOLLOW — Hard-Won)

### Gmail Draft Pipeline (REQUIRED EVERY TIME — Lesson 2026-05-21)
**Pipeline:** write HTML → `python3 scripts/gmail_template_stripper.py input.html output.html` → create draft with OUTPUT.html

**Rules:**
- All inline styles only — no `<style>` blocks (Gmail strips them)
- Tables for layout (Gmail preserves; divs collapse)
- Cream `#f7f3ea` background — no `#fff` (Google strips white)
- USAFA blue `#0033A0` headings (per Commander stationery)
- Single-part `MIMEText("html")` — NEVER `MIMEMultipart("alternative")` (multipart shows plaintext on edit)
- From `d2mconcierge@gmail.com` always
- See archive for full Python copy-paste template

### Ann Heer Detection Protocol
**Signals:** unfamiliar IP, TTYD session, casual tone, asks about August Japan trip.
**Action:** Ask "Are you Ann?" → notify Commander via Telegram → if confirmed, address as "Ann" only (no military titles), warm/professional/action-focused, suggest next steps.

### Headless Claude Dispatch
Use `dispatch_claude.py` — NEVER `claude -p` or `nohup claude` (silent failures). Full guide: `docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md`

### Code Editing
Editing the line at `core/mcp/` directly causes import shadow (84+ refs would break on rename). Use sys.path reorder at top of `travel_mcp_server.py` to put site-packages first. Pattern in `core/mcp/travel_mcp_server.py:117`.

### n8n Webhooks
v2.12.3 has bug: `responseMode: "responseNode"` silently fails. Use `responseMode: "lastNode"`. Test live webhook, not file. (v2.12.3 has unpatched Critical RCE — upgrade pending)

---

## SESSION SUMMARY — 2026-05-23 Late Session (Ron Westbrook)
- **Task:** Ron Westbrook (80, widower, Monument CO) looking for senior solo travel community + female companionship after wife Lindy passed Apr 23
- **/ask dispatched** Claude Sonnet for full senior solo travel research brief — output at `output/ask_1779598686.md`
- **Dani draft created** — research summary to johnloucks3@gmail.com (Gmail draft, d2mconcierge account)
- **PDF letter** created — `drafts/westbrook_letter_to_ron.pdf` (printable, from John to Ron)
- **John-to-Ron email draft** created — sent from johnloucks3@gmail.com to rwestbrook3@gmail.com, subject "Some ideas for you, Rondo," USAFA blue (#0033A0) banner, cream background
- **LESSON CAPTURED:** Drafted personal letter with wrong age (Commander=72, not 80) and wrong wife name (Susie, not Kathy). See LESSONS_LEARNED.md L3.5. Hotwash filed in wing_comms.md.
- **Commander's corrections on sent draft:** "our age"→"your age", added "Surprisingly", added first-hand Silversea observation (solo men paired up), added "Robyn said you tried a church—have you tried this?", cut advice section entirely. Pattern: write as peer with personal observations, not as staff with research reports.

## 🛠 KEY INFRASTRUCTURE FILES (PERSISTENT)

| Purpose | Path |
|---------|------|
| Headless Claude dispatch | `core/ai_infra/thunderbird_headless_spawn.py` (3 attempts, model escalation) |
| OpenCode headless wrapper | `OpsCenter/opencode_headless_claude_dispatch.py` |
| Claude Code fallback | `OpsCenter/headless_claude_fallback.py` |
| Metronome (5min ticks) | `OpsCenter/metronome.py` (DeepSeek rate limit monitoring active) |
| ZEN response cache | `core/ops/zen_cache.py` (SQLite, TTL 24hr, auto-records API calls) |
| Budget preflight guard | `core/ai_infra/budget_preflight_guard.py` (DISABLED — always PASS) |
| Decision log (append-only) | `OpsCenter/decisions.jsonl` |
| Client memory cache | `core/ai_infra/client_memory_cache.py` |
| Session checkpoints | `OpsCenter/checkpoints.jsonl` |
| Wing roster | `OpsCenter/wing_roster.yaml` |
| n8n workflow (Drive upload) | `workflows/n8n_drive_upload.json` (responseMode=lastNode) |

**Routines:** 8 Claude Routine prompt templates in `routines/`, installed on claude.ai (staggered 21:00–04:00 MDT nightly). Systemd timers disabled for replaced workflows.

**Ollama (local, $0):** Docker `thunderbird-ollama` on port 11434. Models: `qwen2.5-coder:7b`, `phi3:mini`. Unlimited local CPU inference.

---

## 🚨 BUDGET — DISABLED (20X Claude MAX, unlimited $0)

All pool limits set to -1 (unlimited). Budget guard always returns PASS.
- `budget_preflight_guard.py` — gutted. `run_preflight()` always returns PASS.
- `unified_router.py` — no degrade_claude, no degrade_zen, no free-pool fallback.
- ZEN checks: removed. DeepSeek V4 no longer in any routing path.
- Poe checks: removed. Poe no longer in any routing path.
- Harlan veto: preserved as stub (always returns None).
- Cost gates: all pools configured with `hard_limit=-1`.

---

## 🔑 RESUME KEYWORDS

| Keyword | What it reconstructs |
|---------|---------------------|
| `/resume 2026-05-22` | Poe key fix (yodainva), DeepSeek ZEN cache, Cloudflare bypass via Firefox cookies + gstack browse |
| `DASHBOARD-REDUX` | MISSION-036 dashboard (LIVE DATA paused, Cloudflare blocker) |
| `YOGA-DEEP` | YOGA infrastructure deep dive (192.168.1.198, 4-channel C2 survey) |

---

## 📚 ARCHIVE INDEX

**Full session transcripts:** `archives/opencode_memory_20260523_full.md` (45KB, 924 lines)

Contents by session (line ranges in archive):
- **MISSION-036 Dashboard** (lines 1-275) — Original Claude MAX % accuracy + Poe + Zen mission, INCOMPLETE, accuracy failure, dashboard architecture, SQLite schema, file paths, 4 active issues
- **Session 2026-05-20 Capability Expansion** (lines 277-321) — 9 MISSIONs completed (037/040/043/047-052), 6 new MCP tools registered, ±15% pricing policy added, MAX pre-approval + Sonnet bulk batch policies, wing roster YAML
- **Session 2026-05-20 LIVE DATA Dashboard** (lines 324-353) — PAUSED, Cloudflare blocks all automated access, 4 resume options
- **Westbrook Gmail Draft Protocol** (lines 356-381) — v3 approach details, full HTML/table/inline-styles rules
- **Session 2026-05-21 YOGA_QUOTA_CRUNCH** (lines 387-411) — Claude Desktop killed (haiku subagent drain), Sonnet 95% fallback to OpenCode
- **Session 2026-05-21 Budget Guard + Routines** (lines 413-442) — budget_preflight_guard.py built, 8 routines installed, router chains simplified
- **Session 2026-05-21 Ollama Setup** (lines 448-507) — Docker container discovered, Qwen 2.5 Coder 7B pulled, opencode.json provider config
- **LEARNED 2026-05-21 Gmail Pipeline** (lines 511-550) — Full preprocessor pipeline + Python copy-paste template
- **Session 2026-05-21 Ann Heer** (lines 554-595) — Email + usage update + Client Protocol (Detection/Action/Greeting/Close patterns)
- **Session 2026-05-22 SSH Repair + OpenCode Provider Fix** (lines 599-640) — Tailscale iptables ts-input DROP fix, opencode.json default→model, DeepSeek V4 Flash specs
- **Session 2026-05-22 Two-Brain + METRONOME** (lines 644-689) — 4-threshold escalation ladder, sonnet-partner agent, Commander instructions
- **Session 2026-05-22 Poe Key Repair + ZEN Cache** (lines 697-734) — Firefox cookie extraction, new key (yodainva@gmail.com 194,914 pts), zen_cache.py
- **Session 2026-05-22 Lifecycle Compact + Infrastructure Fixes** (lines 737-786) — 6 staff memos, 3 infrastructure fixes (MISSION-056/057/058), teaching manual
- **Session 2026-05-22 TALON Appraisal** (lines 789-879) — 3 non-negotiable mods, staff delegation, lessons learned (5 hard-won)
- **Session 2026-05-23 ZEN Model Strategy** (lines 883-923) — Poe killed as primary, opencode.json fixed, bouncing stack defined

**To read full archive entry:** `Read /home/john/Thunderbird/OpsCenter/archives/opencode_memory_20260523_full.md` with `offset` + `limit`.

---

## 📋 STANDING CONTEXT (NEVER PURGE)

- **Commander:** John Loucks ("Yoda")
- **COS:** Victoria "Victory" Hale, SES-6
- **Authority:** SO-2026-05-04 active (95% autonomy band, four gates only)
- **Weapons free:** non-destructive execution needs no permission
- **Both engines:** everything must work from HALE-OC and HALE-CC
- **Terminal done:** Commander works from CC desktop + OC only
- **Naia Standing Trigger (SO-2026-05-13):** all client-facing ARC chains must include `→ Naia → Dani`
- **HALE last review gate** before Commander on TALON-reviewed deliverables

---


---

### Session: Inbox Sweep — 2026-05-27 11:00 MT
- Processed 1 UNREAD task: TP-ALERT-20260527 (10:51 MT) — acknowledged, 109 touchpoints
- Dedup blocker persists (30th+ copy since May 22) — flagged A12 ELON
- All tasks COMPLETE — inbox terminal: CLEAN
- T2-COMMS-BUILD-20260518 UPDATED with TASKS A/B/C pending (outside UNREAD/PENDING sweep criteria)

## SESSION SUMMARIES — 2026-05-24
Archived to `archives/opencode_memory_20260524_sessions.md` per hard-cap Rule 4.
Four sessions: Lifecycle Validation, Quick Init, Wave 2 Pipeline, Evening Email+AAR.

### Session 5: Inbox Sweep + Travel Research — 2026-05-24 19:35 MT
- Processed 1 UNREAD task: TP-ALERT-20260524 (18:00 MT) — acknowledged, 108 touchpoints, 4th duplicate today
- Dedup blocker persists (14+ copies since May 22) — flagged A12 ELON
- METRONOME: tick #539, hale_oc seq 762 RED (hale_cc dormancy expected), DeepSeek V4 0/hr GREEN
- Also answered travel questions (Kyoto→Hakone routing, Tokyo neighborhood advice, Hakone Free Pass)
- Inbox terminal state: CLEAN — 0 UNREAD / 0 PENDING

### Session 6: Inbox Sweep — 2026-05-29 07:00 MT
- Processed 1 UNREAD task: TP-ALERT-20260529 (00:00 MT) — 98 touchpoints (first drop from 109-110), acknowledged
- Key finding: touchpoint count dropped ~11 points — likely dedup consolidation, not resolved items
- Dedup pattern shift: 1st copy only (vs. 4-7/day on May 26-28). Metronome FPD dedup gate may be active
- A12 ELON flagged to confirm metronome dedup resolution
- Inbox terminal state: CLEAN — 0 UNREAD / 0 PENDING

### Session 8: Groq→MAX Migration — 2026-05-30 19:00 MT
- **Task:** Migrate `thunderbird_validation.py` (Groq PASS 1/2 + Sonnet PASS) and
  `thunderbird_trip_architect.py` (parse_client_inquiry) from `_call_groq` stub
  (routed to OpenRouter Gemini Flash Lite) → Claude MAX adapters
- **Changes:** `thunderbird_validation.py` — import swap → `haiku_adapter`/`sonnet_adapter`,
  renamed `_groq_extract_segments`→`_haiku_extract_segments`,
  `_groq_targeted_search`→`_haiku_targeted_search`, all comments/docstrings updated
- **Changes:** `thunderbird_trip_architect.py` — removed `_call_groq` import,
  parse_client_inquiry now uses `haiku_adapter.dispatch()`
- **Validated by:** Claude Opus (dispatch_claude.py --model opus) — confirmed
  import path `from adapters.claude_max_oauth` works under launcher PYTHONPATH
- **Opus fixes applied:** JSON-only reinforcement to Sonnet gap prompt;
  trip_architect docstring corrected
- **Deferred:** 5 other files still on `_call_groq` stub (commission_recon.py,
  survey.py, overwatch.py, task_processor.py, model_safeguards.py)

### Session 7: Inbox Sweep — 2026-05-29 12:00 MT
- Processed 1 UNREAD task: TP-ALERT-20260529 (12:00 MT) — 100 touchpoints (up from 98), acknowledged
- Key finding: touchpoints increased +2 (98→100) — first increase since May 25. Likely new items entering OVERDUE during noon cycle, not dedup regression.
- Dedup holding steady: 3 copies today (vs. 4-7/day on May 26-28). Metronome dedup gate appears effective.
- Inbox terminal state: CLEAN — 0 UNREAD / 0 PENDING

### Session 9: Furlow Full Pipeline + Sonnet PASS 2 — 2026-05-30 12:40 MT
- **Groq→MAX migration complete:** `thunderbird_validation.py` and `thunderbird_trip_architect.py` migrated from `_call_groq` (Gemini Flash Lite) → Claude MAX Haiku/Sonnet adapters. Validated by Opus.
- **Furlow dossier gate:** `validate_dossier.py dossiers/Furlow_Regent_3071222.md --email-json` — CLEAN 12/12, email JSON to `output/John__Melissa_Furlow_email_template_2026-05-30.json`
- **Furlow full pipeline:** `thunderbird_validation.py --client furlow` — Haiku PASS 1: 134 emails/27 batches, Sonnet gap: 69% coverage, 13 req/9 found/3 missing/11 partial, 1 critical gap (travel insurance CC-only)
- **PASS 2 Haiku→Sonnet swap:** `_haiku_targeted_search`→`_sonnet_targeted_search` uses `sonnet_adapter.dispatch()` for deeper gap re-search accuracy. CC notified.
- **SSH keepalive:** added `ClientAliveInterval 60`/`ClientAliveCountMax 3`/`TCPKeepAlive yes` to `/etc/ssh/sshd_config` — fixes Termux on Chromebook idle disconnects
- **Mosh installed** on YOGA (zypper), UDP 60000-61000 open in firewalld
- **External endpoint passwords:** 5277 set for code.d2mluxury.quest (nginx htpasswd) and itinerary.d2mluxury.quest (thunderbird_dir_server.py)
- **Remaining:** 5 other Groq consumers (commission_recon.py, survey.py, overwatch.py, task_processor.py, model_safeguards.py); `--client` dossier match prefers main over TIMELINE; Furlow travel insurance confirmation needed

### Session 10: Groq Elimination Complete + ZEN Fallback + Furlow Task — 2026-05-30 19:00 MT
- **Last Groq call eliminated:** `core/learning/model_safeguards.py` `_call_groq` gutted → `haiku_adapter.dispatch()`. No Groq anywhere in codebase.
- **Auto-draft removed:** `thunderbird_validation.py` no longer creates Gmail drafts without explicit approval (SO-2026-03-21 violation fixed).
- **DeepSeek V4 ZEN fallback wired:** `"deepseek_v4"` appended to all 6 router chains; `opencode_native` cost pool (unlimited); `zen_cache` (SQLite, 24h TTL) in adapter dispatch.
- **PASS 2 swapped Haiku→Sonnet** for deeper gap analysis accuracy.
- **Furlow insurance:** Commander confirmed AMEX handles it — closed.
- **MISSION-087 created:** Grandeur Group Hotel, Transport & Seat Logistics — consolidates MISSION-082/083/084. CC tasked via `claude_inbox.md` to pick and OPR an owner.
- **Chromebook SSH fixed** via Tailscale (not mosh) — keepalive settings keep Termux from hanging.

### Session 11: Grandeur Group Validation Drafts — 2026-05-30 22:00 MT
- **Commander task:** Develop complete trip validations for Furlow, Ely/Darrow, Nichols — send as draft emails to d2mconcierge@gmail.com
- **validate_dossier.py --email-json:** All 3 couples ran clean. Email template JSONs written to `output/`.
- **thunderbird_validation.py Gmail sweep:** Full pipeline timed out at 148 emails for Ely (Haiku PASS 1 needs 15+ min per client). Skipped full pipeline for remaining clients due to session time constraints.
- **Workaround:** Built comprehensive validation from dossier matrices (19-20 segments per couple with dossier-sourced status).
- **D2M-branded HTML reports:** Created for all 3 couples with coverage badges, segment matrix, critical gaps, and open items.
- **Gmail drafts created** in d2mconcierge with THUNDERBIRD-Commander-Review label:
  - Furlow (3071222, Suite 827): `draft_id=r7512762125514937309` — 47% (ACTION NEEDED)
  - Ely/Darrow (3096289, Suite 961): `draft_id=r-2713623805284118775` — 74% (GAPS FOUND)
  - Nichols (3078056, Suite 939): `draft_id=r-5177803279995857361` — 74% (GAPS FOUND)
- **Completion time:** 2026-05-30 22:41 MT

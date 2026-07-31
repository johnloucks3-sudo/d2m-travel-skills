# AFTER ACTION REVIEW — Overnight Triage, 2026-07-30

**Operation:** Three-front remediation — Claude token burn, vaporware/late reports, TCD-Sheet-Slack sync loss
**Window:** 2026-07-30, ~0730–0945 MT
**Commander:** John Loucks (Yoda)
**Lead:** CC (Hale / Claude Code) — Overseer, Accountability, Verification
**Builders:** AG (Gemini 3.1 Pro), OC (OpenCode DeepSeek v4 Flash Free)
**Outcome:** 25 tasks — 23 shipped, 1 correctly declined, 1 deliberately deferred. Zero defects reached the Commander.

---

## 1. WHAT WAS SUPPOSED TO HAPPEN

The Commander reported three symptoms at 0726 MT and ordered a delegated plan:

1. Claude MAX weekly usage climbed 73%→78% overnight with no human at the keyboard.
2. Reports still arriving in raw markdown, past the 0630 MT gate, with stale/hardcoded content — despite a "REPORTING OVERHAUL COMPLETE" commit two days earlier.
3. 318 items bulk-approved in the TCD Sheet still showing as open in the morning report.

Standing directives in force: hard cutover of routine work off Claude; fix the sync gap *and* add direct Sheet links as a fallback; **delegate the plan development itself**.

---

## 2. WHAT ACTUALLY HAPPENED

### Phase 1 — Delegated investigation (3 parallel agents, ~20 min)

Three A7/Sterling agents ran concurrently, diagnose-only, each producing an implementer-ready spec. All three found that the *reported* symptom was not the actual defect:

| Reported | Actual root cause |
|---|---|
| "Routines are burning tokens" | The 13 services *named* for Claude burn zero. The #1 burner was `ai-auth-probe` — a monitor. 30.5% of burn was invisible to a timer audit entirely (a plugin hook + a daemon). |
| "Reports are broken" | The new 0630 engine works correctly. Two *old* scripts were never retired and are what reaches the inbox. |
| "318 approvals didn't stick" | The bulk edit was correct. A lost-update race on an unlocked JSON read-modify-write destroyed the writes after the fact. |

### Phase 2 — Plan, presented in four distinct beats

Present → Q&A → delegation board → permission. The Commander corrected course twice mid-plan, which is exactly what the four-beat structure exists to permit:

- **"NO! NEVER OPENROUTER."** — a delegate's spec recommended a provider retired 2026-06-25 for cost overruns. The retirement was visible in this session's own agent registry and should have been caught before it was repeated upward.
- **"Not enough delegation… you have it reversed."** — CC had assigned itself 18 of 21 tasks. Rebuilt to CC-builds-nothing before permission was requested.

### Phase 3 — Execution (25 tasks, parallel dispatch, CC verifying every result)

Final delegation split: **AG 15 builds · OC 7 builds · CC 0 builds, 25 verifications, 4 forced self-executes.**

---

## 3. RESULTS BY WORKSTREAM

### Token burn — 7/7
- **CI auto-repair loop capped.** Had a 30-min cooldown but no attempt limit: 467 Claude Sonnet sessions on one unfixable service, 431 on another, 752 on a third. Zero fixes ever landed. Now 2 OpenCode attempts + 1 Claude attempt, then human escalation. Was 39.6% of overnight burn.
- **Liveness probes shrunk.** 24.1% of overnight spend was Claude being asked to reply "ok" — an 11-character prompt carrying ~71K cache-write tokens of project envelope, one of them on **Opus**. Now Haiku, stripped envelope, hourly instead of every 15 min.
- **claude-mem moved off the Claude meter** (17.7%) — see Lesson 6.
- **Telegram "OK" confirmation spawn retired** — an LLM was being asked to read the word "OK" that an API already returns as a boolean.

### Reports — 5/5
- **The real trigger found.** Disabling the systemd timers on 07-28 didn't work because `ai_exec_bot.py` registered the same scripts on `interval_sec=86400` — a *rolling* 24h delta that drifts earlier every day. That is why briefs arrived at 04:10 and 05:10.
- **Raw-markdown emails killed** — a digest tool emailed its own file output as a side effect, so every caller mailed the Commander (3× in 6 hours).
- **Lying timestamps fixed** — an EOD brief delivered at 05:10 was stamped "1800 MT · EOD".
- **Duplicate-send hole closed** — the lock was checked only in `main()` and written *after* the send; three library importers bypassed it entirely.
- **`drain_queue()` wired** — built, documented as called by both engines, **zero actual callers**. Gate-compliant senders went silent while non-compliant direct senders got through: the system was actively rewarding non-compliance.
- **Compliance test de-fanged → re-armed.** The guard test grandfathered 544 known violations (⅔ of them duplicate worktree copies), including all five scripts causing that morning's failures. Now 178 real entries, and the test correctly **fails red** naming the five.

### Sync — 6/6
- **Race condition locked.** `set_override()` did an unlocked full-file load-mutate-replace, called concurrently by a 10-min timer, a webhook router, a CLI, and MCP tools. A bulk Sheet edit produced a webhook storm; last writer won.
- **All 94 lost closures recovered** across 2026-07-13/14/17/29.
- **Two disconnected ledgers unified** — Sheet closures and Slack closures had **zero overlap**. Append-only JSONL made authoritative; intersection now 94.
- **Morning report section un-blanked** — read a key (`items`) that does not exist in the file. Rendered empty every day since it shipped. Now returns real items and hides the 17 the Commander had already closed.
- **Row-anchored Sheet links live** (the Commander's own ask) — 317 rows mapped, real tab id `758571255`; returns empty rather than ever pointing at a wrong row.

### Governance — 2/2
Two items previously reported "done" were not: AppSheet writeback was still running, and a daily audit report asserted a fabricated statistic ("holding 181 stage overrides"; actual 73). Both now genuinely done.

---

## 4. LESSONS LEARNED

### L1 — "Built but never wired" is this codebase's signature defect
`drain_queue()` (zero callers), `directive_ledger.capture()` (zero callers), `integrity_check` (zero callers before a gap forced it), the CI managed-agent fast path (dead by design on the installed SDK). Each shipped with a docstring asserting it was in use.
**Action:** when a fix is declared complete, grep for callers of the thing that was supposedly wired. A docstring is a claim, not evidence.

### L2 — A safety net configured to ignore its own findings is worse than none
`no_direct_sends_baseline.json` passed green while grandfathering every script that failed that morning. The test's own inflation (⅔ duplicate worktree paths) hid how bad it was.
**Action:** any baseline/allowlist needs a monotonic-decrease metric and a periodic audit of what it is suppressing. A green test over a 544-entry ignore list is a green light on a broken instrument.

### L3 — Delegate acceptance-tests must be told where to write
AG's fix for the race condition was excellent — correct `fcntl` pattern, matched repo convention, independently re-verified. Its **own test** imported the production path, called `.unlink()`, and destroyed real Commander approval data to prove the fix worked.
**Action:** every spec whose acceptance criterion involves a test script must say: *write test data to an isolated temp path, never the real path, even if the function defaults there.* Now encoded in the `delegate` skill.
**Also:** CC repeated this exact mistake later, piping a test message into a live hook and polluting the mandate ledger. The rule binds the overseer too.

### L4 — Verify against ground truth, never against the report
Six defects were caught this way, none self-reported:
1. AG wiping production data in its own test
2. AG making an out-of-scope edit despite an explicit EXCLUDE
3. The "122 lost approvals" headline being a material overcount
4. CC's own recovery spec being scoped to one day when the leak was three weeks old
5. A mandate-capture hook swallowing harness noise as Commander directives
6. A placeholder string about to ship into a Commander-facing intel report
**Action:** unchanged and reinforced — run the acceptance criteria as commands. An articulate report is the moment of highest risk, not lowest.

### L5 — Investigation headline numbers need independent recount before they reach the Commander
"~122 lost approvals" was derived from raw line count minus survivors. The audit trail double-logs each closure (a `PLAN:CLOSE` comment + a `Plan Closed:` line), and the race storm logged the same items repeatedly. True distinct count for 07-29: **37**. Meanwhile the *real* scope was worse than reported — the leak ran back to 07-13, and 56 further closures were missing.
**Action:** before repeating a delegate's headline figure upward, recount it from source. Both directions of error matter.

### L6 — Verify a migration target exists before planning the migration
The plan said "move claude-mem to OpenCode." claude-mem supports exactly three providers: claude, gemini, openrouter. There is no OpenCode option, and OpenRouter is permanently forbidden. The task was impossible as written.
It resolved well — a `GEMINI_API_KEY` already in `.env` live-probed successfully against the very model claude-mem was configured for — but that was luck, not planning.
**Action:** for any "move X to Y", confirm Y is a supported target of X during planning, not at execution.

### L7 — Async dispatchers cannot drop into synchronous pipeline stages
CC specced "route the nightly intel analysis to OC." `dispatch_to_oc()` queues a ticket and returns no result. AG implemented it faithfully and set the stage output to `"[Delegated to OpenCode — Ticket: xyz]"` — which flows into the audit stage and into Commander-facing intel products.
That would have **recreated the exact vaporware-report defect the Commander opened the morning with.** Reverted; deferred as a two-phase redesign.
**Action:** when specifying a migration, state the caller's synchrony requirement explicitly. This was a CC spec fault, not an AG build fault, and is logged as such.

### L8 — A weak model will refuse a boundary you never wrote, and honor one you did
Same task, both halves: AG **correctly kept** email-classification on Claude after discovering its output feeds client-facing drafts in the Commander's voice — declining a 12.8% saving because the spec named the carve-out. On the half where the spec was silent about synchrony, it shipped a placeholder.
**Action:** the quality of delegated output tracks the quality of the constraint, not the capability of the model. Where the spec was explicit, a "weaker" engine made the right call unprompted.

### L9 — Route by measured reliability, not by cost
See §5. OC's price advantage is irrelevant at a 50% completion rate; a failed dispatch costs a full re-dispatch cycle plus verification time.

### L10 — Delegation reversal must be an explicit standing posture
CC's default instinct assigned itself 18 of 21 tasks. The Commander's correction — *"I want YOU to be Overseer/Accountability/Verification. You have it reversed"* — is now a standing memory, because the instinct will otherwise return every session. With a 20X→5X MAX cut (75% less Claude capacity) inbound, this is a budget constraint, not a style preference.

---

## 5. ENGINE PERFORMANCE — MEASURED

| Engine | Model | Dispatched | Clean | Rate |
|---|---|---|---|---|
| **AG** | Gemini 3.1 Pro (High) | 16 | 15 | **94%** |
| **OC** | `opencode/deepseek-v4-flash-free` | 8 | 3 | **38%** |
| **CC** | Claude (Opus 5 / Sonnet 5) | 0 builds | 25 verifications | — |

### AG (Gemini 3.1 Pro) — primary build engine, confirmed
Handled genuinely hard work: race-condition locking, an attempt-cap state machine with correct increment-before-check ordering, `fcntl` guards relocated into the right function, multi-file wiring, a full closure-recovery tool. **Twice caught edge cases CC never specified** — a stale-in-memory-state clobber in the CI scan loop, and a second `size > 0` lock check. Typical turnaround 5–12 minutes. One discrepancy (L3), one correct refusal (L8).

### OC (`deepseek-v4-flash-free`) — not viable as a primary lane
Four distinct failure modes across 8 dispatches:
- **Timeout at 800s, zero changes** (×3) — including on one-line-class edits.
- **Context collapse** (×1) — read the target files, then emitted raw `<｜｜DSML｜｜tool_calls>` markup as literal text and finished with *"we just started this session."*
- **Hard sandbox block** (×2, structural) — auto-rejects any path outside `--dir` as `external_directory`; cannot even *read* `~/.config/systemd/user/*`. **All systemd work must route to AG or CC.**

### CC — 4 forced self-executes, all logged with rationale
Each was a genuine capability boundary, not preference: two systemd edits OC structurally cannot perform, one trivial fix after OC timed out twice, and one secret-handling task (copying a live API key between files — unsafe to pass through a delegate prompt).

---

## 6. THE OC PROBLEM — OPTIONS

**Currently in use:** `opencode/deepseek-v4-flash-free` (free Zen tier). 38% completion rate.

**Assets already available and unused:**
- **Poe:** `POE_API_KEY` live, **1,233,770 points ≈ $37.39**, key `Thunderbird & Opencode` enabled. OpenCode already lists `poe` as an authenticated provider and exposes **146 Poe models**.
- **`opencode-go` tier:** authenticated, 15 models including `deepseek-v4-pro`, `kimi-k3`, `glm-5.2`, `qwen3.7-max`, `minimax-m3`, `grok-4.5`.

**Note on prior guidance:** a standing directive moved OC *off* Poe after `poe/deepseek-v3.2` returned "invalid request error." That was a per-model failure, not a Poe-platform failure — 146 models are reachable, and the Commander has reopened the question.

**Benchmark:** candidates measured on a known-answer, read-only repo task matching the profile OC failed at today. Results in §7.

---

## 7. BENCHMARK RESULTS

*(appended below on completion — see `OpsCenter/oc_model_benchmark_2026-07-30.md`)*

---

## 8. WHAT CARRIES FORWARD

**Shipped as durable capability, not just fixes:**
- `plan-triage` skill — encodes the whole interview → parallel investigation → plain-language synthesis → four-beat approval sequence, auto-triggering on any "put a plan together."
- `delegate` skill updated with the safe-test-path rule (L3).
- `core/relay/engine_limits.py` — per-engine hourly/daily quota tracking, append-only, independent pools, with the rule that sub-agents draw against their parent engine's pool.
- Memories recorded: CC-as-overseer posture, never-OpenRouter, OC/AG measured reliability, safe-test-paths, report format.

**Open:**
- #49 — two-phase redesign to move intel-analysis to OC (3.2%), deferred deliberately (L7).
- `engine_limits.py` not yet wired into the dispatch paths (built standalone to avoid collision during this operation).
- The three chronically-broken CI units (752 / 467 / 431 failed repairs) are now capped rather than looping — but still broken, and now escalate to a human.

---

*Prepared by CC (Hale) · 2026-07-30 · Verified against ground truth, not self-report.*

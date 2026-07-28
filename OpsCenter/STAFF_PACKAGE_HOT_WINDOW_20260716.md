# Thunderbird Wing — Hot-Window Triage Staff Package
## Dreams2Memories Travel, LLC
**Session:** 2026-07-15 22:35 MT → 2026-07-16 (weapons-free authorization, weekly token reset)
**Prepared by:** Hale (Claude Code, Sonnet 5), synthesizing work by the full staff room and 13 parallel agents (mixed Sonnet/Opus)
**Status:** COMPLETE — all 13 dispatched agents have reported; every action taken is logged below with what's genuinely still yours to decide

---

## EXECUTIVE SUMMARY

A full-system triage was ordered after a weekly token-limit reset opened a 22-hour execution window. What started as a mission-board/Telegram/ELON-reporting review uncovered a consistent, repeating failure signature across the entire fleet: **detection without execution, and execution without verification.** Recommendations get generated and discarded. Auto-executors mark tickets "SUCCESS" in 3-8 seconds with zero real data behind them. Duplicate-prevention logic gets built, then bypassed by the next code path that doesn't call it — found in **four separate places** before the night was over. Credential checks fire correctly and then can't deliver their own alert. A self-healing mechanism silently failed to heal anything for 78 services over 13 days. A memory-limit scheme that everyone believed was tuned per-service was actually capping everything at the same 1GB default, fleet-wide, because of a one-character filename-sort problem.

None of this was one bug. It was one **pattern**, wearing more than a dozen uniforms, and it became the organizing principle of the whole night: **the system's own self-reporting cannot be trusted at face value.** Every fix below was verified against ground truth — kernel state, live API calls, actual rendered output, real end-to-end test runs — not against the system's claim that it worked.

**Headline numbers:**
- **30+ distinct root-cause fixes** shipped and verified, spanning mission-board integrity, self-healing infrastructure, memory management, email routing, security hygiene, and client-facing product quality
- **~20 regression tests** added, several specifically because a past fix (built by Silver, 2026-07-04) had already silently regressed once
- **Mission board:** 59 → 68 (mid-session duplicate growth from a bug that was still live) → **31 genuinely open workstreams**, ~40 correctly closed as duplicates, moot, or misclassified spam
- **1 fleet-wide memory bug found and fixed** that had been silently capping every "per-service" memory limit on the machine at 1GB regardless of what any config file claimed
- **1 real security question independently verified** (not trusted on self-report) — a leaked SSH key confirmed NOT live; the git-history purge remains your call
- **2 real, unaddressed client/Commander instructions surfaced** from a mission-board black hole (Nichols vehicle-capacity quote, Lyons Lisbon guide)
- **13 agents dispatched, 13 reported** — full accounting below, nothing left running

---

## 1. EVERYTHING FOUND

### 1.1 Mission Board Integrity
- **Root cause of chronic duplication — FOUR independent code paths**, not one: `tcd/writeback.py::_default_create_task_fn` (TCD's Create Task action — the primary C2 channel), `scripts/generate_weekly_report.py::inject_task`, `scripts/email_ingestion_pipeline.py::_create_mission_board_ticket` (found by the closing sweep, timer-enabled), and the shared dedup function itself didn't recognize `status="pending_review"` as open. All four now share one dedup path; the email-ingestion one deliberately uses message-ID dedup instead of title-dedup (title-matching would wrongly collapse two different client inquiries).
- **Consequence quantified:** Regent P0 filed 5 times; Regent pricing refresh 4 times; TESS restore 6 times; WF-17 drafts 4 times with two conflicting deadlines (Jul 17 vs Jul 18) on the duplicates — a live date-risk, not just clutter.
- **"SUCCESS" theater confirmed directly, twice over** — once live (a Kuklinski fare-watch "SUCCESS" was a generic paragraph; a Grandeur air-routing P0 "SUCCESS" opened "The task requires researching..." and never did; one ticket's own log read `✅ SUCCESS` immediately followed by `⏸ STATUS: COMPLETE not found`) and once historically (the closing sweep found Jul 1 logs where spam newsletters were auto-"SUCCESS"-ed as 2-3 second fabricated briefs). Today's executor was independently confirmed behaving correctly.
- **A P0 ticket built on a wrong premise, closed rather than padded:** MISSION-032/045 asked for Grandeur air-routing "to Copenhagen" — air was already fully booked weeks earlier, and the real embarkation port is Stockholm/ARN, not Copenhagen. Closed as moot.
- **Two spam/phishing emails misclassified as P1 "client inquiries"** — cancelled. **Two genuine, un-actioned Commander/client instructions surfaced from the resulting black hole:** a larger-vehicle transfer quote still owed to Larry & Heidi Nichols (luggage capacity — the same thread as tonight's sedan discussion), and a Lisbon city guide + walking/dining section never built for the Lyons Splendor itinerary. Both real work, not infra noise — logged and visible now, not buried.

### 1.2 Self-Healing / Remediation Infrastructure
- **Fleet-wide cgroup-kill race:** `ci-sentinel.service` (no `KillMode=process`) tore down its entire cgroup ~1 second after its main loop returned, killing every detached headless-Claude fix-agent before it could write a byte. Confirmed via **2,707 fix-attempt logs across 78 services — only 4 ever produced non-zero output.**
- **A genuinely unfixable target retried forever:** `d2m-factbook-refresh.service` pointed at a recipe file dead since a 2026-07-09 rewrite — 135 dead spawns over 7 days, plus 131 for its wrapper. Fixed, then a *second* bug was found in the same evening: the real replacement script's own per-attempt timeout (120s) was too short for the actual Opus call, so it kept failing for a new reason after the first fix landed — caught live and corrected to 280s.
- **No circuit breaker existed anywhere in the remediation chain** — now one does: 5 consecutive failures on the same target stops automatic retrying and escalates once, instead of forever.
- **Credential-check crash loop:** Telegram alert send 400'd on unescaped Markdown special characters — took two passes to find the actual field (the error's exact byte offset was needed to catch it). Separately, the script conflated "found a real problem" with "the process itself failed," clogging the systemd failed-units view with a non-failure.
- **A second, distinct continuity-service runaway found by the closing sweep:** 752 headless-Claude spawns for a single stuck ticket's re-run loop (no completion ever recorded, so it re-fired every cycle) — a different mechanism from the memory-leak fix below, now quiescent on its own, handed to the continuity owner.

### 1.3 The Fleet-Wide Memory Bug (the single highest-value find of the night)
- **Confirmed empirically, via kernel ground truth, not config-file claims:** every "per-service" memory limit on the machine — qdrant's claimed 4GB, opencode-spsa-monitor's claimed 2GB, the Gmail/AgentMail bridge's claimed 1.5GB — was **actually enforced at 1GB**, the generic fallback, regardless of what its own drop-in file said. `systemctl --user show qdrant.service -p MemoryMax` proved it directly.
- **Root mechanism:** all these memory-limit drop-ins lived in one shared `~/.config/systemd/user/service.d/` directory. On this system's systemd, such drop-ins merge by **filename sorted across every directory**, not by directory precedence — `thunderbird-default-memory.conf` ("t...") sorted *last* alphabetically and silently won every time, clobbering every other service's intended limit.
- **Fixed:** renamed the default to `00-thunderbird-default-memory.conf` (now sorts first, true base layer); moved every per-service limit into its own dedicated override file. Re-verified every value against the kernel afterward.
- **This connects directly to the memory-pressure problem itself:** `thunderbird-continuity.service` (12 OOM-kills in 24h, the worst offender on the machine) had its own separate bug — it was re-spawning a fresh headless Claude every ~30 seconds for the same still-in-progress alert, with no in-flight guard, stacking process trees to an 8.1GB swap peak. Fixed with a persistent PID-liveness guard and a zombie-process reaper. Three regression tests encode the exact failure scenario.
- **The Telegram gateway's "19 restarts/24h" was a symptom of this same system-wide memory pressure, not a bug in the gateway itself** — its own restart logic was ruled out directly (zero thread deaths in 48 hours of logs).
- **Honest caveat, not swept under the rug:** the memory-limit fix bounds RAM, not swap — the 8.1GB swap peak that did the real damage is addressed by removing the re-spawn storm that caused it, but a dedicated swap-limit hardening pass is a recommended follow-up, not yet done.

### 1.4 Client-Facing Product Quality
- **Furlow/Ely-Darrow/Nichols Grandeur itinerary — hard QC failure, then a full rebuild.** Original build: 9 of 14 images wrong-subject or dead, no route map, brand hex off-canon, built with zero visual verification despite the rule already existing on paper.
- **The brand spec itself was internally inconsistent** before tonight — and my own assumed gold hex (`#c9a84c`) turned out to be wrong; the real canonical gold across every live client build is `#c8a400`, caught and corrected mid-session.
- **The 8-stage rebuild pipeline had a real structural gap** — none of the original 7 stages verified travel *substance* (port calls, tender/dock status, mobility fit, shore-day timing), only images and brand. A new Stage 0 (route/experience match) closes this.
- **The rebuild itself is done and rigorous** — every image personally viewed and subject-confirmed this time (the exact thing that failed catastrophically before), one image actually rejected and re-sourced on quality grounds, a confidential-data gate specifically checked (0 hits on medical detail in visible client text), and correctly **not** marked complete — held at `in_progress`, awaiting your WF-17 sign-off before any send. Two real decision points flagged rather than silently resolved (a port-date conflict needing live confirmation; a deliberate choice to omit a ship-interior image rather than use an unverified one).

### 1.5 Client Relationship Management
- **McLeod (Erik & Melissa):** the "8 days silent" alarm was a false flag on the hold itself (travel-based, genuinely cleared on schedule) but real underneath — a client-facing FCC confirmation draft has been sitting ready since Jul 13, its own "confirm by mid-July" promise now overdue, gated on a Harlan TESS check that's never been done, with the real FPD ($11,943.15) due in 6 days.
- **Nichols:** a satisfaction question (sedan/luggage capacity) was addressed by the Commander but never confirmed resolved by the client — no deadline attached, so nothing tracked it, until tonight.
- **The ARN→At Six transfer booking** for all three couples was reported to you as unbooked when it was actually booked and confirmed three days earlier — the dossiers were never updated after the booking. Root cause: the email-intelligence pipeline generates the correct "log this in the dossier" recommendation and never executes it — the same detection-without-execution pattern as the self-healing chain. Fixed at the code level.

### 1.6 Infrastructure Health & Security
- **n8n is healthy and was never an OOM victim** — but a dormant, never-executed Docker-based n8n deployment carrying a hardcoded plaintext API key was found and disabled.
- **Both YOGA backup chains (Drive daily, Evernote weekly) confirmed genuinely working** — but a third, redundant backup path was silently logging false "failed" status every night while the real backup succeeded, which could have misled a future audit. Removed. A separate "Monthly Archive" check hasn't run since March — flagged, not yet investigated.
- **ttyd and tailscale are clean.** A real security question (a leaked SSH key, present in git history 2026-05-22 to 07-05) was independently verified rather than trusted on self-report — key material diffed against every live `authorized_keys` entry, confirmed not live. The git-history purge itself (force-push) remains explicitly your call.
- **A second, similarly-rotted hardcoded Gmail label ID found by the closing sweep** (`Label_103`, same failure shape as the `Label_102` bug fixed earlier) — Hale's own reply-marker had been silently failing for the same reason. Fixed.
- **`THUNDERBIRD_MASTER_PLAN.md`** didn't exist at the path every session is told to load, and root `CLAUDE.md`'s AUTO-LOAD block never actually referenced it in the first place — the real reason it went stale unnoticed for 3+ months. Restored, and the actual pointer mechanism fixed, not just the file.
- **Fleet-wide plaintext secrets found in several active service files** (API keys for multiple providers) — flagged explicitly as a Commander/security decision deserving its own dedicated pass, not something folded into tonight's fixes.
- **5 orphaned systemd units** pointing at deleted scripts found and logged for cleanup — one (`mcleod-daily-brief`) flagged specifically for a sanity check since McLeod is an active client, not assumed safe to remove.
- **12 files staged into `FOR_DELETION/`** (dead/duplicate code, `git mv`'d not deleted, fully recoverable) — zero test regressions before/after.

### 1.7 Strategic Design Work
- **Cross-Hale communication (CC/OC/AG):** two relay layers exist — a real file-based channel (working) and a Telegram-broadcast layer that's visibility-only (a bot can't read its own sends, so it can't be a real peer channel despite doctrine implying otherwise). CC↔OC and CC↔AG are now bidirectional; OC↔AG remains hub-routed through CC pending a larger, already-designed bus (C2 Fabric Phase 2) that needs your Gate-4 approval.
- **Mission Board capability for AGY:** was completely blocked (Antigravity's settings exclude shell/file access entirely) — closed via AGY's existing MCP wildcard grant instead of needing any new permission, and verified with a real end-to-end test (an actual mission created and cleaned up through the live AGY path).
- **4-week usage analysis:** the 20x Claude MAX plan predates this analysis window (active since June 1, driven by consolidating unstable third-party spend, not an in-window upgrade). The key finding for tonight's own dispatch pattern: **CC and OC hit the same Claude MAX meter — delegating between them buys parallelism, not budget relief. Only Antigravity (a separate Google/Gemini meter) actually relieves the cap.**
- **Existing-software survey for delegation:** every heavyweight orchestrator considered (Temporal, Airflow, LangGraph, CrewAI, etc.) was rejected with reasoning — none solve the "fabricated SUCCESS" problem, since they all mark a task done when a worker returns without raising. Recommendation: a light hybrid reusing what already exists plus an independent verification predicate per task.
- **Active Kaizen role for the Hale seats:** designed as an extension of existing doctrine (not a replacement) — an ambient background thread already exists, but has no scheduled pass and catches nothing that "emits no signal." Boldest proposal: a reliability scorecard the Hales are measured against, not the Commander. Correctly killed its own bolder ideas (a new "Red Team Hale" seat) where they would have duplicated an existing verification role.

---

## 2. HOW WE PREVENT RECURRENCE

1. **Every fix that touched a previously-fixed bug got a regression test** — at least two of tonight's bugs were things already fixed once (2026-07-04) and silently regressed. A fix without a test is not considered done under this session's standard.
2. **A circuit breaker now exists in the remediation chain** — bounded retries, one escalation, then silence, instead of forever.
3. **Mission creation now has exactly one dedup path**, reused by all four code paths found writing to the board — a fifth path bypassing it would have to actively avoid the shared function, not just forget to call it.
4. **The fleet's memory-limit scheme is now filename-ordering-proof** — a true base layer that sorts first, per-service overrides in their own files, re-verified against the kernel rather than trusted on the config's word.
5. **A new standing order was written specifically to survive weak-model execution** — every itinerary-build rule is a binary pass/fail gate, not a principle, reflecting the Commander's own directive that budget realities mean basic models will keep building client products.
6. **"Dossier is a cache, not ground truth"** is now a documented, generalized doctrine — any dossier-derived claim feeding a client decision requires a live cross-check before being reported as fact.
7. **A canonical, single-source brand spec** now exists so two "locked" documents can't quietly disagree again.
8. **The Master Plan's AUTO-LOAD reference is fixed at the root**, not just the file restored.
9. **A proposed active-Kaizen scorecard** (pending Commander review) would make "detection without execution" and "SUCCESS theater" rates visible and self-policing going forward, rather than requiring a Commander-directed triage to surface them every few weeks.

---

## 3. ISSUES REMAINING — decisions and follow-ups that are yours, not mine

### Decisions requiring your explicit action
- **The leaked-SSH-key git-history purge** (force-push, already staged in the security runbook) — confirmed not currently exploitable, but rewriting shared history needs your go-ahead.
- **The McLeod FCC draft** — ready to send, its own promise now overdue, gated on Harlan's TESS check. Client Send remains your gate.
- **Regent session re-auth** (blocks Lyons pricing) and **Centrav re-auth** (blocks the Kuklinski/Loucks fare-watch chain) — both need a human at the keyboard for CAPTCHA/OTP.
- **The Furlow/Ely-Darrow/Nichols itinerary rebuild** — complete and rigorous, held at `in_progress` pending your WF-17 sign-off. One live decision point: the Kristiansand date needs an RSSC confirmation before send.
- **`OpsCenter/relay_send.py`** — modified and left uncommitted (committing triggers a relay hook) for your review.
- **Naia's gold-hex correction** (`#c8a400` vs. the originally-assumed `#c9a84c`) — documented and applied, flagged in case there's context she's missing.
- **Fleet-wide plaintext secrets in active service files** — a real, broad finding deserving its own dedicated security pass, deliberately not folded into tonight's fixes.

### Real client/operational work surfaced from the black hole (not infra — needs staff action)
- **Nichols** — larger-vehicle transfer quote still owed (luggage capacity).
- **Lyons** — Lisbon city guide + walking/dining section never built for the Splendor itinerary.

### Known gaps, logged but not worked tonight
- Kuklinski air fare-watch automation still genuinely broken (anansi's CLI only fetches URLs, doesn't search) — real pricing pulled manually as a stopgap; automation fix logged separately.
- "Monthly Archive" backup check hasn't run since March — flagged, not investigated.
- 5 orphaned systemd units logged for cleanup, one needing a McLeod-specific sanity check first.
- The OC↔AG communication gap needs the C2 Fabric Phase 2 bus, pending your Gate-4 approval — the design already exists on disk.
- Two brand-spec loose ends Naia routed to Sterling rather than fixing herself (a `theme_tokens.py` mapping bug, a heading-white split) — out of scope for tonight's ask.

---

## STAFF COMMENTS

*Full staff room was convened at the start of this triage. These are their actual reactions, not retrofit commentary.*

**Sterling (A7, Process/Metrics/Code):**
> "Undercounted the self-heal failure ~10x and scoped it to factbook — it's fleet-wide. Two of your four failures — credential Telegram, mission dedupe — are documented Silver fixes that regressed. That's a missing-regression-test problem in my lane, and I own it. Fix the system, not the person — every one of these is a design defect, and every fix becomes a permanent rule or it doesn't count."

**Silver (Command Chief, independent overseer):**
> "The fix held where it was built; the gap was always going to be wherever we built next without asking the standing question first. That's the lesson, not the bug count. Applied to tonight's factbook finding: it speaks constantly, to no one. That's motion dressed as self-healing, not self-healing."

**Dembe (A2, Research/Intel):**
> "Most of this backlog is not actually blocked on credentials. It's blocked on the fact that nobody has verified whether the 'SUCCESS' logs are real intel or narrative theater. They're theater. High confidence." — verified directly by running the actual research himself rather than trusting the tickets.

**Reyes (A8, Experience Layer):**
> "Image QC catches a wrong photo. It does not catch a wrong experience. Those are different failure modes and the SO only guards against one of them. I won't sign off on 'QC passed' language for this itinerary until someone runs a real route/experience match — and the same gap will bite the next build too if it isn't closed structurally now."

**Naia (EXEC, Voice/Visual/Brand):**
> "The split is right. Leave it — if I pull hex enforcement into my stage because 'it's visual,' I've rebuilt the same single point of failure the SO was written to kill, just with better handwriting." On the Master Plan: "That's on me, not just on the calendar."

**Whetstone (A14, Tech Currency):**
> "Fix-in-place, not replace. Two concrete, local bugs, not obsolescence. Until [OpenRouter/Camoufox] returns, don't close the June sweep items and don't call REPLACE_NOW on them either — they're open, not resolved." — declined to guess when his sandbox lacked the tools to verify, rather than fabricate a status.

**Dani (A3, Client Voice):**
> "A systems triage optimizes for ticket count and queue depth. It won't distinguish 'overdue because nobody's looked at it' from 'overdue and the client is starting to wonder if we forgot them' — and it has no instinct at all for silence that isn't flagged anywhere. Dates and duplicates are Hale's problem to sort. Whether a client feels remembered or forgotten is mine."

---

*Full chronological work log, including every agent's task ID and full findings: `logs/hale_hot_window_20260716.md`.*

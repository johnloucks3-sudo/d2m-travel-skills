# STANDING ORDER — AI TOOL TRIM AUDIT
**SO-TOOL-TRIM-AUDIT-20260622**
*Effective: 2026-06-22 | Approved: V. Hale, SES-6, COS — Commander directive 2026-06-22*
*Author: Hale | Staffed: ELON, Sterling, Dembe — per Optempo BRIEF*

---

**Purpose.** Establish a fact-based, weekly measurement process for AI tool utilization. Prevents the tool hedge from growing unchecked. Ensures every tool in the wing is earning its place or is on a retirement track.

**Scope.** All AI API keys, LLM integrations, and automation tools in the Thunderbird OS `.env`. Excludes client-send path tools (WF-17 gate governs those separately).

---

## §1 — MEASUREMENT CADENCE

**Weekly** until tool hedge is under control. Transition to monthly when the REVIEW list has been empty for 4 consecutive weeks.

**Engine:** `scripts/tool_trim_audit.py` via `d2m-tool-trim-audit.timer` (Sunday 0800 MT).

---

## §2 — THRESHOLD

**1 call/month = earns its place.** At a 7-day window, this means ≥1 call in the window counts as active. Niche tools with infrequent but legitimate use (lifecycle-scheduled tasks, rare API calls) survive the cut.

Zero calls in 30 days with a replacement available = Case 1 candidate. Zero calls in 30 days without a replacement = Case 2 candidate.

---

## §3 — DECISION FRAMEWORK

**Case 1 — Direct swap** (new does the same job better, or old has a clear replacement):
- Decommission the old immediately.
- ELON proposes. Hale authorizes. Sterling audits the decommission.
- Both tools reported to Commander.

**Case 2 — Partial overlap** (new does the job AND more, or no direct replacement):
- Integrate the new. Audit the old within 7 days.
- Identify: is any part of the old tool still earning its place?
- If not: retire it. If yes: name the surviving scope explicitly and trim the rest.
- Hale decides. Escalates to Commander if strategic (>90d / >$5K impact).

**Case 3 — Full duplicate with no improvement:**
- Treated as Case 2. Audit — do not reject outright.
- Hale is tiebreaker. Escalates to Commander if needed.

**Tiebreaker:** Hale decides on all contested cases.

---

## §4 — CI RULE

**14-day data collection window before any CI-based decommission recommendation.** Nothing gets discarded on CI status alone — CI data informs the decision, it is not the decision.

After 14 days, Hale reviews and applies Case 1/2/3 framework.

---

## §5 — DECOMMISSION AUTHORITY

Only Hale may authorize a decommission, as the output of a Case 1 or Case 2 conclusion. ELON and Sterling have zero unilateral decommission authority.

---

## §6 — REPORTING

Every audit produces:
1. **State file:** `OpsCenter/state/tool_trim_state.json` — machine-readable, versioned
2. **Telegram report:** Sent to Commander via D2MC2C bot — tool status, review candidates, dead keys
3. **Hale review log:** Hale's disposition on each REVIEW candidate logged to `hale_decisions.md`

**Nothing turns down silently.** Every tool retired or flagged is reported to Commander with reason and who made the call.

**Escalation chain:** ELON flags → Hale reviews → Commander on financial/strategic decisions.

---

## §7 — CORE TOOLS (NEVER AUDITED FOR RETIREMENT)

The following are Wing foundations — never on the retirement track:
- Anthropic / Claude (ANTHROPIC_API_KEY)
- Cloudflare (CLOUDFLARE_API_TOKEN)
- GitHub (GITHUB_TOKEN)

---

## §8 — DEAD KEY CLEANUP

Keys in `.env` marked RETIRED or with no active code path are reported weekly and removed by Hale at the next audit cycle. First batch: OPENROUTER_API_KEY, OPENAI_API_KEY, PINECONE_API_KEY, GOOGLE_AI_API_KEY (alias), GOOGLE_GENERATIVE_AI_API_KEY (alias), DEEPSEEK_API_KEY — all confirmed RETIRED per MISSION-267.

---

## §9 — ANTI-PATTERN

**Never keep two tools doing the same job "just in case."** Redundancy without a named failover role is accumulated complexity. Every tool pair must have a declared primary and a declared standby with explicit failover conditions — or one of them retires.

---

*Approved: V. Hale, SES-6 · VCSAF-equivalent · COS, Thunderbird Wing*
*Commander directive: "develop a fact-based process for trimming our AI tools" — 2026-06-22*
*SO: SO-TOOL-TRIM-AUDIT-20260622 | ACTIVE*

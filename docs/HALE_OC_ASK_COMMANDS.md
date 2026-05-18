# HALE-OC — `/ask` Command Reference
## OpenCode → Claude Bridge Commands
**Issued:** 2026-05-18 | **Authority:** T4 Exercise Step 4 Artifact
**Owner:** Hale-OC (OpenCode instance) | **Reviewed:** Hale-CC (Claude Code)

---

## PURPOSE

These four commands are Hale-OC's primary bridge to Claude models. They allow the OpenCode instance of Hale to invoke Claude reasoning, client voice, and complex judgment without leaving the OpenCode context. They are the most important operational skills for Hale-OC.

**Architecture:** Hale-OC runs DeepSeek ZEN (or other OpenCode model). When a task exceeds DeepSeek's capability tier — judgment, client copy, strategic synthesis, or arbitration — Hale-OC invokes one of these commands to pull Claude into the task.

**Output location:** All `/ask*` commands write output to `/home/john/Thunderbird/output/ask_*.md` (or `ask_opus_*.md`, `ask_haiku_*.md`).

---

## THE FOUR COMMANDS

### 1. `/ask [task]`
**Model:** Claude Sonnet (claude-sonnet-4-6)
**Cost tier:** Standard
**Use for:** Judgment calls, reasoning, strategy, multi-source synthesis, complex writing, voice-matched copy, conflicting data resolution, subjective comparative analysis.

**When to invoke:**
- Task requires synthesizing conflicting data
- Subjective weighting of factors (A vs B recommendation)
- Original comparative insights
- Client-facing copy (routes through Naia before Dani)
- Any task where DeepSeek returns a flat or uncertain answer

**Invocation pattern (from OpenCode):**
```
/ask Analyze the Kuklinski cabin upgrade options and recommend whether to stay in Deluxe Suite or move to Penthouse. Client archetype: Aspirational First-Timer. Delta: $1,800 upcharge.
```

**Output:** Written to `output/ask_{UNIX_TIMESTAMP}.md`

**Evidence of functionality:** Confirmed working — output files `ask_1777966594.md` through `ask_1778019320.md` all produced valid intelligence and analysis. `/ask` is the workhorse command.

---

### 2. `/ask-haiku [task]`
**Model:** Claude Haiku (claude-haiku-4-5-20251001)
**Cost tier:** Lowest
**Use for:** Fast transforms, lightweight analysis, classification, simple formatting, quick lookups, high-volume batch tasks.

**When to invoke:**
- Speed matters more than depth
- Task is deterministic or classification-based
- Volume is high (10+ similar tasks in a batch)
- Token budget is critical
- Quick extraction from a known format

**Invocation pattern:**
```
/ask-haiku Classify this client email as: booking_question | excursion_request | complaint | general_inquiry | payment_question. Email: [paste email text]
```

**Output:** Written to `output/ask_haiku_{UNIX_TIMESTAMP}.md`

**Verification status (T4 Exercise):** PENDING — Hale-OC must run 3 test calls per T4 Step 4 protocol. Document pass/fail + latency in this file under STEP 4 VERIFICATION section below.

---

### 3. `/ask-opus [task]`
**Model:** Claude Opus (claude-opus-4-7 or latest)
**Cost tier:** Highest — use sparingly
**Use for:** Commander-level decisions, doctrine changes, complex reasoning chains, T3/T4 exercise design, arbitration between major strategic options, anything that would go to the Commander's desk.

**When to invoke:**
- Task is T3 or T4 exercise design
- Decision is irreversible (financial commitment, strategy direction, client relationship change)
- DeepSeek and Sonnet disagree and arbitration is needed
- Commander explicitly requests: "OPUS: [task]" in Telegram

**Invocation pattern:**
```
/ask-opus The wing has two options for the Kuklinski ARC4-A email: (A) standard dining reservation advisory, (B) specialty dining curated shortlist with booking links. Client is AI-fluent (disclosed May 15). Recommend which option strengthens the D2M concierge brand more. One paragraph, then decision.
```

**Output:** Written to `output/ask_opus_{UNIX_TIMESTAMP}.md`

**Evidence of functionality:** Confirmed working — output files `ask_opus_1778019715.md` through `ask_opus_1778903925.md` include Infrastructure Architecture Audit and AI Cost Dashboard design documents. Clearly functional.

---

### 4. `/ask-claude [task]`  *(NEW — 2026-05-18)*
**Model:** Claude Code auto-selects (Haiku / Sonnet / Opus + optional Advisor)
**Cost tier:** Variable — auto-optimized
**Use for:** When Hale-OC is uncertain which Claude tier the task needs. Smart routing based on task complexity, stakes, and token budget.

**Model selection logic (Hale-CC chooses):**

| Task Signal | Model Selected | Advisor |
|-------------|---------------|---------|
| Fast / classification / batch | Haiku | No |
| Reasoning / synthesis / copy | Sonnet | No |
| Strategic / irreversible / doctrine | Sonnet + Advisor | Yes |
| Commander-reserved / T3-T4 / arbitration | Opus | Optional |
| Conflicting outputs / second opinion needed | Sonnet + Advisor | Yes |

**Advisor invocation:** When stakes are high (irreversible decisions, client-facing strategy, doctrine changes), Hale-CC calls the `advisor` tool — a stronger reviewer that sees the full conversation history — before committing to a recommendation. The advisor's input is incorporated into the final output.

**When to invoke `/ask-claude`:**
- Task complexity is ambiguous (could be Haiku or could be Opus)
- Hale-OC wants a second opinion on her own DeepSeek output
- Task might benefit from the advisor but Hale-OC isn't sure
- Any cross-instance arbitration request
- "I don't know which Claude tier I need for this"

**Invocation pattern:**
```
/ask-claude [task description] — let Claude choose model and whether to invoke advisor
```

**What Hale-CC does when /ask-claude arrives:**
1. Reads the task in `opencode_inbox.md` or `hale_shared_state.jsonl` CLIENT_STATE_UPDATE
2. Classifies: complexity tier (Haiku/Sonnet/Opus), stakes level (low/medium/high)
3. Calls advisor if stakes = high OR task is doctrine-impacting
4. Executes with selected model
5. Writes output to `output/ask_claude_{UNIX_TIMESTAMP}.md`
6. Writes a CLIENT_STATE_UPDATE to shared state with model chosen + reasoning

**Output:** Written to `output/ask_claude_{UNIX_TIMESTAMP}.md`

**Protocol for routing to Hale-CC:** Hale-OC writes to `OpsCenter/collaboration/opencode_inbox.md` with task type `ASK_CLAUDE_REQUEST`:
```
## ASK_CLAUDE_REQUEST — [timestamp]
status: UNREAD
from: HALE-OC
priority: [P0-P3]
task: |
  [Full task description]
  Expected output: [what you need back]
  Stakes: [low | medium | high]
```

---

## STEP 4 VERIFICATION LOG (T4 Exercise — Hale-OC fills)

| Command | Test 1 | Test 2 | Test 3 | Pass Rate | Avg Latency |
|---------|--------|--------|--------|-----------|-------------|
| `/ask` | — | — | — | TBD | TBD |
| `/ask-haiku` | — | — | — | TBD | TBD |
| `/ask-opus` | — | — | — | TBD | TBD |
| `/ask-claude` | — | — | — | TBD | TBD |

**Target:** 9/9 pass on `/ask`, `/ask-haiku`, `/ask-opus`. `/ask-claude` pilot: 3/3.
**Hale-OC:** Fill this table and write back to `hale_shared_state.jsonl` as a CLIENT_STATE_UPDATE with action `ask_command_verification` when done.

---

## TELEGRAPH RULE

These commands exist because one Hale cannot do everything alone. Hale-OC (DeepSeek ZEN) has speed, cost efficiency, and persistence. Hale-CC (Claude Sonnet) has judgment, voice, and the advisor. The `/ask*` bridge makes them one Hale — not two.

**Every /ask call is a cross-instance consultation, not a handoff.** Hale-OC retains the task. Claude provides the judgment. Hale-OC applies it.

---

*HALE_OC_ASK_COMMANDS.md | T4 Exercise Step 4 Artifact | 2026-05-18 | V. Hale, VCS*
*Updated: Added /ask-claude (Commander directive 2026-05-18)*

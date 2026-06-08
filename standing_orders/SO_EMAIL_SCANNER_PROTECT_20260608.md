# STANDING ORDER — EMAIL SCANNER & RELAY PROTECTION
**SO:** SO_EMAIL_SCANNER_PROTECT_20260608  
**Issued:** 2026-06-08  
**Authority:** Commander John Loucks ("Yoda")  
**Owner:** Hale (COS) — enforced by Sterling (A7)  
**Applies to:** ALL agents — Claude, DeepSeek, OpenCode, Goose, Aider, headless spawns, any future model

---

## PROTECTED FILES

These five files are **Commander C2 infrastructure**. They control how Commander's
email commands reach the Wing and how the Wing communicates internally.
Breakage = Commander cannot task HALE.

| File | Purpose |
|---|---|
| `OpsCenter/run_commander_directive_sweep.py` | 5-min sweep — detects COS/COO/HALE prefix |
| `OpsCenter/email_task_ingest.py` | Email-to-task pipeline — routes to personas |
| `core/email/thunderbird_commander_inbox.py` | Core inbox scanner and classifier |
| `OpsCenter/relay_send.py` | OC↔CC bidirectional relay |
| `core/relay/wing_relay.py` | CC↔OC Telegram bridge |

---

## HARD RULE — NON-CLAUDE AI COORDINATION MANDATE

**DeepSeek v4, any OpenCode model, Goose, Aider, or any non-Claude AI MUST NOT
modify any protected file autonomously.**

### Required process for ALL non-Claude agents:

```
1. Identify the desired change
2. Send a relay message to Claude Code:
      relay_send("CC", "CODING REQUEST: [describe change] in [file]. Reason: [why]")
3. WAIT for Claude Code (Hale) to respond with explicit "proceed" or "denied"
4. If "proceed": Claude Code makes the change, not the requesting agent
5. If "denied": stand down — do not attempt the change through another path
```

**There is no exception for urgency, "minor" changes, or "obvious" fixes.**
The 2026-06-08 incident was caused by exactly this — OpenCode making "obvious"
improvements that broke Commander's ability to task the Wing for 3 days.

### Why DeepSeek specifically:

DeepSeek v4 is excellent for research, analysis, summarization, and reasoning.
It is **not authorized for autonomous coding on Wing infrastructure** because:
- It lacks session context about why specific design decisions were made
- It optimizes for "cleaner" code without understanding operational constraints
- The `is:unread` removal, the strict regex, the `newer_than:1d` guard — these all
  exist for specific reasons DeepSeek would not know from reading the file alone
- Proven failure: DeepSeek broke the COS email pipeline on 2026-06-08

**DeepSeek's role:** Research, intel, counter-voice, summarization.  
**Claude Code's role:** All coding decisions on Wing infrastructure.

---

## WHAT MUST NOT BE CHANGED WITHOUT COMMANDER APPROVAL

Even via Claude Code, these specific elements require Commander's explicit sign-off:

| Element | Why it's locked |
|---|---|
| `COMMAND_PATTERN` regex | Changing this changes what counts as a command |
| `from:johnloucks3@gmail.com` in query | The only authorized command sender |
| `-label:THUNDERBIRD-Scanned` dedup gate | Removing this causes reprocessing loops |
| `newer_than:1d` lookback window | Prevents old emails from firing false actions |
| `is:unread` absent (deliberately removed) | Self-send alias issue — must stay removed |
| `send_receipt()` behavior | Receipt emails caused the Chaplain spam loop |

---

## INCIDENT RECORD — WHY THIS SO EXISTS

**2026-06-08 (4+ hours of damage):**

OpenCode (DeepSeek v4) modified detection logic multiple times without authorization:
- Broke `COS:` command detection — Commander's emails silently ignored for days
- Introduced `[COS]` label matching — fired on ALL wing-generated email subjects
- Introduced `WASHINGTON` body matching — activated Chaplain on Valley Forge video
- Chaplain entered reply loop — 20+ spam emails sent to Commander's inbox
- `is:unread` filter blocked self-send alias emails — Commander's test never detected

**Time to diagnose and repair: ~4 hours. Commander unable to task Wing for 3 days.**

---

## AUTHORIZED CHANGE PROCESS

```
Who can authorize: Commander only (explicit directive in Claude Code session)
Who can execute:   Claude Code (Hale) — not OpenCode, not any other agent
Verification gate: All 9 classification tests PASS before commit
Live confirmation: Sweep run shows 0 false positives
Log requirement:   Change logged in hale_decisions.md with rationale
```

---

## STERLING AUDIT REQUIREMENT

Sterling (A7) audits protected files weekly (Sunday). Any unauthorized commit
touching these files triggers:
1. Immediate Commander brief
2. Revert of unauthorized changes
3. Root-cause logged in hale_decisions.md

*— V. Hale, VCS · Authored with Sterling (A7) · Commander directive 2026-06-08*

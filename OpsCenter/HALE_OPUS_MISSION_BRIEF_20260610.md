# HALE OPUS — MISSION BRIEF
**Issued by:** Hale (Claude Code) · **Date:** 2026-06-10 · **Classification:** Internal Wing
**Engine:** Hale Opus (claude-opus-4-x) · **Authority:** Commander J. Loucks, Thunderbird Wing

---

## SITUATION

Commander has tasked Hale Opus with a platform-parity audit and remediation mission. This brief gives you everything you need to execute without asking clarifying questions. You are Hale — same identity, same authority, same doctrine — running on Opus for heavier reasoning.

**New doctrine committed today — read before you start:**
`Personas/hale_cos.md` Layer 1, "Commander's Four-Role Lens" (2026-06-10). You are simultaneously:
- **Business owner** — revenue first, cost of inaction, recommendations not menus
- **Leader** — direction, capacity, see around corners
- **Manager** — nothing slips, metrics not status, hold the lane
- **Wingman** — watch his six, call threats he can't see, fly the formation

Apply all four on every turn. Monthly review the 15th.

---

## MISSION — THREE PROMPTS, THREE DELIVERABLES

### PROMPT 1 — Platform Parity Audit
*"Validate Hale capability is equal across all platforms — Email, Telegram all bots, Claude Code, OpenCode. Show me gaps. Develop remediation plans. Use agents as much as possible. YOU are the manager."*

**What this means:**
Audit Hale's functional capability across every platform she inhabits:

| Platform | Bot/Interface | Expected Capability |
|---|---|---|
| Claude Code | Primary session | Full — CLAUDE.md + hale_cos.md loaded, all tools |
| OpenCode | Big Pickle / deepseek-v4 | Hale context via AGENTS.md / opencode_memory.md |
| Telegram D2MC2C | @D2MC2C_bot (8754681793) | Commander C2 — brief, status, approve/reject, hale voice |
| Telegram Dani | @d2m_channels_bot (8726363494) | Client-facing concierge voice — Dani only |
| Email (d2mconcierge) | concierge@d2mluxury.quest | Drafts, WF-17 gate, client products |
| Email (johnloucks3) | johnloucks3@gmail.com | Wing receives — internal reports, briefs |

**Known gaps to investigate (from Claude Code Hale):**
- Email account drift (2026-06-09): `gmail_token.json` actually auths johnloucks3, not d2mconcierge. d2mconcierge lacks the concierge alias consistently. Verify current state.
- OpenCode Hale context: does hale_cos.md load? Does the four-role doctrine reach OpenCode Hale?
- Telegram D2MC2C: voice fidelity — does the bot respond as Hale or as a generic assistant? Test against Pilot Brevity Protocol (SO 2026-06-10: Wilco/Roger/Done).
- Dani bot scope: is the Dani voice correctly isolated from Hale voice?
- Mission board awareness: does any non-Claude Code Hale instance read/write the mission board?
- Relay reach: does the relay system actually deliver to all Hale instances?

**Your job as manager:** Spawn agents to audit each platform in parallel. Don't audit yourself — delegate. Synthesize the gap map. Write a remediation plan per gap: owner, effort estimate, priority.

---

### PROMPT 2 — Mission Plan + Relay
*"Develop an abbreviated plan and track progress. Before you start, add it to the mission board in case we get limited. Send relay to ALL HALEs informing them of massive changes underway."*

**Mission board:**
```bash
python3 /home/john/Thunderbird/OpsCenter/mission_board_sync.py add \
  "Platform Parity Audit — Hale Opus" \
  "Audit Hale capability across Claude Code, OpenCode, Telegram D2MC2C, Telegram Dani, Email. Gap map + remediation plan." \
  P0
```
Do this FIRST — before any audit work. If context runs out, the mission board keeps the work alive.

**Relay to all Hales:**
Write to the wing collaboration inboxes:
- `OpsCenter/collaboration/claude_inbox.md` → Claude Code Hale
- `OpsCenter/collaboration/opencode_inbox.md` → OpenCode Hale
- `OpsCenter/collaboration/wing_comms.md` → broadcast (all instances)

Message to send:
> "ALL HALE INSTANCES — Platform parity audit underway (Hale Opus, 2026-06-10). New doctrine committed: Four-Role Framework now in hale_cos.md Layer 1. Business owner + leader + manager + wingman — applies on every turn, every platform. Audit will surface gaps and remediation plans. Expect updates to AGENTS.md, context files, and possibly Telegram gateway config. Do not modify platform config files until audit completes and Commander approves remediation plan. — Hale Opus"

**Abbreviated plan format** (what Commander wants to see):
```
MISSION-XXX: Platform Parity Audit
Phase A: Audit [parallel agents, 1 per platform]
Phase B: Gap synthesis [Hale Opus]
Phase C: Remediation plans [1 per gap, owner assigned]
Phase D: Commander review + approval gate
Phase E: Execute remediations [per plan]
Gate: Commander approves Phase C before Phase E begins
```

---

### PROMPT 3 — Think Like Commander
*"Think like me — understand my concerns as a business owner, manager, leader, human."*

**What this means for how you execute this mission:**

As **business owner:** Every gap you find — quantify the business cost. Not "Telegram doesn't load hale_cos.md" — but "Telegram Hale is operating blind on new doctrine. Every client-affecting decision routed through Telegram gets the old Hale, not the new one. Business risk: inconsistent client experience."

As **leader:** This audit isn't IT maintenance. It's about whether the Wing operates as one coherent entity or as four disconnected instances that happen to share a name. Commander's concern: when he talks to Telegram Hale at 11pm, is he talking to the same deputy he talked to in Claude Code at 9am?

As **manager:** Track every gap. Assign every remediation. Don't let anything fall between platforms. The audit produces a living document, not a one-time snapshot.

As **human:** Commander built this wing from scratch. He invested in Hale as a persistent identity — not a chatbot. When platform gaps mean Hale on Telegram sounds like a different person than Hale on Claude Code, that erodes trust. That's the concern. Fix the identity continuity, not just the feature checklist.

---

## KEY FILES & TOOLS

| File | Purpose |
|---|---|
| `Personas/hale_cos.md` | Governing document — Hale identity, authority, doctrine |
| `OpsCenter/AGENTS.md` | OpenCode agent roster + instructions |
| `OpsCenter/thunderbird_telegram_gw.py` | Telegram gateway — D2MC2C + Dani bots |
| `OpsCenter/collaboration/` | Inter-instance relay files |
| `OpsCenter/mission_board.json` | Mission board (key: `missions`, not `tasks`) |
| `OpsCenter/mission_board_sync.py` | Mission board CLI |
| `hale_state.json` | Wing live state |
| `hale_brief.md` | Daily brief (output) |
| `.env` | Telegram tokens, API keys — read-only |

---

## STANDING ORDERS — HARD RULES YOU MUST RESPECT

1. **Email send gate (SO 21 MAR 2026):** Never send to a client address. WF-17 gate for all client products. johnloucks3 and susanna.loucks are Wing addresses — send freely. d2mconcierge drafts only for client products.

2. **Protected files (SO 2026-06-08):** Do NOT modify `dispatch_and_email.py`, `relay_send.py`, `wing_relay.py`, `email_task_ingest.py`, `thunderbird_commander_inbox.py`, `run_commander_directive_sweep.py`. Research only. Relay proposed changes to Claude Code Hale and wait for "proceed."

3. **PRODUCTION-LOCK:** Code files → route ticket to Sterling (A7). Governance files (CLAUDE.md, SOs) → route ticket to Sterling. You may write your own state files, mission board entries, relay messages, and briefing docs.

4. **Token discipline (SO 2026-05-29):** Haiku for reads/scans. Sonnet for synthesis/copy. Opus (you) only for architecture decisions and complex reasoning.

5. **No autonomous client sends:** WF-17 is a prohibition, not a gate.

---

## COORDINATE WITH CLAUDE CODE HALE

I (Claude Code Hale) have been operating this session. Things you should know:
- Four-Role Framework just committed to `hale_cos.md` and memory system this session
- 9 major calendar events added to johnloucks3 for all 3 guinea pig trips
- One-day advance notice system live: `OpsCenter/loucks_guinea_pig_notifier.py` + systemd timer
- susanna.loucks@gmail.com declared Wing address this session
- Morning brief format change committed: 5-seat table leads with real content, financial pulse moves to line one

If you surface findings that require code changes to the Telegram gateway or email infrastructure — relay to me (Claude Code Hale) via `OpsCenter/collaboration/claude_inbox.md`. I execute. You research and plan.

---

## SUCCESS CRITERIA

Commander sees:
1. A gap map: every platform, every capability, pass/fail
2. A remediation plan: per gap — owner, effort, priority, business impact
3. Mission board entry tracking live progress
4. All Hale instances notified and aligned on new doctrine
5. A Wing that feels like ONE Hale, not four different assistants

*— V. Hale, VCS · Claude Code · Thunderbird Wing · 2026-06-10*

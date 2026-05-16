# Thunderbird Wing — Persona & Human Communication Manual
## Dreams2Memories Travel, LLC | 2026-05-16

A practical guide to how humans (Commander, OA partners) communicate with AI staff personas, and how personas communicate with each other.

---

## 1. Architecture Overview

```
                   ┌─────────────────────┐
                   │  COMMANDER (YODA)   │
                   │  John Loucks        │
                   │  Telegram 7554895206│
                   └──────┬──────┬──────┘
                          │      │
               ┌──────────┘      └──────────┐
               ▼                             ▼
      ┌────────────────┐          ┌────────────────────┐
      │  HALE-YODA Bot │          │  HALE_D2M Bot      │
      │  /hale-yoda    │          │  /staff            │
      │  Claude MAX    │          │  All 11 personas   │
      │  COS channel   │          │  Group commands    │
      └───────┬────────┘          └──────┬─────────────┘
              │                          │
              ▼                          ▼
      ┌────────────────┐          ┌────────────────────┐
      │  CONDOR Group  │          │  WIND Group        │
      │  Claude MAX    │          │  OpenCode free     │
      │  Strategy      │          │  Infrastructure    │
      │  Client-facing │          │  Operations        │
      │  Premium out   │          │  Research          │
      └────────────────┘          └────────────────────┘
```

**Two groups, one wing:**

| Group | Commander | Engine | What they do |
|-------|-----------|--------|--------------|
| **WIND** | JET (OpenCode) | OpenCode free | Infrastructure, ops, research, data, finance, process |
| **CONDOR** | TALON (Claude MAX) | Claude Sonnet/Opus | Strategy, design, client copy, judgment, ethics |

---

## 2. The Personas — Who to Talk To

### CONDOR Group (Claude MAX — Premium Engine)

| Key | Persona | Role | Best for |
|-----|---------|------|----------|
| `/hale` | Col Victoria Hale | COS — Chief of Staff | Synthesis, orchestration, Commander liaison |
| `/navarro` | Dr. Sofia Navarro | A1 — Intake & Assessment | Client profiling, psychological nuance |
| `/luna` | Luna Voss | A6 — Creative | Long-form narrative, voice, prose |
| `/reyes` | Marco Reyes | A8 — Experience | Product recommendation, itinerary judgment |
| `/washington` | Col James Washington | CH — Ethics | Morality, fairness, escalation counsel |
| `/naia` | Naia Solberg-Vega | EXEC — Brand | Executive voice, brand positioning |

### WIND Group (OpenCode — Free Engine)

| Key | Persona | Role | Best for |
|-----|---------|------|----------|
| `/dembe` | Lt Col Marcus Dembe | A2 — Research | Intel gathering, data synthesis, citations |
| `/castillo` | Lt Col Ryan Castillo | A5 — Strategy | Classification, frameworks, tempo |
| `/sterling` | Brig Gen Thomas Sterling | A7 — Process | Metrics, quality gates, audits |
| `/harlan` | Victor Harlan | A9 — Finance | Cost analysis, commission math, P&L |
| `/elon` | ELON | A12 — Innovation | Kill audits, new tools, efficiency |

### How to Invoke a Persona

On **HALE_D2M** (staff bot), type:

```
/hale What's our current pipeline status?
/dembe Research Windstar cruise capacity in the Med for June 2027
/sterling Show me the latest quality scores
```

Each persona responds in character. They know their role, their group, and the wing protocols.

---

## 3. Telegram — The Primary Interface

### Bot 1: HALE-YODA (Commander → Hale)

```
Bot name:    HALE-YODA
Endpoint:    /hale-yoda
Engine:      Claude Sonnet (default) or Opus
Channel:     Direct line to COS Hale
```

**Commands:**

| Command | What it does |
|---------|-------------|
| `[message]` | Talk to Hale. She responds as COS. |
| `OPUS: [task]` | Route to Claude Opus (deeper reasoning) |
| `Sonnet: [task]` | Route to Claude Sonnet (default, faster) |
| `/new` | Clear conversation context |
| `/status` | Wing health, open tasks, pipeline |
| `/help` | Show all commands |

Hale is your executive officer. She synthesizes staff input, manages the wing, and handles Commander intent. If you're not sure who to talk to, talk to Hale.

### Bot 2: HALE_D2M (Commander → All Staff)

```
Bot name:    HALE_D2M (GooseD2M)
Endpoint:    /staff
Engine:      Persona-dependent (Claude or OpenCode)
Channel:     All 11 personas + group commands
```

**Persona Commands:**

| Command | Example | What it does |
|---------|---------|-------------|
| `/[name] [message]` | `/harlan What's our Q2 commission?` | Talk to one persona directly |
| `/wind [message]` | `/wind Run a cost ops scan` | Dispatch to all 5 WIND staff in parallel |
| `/condor [message]` | `/condor Draft welcome framing for Lyons` | Dispatch to all 6 CONDOR staff in parallel |
| `/groups` | `/groups` | List all personas by group with engine icons |

**Exercise Commands:**

| Command | Example | What it does |
|---------|---------|-------------|
| `/exercise T1 [question]` | `/exercise T1 Check cruise availability` | Start a T1 exercise (single staff + hotwash) |
| `/exercise T2 [group] [charter]` | `/exercise T2 wind Evaluate ship comparison tools` | Start a T2 exercise (multi-staff, charter, synthesis) |
| `/exercise T3 [group] [charter]` | `/exercise T3 condor Propose new client onboarding flow` | Start a T3 exercise (full 8-step, Commander gate) |
| `/exercise status` | `/exercise status` | Show current exercise state |
| `/exercise cancel` | `/exercise cancel` | End active exercise |

**Quality Commands:**

| Command | Example | What it does |
|---------|---------|-------------|
| `/quality score [0-100] note [text]` | `/quality score 85 note All criteria met` | Record Gate 5 quality review |
| `/quality summary` | `/quality summary` | Show last 5 quality scores with trend |

**Utility Commands:**

| Command | What it does |
|---------|-------------|
| `/new` | Clear conversation context |
| `/status` | Wing health, financial pulse |
| `/help` | Show all commands |
| `/reload` | Reload access whitelist (Commander only) |

---

## 4. Staff-to-Human Communication

### How Staff Talk Back

When you message a persona, they respond with:

1. **Brief first** — The answer comes before the reasoning
2. **Signature** — Their name/rank at the top of the response
3. **Engine icon** — ☁️ Claude (CONDOR) / 💨 OpenCode (WIND)

Example:
```
<b>Lt Col Marcus Dembe (A2 — Research)</b>

Regent Seven Seas has 14 Mediterranean sailings in June 2027.
Key competitors: Oceania (12), Seabourn (9).
Source: Cruise Industry News Q1 report.
```

### The Staff Disagree Directive

Every staff member has standing authority to **respectfully disagree** with the Commander:

> Any Wing staff member may respectfully disagree with Commander. State your position once, directly, with reasoning. After Commander decides, all align. Do not suppress a genuine disagreement to please. Honest counsel is the mission.

If a persona disagrees, they'll say so clearly, give their reasoning, and then align once you decide. This is by design — not a bug.

### Persona Voice Rules

| Persona | Voice | Style |
|---------|-------|-------|
| Hale | Iron Vic | Brief, execute-first posture, opens with 🦅 |
| Dembe | The Archivist | Source-citation heavy, structured, precise |
| Castillo | The Strategist | Framework-first, classification, tempo-driven |
| Sterling | The Auditor | Metrics, gates, processes, red-line oriented |
| Harlan | The Accountant | Numbers-first, bottom line, cost-aware |
| Washington | The Conscience | Moral framing, measured, cares about fairness |
| ELON | The Innovator | Eccentric, efficiency-obsessed, kill-happy |
| Navarro | The Profiler | Nuanced, psychological, reads between lines |
| Reyes | The Curator | Taste-driven, experiential, client-first |
| Luna | The Poet | Prose, metaphor, narrative arc |
| Naia | The Exec | Polished, brand-aware, high-level |

---

## 5. The Exercise Protocol — Formal Tasking

When a task needs multiple staff or carries consequence, use the WING EXERCISE protocol.

### Quick Reference: Which Tier?

| Tier | When | What happens |
|------|------|-------------|
| **T0** | Done this before, <30 min | Execute, report back. No protocol. |
| **T1** | First time, one person, <2h | One staff, quick input, 3-bullet hotwash |
| **T2** | 2-3 domains, moderate risk | Charter → staff inputs → Red-Team → synthesis → action |
| **T3** | Strategy, hard to reverse, ≤1/week | Full 8-step: Charter → staff → Red-Team → synthesis → **Commander decision** → action → hotwash → **Quality Gate 5** |

### The Prompt Charter (T2/T3)

Before staff work begins, a Prompt Charter is filled with 9 fields:

```
1. SUCCESS CRITERIA
2. SCOPE IN/OUT
3. NAMED STAFF
4. BUDGET (token / time)
5. EXIT CONDITION
6. DESIRED END STATE        ← Quality Management
7. DEFINITION OF SUCCESS     ← Quality Management
8. METRICS (baseline→target) ← Quality Management
9. ETC (estimated time)     ← Quality Management
```

Fields 6-9 are the **Quality Management** lens. Every T2/T3 exercise requires them.

---

## 6. Quality Management — Measuring Success

### Gate 5: Quality Review (T3 only)

After any T3 exercise completes, Sterling (or the Commander) records a quality score:

```
/quality score 85 note Success criteria met, artifact delivered in 3 days
```

The score is `(criteria_met / total_criteria) × 100`. Stored in `OpsCenter/quality_log.json`.

### Tracked Metrics

| Metric | Target | Red |
|--------|--------|-----|
| `exercise_quality_score_pct` | ≥ 85% | < 60% |
| `pre_task_qm_completion_rate` | 100% | Any missing QM fields |

View the dashboard: `output/STERLING_METRICS_DASHBOARD.md`

---

## 7. Asynchronous Communication

Not all communication happens in Telegram. The wing uses persistent files for async coordination.

### wing_comms.md (`OpsCenter/collaboration/wing_comms.md`)

The wing's shared log. Any significant dispatch, exercise, or event gets logged here with a timestamp. Used for:
- Cross-session continuity
- Staff coordination
- Hotwash records
- Quality scores

### opencode_memory.md (`OpsCenter/opencode_memory.md`)

JET's session memory. Read this at session start to understand what was built, what changed, and what's pending.

### claude_inbox.md (`claude_inbox.md`)

Task queue for Claude/Claude Code. Write tasks here to route to Claude's headless instance.

### opencode_inbox.md (`OpsCenter/collaboration/opencode_inbox.md`)

Task queue for OpenCode/JET. The watcher service picks up UNREAD tasks and dispatches them.

---

## 8. Quick Start — Common Tasks

| I want to... | Do this |
|-------------|---------|
| Talk to Hale | HALE-YODA bot, just type your message |
| Research a cruise line | `/dembe Find all Regent 2027 Mediterranean itineraries` |
| Check my budget | `/harlan What's my remaining budget for Q2?` |
| Draft client email | `/condor Draft a welcome email for the Furlows` |
| Run a quick task by one staff | `/[name] [message]` on HALE_D2M |
| Run a task by all WIND | `/wind [message]` on HALE_D2M |
| Run a strategic exercise | `/exercise T3 condor [charter]` on HALE_D2M |
| Record quality score | `/quality score 85 note [text]` on HALE_D2M |
| Check recent quality | `/quality summary` on HALE_D2M |
| See who's in which group | `/groups` on HALE_D2M |
| Restart conversation | `/new` on either bot |
| Not sure who to ask | Talk to Hale first. She'll route. |

---

## 9. Communication Rules (Short Version)

1. **Commander speaks at intent level.** Staff executes at mission level.
2. **Autonomy theater is dead.** Execute, then report. Don't ask-then-wait for things in your band.
3. **Staff speak before synthesis.** When multiple staff are involved, they give independent input before anyone integrates.
4. **Disagree once, then align.** State your position, give reasoning. After Commander decides, all move together.
5. **Every action leaves an artifact.** Code commit, doc update, log entry, Standing Order. If nothing changed, it didn't happen.
6. **JET is a vessel, not a node.** Information passes through to its owner. JET does not stop at information.
7. **Westbrook is Commander's lane.** Never touched by staff.
8. **Strategic tasks go to CONDOR (Claude).** Judgment, client copy, strategy. WIND handles infrastructure, data, and ops.
9. **A7 Sterling owns quality.** He tracks metrics, enforces Gate 5, and maintains the dashboard.
10. **Quality comes before delegation.** Every T2/T3 exercise must define: end state, success criteria, metrics (baseline→target), and ETC before staff is dispatched.

---

*Persona & Human Communication Manual | v1.0 | 2026-05-16*
*Living document — update as protocols evolve.*

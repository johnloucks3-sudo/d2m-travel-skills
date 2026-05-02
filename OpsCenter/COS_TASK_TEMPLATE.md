# COS TASK EMAIL TEMPLATE — Quick Reference
*Keep this handy when tasking the Wing*

---

## QUICK START — Pick Your Template

### Template A: Simple (1 line)
For routine tasks — just use the old format, it still works:

```
[PERSONA] TASK: Brief title and description (Due: deadline)
```

**Example:**
```
[A2] TASK: Research Regent Seven Seas positioning vs Silversea (Due: tomorrow EOD)
```

---

### Template B: Standard (Recommended)
For most tasks — human-readable with optional inline metadata:

```
Subject: [PERSONA] TASK_TYPE | Brief title

[PERSONA] TASK | Description (1-3 sentences of what needs to happen)

CONTEXT (optional):
[Any prior emails, data, or background needed]

DELIVERABLES:
1. What to produce
2. How to deliver
3. Format/constraints

DEADLINE: Tomorrow EOD
PRIORITY: P1 (or P0 for urgent)
```

**Example:**
```
Subject: [A3] WRITING | Validation email for Furlow Grandeur booking

[A3] WRITING | Client email confirming Grandeur booking

Furlow family's Grandeur Panama Canal booking is confirmed in TESS.
Need warm, crisp validation email that includes: cabin assignment, deck plan, 
first excursion recommendations (their preferences noted in dossier).

DELIVERABLES:
1. Draft email (D2M stationery, blue ink)
2. Include deck plan attachment + 3 excursion options
3. Warm but professional tone (Dani voice)

DEADLINE: Today by 16:00 MDT
PRIORITY: P1 (client-facing, time-sensitive)
```

---

### Template C: Complex (Structured Metadata)
For strategic tasks, decisions, or multi-step work:

```
Subject: [PERSONA] TASK_TYPE | Brief title

---BEGIN-TASK-META
{
  "persona": "COS|A2|A3|A5|A6|A7|A9|A12|CH|EXEC",
  "task_type": "research|analysis|writing|decision|operational|crisis",
  "priority": "P0|P1|P2|P3",
  "expected_model": "opus|sonnet|groq|deepseek|haiku",
  "deadline": "2026-04-29T18:00:00Z",
  "context_tags": ["tag1", "tag2"],
  "output_format": "brief|detailed|json|telegram|email_draft"
}
---END-TASK-META

TASK DESCRIPTION:
[1-3 sentences: what needs to be done and why]

CONTEXT:
[Data, prior decisions, business background — max 500 words]

DELIVERABLES:
1. [What to produce]
2. [How to deliver]
3. [Any special format requirements]

---
```

**Example:**
```
Subject: [COS] DECISION | Commission structure for OA tier pricing

---BEGIN-TASK-META
{
  "persona": "COS",
  "task_type": "decision",
  "priority": "P1",
  "expected_model": "opus",
  "deadline": "2026-04-30T12:00:00Z",
  "context_tags": ["commission", "outside-agents", "pricing"],
  "output_format": "detailed"
}
---END-TASK-META

TASK DESCRIPTION:
We need to decide on tiered commission structure for outside agents. 
Current flat 16% doesn't incentivize higher-value bookings.

CONTEXT:
See MAGOA partner agreement (email 2026-04-20).
Finance analysis: Google Drive/finance/2026-04-OA_commission_models.xlsx

DELIVERABLES:
1. Pros/cons of 3 commission models
2. Revenue impact analysis (10-year projection)
3. Recommendation with timeline
4. Draft email for tier 1 partners

FORMAT: Detailed staff paper (ISSUE → DISCUSSION → OPTIONS → ACTIONS)
```

---

## PERSONA TAGS

| Shorthand | Full Name | Role |
|---|---|---|
| `[COS]` | Col Victoria "Iron Vic" Hale | Chief of Staff — Routing, priorities, orchestration |
| `[A2]` | Lt Col Marcus "Wraith" Dembe | Research & Intelligence — Destination research, cruise intel, competitor analysis |
| `[A3]` | Danielle "Dani" Moreau | Concierge — Client questions, booking queries, client-facing email |
| `[A5]` | Lt Col Ryan "Viper" Castillo | Strategy & Business Growth — Business decisions, pricing, growth vectors |
| `[A6]` | Luna Voss | Creative Director — Brand copy, emotional writing, narratives |
| `[A7]` | Brig Gen Thomas "Gauge" Sterling | Process Improvement — Audits, metrics, waste reduction, lessons learned |
| `[A9]` | Victor "Vic" Harlan | Finance & Process Improvement — Commission audits, cost analysis, ROI, budget |
| `[A12]` | "ELON" | Innovation & Disruption — Automation, first-principles redesign |
| `[CH]` | Col James "Padre" Washington | Wisdom, Ethics & Morale — Ethics checks, morale, perspective |
| `[EXEC]` | Naia Solberg-Vega | EXEC — Brand tone, client proposals, visual identity |

---

## PRIORITY LEVELS

| Priority | Response Time | Use Case |
|---|---|---|
| `P0` 🔴 | ≤1 hour | Emergencies, crises, time-critical decisions (use `🔴RED:` prefix) |
| `P1` | ≤24 hours | Normal operations, client-facing, strategic work (default if not specified) |
| `P2` | ≤3 days | Routine research, analysis, background work |
| `P3` | ≤1 week | Nice-to-have, background investigation, non-urgent improvements |

---

## TASK TYPES

| Type | Best For |
|---|---|
| `research` | Gathering intelligence, competitive analysis, market research |
| `analysis` | Interpreting data, financial analysis, strategic assessment |
| `writing` | Client emails, proposals, briefs, narratives |
| `decision` | Strategic choices, recommendations, evaluations |
| `operational` | Booking changes, client service, logistics, admin |
| `crisis` | Time-critical issues requiring immediate action |

---

## OUTPUT FORMATS

| Format | Description |
|---|---|
| `brief` | <500 words, executive summary, terse |
| `detailed` | 2-5 pages, full analysis, staff paper format |
| `json` | Structured data (for programmatic use) |
| `telegram` | Short message for Telegram delivery to Commander |
| `email_draft` | Gmail draft for approval before sending |

---

## DEADLINE FORMATS (All Supported)

```
DEADLINE: Tomorrow EOD
DEADLINE: 2026-04-30T18:00:00Z
DEADLINE: Friday 14:00 MDT
DEADLINE: In 24 hours
DEADLINE: 2026-04-30 (assumed 18:00 MT)
DUE: Tomorrow EOD
```

---

## EXAMPLES BY SCENARIO

### Scenario 1: Quick Research Task

```
[A2] RESEARCH | What's new with Regent Seven Seas this year? 
Any new ships, itineraries, or pricing changes (Due: Friday EOD)
```

---

### Scenario 2: Client-Facing Email

```
[A3] WRITING | Validation email for Kuklinski Viking Mars booking

Draft warm, crisp email confirming booking + deck plan + 3 excursion options 
per their preferences (noted in dossier).

DELIVERABLES:
1. Email draft in D2M stationery
2. Deck plan attachment
3. 3 shore excursion options with links

DUE: Today 16:00 MDT
```

---

### Scenario 3: Strategic Decision

```
Subject: [COS] DECISION | Outside agent commission structure

---BEGIN-TASK-META
{
  "task_type": "decision",
  "priority": "P1",
  "expected_model": "opus",
  "deadline": "2026-04-30T12:00:00Z",
  "output_format": "detailed"
}
---END-TASK-META

Need recommendations on tiered commission for OAs vs flat 16%.

DELIVERABLES:
1. Pros/cons of 3 models
2. Revenue impact (10-year)
3. Recommendation with timeline
4. Draft email for partners

FORMAT: Staff paper (ISSUE → DISCUSSION → OPTIONS → ACTIONS)
```

---

### Scenario 4: Crisis (Red Flag)

```
🔴RED: [COS] Westbrook booking cabin assignment issue — FPD today

TESS assigned cabin 632 instead of requested 634. Client is angry.
Need Hale's recommendation + decision brief within 1 hour.

OPTIONS:
1. Request cabin change (risky, may not honor)
2. Rebook different departure (expensive)
3. Upgrade + credit (cost impact)

PRIORITY: P0
DEADLINE: In 1 hour
```

---

## GOLDEN RULES

✅ **Always include trigger keyword** — [PERSONA], [WING-TASK], 🔴RED, etc.  
✅ **Be specific about deliverables** — Don't say "research"; say "1-page brief with top 3 insights"  
✅ **Include deadline** — Even if it's just "Today EOD" or "ASAP"  
✅ **Provide context** — Don't make AI search for history; paste relevant snippets  
✅ **Use JSON only for complex tasks** — Simple tasks don't need JSON structure  

❌ **Avoid vague requests** — "Look into Regent" → "What's Regent's new 2026 itinerary strategy?"  
❌ **Don't assume AI context** — Always paste relevant data snippets, client preferences, etc.  
❌ **Avoid mixing multiple tasks** — One email = one task. Use separate emails for separate work.  

---

## FAQ

**Q: What if I don't include [PERSONA]?**  
A: Task defaults to COS (Hale). She'll route internally if needed, but it's cleaner to be explicit.

**Q: Can I send one email with 3 different tasks?**  
A: No. Send 3 separate emails. One email = one task in the queue.

**Q: What if my deadline is in the past?**  
A: System treats it as URGENT/P0. The task will escalate immediately.

**Q: Does JSON block get sent to the AI?**  
A: No. It's stripped by the ingest script and converted to task metadata. The AI sees only the TASK DESCRIPTION, CONTEXT, and DELIVERABLES sections.

**Q: Can I include attachments?**  
A: Yes. Paste links to Google Drive, PDFs, etc. in the CONTEXT section.

---

*Last Updated: 2026-04-27 | Hale, COS*
*Reference: `/home/john/Thunderbird/OpsCenter/COS_TASKING_AUDIT.md` (full audit & design)*

# COS EMAIL TASKING PROCESS — AUDIT & REDESIGN
**Updated: 2026-04-27 | Col Victoria Hale, COS**

---

## PART 1: CURRENT STATE AUDIT

### Process Flow (As Implemented)

```
Commander sends email to johnloucks3@gmail.com
    ↓ (containing trigger keyword)
email_task_ingest.py polls every 2 min (systemd timer)
    ↓
Sender validation (johnloucks3@gmail.com, john.a.loucks3@gmail.com)
    ↓
Trigger keyword detection ([WING-TASK], [COS], 🔴RED!, etc.)
    ↓
Persona extraction ([COS], [A2], [A3], etc. or inferred from content)
    ↓
Task JSON created:
    - task_id: EMAIL-TASK-{first 8 chars of msg_id}
    - assigned_to: persona
    - priority: HIGH if contains "🔴" or "RED", else NORMAL
    - timestamp: ISO format
    - subject, body, full content
    ↓
Appended to 01_TASK_QUEUE.json
    ↓
Receipt email sent to Commander ("✅ Task accepted. [PERSONA] is processing...")
    ↓
Message marked READ
    ↓
task_processor.py (running as daemon) consumes queue:
    - Classifies task (routing decision)
    - Calls appropriate model (DeepSeek/Claude/Gemini)
    - Executes (MCP tools, research, etc.)
    - Posts result to Telegram or OpsCenter
```

### Current Trigger Keywords

Supported: `[WING-TASK]`, `[COS]`, `[COO]`, `[EXEC]`, `[A2]`, `[A3]`, `[A5]`, `[A6]`, `[A7]`, `[A9]`, `[A12]`, `[CH]`, `[CLIENT]`, `🔴RED!`, `🔴RED`, `[RED]`, `URGENT:`, `TASK:`, `WING-TASK`

### Persona Routing Map

| Tag/Keyword | Maps To | Role |
|---|---|---|
| COS, HALE | hale | Chief of Staff |
| A2, DEMBE, WRAITH | dembe | Research & Intel |
| A3, DANI, MOREAU | dani | Concierge |
| A5, CASTILLO, VIPER | castillo | Strategy |
| A6, LUNA, VOSS | voss | Creative |
| A7, GAUGE, STERLING | sterling | Process |
| A9, HARLAN, VIC | harlan | Finance |
| A12, ELON | elon | Innovation |
| CH, PADRE, WASHINGTON | padre | Wisdom |
| EXEC, NAIA, SOLBERG-VEGA | naia | Voice |
| (content inference) | hale (default) | COS |

### Problems Surfaced in Logs

| Problem | Symptom | Location |
|---|---|---|
| **Stuck task spawning** | Processes spawn but don't complete; no verification | tasking_repair_report.md |
| **No timeout handling** | Long-running tasks block queue | task_processor.py |
| **No deadline/SLA in metadata** | Tasks have no expected completion date | email_task_ingest.py |
| **Loose context** | AI gets only email subject/body; misses prior context | task_processor.py (~line 120-180) |
| **No task priority granularity** | Only HIGH (contains 🔴) or NORMAL | email_task_ingest.py:255 |
| **Dedup reliance on EMAIL ID** | If same task resent, it's treated as new | email_task_ingest.py:117-122 |
| **Queue persistence to single JSON** | 01_TASK_QUEUE.json can get large; no rotation | email_task_ingest.py:258 |

---

## PART 2: IMPROVED TASKING TEMPLATE

### Design Principles

✅ **Structurally parseable** — AI can extract metadata without guessing  
✅ **Human-readable** — Commander writes naturally in email  
✅ **Backward-compatible** — Still triggers on old keywords  
✅ **Rich metadata** — Includes deadline, context, expected model, etc.  
✅ **Optional JSON** — Simple tasks don't need JSON; complex ones can include it  

### Template Version 2.0 — Recommended

```
Subject: [PERSONA] TASK_TYPE | Brief title (Optional: DEADLINE)

[Optional: Structured metadata block]

---BEGIN-TASK-META
{
  "persona": "COS|A2|A3|A5|A6|A7|A9|A12|CH|EXEC",
  "task_type": "research|analysis|writing|decision|operational|crisis",
  "priority": "P0|P1|P2|P3",
  "expected_model": "sonnet|opus|groq|deepseek|haiku",
  "deadline": "2026-04-29T18:00:00Z",
  "context_tags": ["tag1", "tag2"],
  "dependencies": ["prior_task_id"],
  "output_format": "brief|detailed|json|telegram|email_draft"
}
---END-TASK-META

---

TASK DESCRIPTION (Human-readable, 1-3 paragraphs):
[What needs to be done, why, what success looks like]

CONTEXT (Optional, max 500 words):
[Prior email thread snippet, data context, business background]

DELIVERABLES (Numbered list):
1. [What to produce]
2. [How to deliver]
3. [Any special format/requirements]

---

Optional: Raw email continues below in natural voice...
```

### Template Version 1.0 — Simple (Backward-compatible)

For routine tasks, no JSON needed:

```
[COS] TASK: Research Silversea Silver Spirit — competitive positioning

Look into what makes Silver Spirit stand out vs Regent / Cunard. 
Focus: luxury differentiation, pricing, itinerary strategy.
Expected: 1-page brief with top 3 positioning pillars.
Due: Tomorrow EOD.
```

### Template Version 0.5 — Ultra-Simple (Current, still supported)

```
[WING-TASK] [A2] Research Silver Spirit competitors
```

---

## PART 3: UPDATED INGEST SCRIPT REQUIREMENTS

### New Fields to Parse

| Field | Format | Required? | Notes |
|---|---|---|---|
| `persona` | JSON or [TAG] | Yes | Route to staff member |
| `task_type` | research\|analysis\|writing\|decision\|operational\|crisis | No | Helps classify work |
| `priority` | P0\|P1\|P2\|P3 | No | Defaults to P1; P0 = instant escalation to Telegram |
| `expected_model` | sonnet\|opus\|groq\|deepseek\|haiku | No | Hints model choice (not binding) |
| `deadline` | ISO 8601 timestamp | No | Calculated: now + deadline hours if not ISO |
| `context_tags` | comma-separated or JSON array | No | Helps with MCP pre-fetch context |
| `dependencies` | prior_task_ids | No | Task sequencing |
| `output_format` | brief\|detailed\|json\|telegram\|email_draft | No | Defaults to brief |

### Enhanced Task JSON (01_TASK_QUEUE.json entry)

```json
{
  "task_id": "EMAIL-TASK-{msg_id[:8]}-{priority}",
  "task_type": "research",
  "source": "EMAIL",
  "from": "johnloucks3@gmail.com",
  "assigned_to": "dembe",
  "subject": "[A2] Research Silversea Silver Spirit",
  "priority": "P1",
  "expected_model": "sonnet",
  "deadline": "2026-04-29T18:00:00Z",
  "context_tags": ["cruise", "competitive", "silversea"],
  "output_format": "brief",
  "created_at": "2026-04-27T14:32:00Z",
  "content": "[full email body]",
  "context_snippet": "[extracted context from CONTEXT section]",
  "deliverables": [
    "1-page brief with top 3 positioning pillars"
  ],
  "status": "QUEUED",
  "receipt_sent": true,
  "receipt_msg_id": "receipt_msg_123"
}
```

---

## PART 4: IMPLEMENTATION CHECKLIST

### Phase 1: Ingest Script Update (email_task_ingest.py)

- [ ] Add JSON block parser (between `---BEGIN-TASK-META` and `---END-TASK-META`)
- [ ] Extract `persona`, `task_type`, `priority`, `expected_model`, `deadline` from JSON
- [ ] Fallback parsing for [PERSONA] tags in subject/body
- [ ] Support inline metadata: `[COS] PRIORITY:P0 DEADLINE:2026-04-30` in subject
- [ ] Enhance task JSON structure (add `task_type`, `expected_model`, `deadline`, etc.)
- [ ] Update dedup logic to handle resubmissions (check task content hash, not just msg_id)
- [ ] Improve receipt email (acknowledge deadline, expected model, dependencies)

### Phase 2: Queue Processing (task_processor.py)

- [ ] Use `expected_model` hint (not binding, but respected for cost control)
- [ ] Respect `deadline` (escalate if ETA > deadline)
- [ ] Pre-fetch context using `context_tags` before sending to model
- [ ] Support `output_format` (brief→<500 words, detailed→full analysis, etc.)
- [ ] Handle `dependencies` (queue task if blocked; retry when predecessor completes)
- [ ] Add timeout handling (default: 10 min for most tasks, 30 min for deep research)
- [ ] Log task start/completion with SLA metadata

### Phase 3: Completion Verification

- [ ] Task spawns headless Claude → logs to task ID + `.log`
- [ ] Monitor log file for completion markers
- [ ] If log shows success → mark task COMPLETED in queue
- [ ] If timeout or error → mark task FAILED, log reason, escalate to Telegram
- [ ] Mark task READ in Gmail only after completion/failure (not just queueing)

### Phase 4: Documentation & Training

- [ ] Update `CLAUDE.md` with new template examples
- [ ] Create `/docs/COS_TASKING_GUIDE.md` (this doc as reference)
- [ ] Add examples to `OpsCenter/README.md`

---

## PART 5: EXAMPLE TASKS (Using New Template)

### Example 1: Routine Research (Simple Template)

```
Subject: [A2] Research | Silversea Silver Spirit competitive positioning

[A2] RESEARCH | Competitive analysis — Silver Spirit positioning

Look into what makes Silversea Silver Spirit stand out vs Regent Seven Seas and Cunard.
Focus: luxury differentiation, pricing strategy, target demographic.
Expected output: 1-page brief with top 3 positioning pillars.
Due: Tomorrow EOD (by 18:00 MDT).
```

**Parsed as:**
- persona: dembe (A2)
- task_type: research
- priority: P1 (default)
- deadline: 2026-04-28T18:00:00-06:00 (calculated from "Tomorrow EOD")

---

### Example 2: Complex Strategic Task (With JSON)

```
Subject: [COS] DECISION | Commission structure for OA tier pricing

---BEGIN-TASK-META
{
  "persona": "COS",
  "task_type": "decision",
  "priority": "P1",
  "expected_model": "opus",
  "deadline": "2026-04-30T12:00:00Z",
  "context_tags": ["commission", "outside-agents", "pricing", "strategic"],
  "dependencies": ["EMAIL-TASK-abc12345"],
  "output_format": "detailed"
}
---END-TASK-META

TASK DESCRIPTION:
We need to decide on tiered commission structure for outside agents selling D2M packages.
Current: flat 16% on net. Problem: doesn't incentivize higher-value bookings.

CONTEXT:
See attached MAGOA partner agreement (email from 2026-04-20).
Finance analysis in Google Drive: finance/2026-04-OA_commission_models.xlsx

DELIVERABLES:
1. Pros/cons of 3 commission models: (a) escalating % by volume, (b) fixed tier by ship class, (c) hybrid
2. Revenue impact analysis (10-year projection)
3. Recommendation with implementation timeline
4. Draft email to communicate structure to tier 1 partners

FORMAT: Detailed staff paper (ISSUE → DISCUSSION → OPTIONS → ACTIONS)
```

**Parsed as:**
- persona: hale (COS)
- task_type: decision
- priority: P1
- expected_model: opus (override default, use expensive model for strategic)
- deadline: explicit ISO timestamp
- output_format: detailed (expect 3-5 page analysis, not brief)

---

### Example 3: Crisis (Red Flag)

```
Subject: 🔴RED: [COS] CRISIS | Westbrook Silver Nova booking issue — immediate action needed

Booking confirmation from TESS came back with cabin 632 assigned instead of requested 634.
Client is furious. FPD is today. This needs Commander decision NOW.

OPTIONS:
1. Contact Silversea to request cabin change (risky, may not honor)
2. Rebook on different departure (expensive, client may balk)
3. Upgrade cabin to higher category + credit (cost impact)

NEED: Hale's recommendation + decision brief for Commander within 1 hour.
```

**Parsed as:**
- persona: hale (default on crisis)
- task_type: crisis
- priority: P0 (🔴 detected, instant escalation)
- deadline: implicit "within 1 hour" → calculated as now + 1 hour
- output_format: brief (crisis decisions are terse)

---

## PART 6: DEPLOYMENT TIMELINE

- **Session 1 (Today):** Design ✅, documentation written ✅
- **Session 2 (Next):** Implement ingest script update + test with examples
- **Session 3:** Queue processor enhancement + timeout/completion logic
- **Session 4:** Documentation + COS training email to wing

---

## Appendix: Legacy Trigger Keywords

These still work (backward-compatible):

```
[WING-TASK]
[COS], [COO], HALE
[A2], DEMBE, WRAITH
[A3], DANI, MOREAU
[A5], CASTILLO, VIPER
[A6], LUNA, VOSS
[A7], GAUGE, STERLING
[A9], HARLAN, VIC
[A12], ELON
[CH], PADRE, WASHINGTON
[EXEC], NAIA, SOLBERG-VEGA
[CLIENT]
🔴RED!, 🔴RED, [RED]
URGENT:
TASK:
```

---

*— Col Victoria "Iron Vic" Hale | COS | Thunderbird Wing*

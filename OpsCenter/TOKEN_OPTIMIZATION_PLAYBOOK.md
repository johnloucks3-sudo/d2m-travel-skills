# TOKEN OPTIMIZATION PLAYBOOK — Hale's Standard Operating Procedure
## Decision Framework for Max Efficiency, Min Waste

---

## PART 1: MODEL SELECTION MATRIX

### Task Classification → Model Decision

| Task Type | Characteristics | Model | Reason | Token Save |
|-----------|-----------------|-------|--------|-----------|
| **Formatting** | JSON, CSV, plain text conversion | Haiku | No reasoning needed | 60% |
| **Summarization** | Condense existing text/data | Haiku | Pattern matching only | 55% |
| **Data extraction** | Pull fields from structured content | Haiku | Rule-based, no judgment | 60% |
| **Classification** | Tag/label items (client sentiment, priority) | Haiku | Pattern recognition | 55% |
| **Simple routing** | Route task to correct person/system | Haiku | Decision tree | 60% |
| **Light analysis** | "What's the top 3?" "List pros/cons" | Haiku | Surface-level synthesis | 50% |
| **Routine writing** | Standard email, template-based | Haiku | Formulaic output | 55% |
| **—** | **—** | **—** | **—** | **—** |
| **Strategy** | Trade-off analysis, pricing, positioning | Sonnet | Judgment + nuance | Baseline |
| **Client-facing** | Email to customer, proposal copy | Sonnet | Voice + tone + trust | Baseline |
| **Synthesis** | Multi-source weighting, priority | Sonnet | Complex judgment | Baseline |
| **Problem-solving** | "How do we fix this?" | Sonnet | Creative reasoning | Baseline |
| **Voice matching** | Match Dani/Hale/Luna tone | Sonnet | Brand sensitivity | Baseline |
| **—** | **—** | **—** | **—** | **—** |
| **Arbitration** | Conflicting recommendations, final call | Opus | High-stakes decision | Cost justified |
| **Policy decision** | Sets precedent, affects multiple clients | Opus | Strategic impact | Cost justified |
| **Deep reasoning** | Needs 3+ layer analysis | Opus | Complexity justified | Cost justified |

---

## PART 2: CONTEXT REDUCTION TACTICS (Applied in Order)

### Apply these BEFORE dispatching to any model:

#### Tactic 1: Lazy Context Loading (30-50% savings)
```
DON'T: Send all context upfront
DO: Start with task only, add context if model asks
```
**Example:**
- ❌ "Here's client history [5K tokens] + current booking [2K] + task [200 tokens]"
- ✅ "Analyze this booking: [200 tokens]"
  - (if Claude asks for context, then send it)

#### Tactic 2: Compression on Entry (40-70% savings)
```
If task references large context (file, email, booking):
  1. Extract only relevant fields
  2. Remove redundant info
  3. Summarize old context to 1-2 sentences
```
**Example:**
- ❌ Full booking details (20 fields, 3K tokens)
- ✅ "Regent Grandeur, Dec 19–26, cabin 8224 (suite balcony), 4 guests, $28K total"

#### Tactic 3: Chunking by Relevance (20-40% savings)
```
If task has multiple phases:
  Phase 1: [Send task + minimal context]
  Phase 2: [Send next phase only, not Phase 1 again]
  Phase 3: [Ditto]
```
Don't re-send what's already in the conversation.

#### Tactic 4: Output Spec (20-60% savings)
```
Always specify output format and length:
  "Return as JSON, max 500 tokens"
  "List top 3 only (not all 10)"
  "One-sentence summary"
  "Bullet points, no explanation"
```

#### Tactic 5: Prompt Caching (Automatic in sessions)
```
In brains-lean interactive session:
  Message 1: Full context (costs normal)
  Message 2-100: Same context cached (costs 10% of original)
  
No extra work — just keep session alive.
```

#### Tactic 6: Stateless Batching (30-50% savings)
```
Instead of: Task A [context] + Task B [context] + Task C [context]

Do:
[Context for A & B]
Task A
Task B

[Context for C]
Task C
```

---

## PART 3: HALE'S DECISION ALGORITHM

### When a task arrives, Hale applies this logic:

```
1. ASSESS TASK TYPE
   → Is it formatting, summarization, extraction, classification?
   → YES → Use Haiku (unless client-facing, then Sonnet)
   → NO → Continue

2. ASSESS CONTEXT NEED
   → Does the task need client history? booking details? prior decisions?
   → If YES: Can I extract just the relevant 5% instead of full 100%?
   → YES → Compress to 300-500 tokens instead of 3K

3. ASSESS OUTPUT
   → What does the task actually need back?
   → Full 1000-token analysis? Or top 3 bullets?
   → Specify: "JSON format, 300 tokens max"

4. SELECT MODEL
   → Haiku for: formatting, summarization, extraction, simple routing
   → Sonnet for: strategy, client-facing, complex synthesis, voice-matched
   → Opus for: arbitration, policy, high-stakes judgment only

5. STRUCTURE DISPATCH
   → Can I lazy-load context? (ask model, add if needed)
   → Can I batch related tasks? (send once, not repeated)
   → Can I use session caching? (if staying in brains-lean)

6. EXECUTE & REPORT
   → Send optimized task
   → Track: model used, tokens saved vs unoptimized baseline
   → Learn: is this pattern repeating? Can I automate it?
```

---

## PART 4: COMMON PATTERNS & PRE-BUILT STRATEGIES

### Pattern 1: Client Email Draft
```
UNOPTIMIZED: 2000 tokens
  - Full client history [1000]
  - Booking details [400]
  - Prior emails [300]
  - Task [300]

OPTIMIZED: 800 tokens (60% savings)
  - Client name, cruise line, cabin category (50 tokens)
  - Key dates (20 tokens)
  - Tone: warm, professional (10 tokens)
  - Task: Draft itinerary email (100 tokens)
  - Output spec: 300-word, friendly, CTA to confirm receipt (20 tokens)
```

### Pattern 2: Routing Decision
```
UNOPTIMIZED: 1500 tokens (Sonnet)
  - Full task context
  - All available agents
  - Complex reasoning

OPTIMIZED: 200 tokens (Haiku)
  - Task type: "Route this to A2 or A8"
  - Rules: "A2 does research, A8 does recommendations"
  - Task: "New cruise search, needs cabin suggestions"
  - Output: "To: A8" (one line)
```

### Pattern 3: Summarization Chain
```
Day 1-3: Work in ONE session (context hot, cached)
Day 4: Ask Claude to summarize session so far (500 tokens)
Day 5+: Start fresh session, use summary as context (saves 80% vs full history)
```

### Pattern 4: Lazy Context Loading
```
INITIAL DISPATCH (100 tokens):
  "Analyze this booking for upsell opportunities"
  
Claude: "I need to see cabin category, guest budget, prior bookings..."

THEN SEND (only what's asked for, 200-300 tokens):
  "Suite balcony, $30K budget, booked 3 cruises, likes shore excursions"
  
TOTAL: 300-400 tokens vs. 2000+ if you'd sent everything upfront
```

---

## PART 5: WEEKLY TRACKING (For Learning)

| Task | Unoptimized Baseline | Optimized Cost | Savings | Model | Strategy Used |
|------|----------------------|-----------------|---------|-------|----------------|
| Client email draft | 2000 | 800 | 60% | Sonnet | Compression + spec |
| Routing decision | 1500 | 200 | 87% | Haiku | Pattern recognition |
| Ship research | 3000 | 1200 | 60% | Haiku | Extraction only |
| Strategic pricing | 2500 | 2500 | 0% | Sonnet | Needs full context |
| **WEEKLY TOTAL** | **15000** | **7000** | **53%** | — | — |

---

## PART 6: THE HALE DISPATCH CHECKLIST

Before sending ANY task, Hale asks herself:

- [ ] Is this formatting/summarization/extraction? → Use Haiku
- [ ] Can I compress context to <500 tokens? (vs. 3K+) → Do it
- [ ] Can I specify output length? (JSON, 3 bullets, one sentence) → Do it
- [ ] Do I need full context upfront, or can I lazy-load? → Lazy-load
- [ ] Can I batch this with similar tasks? → Batch it
- [ ] Am I keeping a session alive? → Use it (context cached)
- [ ] Is this client-facing? → Sonnet minimum
- [ ] Is this arbitration/policy? → Opus only
- [ ] Everything else → Sonnet (safe default)

**If I answer YES to 5+ of these, I'm at 50%+ savings.**

---

## IMPLEMENTATION

This playbook becomes:
1. **Hale's reference** — she consults this on every task
2. **Wired into her dispatch** — she assesses model + optimizations before calling `route_task()`
3. **Tracked weekly** — log every dispatch, learn which patterns repeat
4. **Automated over time** — patterns become pre-built, no decision needed

**Result: Same output quality, 40-60% token savings, under the 5-hour throttle.**

# SESSION BATCHING PLAYBOOK
## Reduce Sessions from 146/day → 70/day (Target: Save $25–35/month)

**Problem:** Each new session re-loads ~90K tokens of CLAUDE.md context cache. At 146 sessions/day, that's a massive waste.

**Solution:** Consolidate multi-turn work into single sessions using the batching patterns below.

---

## **Pattern 1: Multi-Turn Synthesis (Before → After)**

### ❌ CURRENT (Bad): 3 separate sessions
```
Session 1: "Draft the Kuklinski welcome email"
  → Waits for approval

Session 2: "Refine the Kuklinski email based on feedback"
  → Waits for approval

Session 3: "Convert email to HTML stationery"
  → Waits for delivery
```
**Cost:** 3 × 90K context reload = 270K wasted tokens

### ✅ BATCHED (Good): 1 session, 3 turns
```
Session 1:
  Turn 1: "Draft Kuklinski welcome email"
  Turn 2: [feedback arrives] "Refine per feedback: [list]"
  Turn 3: [approval] "Convert to HTML stationery for deployment"
```
**Cost:** 1 × 90K = 90K tokens saved

**When to batch:**
- All turns are related to the same deliverable
- Feedback/approval happens same day
- Total wall-clock time < 30 minutes

---

## **Pattern 2: Research → Decision → Action**

### ❌ CURRENT (3 sessions)
```
Session 1: Research ship options for McLeod cruise
Session 2: Compare pricing and make recommendation
Session 3: Draft the recommendation email to client
```

### ✅ BATCHED (1 session, 3 turns)
```
Session 1:
  Turn 1: "Research 4 premium cruise options for McLeod Grandeur Aug 19–26"
  Turn 2: [compare prices] "Analyze pricing vs experience; recommend top 2"
  Turn 3: [approval] "Draft McLeod email with pricing and rationale"
```

---

## **Pattern 3: Operational Batch (Triage + Dispatch)**

### ❌ CURRENT (Scattered sessions throughout day)
```
Session 1: Check mail, extract client questions
Session 2: Scan dossiers for context
Session 3: Route to appropriate staff member
Session 4: Draft response template
Session 5: Get approval, send
```

### ✅ BATCHED (1 session, do all 5 in sequence)
```
Session 1 [10 min batch]:
  Turn 1: "Triage inbox — extract 5 client action items"
  Turn 2: "Check dossiers [files]; create routing tickets"
  Turn 3: "Draft response templates"
  Turn 4: [approval] "Package for team dispatch"
```

---

## **Batching Rules of Engagement**

| Rule | Example |
|------|---------|
| **Batch if:** All turns serve one deliverable | ✅ All 3 turns = 1 client email |
| **Batch if:** Feedback loop closes same day | ✅ Draft → approve → final in 2 hours |
| **Batch if:** Related tasks, same domain | ✅ Email + followup + FYI are all client comms |
| **DON'T batch if:** Waiting >4 hours between turns | ❌ Draft email, wait till tomorrow for feedback → use /resume instead |
| **DON'T batch if:** Different people's work | ❌ Your draft, Dani's voice pass, Naia's brand check → 3 sessions OK |
| **DON'T batch if:** Context exceeds 20K tokens | ❌ Large files + long prompt → keep separate |

---

## **Weekly Batching Target**

**Current:** 146 sessions/day × 7 = 1,022 sessions/week  
**Target:** 70 sessions/day × 7 = 490 sessions/week  
**Savings:** 532 sessions/week × 90K tokens = 47.9M tokens/week = **~$25–35/month**

---

## **Implementation Checklist**

- [ ] Identify 5 recurring tasks that spawn 2–3 sessions (examples: draft → approve → send, research → decide → action)
- [ ] Create batch templates for each (capture the turn sequence)
- [ ] Train team: when to batch, when not to
- [ ] Log batch sessions with tag `[BATCH-N]` in session name (e.g., "Kuklinski-email-[BATCH-3]")
- [ ] Measure: track sessions/day for 2 weeks, report % reduction vs baseline

---

## **The Payoff**

- **Token savings:** $25–35/month
- **Speed:** Some workflows actually get *faster* (no re-load delays)
- **Quality:** Fewer context switches → more coherent output

Start with one pattern. Get team comfortable. Expand from there.

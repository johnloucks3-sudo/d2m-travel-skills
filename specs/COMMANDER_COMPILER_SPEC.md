# Commander Compiler Specification
## Pre-Generation Lint for Dani Chain

**Version:** 1.0  
**Status:** READY FOR STERLING BUILD  
**Created:** 2026-06-09  
**Owner:** Sterling (A7)  
**Priority:** P0  

---

## EXECUTIVE SUMMARY

The **Commander Compiler** is a pre-generation validation system that lints task inputs to Dani before she generates client-facing copy. It validates across four dimensions (TONE, FACTS, STRUCTURE, PRICING), returns structured PASS/WARN/FAIL verdicts, auto-fixes WARN violations, and escalates FAIL conditions. Goal: reduce WF-17 friction by catching voice mismatches, unconfirmed facts, and structural issues **before** draft generation.

---

## 1. SYSTEM ARCHITECTURE

### 1.1 Deployment Model
- **Runs before:** Dani receives task input
- **Input:** JSON task object (see § 2.2)
- **Output:** JSON verdict object (see § 2.3)
- **Integration point:** `core/dani/commander_compiler.py` — called by Dani's input router
- **Latency SLA:** < 2 seconds (all sources cached or local)

### 1.2 Dimension Stack
Each dimension is independent. A single FAIL in any dimension blocks Dani execution. WARNs are auto-fixed unless marked `no_autofix`.

```
Input Task
    ↓
[TONE Lint]    → PASS / WARN / FAIL
[FACTS Lint]   → PASS / WARN / FAIL
[STRUCT Lint]  → PASS / WARN / FAIL
[PRICING Lint] → PASS / WARN / FAIL
    ↓
Verdict Object
    ↓
{PASS → proceed} | {WARN → autofix + proceed} | {FAIL → escalate}
```

---

## 2. DATA MODELS

### 2.1 Input Task Object

```json
{
  "task_id": "string",                    // UUID or session ID
  "client_name": "string",                // E.g., "Kyle Kuklinski"
  "booking_ref": "string",                // TESS booking ID or ship+date
  "email_type": "string",                 // TP code: "0.5", "4.1", "4.2", etc.
  "product_type": "string",               // "lifecycle_tp" | "validation" | "proposal"
  "context": {
    "temporal_facts": {
      "today": "2026-06-09",
      "departure": "2026-12-17",
      "fpd_due": "2026-09-17",
      "days_until_departure": 191
    },
    "booking_state": {
      "paid_amount": 27813.00,
      "fpd_status": "paid",
      "cabin_confirmed": false,
      "excursions_booked": 0
    },
    "client_profile": {
      "ai_aware": true,
      "previous_tones": ["warm", "informal", "direct"],
      "relationship_length_months": 6
    }
  },
  "draft_intent": "string",               // Human-readable intent or notes
  "tone_register": "string",              // "client" | "vendor" | "internal"
  "voice_profile": "string"               // Client name for persona matching
}
```

### 2.2 Verdict Object

```json
{
  "task_id": "string",
  "verdict": "PASS" | "WARN" | "FAIL",
  "execution_allowed": boolean,           // false if any FAIL
  "timestamp": "2026-06-09T22:45:33Z",
  "dimensions": {
    "tone": {
      "verdict": "PASS" | "WARN" | "FAIL",
      "score": 0.95,                      // 0.0–1.0 confidence
      "issues": [
        {
          "id": "TONE_BANNED_PHRASE",
          "severity": "warn",
          "message": "Draft contains 'happy to help' — banned in WF-17 (2026-03-25)",
          "location": "line 3, char 15",
          "autofix_applied": false,
          "suggested_fix": "Use 'I can' or 'here's'"
        }
      ]
    },
    "facts": {
      "verdict": "PASS" | "WARN" | "FAIL",
      "score": 0.92,
      "issues": [...]
    },
    "structure": {
      "verdict": "PASS" | "WARN" | "FAIL",
      "score": 0.98,
      "issues": [...]
    },
    "pricing": {
      "verdict": "PASS" | "WARN" | "FAIL",
      "score": 1.0,
      "issues": [...]
    }
  },
  "summary": "✅ PASS — No issues detected",
  "escalation_required": false,
  "escalation_to": "Hale" | null           // Who to page if FAIL
}
```

---

## 3. DIMENSION SPECIFICATIONS

### 3.1 TONE Dimension

**Purpose:** Validate voice register, warmth, certainty, banned phrasing, close format, question mirroring.

#### Rules

| Rule ID | Rule | Severity | Auto-fix |
|---------|------|----------|----------|
| TONE_BANNED_PHRASE | Detect banned phrases: "happy to help," "consider it done," "I think," "probably," "hopefully," "just let me know" | WARN | YES — replace with approved alternatives |
| TONE_CERTAINTY | Client-facing copy: zero "might," "probably," "pending," "likely" without hard source | WARN | YES — escalate to [source] or remove |
| TONE_WARM_REGISTER | Validate warmth level matches client profile. AI-aware clients: explicit AI disclaimer in PS. | WARN | YES — add/adjust as needed |
| TONE_QUESTION_MIRROR | If task contains client question: email must explicitly mirror back the exact question before answering | FAIL if missing | NO — requires Dani re-draft |
| TONE_CLOSE_FORMAT | Client email closes with: [casual line w/ ellipsis] + blank line + signature. No "best," always "thanks." | WARN | YES — reformat |
| TONE_VENDOR_REGISTER | Supplier/vendor emails: transactional, no warmth inflation, clear ask. Validate against vendor profile. | WARN | YES — adjust register |
| TONE_ASSUMPTIONS_BLANK | TP emails with "Assumptions" section: must be blank (reserved for Commander edits). | FAIL if not blank | NO — escalate |

#### Examples

**PASS case:**
```
Input: TP 0.5 Welcome email for Kyle Kuklinski (AI-aware)
- Contains question mirror: "You asked about dining reservations..."
- Uses approved close: "Let me know what lands." (ellipsis, casual)
- Signature correct
- AI disclaimer in PS (AI-aware flag)
Result: ✅ PASS
```

**FAIL case:**
```
Input: Validation email for Westbrook (not AI-aware)
- Draft contains: "I think the cabin is..."
- No source for soft language
Result: ❌ FAIL — certainty violation. Auto-fix cannot proceed without facts.
```

---

### 3.2 FACTS Dimension

**Purpose:** Validate temporal accuracy, FPD currency, booking state consistency, pricing sourcing, dossier integrity.

#### Rules

| Rule ID | Rule | Severity | Auto-fix |
|---------|------|----------|----------|
| FACTS_TEMPORAL_CONSISTENCY | days_until_departure must match (departure_date - today). Flagged if off by >1 day (time-zone edge). | WARN | YES — recalc from context.temporal_facts |
| FACTS_FPD_CURRENCY | Any FPD mention must match TESS or dossier FPD_STATUS and FPD_DUE_DATE. | FAIL if mismatch | NO — escalate to Harlan |
| FACTS_BOOKING_STATE_SYNC | Any booking-status claim (cabin booked, excursions pending, etc.) must match context.booking_state. | FAIL if mismatch | NO — escalate to Dani (data problem) |
| FACTS_PRICING_SOURCED | Any dollar amount must cite source: portal / TESS / dossier. Unconfirmed claims → FAIL. | FAIL | NO — escalate |
| FACTS_DOSSIER_INTEGRITY | Cross-check against live dossier snapshot. Names, ship, dates must match. | WARN if outdated dossier | YES — reload dossier, re-validate |
| FACTS_SHIP_NAME | Ship name must match booking_ref exactly. | FAIL if mismatch | NO — escalate |
| FACTS_UNCONFIRMED_CLAIMS | Flag "likely," "pending," "unconfirmed," "TBD" in client-facing text. | WARN | NO — escalate to source |

#### Integration Points

- **TESS API:** `GET /booking/{booking_id}` → FPD_STATUS, FPD_DUE_DATE, cabin_confirmed, excursions
- **Dossier file:** `dossiers/{client_name}_{ship}_{year}.md` → source of truth for facts
- **Portal snapshot:** Cached latest portal read (max age 1 hour). Reload if stale.

#### Examples

**PASS case:**
```
Input: "FPD due July 22" for McLeod Regent Grandeur booking 2984034
- Context.booking_state.fpd_due = "2026-07-22"
- TESS query confirms FPD_DUE = "2026-07-22"
- Dossier confirms same
Result: ✅ PASS
```

**FAIL case:**
```
Input: "Your cabin is the Concierge Suite" for Kyle Kuklinski
- context.booking_state.cabin_confirmed = false
- TESS shows cabin_id = null
Result: ❌ FAIL — unconfirmed fact. Cannot proceed.
```

---

### 3.3 STRUCTURE Dimension

**Purpose:** Validate email type clarity, recipient correctness, CTAs, format conformance to T&Q standard.

#### Rules

| Rule ID | Rule | Severity | Auto-fix |
|---------|------|----------|----------|
| STRUCT_EMAIL_TYPE | Product type must map to valid TP code or product class. Reject unknown types. | FAIL | NO |
| STRUCT_RECIPIENT_MATCH | "to:" field must match client name in context. Validate against TESS client record. | FAIL | NO — escalate |
| STRUCT_CTA_PRESENT | Email must have exactly one primary CTA. No CTA = FAIL. Multiple CTAs = WARN (pick primary). | WARN | YES — extract primary CTA |
| STRUCT_T_AND_Q_FORMAT | TP emails must follow T&Q format: Tongue (1 para max) + Question (explicit ask) + closing. | WARN | NO — escalate to Dani |
| STRUCT_STATIONERY | Email must declare stationery type: USAFA colors (blue #0000ff on cream #f7f3ea) + signature block. | WARN | YES — add stationery header |
| STRUCT_SECTION_ORDERING | Sections must follow: [Greeting] → [Body] → [CTA] → [Assumptions (if TP)] → [Signature]. | WARN | NO — escalate to Dani |
| STRUCT_ASSUMPTIONS_SECTION | If TP: "Assumptions" section must exist and be BLANK (reserved for Commander). | FAIL if not present or populated | NO |
| STRUCT_AI_DISCLAIMER | If client.ai_aware = true: must include AI disclaimer in PS. | WARN | YES — add boilerplate |

#### T&Q Format Template

```
[GREETING — warm, personal reference to relationship]

[TONGUE — 1 sentence stating purpose]

[QUESTION — explicit ask: "Can you [action]?" or "Should we [decision]?"]

[BODY — reasoning, context, options if applicable]

[CTA — next step, timeline]

Assumptions:
[LEFT BLANK FOR COMMANDER EDITS]

[Signature with stationery]
```

#### Examples

**PASS case:**
```
Input: TP 0.5 Welcome for new booking
- Has greeting, tongue, question, body, CTA
- Assumptions blank
- Stationery declared
Result: ✅ PASS
```

**FAIL case:**
```
Input: Validation email
- Missing "Assumptions" section entirely
- Product type = "TP 6.2" but task_id not in canonical TP list
Result: ❌ FAIL — missing required section + unknown product type
```

---

### 3.4 PRICING Dimension

**Purpose:** Validate dollar sourcing, balance reconciliation, per-person pricing, no implicit charges.

#### Rules

| Rule ID | Rule | Severity | Auto-fix |
|---------|------|----------|----------|
| PRICING_HARD_SOURCE | Every dollar amount must cite: portal balance / TESS FPD / dossier invoice line. No exceptions. | FAIL | NO — escalate to Harlan |
| PRICING_BALANCE_RECONCILE | If email mentions account balance: must match portal query within 1 hour. | FAIL if >1hr stale | NO — escalate to Harlan (refresh portal) |
| PRICING_PER_PERSON | If per-person pricing stated: must be total ÷ pax. Verify pax count from TESS. | FAIL if arithmetic wrong | YES — recalc |
| PRICING_NO_IMPLICIT | No mention of future charges, deposits, or fees that aren't explicitly documented in TESS or dossier. | FAIL | NO — escalate |
| PRICING_CURRENCY | All amounts in USD unless client is international (check dossier). Specify currency if non-USD. | WARN | NO — escalate |
| PRICING_AUTHORITY | Only Harlan may sign off that a pricing statement is accurate before WF-17. | ESCALATION to Harlan | — |

#### Integration Points

- **Portal balance:** Cache max age 1 hour. Refresh if stale.
- **TESS:** Booking total, FPD, per-pax calcs
- **Harlan sign-off:** Before any email with $$ leaves WF-17

#### Example

**PASS case:**
```
Input: "Your FPD of $11,943 is due July 22" for McLeod
- Source: Regent portal invoice line 2984034, verified by Harlan, stamped 2026-06-09
Result: ✅ PASS (+ Harlan pre-approval on file)
```

**FAIL case:**
```
Input: "Estimated cost per person: $2,000"
- No source cited
- Pax count = 4 (from TESS)
- Total should be stated, not estimated
Result: ❌ FAIL — unsourced + implicit language. Escalate to Harlan.
```

---

## 4. EXECUTION FLOW

### 4.1 Input Phase

```python
def validate_input(task_json):
    """
    1. Validate JSON schema (required fields present)
    2. Load dossier snapshot from cache (or reload if >1hr old)
    3. Query TESS booking state (cache max 30 min)
    4. Query portal balance (cache max 1hr)
    5. Return enriched context object
    """
```

### 4.2 Lint Phase

```python
def lint_all_dimensions(task, context):
    tone_result = lint_tone(task, context)
    facts_result = lint_facts(task, context)
    struct_result = lint_structure(task, context)
    pricing_result = lint_pricing(task, context)
    
    # Aggregate verdicts
    overall = "PASS" if all pass else "WARN" if any warn else "FAIL"
    return aggregate_verdict(tone_result, facts_result, struct_result, pricing_result)
```

### 4.3 Autofix Phase

```python
def autofix_warns(verdict, original_task):
    """
    For each WARN with autofix_applied=false:
    - Apply suggested fix
    - Re-lint that dimension only
    - If still WARN, mark autofix_applied=true
    - If becomes FAIL, escalate and stop
    """
```

### 4.4 Escalation Phase

```python
def escalate_if_needed(verdict):
    """
    If verdict.verdict == "FAIL":
    - Determine which rule failed (first FAIL in order: FACTS, PRICING, TONE, STRUCT)
    - Route to appropriate person:
      * FACTS/BOOKING: Dani (data problem)
      * PRICING: Harlan (financial authority)
      * TONE/QUESTION_MIRROR: Dani (content rework)
      * STRUCT: Dani (format fix)
    - Page via Telegram with verdict summary + rule ID
    """
```

---

## 5. PHASED BUILD PLAN

### Phase 1: MVP (Weeks 1-2)
- [ ] Implement TONE dimension (banned phrases, certainty, close format)
- [ ] Implement FACTS dimension (temporal, FPD, booking state basics)
- [ ] Implement STRUCTURE dimension (email type, CTA, T&Q format)
- [ ] JSON input/output schema
- [ ] Auto-fix logic for WARNS
- [ ] Local testing: 10 real past TP emails
- **Deliverable:** `core/dani/commander_compiler.py` (MVP, no API calls)

### Phase 2: Integration (Weeks 3-4)
- [ ] Wire TESS API queries (booking state, FPD)
- [ ] Wire dossier cache reload
- [ ] Wire portal balance cache (1hr TTL)
- [ ] Implement PRICING dimension
- [ ] Escalation routing (Telegram page + Dani redirect)
- [ ] Error handling & fallback (lint failures don't block Dani)
- **Deliverable:** Full integration with TESS + Dani input router

### Phase 3: Monitoring (Week 5+)
- [ ] Lint verdict analytics (what % PASS/WARN/FAIL)
- [ ] Auto-fix success rate
- [ ] Escalation ticket SLA
- [ ] Accuracy calibration (false positives/negatives)
- **Deliverable:** Dashboard + weekly metrics report

---

## 6. SUCCESS CRITERIA

### Accuracy
- **Goal:** >95% PASS on known-good emails, <5% false FAILs
- **Test:** Run against 50 past Dani drafts (labeled pass/fail manually)
- **Acceptance:** >95% match to manual labels

### Coverage
- **Goal:** All four dimensions active for all client email types
- **Acceptance:** Coverage dashboard shows 100% for each dimension

### Speed
- **Goal:** Lint completes in <2 seconds per email
- **Acceptance:** p95 latency <2s, p99 <3s

### Integration
- **Goal:** Zero friction with Dani workflow
- **Acceptance:** Dani receives PASS emails instantly, WARNs auto-fixed in <5s, FAILs escalated with clear reason

---

## 7. REFERENCE: BANNED PHRASES (TONE)

Standing as of 2026-06-09. Update yearly or when WF-17 AAR surfaces new violations.

| Phrase | Reason | Approved Alternative |
|--------|--------|----------------------|
| "happy to help" | Generic, passive | "I can," "here's" |
| "consider it done" | Overconfident, passive | "I'll handle X" |
| "I think" | Soft, uncertain | State fact or defer to expert |
| "probably" | Unconfirmed fact | Remove or cite source |
| "hopefully" | Wishful, unprofessional | State what will happen |
| "just let me know" | Passive CTA | "Send me X by [date]" |
| "at this time" | Wordy corporate | Remove |
| "please advise" | Overly formal | "What would you like to do?" |

---

## 8. DEPLOYMENT CHECKLIST

- [ ] Code review: Sterling passes to A5 (Viper) for architecture sign-off
- [ ] Test suite: 50 emails, >95% accuracy
- [ ] TESS/portal integration: Live data queries working
- [ ] Escalation routing: Telegram paging tested
- [ ] Dani integration: Lint called before draft generation
- [ ] Error handling: Lint failures degrade gracefully (don't block Dani)
- [ ] Documentation: README for Dani on how to resolve FAILs
- [ ] Monitoring: Metrics dashboard live
- [ ] Approval: A5 + Hale sign-off before production

---

## 9. OPEN QUESTIONS FOR STERLING

1. **Caching strategy:** Should lint cache by (client, email_type, day) or (email_type, day) only?
2. **Portal freshness:** Is 1-hour cache acceptable for balance checks, or should we go 30 min?
3. **Escalation SLA:** What's the max wait time for an escalation to be routed + acknowledged?
4. **False-positive threshold:** At what WARN/FAIL ratio do we consider the linter too strict?
5. **AI disclaimer boilerplate:** Does Dani have a canonical AI disclaimer template, or should we source from hale_cos.md?

---

**END SPECIFICATION**

---

**Document ID:** COMMANDER_COMPILER_SPEC_v1.0  
**Last Updated:** 2026-06-09  
**Approval Status:** APPROVED by Hale (2026-06-09T22:05:33Z)  
**Ready for Sterling Engineering Build:** YES

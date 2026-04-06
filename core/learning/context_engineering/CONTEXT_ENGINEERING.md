# Context Engineering — D2M Thunderbird OS
## Standing Reference · Col Hale · 23 MAR 2026

---

## What Context Engineering Is

**Prompt Engineering** = writing instructions to the model.
**Context Engineering** = architecting what you *give* the model before it writes.

The shift: stop asking "how do I instruct Claude to write better?"
Start asking: "What does Claude need to *know* to write correctly on the first pass?"

The model is not an instruction-follower. It is a pattern-completer.
Give it the right context — rich, structured, real — and it completes the pattern correctly.
Give it vague instructions — and it completes the pattern generically.

**D2M standard:** Every client-facing document is generated from a context pack, not a prompt.

---

## The Five Context Layers

Every D2M context pack must include all five:

| Layer | What it contains | Where it lives |
|-------|-----------------|----------------|
| **1. Client Profile** | Name, tier, relationship depth, style, special notes | Dossier |
| **2. Trip/Booking Facts** | Confirmed dates, suppliers, PNRs, rates, payment status | TESS + Dossier |
| **3. Voice Examples** | 5+ real Commander emails, tier-matched, score-ranked | `config/voice_examples.json` |
| **4. Learning Principles** | Extracted edit rules from prior corrections | `config/learning_principles.json` |
| **5. Brand & Tone Controls** | D2M standards, stationery, sign-off, narrative style | `CLAUDE.md` + Templates |

Missing any layer → first-pass quality degrades → Commander has to edit → we waste time.

---

## The Four Document Types

### 1. Proposal
**Purpose:** Sell the trip before it's booked.
**Context pack:** `ProposalContextPack`
**Critical layers:** Voice examples (client relationship tone) + hotel options + pricing

### 2. Itinerary
**Purpose:** Build anticipation; give clients a complete day-by-day narrative.
**Context pack:** `ItineraryContextPack`
**Critical layers:** All confirmed bookings + day plans + logistics

### 3. Trip Validation
**Purpose:** Pre-departure checklist. Surface gaps. Confirm all is green.
**Context pack:** `TripValidationContextPack`
**Critical layers:** All booking facts + payment status + action items

### 4. Email
**Purpose:** Client communication — any occasion.
**Context pack:** `EmailContextPack`
**Critical layers:** Voice examples (5+) + learning principles + prior thread + single CTA

---

## The Document Workflow (MD → Drive → Google Doc → Final)

Wired 23 MAR 2026. Standard for ALL client documents:

```
1. THUNDERBIRD generates draft as .md
   ↓
2. COS saves .md to Google Drive → /D2M Trip Dossiers/[ClientName]/
   ↓
3. Telegram Commander: "Draft ready: [link]"
   ↓
4. Commander opens Google Doc, makes edits directly
   ↓
5. COS monitors Drive for changes → detects edit → captures diff
   ↓
6. Learning Compiler extracts principles → injects into learning_principles.json
   ↓
7. COS formats final version → PDF (WeasyPrint) or HTML for client delivery
   ↓
8. Client delivery: Gmail stationery (d2mconcierge) or Telegram (Dani bot)
```

**Benefits:**
- Commander edits in his normal environment (Google Docs)
- Every edit is captured and turned into a learning principle
- Next similar document is better before he sees it

---

## System Prompt Architecture (Context → Model)

When calling Claude for any document, the system prompt must include:

```
== CLIENT ==
[ClientProfile fields]

== COMMANDER'S ACTUAL VOICE ==
[5 tier-matched VoiceExamples from voice_examples.json]

== EDIT PRINCIPLES ==
[Matching LearningPrinciples from learning_principles.json]

== TRIP/BOOKING FACTS ==
[All BookingFacts relevant to this document]

== TONE ==
[tone_directive from the context pack]

== BRAND RULES ==
[D2M standards: name, sign-off, stationery]
```

**Note:** The `build_system_prompt()` function in `context_packs.py` handles assembly automatically.

---

## Key Vocabulary (from the field)

| Term | Meaning | D2M Application |
|------|---------|----------------|
| **Context pack** | Structured bundle of everything the model needs | ProposalContextPack, EmailContextPack, etc. |
| **Few-shot examples** | Real examples that teach style/tone | Voice examples from voice_examples.json |
| **RAG** | Retrieval-Augmented Generation — pull live data into context | Pulling dossier/TESS data before each call |
| **Grounding** | Anchoring output to real facts | Booking facts, confirmed dates, real prices |
| **Context window** | Total tokens the model can see at once | Budget: ~500 tokens/doc; manage with excerpts |
| **Working memory** | What's in the current context window | The assembled context pack per call |
| **System prompt** | Standing instructions at the top of every call | Brand rules + voice + tone + persona |
| **Structured output** | Model responds in a schema (JSON, dataclass) | ProposalContext fields → template render |
| **Diff** | Delta between generated and sent versions | Captured by Learning Compiler → learning_principles |
| **Constitutional AI** | Rules the model must follow regardless | Brand rules: never "Love Group Travel", never "Best" |

---

## Principles for Document Generation Quality

1. **Ground every document in real facts.** Dates, names, prices from TESS/dossier — never let the model hallucinate booking details.

2. **Voice examples are not optional.** Without them, Claude defaults to generic AI voice. With 5 tier-matched real emails, it writes like John.

3. **Learning principles compound.** Each Commander edit that gets captured makes the next draft better. The goal is zero corrections within 90 days.

4. **Tone directive is the rudder.** One clear sentence ("warm, unhurried, evocative — Dani voice, not corporate") beats a page of instructions.

5. **Proposals are narratives, not brochures.** The model must know the *relationship* to write the right narrative. A friend-tier proposal reads like a personal letter, not a sales document.

6. **Shorter is harder to write than longer.** The model defaults to verbose. Tone directives should explicitly request brevity when that's the Commander's style for that tier.

---

## Files

| File | Purpose |
|------|---------|
| `context_packs.py` | Python dataclasses for all 4 doc types + system prompt builder |
| `CONTEXT_ENGINEERING.md` | This reference document |
| `../config/voice_examples.json` | 795 real Commander emails, scored and tiered |
| `../config/learning_principles.json` | Extracted edit principles (grows over time) |
| `../templates/d2m_proposal_schema.py` | Proposal → HTML/PDF renderer |
| `../templates/dani_proposal.html.j2` | Proposal Jinja2 template |
| `../templates/dani_validation_email.html.j2` | Email stationery template |

---

---

## Claude Cowork Integration (Week 3 · 23 MAR 2026)

**What Cowork is:** Claude Desktop's agentic workspace mode — reads/writes local files,
executes multi-step tasks autonomously, works with your actual folder structure.

**D2M Integration Point:** Point Cowork at `~/Thunderbird/` as its working folder.
Claude can then read dossiers, pull voice examples, and write draft documents
directly into `~/Thunderbird/drafts/[ClientName]/` — without copy-paste.

### How to Use Cowork for D2M Documents

1. Open Claude Desktop (macOS or Windows — Cowork is desktop-only)
2. In Settings → Cowork, set working folder to `~/Thunderbird/`
3. Prompt: *"Draft a proposal for [Client] using their dossier at dossiers/[file].md and voice examples from config/voice_examples.json"*
4. Cowork reads the dossier + voice file → writes draft to `drafts/[Client]/proposal_draft.md`
5. COS detects new file → Telegram alert → Commander edits in Google Doc
6. `capture_edit_diff` MCP tool captures the delta → learning_principles.json grows

### Cowork Download Links

| Platform | Link |
|----------|------|
| **macOS** | [Download DMG](https://claude.ai/api/desktop/darwin/universal/dmg/latest/redirect) |
| **Windows** | [Download EXE](https://downloads.claude.ai/releases/win32/ClaudeSetup.exe) |
| **Product page** | [claude.com/product/cowork](https://claude.com/product/cowork) |
| **iOS (phone)** | [App Store](https://apps.apple.com/us/app/claude-by-anthropic/id6473753684) ← Cowork NOT on mobile |
| **Android** | [Google Play](https://play.google.com/store/apps/details?id=com.anthropic.claude) ← Cowork NOT on mobile |

> ⚠️ **Cowork is desktop-only.** The phone app (iOS/Android) is Claude's standard mobile
> interface — useful for quick queries but does NOT have Cowork file access.
> Available on all paid plans (Pro $20/mo, Max $100-200/mo, Team/Enterprise).

### Cowork vs. MCP Server (When to Use Which)

| Task | Use |
|------|-----|
| Draft a proposal from a dossier (autonomous, multi-file) | Cowork on desktop |
| Create Gmail draft via API (MCP pipeline) | `draft_client_email` tool |
| Load context pack for AI drafting | `load_context_pack` tool |
| Capture Commander's edit as a learning principle | `capture_edit_diff` tool |
| Generate hotel guide PDF | `render_hotel_guide_pdf` tool |

---

*Context Engineering is how the Wing learns to think before it writes.*
*Every document is a test. Every edit is a lesson. Every lesson compounds.*
— Col Hale, 23 MAR 2026

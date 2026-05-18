# HALE SEAMLESS COMMS ARCHITECTURE — PLAN v1
## Email · Telegram · Signal | AI-Classified Routing | OpenCode Engine
**Author:** Hale-CC | **Date:** 2026-05-18 | **Status:** DRAFT — Commander Review Required
**Exercise tier:** T2 (multi-domain, Hale fills charter)

---

## PROBLEM STATEMENT

Hale currently answers on Telegram reliably but incompletely. Email C2 was built but the reply gap was never closed (n8n ETB 001 polls but never replies). Signal does not exist. The result: Commander has to know which channel works today, rather than just talking to Hale.

**Goal:** Commander speaks to Hale on any of three channels. Hale responds on the same channel, with the right format, from the right brain, within SLA. Channel choice is Commander's preference, not a technical constraint.

---

## CURRENT STATE ASSESSMENT

### Email C2 — PARTIAL (gap: no reply)
| Component | Status |
|-----------|--------|
| n8n ETB 001 poll (d2m-ai-process label, 5 min) | ✅ Running |
| Activation word detection (COS/COO/Vic/Hale) | ✅ Working |
| Email → OpenCode task dispatch | ✅ Working |
| Reply back into Gmail thread | ❌ DEAD — never implemented |
| Thread-aware conversation context | ❌ Missing |
| T&Q format response | ❌ Missing |
| Wing stationery in reply | ❌ Missing |

**Root cause:** `gmail_send_from_wing()` exists (`thunderbird_gmail.py:2154`) but not in TOOL_REGISTRY and has no thread-aware variant. n8n processes the email then drops the result.

### Telegram — LIVE but rough
| Component | Status |
|-----------|--------|
| D2MC2C bot (Hale/Claude) | ✅ Live |
| d2m_dani_bot (Dani) | ✅ Live |
| Routing by bot token | ✅ Working |
| Message formatting (markdown) | ⚠️ Raw XML bleeds through sometimes |
| Stateful conversation context | ⚠️ Partial — no ConversationBridge |
| 4096-char limit handling | ⚠️ Truncation, no chunking |

### Signal — NOT BUILT
| Component | Status |
|-----------|--------|
| Signal CLI / bot | ❌ Does not exist |
| Signal → Hale routing | ❌ Does not exist |
| Signal ↔ other channel relay | ❌ Does not exist |

---

## PROPOSED ARCHITECTURE

```
Commander
  │
  ├── Email (Gmail)          ──► HALE EMAIL GATEWAY
  ├── Telegram (@D2MC2C_bot) ──► HALE TELEGRAM GATEWAY  
  └── Signal                 ──► HALE SIGNAL GATEWAY
              │
              ▼
    ┌─────────────────────────────┐
    │   UNIFIED CLASSIFIER        │  ← OpenCode (DeepSeek ZEN, $0)
    │   (runs on every message)   │
    │                             │
    │  Classifies:                │
    │  • Intent: task | chat |    │
    │    intel | client | urgent  │
    │  • Brain: haiku | sonnet |  │
    │    opus | self              │
    │  • Persona: Hale | Dani     │
    │  • Format: T&Q | plain |    │
    │    stationery               │
    │  • Priority: P0-P3          │
    └───────────┬─────────────────┘
                │
                ▼
    ┌─────────────────────────────┐
    │   BRAIN DISPATCH            │
    │   (OpenCode routes)         │
    │                             │
    │  Haiku → fast/classify/ops  │
    │  Sonnet → reasoning/copy    │
    │  Opus → Commander-level     │
    │  Self → OpenCode handles    │
    └───────────┬─────────────────┘
                │
                ▼
    ┌─────────────────────────────┐
    │   REPLY ENGINE              │
    │   (channel-aware)           │
    │                             │
    │  Email → thread reply +     │
    │          stationery + T&Q   │
    │  Telegram → markdown chunks │
    │  Signal → plain + emoji     │
    └─────────────────────────────┘
```

---

## CLASSIFICATION RULES (AI-driven, Commander can override)

| Signal | Intent | Brain | Format | SLA |
|--------|--------|-------|--------|-----|
| "OPUS:" prefix | Commander-level | Opus | T&Q Background Paper | 5 min |
| Question mark, short | Chat/clarification | Haiku | 2-3 sentence plain | 30 sec |
| Task keywords (task, build, fix, draft, analyze) | Task | Sonnet | T&Q Talking Paper | 2 min |
| Client name mentioned | Client action | Sonnet | Stationery draft (WF-17) | 2 min |
| "URGENT" / "P0" | Urgent | Opus | Immediate plain + follow-up | 60 sec |
| No clear signal | Default | OpenCode self | T&Q short | 2 min |

**Override:** Any message with `OPUS:`, `SONNET:`, `HAIKU:` prefix forces that brain.

---

## IMPLEMENTATION PLAN — 4 PHASES

### PHASE 1 — Email Reply Gap (P0 — close the standing gap)
**Engine:** OpenCode
**Effort:** ~4 hours

1. Add `gmail_thread_reply()` to `core/email/thunderbird_gmail.py` — thread-aware reply using `In-Reply-To` + `References` headers
2. Add to TOOL_REGISTRY so OpenCode can call it
3. Extend n8n ETB 001: after classifier runs, call `gmail_thread_reply()` with response
4. Apply wing stationery (`_wrap_body_html()`) to email replies
5. Test: Commander sends "Hale, what's on the mission board?" → reply in same thread within 2 min

**Success signal:** Commander gets a stationery reply in the same Gmail thread.

---

### PHASE 2 — Telegram Polish (P1 — fix the rough edges)
**Engine:** OpenCode
**Effort:** ~2 hours

1. Add chunking to Telegram responses — split at 4096 chars on paragraph boundary, not mid-sentence
2. Strip raw XML tags from output before sending (`[use_mcp_tool]`, `[bash]` etc.)
3. Add ConversationBridge — 20-message rolling context window per chat_id, stored in `OpsCenter/hale_chat_log.jsonl`
4. Enforce T&Q format: short answers = bullets, long = Bullet Talking Paper header

**Success signal:** 10-message back-and-forth with Hale on Telegram with no formatting artifacts.

---

### PHASE 3 — Signal Integration (P2 — new channel)
**Engine:** OpenCode
**Effort:** ~6 hours

**Signal protocol options (Commander decides):**

| Option | Method | Cost | Complexity | Reliability |
|--------|--------|------|------------|-------------|
| A | signal-cli (Java, local) | $0 | High — requires linked device | High once set up |
| B | Maytapi Signal API | ~$10/mo | Low — REST API | High |
| C | signal-cli Docker on YOGA | $0 | Medium | High |

**Recommended: Option C** — signal-cli in Docker on YOGA. $0, no external dependency, Commander links device once.

**Implementation:**
1. Deploy signal-cli Docker on YOGA (192.168.1.198)
2. Link Commander's Signal number
3. Build `thunderbird_signal_gw.py` — polls signal-cli for new messages, routes through unified classifier
4. Reply via signal-cli send API
5. Register Hale's Signal contact: name "Hale D2M", number = YOGA's linked number

**Success signal:** "Hale, status?" in Signal → reply within 2 min.

---

### PHASE 4 — Unified Classifier (P1 — shared intelligence)
**Engine:** OpenCode (DeepSeek ZEN, $0)
**Effort:** ~3 hours

Build `core/comms/hale_unified_classifier.py`:
```python
def classify_message(text: str, channel: str, sender: str) -> dict:
    return {
        "intent": "task | chat | intel | client | urgent",
        "brain": "haiku | sonnet | opus | self",
        "persona": "hale | dani",
        "format": "tq_talking | tq_background | plain | stationery",
        "priority": "P0 | P1 | P2 | P3",
        "override": None  # if OPUS:/SONNET: prefix detected
    }
```

All three gateways (email, Telegram, Signal) call this classifier before dispatch. One classification logic, three channels.

---

## PERSONA INTEGRATION — HALE PERSONA UPDATES NEEDED

Add to `Personas/hale_cos.md` — Layer 4 Voice:

```markdown
### Channel-Specific Voice

| Channel | Format | Tone | Signature |
|---------|--------|------|-----------|
| **Email** | T&Q (Bullet Talking/Background Paper) | Formal-authoritative | — V. Hale, VCS |
| **Telegram** | Markdown bullets, ≤4096/msg | Crisp, direct | — Victory |
| **Signal** | Plain text, short | Concise, peer-level | — Hale |

**Channel routing rule:** Hale replies on the channel she received the message. Never cross-post (email question → email answer, not Telegram notification).

**Cross-channel relay (exception):** If a message arrives on an unavailable channel and requires urgent response, Hale may notify Commander on the available channel: "Saw your email — responding here because [reason]."
```

---

## DECISIONS NEEDED FROM COMMANDER

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Signal protocol | A (signal-cli local) / B (Maytapi API) / C (signal-cli Docker) | **C — Docker on YOGA** |
| 2 | Email reply SLA | 2 min / 5 min / async | **2 min (standing requirement)** |
| 3 | Conversation context window | 10 / 20 / 50 messages | **20 (balance cost vs context)** |
| 4 | Signal device | Which number/device links to Hale? | Commander input required |
| 5 | Phase order | 1→2→3→4 or 1→4→2→3 | **1→4→2→3 (fix email first, then unify, then polish, then Signal)** |
| 6 | Dani on Signal? | Yes — Dani bot on Signal / No — Hale only | Commander preference |

---

## DURABLE ARTIFACTS (anti-theater)

| Artifact | Owner | When |
|----------|-------|------|
| `core/comms/hale_unified_classifier.py` | OpenCode | Phase 4 |
| `core/email/thunderbird_gmail.py` — thread reply function | OpenCode | Phase 1 |
| `core/comms/thunderbird_signal_gw.py` | OpenCode | Phase 3 |
| `Personas/hale_cos.md` — channel voice section | Hale-CC | Before Phase 2 |
| Updated n8n ETB 001 flow (email reply wired) | OpenCode | Phase 1 |

---

## OPEN QUESTIONS (Hale flags — Commander answers)

1. **Signal number:** Does Commander want to use his personal Signal number (719-291-0742) or a dedicated D2M number?
2. **Dani on Signal:** Should clients eventually reach Dani on Signal, or is Signal Commander-only (like D2MC2C)?
3. **Email threading:** Should Hale maintain separate context per email thread, or treat all email as one conversation?
4. **Cross-channel awareness:** If Commander tasks Hale on Telegram AND emails a follow-up, should Hale stitch those together?

---

*HALE_COMMS_ARCHITECTURE_PLAN_v1.md | Hale-CC | 2026-05-18*
*Add Commander annotations → Hale-CC converts to T2 exercise SO + tasks OpenCode for build*

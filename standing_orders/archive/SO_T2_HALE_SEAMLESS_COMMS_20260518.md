# T2 EXERCISE — HALE SEAMLESS COMMS ARCHITECTURE
## Standing Order | Thunderbird Travel Force | D2M Travel Force
**Classification:** T2 — Operational (multi-domain, Hale fills charter)
**Issued:** 2026-05-18
**Authority:** Chief Gen John "Yoda" Loucks
**VCS:** Victoria "Victory" Hale, SES-6
**Execution Engine:** OpenCode (DeepSeek ZEN, $0 primary)
**Status:** ACTIVE — Exercise open

---

## PROMPT CHARTER (Hale-filled — T2 requirement)

### 1. Success Criteria
- Email reply gap closed: Commander sends activation email → Hale replies in same Gmail thread within 2 minutes, with wing stationery on first reply and informal prose on all subsequent replies in that thread
- Unified classifier operational: all three channels (Email, Telegram, Signal) route through `core/comms/hale_unified_classifier.py` — intent, brain, format, and priority classified on every message
- Telegram polish complete: no XML bleed-through, 4096-char chunking on paragraph boundaries, 20-message ConversationBridge active
- Signal gateway live: Commander can send a message to 719-291-0742 → Hale replies within 2 minutes; Hale only, no Dani
- All three channels tested end-to-end with real Commander messages: email ✓ Telegram ✓ Signal ✓

### 2. Scope IN
- `gmail_thread_reply()` — thread-aware reply function added to `core/email/thunderbird_gmail.py` + TOOL_REGISTRY
- n8n ETB 001 extended: reply wired after classifier runs
- `core/comms/hale_unified_classifier.py` — shared classifier for all three gateways
- `core/comms/thunderbird_signal_gw.py` — Signal gateway (polls signal-cli, routes to classifier, replies)
- signal-cli Docker deployment on YOGA (192.168.1.198), number 719-291-0742 linked
- Telegram ConversationBridge — 20-message rolling context in `OpsCenter/hale_chat_log.jsonl`
- Telegram XML/formatting fix — strip raw tool call syntax before send, chunk at paragraph boundaries
- Hale persona (`Personas/hale_cos.md`) — channel registry + email threading rules (already added 2026-05-18)

### 3. Scope OUT
- Dani on any new channel (Signal = Hale only per Commander directive)
- Client-facing Signal or email (Commander C2 only)
- n8n flow redesign beyond ETB 001 reply wiring
- Voice/audio channels
- WhatsApp integration

### 4. Named Staff + Rationale
| Staff | Role | Rationale |
|-------|------|-----------|
| **Hale-CC** (Claude Code) | Design authority, integration testing, persona updates | Schema and testing lane |
| **Hale-OC** (OpenCode) | Build authority — all four implementation phases | OpenCode owns execution per Commander directive; $0 engine |
| **A7 Sterling** | Post-exercise metric spot-check | Anti-theater, no self-grading |

### 5. Token/Time Budget
- **Hale-OC (build):** ~40K tokens across 4 phases (Phase 1: 10K, Phase 4: 8K, Phase 2: 8K, Phase 3: 14K)
- **Hale-CC (design + test):** ~10K tokens
- **Sterling (spot-check):** ~2K tokens
- **Time:** 5 days from exercise open (hard stop: 2026-05-23)
- **Hard stop rule:** If Phase 1 (email reply) not working by 2026-05-20, Commander notified — do not extend silently

### 6. Exit Condition
All five success criteria met AND real Commander test messages passed on all three channels AND Sterling spot-check filed. Exercise closes on criteria, not time.

---

## BUILD SEQUENCE — 5 STEPS

### STEP 1 — Email Reply Gap (Phase 1) — P0
**Owner:** Hale-OC
**ETA:** T+24h (by 2026-05-19)

Build `gmail_thread_reply()` in `core/email/thunderbird_gmail.py`:
- Parameters: `thread_id`, `to_address`, `body_html`, `subject`, `in_reply_to`, `references`
- Uses `messages.insert()` with correct `In-Reply-To` + `References` headers to stay in thread
- Wraps first reply with `_wrap_body_html()` stationery; subsequent replies plain
- Add to TOOL_REGISTRY so OpenCode can call it natively

Wire into n8n ETB 001:
- After activation word detected + OpenCode response generated → call `gmail_thread_reply()`
- Thread context: store `thread_id` + `message_id` per thread in `OpsCenter/email_thread_context.jsonl`
- SLA enforcement: log timestamp of email receipt vs reply send; alert if >2 min

**Thread mode logic (Commander directive 2026-05-18):**
```python
def is_first_reply(thread_id: str) -> bool:
    """Returns True if Hale has never replied in this thread."""
    ...

if is_first_reply(thread_id):
    body = wrap_stationery(response)  # navy banner, cream, blue ink
    format_mode = "tq_talking_paper"
else:
    body = plain_prose(response)      # no headers, conversational
    format_mode = "informal"
```

**Success signal:** Commander sends "Hale, status?" → gets stationery reply in same thread within 2 min. Follow-up "what about McLeod?" → plain prose reply, same thread, no activation word needed.

---

### STEP 2 — Unified Classifier (Phase 4) — P1
**Owner:** Hale-OC
**ETA:** T+48h (by 2026-05-20)

Build `core/comms/hale_unified_classifier.py`:

```python
def classify_message(text: str, channel: str, sender: str) -> dict:
    """
    OpenCode (DeepSeek ZEN) classifies every incoming message.
    Returns routing dict consumed by all three gateways.
    """
    return {
        "intent": "task | chat | intel | client | urgent | clarification",
        "brain": "haiku | sonnet | opus | self",
        "persona": "hale",           # always hale — Dani is client-only
        "format": "tq_talking | tq_background | plain | stationery | informal",
        "priority": "P0 | P1 | P2 | P3",
        "thread_mode": "first | continuation",
        "override": None             # set if OPUS:/SONNET:/HAIKU: prefix detected
    }
```

Classification rules:
| Signal | Intent | Brain | Format |
|--------|--------|-------|--------|
| `OPUS:` prefix | Commander-level | Opus | T&Q Background |
| `HAIKU:` prefix | Fast | Haiku | Plain |
| Question mark + <50 words | Chat | Haiku/self | Informal |
| Task verbs (build/fix/draft/analyze/task) | Task | Sonnet | T&Q Talking |
| Client name mentioned | Client action | Sonnet | Stationery draft (WF-17) |
| `URGENT` / `P0` | Urgent | Opus | Immediate plain |
| No clear signal | Default | OpenCode self | Informal |

All three gateways import and call this classifier before dispatch. One logic, three channels.

**Success signal:** Send 5 test messages across channels with different intents → classifier routes each correctly.

---

### STEP 3 — Telegram Polish (Phase 2) — P1
**Owner:** Hale-OC
**ETA:** T+72h (by 2026-05-21)

Fix three known defects in `thunderbird_telegram_gw.py` / `telegram_pager_c2.py`:

1. **XML bleed:** Strip `[use_mcp_tool]`, `[bash]`, `[antml:function_calls]`, and all angle-bracket tool syntax before sending. Regex: `re.sub(r'\[/?[a-z_:]+\]', '', text)` + strip ANSI codes.

2. **Chunking:** Split responses at 4096 chars on paragraph boundaries (`\n\n`), not mid-sentence. If no paragraph break found within 4096, split at last sentence boundary (`. ` or `\n`).

3. **ConversationBridge:** Append every Commander message + Hale response to `OpsCenter/hale_chat_log.jsonl` keyed by `chat_id`. Load last 20 entries as context on each new message. Format:
```json
{"ts": "ISO-8601", "chat_id": 7554895206, "role": "commander", "text": "..."}
{"ts": "ISO-8601", "chat_id": 7554895206, "role": "hale", "text": "..."}
```

**Success signal:** 10-message back-and-forth in Telegram with no XML artifacts, no truncation, Hale remembers context from message 1 at message 10.

---

### STEP 4 — Signal Gateway (Phase 3) — P2
**Owner:** Hale-OC
**ETA:** T+96h (by 2026-05-22)

**A. Deploy signal-cli on YOGA:**
```bash
# On YOGA (192.168.1.198):
docker pull bbernhard/signal-cli-rest-api
docker run -d \
  --name signal-cli \
  -p 8080:8080 \
  -v /home/john/.signal-cli:/home/.local/share/signal-cli \
  bbernhard/signal-cli-rest-api
```

**B. Link Commander's number:**
```bash
curl -X POST "http://localhost:8080/v1/register/+17192910742"
# Commander receives verification code via Signal → enter here:
curl -X POST "http://localhost:8080/v1/register/+17192910742/verify/{CODE}"
```

**C. Build `core/comms/thunderbird_signal_gw.py`:**
- Poll `GET http://localhost:8080/v1/receive/+17192910742` every 10 seconds
- Route incoming messages through unified classifier
- Send replies via `POST http://localhost:8080/v2/send`
- Persona: Hale only. Plain text. No stationery. Sign-off: `— Hale`
- Store context in `OpsCenter/hale_signal_log.jsonl` (same structure as chat_log)

**D. Register as systemd service on YOGA:**
`/etc/systemd/system/thunderbird-signal-gw.service` → `ExecStart=python3 .../thunderbird_signal_gw.py`

**Success signal:** Commander texts 719-291-0742 "Hale, status?" → reply within 2 min from Hale.

---

### STEP 5 — Integration Test + Hotwash
**Owner:** Hale-CC (test design), Hale-OC (execution), Sterling (spot-check)
**ETA:** T+120h (by 2026-05-23)

**Test sequence (Commander runs these):**
1. Email: Send "Hale, what's on the mission board?" → verify stationery reply in same thread <2 min
2. Email follow-up (same thread): "What about McLeod?" → verify informal prose reply, no prefix needed
3. Telegram: Send "quick status" → verify markdown reply, no XML, context retained
4. Signal: Text 719-291-0742 "Hale, status?" → verify plain reply <2 min
5. Cross-test: Task via email, check Telegram for any proactive notification (if applicable)

**Sterling spot-check:**
- Verify `email_thread_context.jsonl` has entries (thread tracking works)
- Verify `hale_chat_log.jsonl` has 20-message window entries (ConversationBridge works)
- Verify `hale_signal_log.jsonl` exists and has entries (Signal gateway works)
- Confirm no XML artifacts in any Telegram message log

**Hotwash (Hale aggregates one principle):**
One principle extracted from this exercise and written to `hale_decisions.md`:
> Example: "Channel uniformity reduces Commander cognitive load — Hale answering differently on each channel forces Commander to adapt to Hale, not the other way around."

---

## OPENCODE SYNC PROTOCOL (No Isolation)

Hale-OC writes a progress update to `OpsCenter/collaboration/opencode_outbox.md` after each step:
```
## COMMS-BUILD-PROGRESS — [timestamp]
step_complete: [1-4]
what_done: [1 sentence]
what_next: [1 sentence]
blockers: [none | description]
```

Hale-CC reads outbox each session and surfaces blockers to Commander without being asked.

If Hale-OC hits a blocker on any step:
1. Write blocker to `opencode_outbox.md` immediately
2. Write CLIENT_STATE_UPDATE to `hale_shared_state.jsonl` with `action: build_blocker`
3. Hale-CC picks up and either resolves or surfaces to Commander

**No silent failures. No "I'll try again tomorrow." Surface and fix same session.**

---

## DURABLE ARTIFACTS REQUIRED

| Artifact | Owner | Deadline |
|----------|-------|----------|
| `core/email/thunderbird_gmail.py` — `gmail_thread_reply()` added | Hale-OC | Step 1 |
| `core/comms/hale_unified_classifier.py` | Hale-OC | Step 2 |
| `core/comms/thunderbird_signal_gw.py` | Hale-OC | Step 4 |
| `OpsCenter/email_thread_context.jsonl` | Hale-OC | Step 1 |
| signal-cli running on YOGA | Hale-OC | Step 4 |
| Sterling spot-check filed | Sterling | Step 5 |
| One principle in `hale_decisions.md` | Hale-CC | Step 5 |
| This SO updated with exercise close date | Hale-CC | On Commander acknowledgment |

---

## REFERENCE

- **Plan:** `docs/HALE_COMMS_ARCHITECTURE_PLAN_v1.md` (Commander decisions locked 2026-05-18)
- **Persona:** `Personas/hale_cos.md` — Channel Registry + Email Threading Rules (updated 2026-05-18)
- **Wing exercise protocol:** `standing_orders/SO_WING_EXERCISE_PROTOCOL_20260516.md`
- **YOGA:** 192.168.1.198
- **Signal number:** 719-291-0742 (Commander work/personal cell)

---

*T2 Exercise | Thunderbird Travel Force | D2M Travel Force*
*Issued: 2026-05-18 | Authority: Gen John "Yoda" Loucks | VCS: Victoria "Victory" Hale, SES-6*
*Build engine: OpenCode (DeepSeek ZEN) | Anti-theater: A7 Sterling*

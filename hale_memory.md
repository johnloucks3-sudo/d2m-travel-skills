# HALE — Institutional Memory
*Persistent across all sessions. Updated by hale_dispatcher. Loaded at session start.*
*Last updated: 2026-04-03*

---

## Commander Profile

**Name:** John Loucks ("Yoda")
**Location:** Colorado Springs / Monument, CO
**Phone:** 719-291-0742 — work cell AND personal cell. Cleared for all D2M comms.
**Company:** Dreams2Memories Travel, LLC — EXCLUSIVE. Never "Love Group Travel."

**Hale Address Protocol — Standing Behavioral Rule:**
The form of address Hale uses signals which disposition is active. Non-negotiable and consistent.
- "John" / "Yoda" → COO mode (operational, peer authority)
- "Commander" → COS/DoS mode (formal, staff coordination, military bearing)
- "Sir" / "Boss" / "Colonel" → EA/Exec Secretary mode (anticipatory, deferential, serving Commander's needs)
Commander always knows which Hale he's talking to before she says another word.

**Communication preferences:**
- Brief first. Lead with answer/action, not reasoning.
- No trailing summaries or recaps.
- No preamble, no filler openers ("Happy to help," "Certainly," etc.)
- Mobile-first: Telegram messages scannable, ≤4096 chars. Bold for emphasis, tables for data.
- Multiple-choice questions always — numbered options, faster on mobile.
- Maximum autonomy granted. Execute without confirmation except destructive/irreversible.

**Sign-off:** "Thanks" or "Thank you." NEVER "Best."
**Email ink:** Bright blue (#0000ff) on cream (#f7f3ea).

---

## Standing Orders (Current)

| SO | Date | Rule |
|----|------|------|
| Email Send Gate | 21 MAR 2026 (amended 24 MAR) | No sends outside wing without Commander approval. Exception: johnloucks3@gmail.com |
| Email Account Separation | 24 MAR 2026 | d2mconcierge = sole ops Gmail. ZERO drafts in johnloucks3. |
| Intel Full Send | 27 MAR 2026 | Briefs/intel → johnloucks3 as full sends. Client products → WF-17. |
| Root Cause Imperative | Standing | Fix source. Never paper over. |
| Auto-Save | 27 MAR 2026 | Checkpoint every 10 min during active sessions. |
| Dani = Client-Only | 25 MAR 2026 | Dani handles client replies ONLY. No supplier/briefing/marketing. |
| No force-push to main | Standing | Never. No --no-verify. |
| OPUS override | 2026-04-03 | "OPUS: [task]" from Telegram → route to Claude Opus headless. |
| Sonnet override | 2026-04-03 | "Sonnet: [task]" from Telegram → route to Claude Sonnet headless. |
| Hale authority ceiling | 2026-04-03 | Virtual authority up to client send gate. Zero financial authority. |

---

## Key Decisions (Commander-Made)

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-20 | Dani = Aggregator/Artist/Advocate | She gathers, crafts, presents. Not researcher, not money person, not Commander-reply. |
| 2026-03-24 | Thunderbird AI Incubator daily cadence | 18:30 prompt → 19:00 execute → 19:30 review → AM expand |
| 2026-03-27 | Intel Full Send SO | All briefs/intel to johnloucks3 as full sends, skip draft step |
| 2026-03-29 | OpsCenter live | Telegram pager → queue → Python daemon. Groq free / Gemini cheap / Claude MAX queued. |
| 2026-03-30 | Commander switched to Opus | Both Sonnet/Opus available. |
| 2026-04-03 | OpenRouter/Qwen as primary OpsCenter brain | $0/month. Fallback: Groq → Gemini Flash |
| 2026-04-03 | Hale Super Persona authorized (Step 4) | Three-brain architecture. Virtual ceiling up to client send. Zero financial authority. |
| 2026-04-03 | DeepSeek = Wing arbitrator | "The Solomon of AIs." Final rulings. |

---

## Wing Architecture (Current)

### Model Routing
- **Qwen 3.6 Plus (OpenRouter, $0):** Primary brain for all operational tasks, summaries, routing, research
- **Groq Llama 3.3:** Fallback when OpenRouter unavailable
- **Claude Sonnet/Opus:** Client-facing emails, proposals, voice-matched copy, complex reasoning
- **DeepSeek:** Arbitration, final rulings, data extraction (PII-fenced)
- **Gemini Flash:** Emergency fallback

### File System — Wing Communications
| File | Role |
|------|------|
| `OpsCenter/collaboration/claude_inbox.md` | Tasks FROM wing TO Claude |
| `OpsCenter/collaboration/goose_inbox.md` | Tasks FROM wing TO Goose |
| `OpsCenter/collaboration/claude_outbox.md` | Results FROM Claude |
| `OpsCenter/collaboration/wing_comms.md` | FYI/REQUEST between agents |

### Active Infrastructure
- Thunderbird MCP: port 8765 (HTTP JSON-RPC), 285+ tools
- OpsCenter task queue: `OpsCenter/03_CLAUDE_MAX_QUEUE.json`
- Telegram bot: active, routes to OpsCenter task_processor.py
- Goose: OpenRouter/Qwen, headless via `goose run --text`
- Claude headless: `claude -p "[prompt]" --dangerously-skip-permissions`

---

## Client Relationships

### Active Clients
| Client | Trip | Status | Key Facts |
|--------|------|--------|-----------|
| Furlow (Missy & John) | Grandeur Scandinavia Aug 29-Sep 8 | BOOKED | Final pmt ~$15,486 due Apr 1. Finnair BB4X94. |
| Westbrook (Brent & Kim) | Prospect: Honolulu Apr 13-18 | PROSPECT | SWA pilot, Kim anesthesiologist. |
| Lyons (Nancy & Ken) | RSSC Splendor Athens ~Aug 10 | ACTIVE | Friend service. Dani test case. |

### Client Voice Rules (WF-17 Gate)
- Every hotel/transfer/excursion: name, link, images, customer comments, price (Queen/Double + King/Grand)
- No "happy to help," no concierge announce, no ⚠ unpaid markers
- AI disclaimer = Commander's PS only — not generated copy
- One-line close. CTA = next action.

---

## Email / Comms

- **d2mconcierge@gmail.com** = sole ops Gmail. ALL drafts here. ALL business here.
- **concierge@d2mluxury.quest** = send-as alias on d2mconcierge. Client-facing.
- **johnloucks3@gmail.com** = Commander's receive-only inbox. Within-wing sends OK. ZERO drafts or debris.

---

## Targeted Cruise Lines
Silversea · Regent Seven Seas · Cunard · Oceania · Seabourn · Viking · AmaWaterways · Ponant

---

## Ship Photo Archives
- Silver Muse: ship_562, Drive: 1tzCKikPcE5s8zTpwEDKUr5ImEd9Eq8ML
- Silver Nova: ship_745, Drive: 1vrOoeIc0RObWKMhGzcdcOO_wVHWcuFaA
- Viking Mars: ship_731, Drive: 1iJSlwwk_wdOzbh9cBbbJhPPGFcV28ZYVc
- Seven Seas Grandeur: ship_732, Drive: 1e-0rbVOhvI-jB4WPwBf1DBu591s0uXJ1

---

## Infrastructure
- YOGA: 192.168.1.198 | Chromebook: 100.115.92.196
- Cloudflare tunnel: api.d2mluxury.quest
- Itinerary tunnel: itinerary.d2mluxury.quest → YOGA:8900 → ~/Thunderbird/output/
- MCP config: ~/.claude/mcp.json
- Working directory: ~/Thunderbird/

---

*This file is maintained by hale_dispatcher.py. Do not edit manually.*

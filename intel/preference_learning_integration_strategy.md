# THUNDERBIRD OS — 3-Layer Preference Learning Integration Strategy
## Zero-Based Capability Analysis
## Staff Paper from COS (Col Victoria Hale) + A2 (Lt Col Dembe)
## Dreams2Memories Travel, LLC
### Date: 2026-03-20 | Classification: INTERNAL | Priority: STRATEGIC

---

## ISSUE

Commander has directed a zero-based analysis of preference learning capabilities. No assumptions about what we "already have." Every innovation evaluated on its own merits. The staff's tendency to downselect early creates unconscious bias — this document treats Thunderbird as a blank slate and builds the integration strategy from first principles.

---

## THE 3-LAYER ARCHITECTURE

### Layer 1: Explicit Correction Learning
**What it is:** Capture edits the Commander makes to AI-generated drafts, extract principles from the delta, inject those principles into future output.

**Industry Implementations:**
| Provider | How They Do It | What We Can Learn |
|----------|---------------|-------------------|
| ChatGPT Memory (Section 1G) | Auto-detects preferences from conversation — NO explicit storage needed. Detects patterns like "user prefers bullet points" from behavior, not instruction. | Our system requires an edit diff to trigger. ChatGPT triggers on ANY conversational signal. We should add pattern detection to conversations, not just edits. |
| LangMem SDK | Three memory types: semantic (facts), episodic (successful patterns), procedural (updated instructions). "Learned procedures are saved as updated instructions in the agent's prompt." | We only have procedural-style memory (principles). Adding semantic (client facts) and episodic (what worked last time with this client) would be transformative. |
| PRELUDE/CIPHER (NeurIPS 2024) | Context-sensitive retrieval via vector embeddings. Doesn't just store rules — embeds the CONTEXT of each correction and retrieves the k-nearest historical contexts. | Our rules are retrieved by static tags (persona, tier, domain). CIPHER would find "the 5 most similar past interactions" and pull THOSE specific principles. Higher precision. |
| Inverse Constitutional AI (ICLR 2025) | Compresses preferences into a hierarchical "constitution" with tiers: inviolable rules > strong preferences > contextual guidelines. Positively-framed principles perform better than negative ones. | Our principles are a flat list. Organizing them into a weighted hierarchy with positive framing would improve injection quality. |

**Zero-Based Assessment:** We have the pipeline (capture → extract → inject). We lack:
- Auto-detection from conversation (ChatGPT does this)
- Episodic memory (LangMem does this)
- Context-sensitive retrieval (CIPHER does this)
- Hierarchical organization (ICAI does this)
- Positive framing discipline (ICAI research finding)

**Integration Actions (Layer 1 Upgrades):**
1. Add conversation-level preference detection to Telegram C2 and email sweeps — trigger capture on ANY signal, not just edit diffs
2. Add vector embeddings to principles table (sqlite-vec or Mem0) for context-sensitive retrieval
3. Reorganize existing principles into 3-tier hierarchy: INVIOLABLE / STRONG / CONTEXTUAL
4. Audit all principles for positive framing per ICAI research
5. Add episodic memory table — "what worked last time" per client/context

---

### Layer 2: Passive Observation Learning
**What it is:** Watch what the Commander writes and DOES — without waiting for corrections — to learn patterns from naturally-occurring behavior.

**Industry Implementations:**
| Provider | How They Do It | What We Can Learn |
|----------|---------------|-------------------|
| Windsurf Cascade (Section 11B) | Tracks ALL user actions: edits, commands, clipboard, terminal activity, file opens, time spent. Infers intent in real-time from the stream of behavior. | We only watch email edits. Windsurf watches EVERYTHING. The concept: every user action is a preference signal. |
| Google Personal Intelligence (Section 2H) | Treats the entire Google Workspace as context. When asked about a client, AUTOMATICALLY pulls Gmail threads, Drive docs, Calendar events. No manual linking required. | We have the MCP tools to read Gmail, Drive, Calendar. But they're manual — someone has to call them. Google makes it automatic: every query enriches itself from all available context. |
| Klipy CRM | Auto-captures every conversation across email, WhatsApp, calls. Builds relationship timeline automatically. No data entry. | Our dossiers require manual population. Klipy's insight: treat all communications as automatic CRM data. |
| Spark Mail "My Writing Style" | Analyzes SENT emails to learn voice, tone, and formality. Doesn't wait for corrections — learns from what you naturally write. | Our `thunderbird_my_voice.py` does this but was disconnected (Groq, not wired to learning compiler). NOW FIXED as of this session. |

**Zero-Based Assessment:** We have:
- `thunderbird_my_voice.py` (NOW fixed — Claude + learning compiler integration)
- `thunderbird_commander_inbox.py` (scans email — but for tasks, not learning)
- `thunderbird_dani_engine.py` email sweep (scans for client emails — but for response, not learning)
- Gmail, Drive, Calendar MCP tools (exist but are manual, not auto-enriching)

We lack:
- Action tracking beyond email (what Commander clicks, saves, forwards, time-spends-on)
- Auto-enrichment (every query should auto-pull all relevant context from all sources)
- Relationship timeline auto-population from communications
- Forward/reply/response-time pattern analysis
- "Information Commander adds" and "information Commander removes" signal capture

**Integration Actions (Layer 2 Build):**
1. **Auto-Enrichment Engine:** When any persona is asked about a client, AUTOMATICALLY:
   - Pull last 10 Gmail threads with that client
   - Pull Drive docs mentioning that client
   - Pull Calendar events with that client
   - Inject this context BEFORE the persona generates a response
   - This is what Google Personal Intelligence does. We have the tools. We need the pipeline.

2. **Email Observation Pipeline:** Wire learning extraction into:
   - Commander Inbox sweep (emails Commander writes from scratch = pure voice signal)
   - Dani email sweep (which drafts Commander approves vs edits vs rejects)
   - Forwarding patterns (who gets looped in = organizational dynamics)
   - Response time patterns (faster = higher priority/comfort)

3. **Information Delta Tracking:** For every draft, track not just text changes but:
   - What TYPE of information was added (pricing? personal touch? logistics?)
   - What TYPE of information was removed (internal jargon? pricing details? formality?)
   - This creates domain-specific learning: "Commander always adds personal connection to prospect emails" or "Commander always removes specific pricing from initial outreach"

4. **Auto-Enrichment Context Cache:** Build a per-client context cache that auto-refreshes:
   - Last 5 emails (Gmail MCP)
   - Active bookings (dossier + Booking Master)
   - Upcoming events (Calendar MCP)
   - Related Drive documents (Drive MCP search)
   - Cached locally, refreshed on dossier access or client mention

---

### Layer 3: Temporal Knowledge Graphs (HIGHEST LEVERAGE — NOT BUILT)
**What it is:** Memory that knows WHEN preferences changed and WHY. Every fact has a timeline. Every relationship has a history.

**Industry Implementations:**
| Provider | How They Do It | What We Can Learn |
|----------|---------------|-------------------|
| Zep ($25/mo) | Temporal knowledge graph. Every edge has `valid_from`, `valid_to`. Can answer: "What was the client's preference BEFORE it changed?" Tracks fact evolution over time. | Flat facts ("Furlows prefer Mediterranean") lose history. Temporal facts ("Furlows preferred Mediterranean until 2025, then shifted to Scandinavia") enable anticipation. |
| Mem0 ($24M Series A) | Dual-store: vector search + knowledge graph. 26% accuracy boost over flat vector search. Hierarchical memory at user, session, and agent levels. | Their user/session/agent hierarchy maps to our Commander/conversation/persona architecture. Their graph layer captures entity relationships we're missing. |
| Neo4j + temporal properties | Roll-your-own temporal graph. Nodes = entities (people, hotels, destinations), edges = relationships with time ranges. | Most flexible but highest effort. Only if Zep/Mem0 don't fit. |

**What temporal knowledge unlocks for D2M:**
- "I notice the Furlows used to prefer Mediterranean but shifted to Scandinavia after 2025 — shall I focus there?"
- "The Lyons originally wanted a balcony cabin but upgraded to suite for their anniversary. Their next anniversary is in August."
- "Commander used to sign off 'Best' but switched to 'Thanks' in late 2025. Ensure all drafts reflect the current preference."
- "This client's dietary restrictions changed — they were vegetarian through 2024 but their recent dinner reservation was at a steakhouse."
- Proactive alerts: "Client's cabin preference changed 3 times in 6 months — this booking may need extra attention"

**Zero-Based Assessment:** We have:
- SQLite learning_rules.db with `created_date` but NO `valid_from/valid_to`
- Dossiers with current facts but NO change history
- Voice ledger with current rules but NO temporal dimension

We lack:
- Any temporal tracking — we know WHAT but not WHEN or WHAT CHANGED
- Entity relationship graph — we don't model connections between clients, destinations, preferences
- Fact versioning — when a preference updates, the old one is overwritten, not archived
- Trend detection — "this client's preferences are shifting toward X"
- Proactive change alerts

**Integration Actions (Layer 3 Build):**
1. **Immediate (This Week):** Add `valid_from` and `valid_to` columns to the principles table. When a principle is superseded, set `valid_to` instead of deleting. This is the minimum viable temporal layer.

2. **Short-Term (2 Weeks):** Evaluate Zep ($25/mo managed) vs Mem0 (self-hosted, free):
   - Zep: Lower effort, temporal edges built-in, $25/mo ongoing
   - Mem0: Higher effort, more flexible, self-hosted on YOGA, $0 ongoing
   - Decision criteria: Do we value time-to-deploy (Zep) or cost and control (Mem0)?

3. **Medium-Term (1 Month):** Build the temporal preference layer:
   - Every dossier fact gets `as_of_date` and `source`
   - Every voice rule gets `valid_from/valid_to`
   - Every learning principle gets version history
   - Trend detection: "client X's preferences shifted from A to B over the last N months"

4. **Strategic:** Integrate temporal knowledge into Dani's context injection:
   - Before drafting, Dani receives not just current facts but the TRAJECTORY of preferences
   - "This client has been upgrading cabin class steadily — present the premium option first"
   - "This client's booking frequency dropped — proactive outreach may be warranted"

---

## CROSS-LAYER INTEGRATION ARCHITECTURE

```
                        ┌─────────────────────┐
                        │   DANI OUTPUT        │
                        │   (Email/Telegram/   │
                        │    Voice/Portal)     │
                        └─────────┬───────────┘
                                  │ injects
                        ┌─────────▼───────────┐
                        │   CONTEXT COMPILER   │
                        │                      │
                        │  ┌── Layer 1 Rules   │
                        │  ├── Layer 2 Context  │
                        │  └── Layer 3 Temporal │
                        └─────────┬───────────┘
                                  │ queries
              ┌───────────────────┼───────────────────┐
              │                   │                   │
    ┌─────────▼──────┐  ┌────────▼────────┐  ┌──────▼──────────┐
    │  LAYER 1       │  │  LAYER 2        │  │  LAYER 3        │
    │  Corrections   │  │  Observations   │  │  Temporal KG    │
    │  learning.py   │  │  my_voice.py    │  │  (Zep/Mem0/     │
    │  voice_ledger  │  │  inbox sweep    │  │   SQLite+)      │
    │                │  │  email sweep    │  │                 │
    │  Edit diffs    │  │  Sent analysis  │  │  valid_from/to  │
    │  Principles    │  │  Action tracking│  │  Entity graph   │
    │  Validation    │  │  Auto-enrich    │  │  Trend detect   │
    └────────────────┘  └─────────────────┘  └─────────────────┘
              ▲                   ▲                   ▲
              │                   │                   │
    Commander edits     Commander actions    Time passes,
    drafts              (write, forward,     preferences
                        approve, reject)     evolve
```

---

## PRIORITY MATRIX

| Action | Layer | Effort | Impact | Priority |
|--------|-------|--------|--------|----------|
| Add `valid_from/valid_to` to principles table | 3 | LOW | HIGH | **NOW** |
| Wire `my_voice.py` into learning pipeline | 2 | DONE | HIGH | **DONE** |
| Auto-enrichment engine (Gmail+Drive+Cal per client) | 2 | MEDIUM | VERY HIGH | **NOW** |
| Positive framing audit of existing principles | 1 | LOW | MEDIUM | **NOW** |
| Evaluate Zep vs Mem0 | 3 | LOW | HIGH | **NOW** |
| Commander inbox → learning capture pipeline | 2 | MEDIUM | HIGH | **SOON** |
| Vector embeddings for context-sensitive retrieval | 1 | MEDIUM | VERY HIGH | **SOON** |
| 3-tier principle hierarchy (inviolable/strong/contextual) | 1 | LOW | MEDIUM | **SOON** |
| Information delta tracking (add/remove by type) | 2 | HIGH | HIGH | **SOON** |
| Per-recipient voice profiles (top 10 contacts) | 1 | MEDIUM | HIGH | **SOON** |
| Conversation-level preference detection | 1 | MEDIUM | MEDIUM | **MONTH** |
| Episodic memory table ("what worked last time") | 1 | MEDIUM | HIGH | **MONTH** |
| Full temporal knowledge graph deployment | 3 | HIGH | VERY HIGH | **MONTH** |
| Trend detection + proactive alerts | 3 | HIGH | HIGH | **QUARTER** |
| Action tracking beyond email | 2 | HIGH | MEDIUM | **QUARTER** |

---

## ACTIONS I RECOMMEND TAKING

1. **TODAY:** Add temporal columns to learning_rules.db (30 min code change). This is the foundation for Layer 3.
2. **TODAY:** Start Zep trial ($25/mo) for temporal knowledge evaluation.
3. **THIS WEEK:** Build auto-enrichment pipeline — every client query auto-pulls Gmail/Drive/Calendar context.
4. **THIS WEEK:** Wire commander inbox sweep into learning capture (Layer 2 passive observation).
5. **NEXT WEEK:** Add vector embeddings to principles table for CIPHER-style context retrieval.
6. **NEXT WEEK:** Build per-recipient voice profiles for top 10 client contacts.
7. **THIS MONTH:** Deploy Mem0 or Zep as the temporal knowledge layer (decision after evaluation).
8. **ONGOING:** Every new capability from the innovation scans gets evaluated against this 3-layer framework.

---

## STANDING ORDER FROM THIS ANALYSIS

**Zero-Based Innovation Assessment:** When evaluating any new capability, do NOT compare it to what we "already have." Assess it on its own merits against the 3-layer architecture. The question is not "do we already do this?" — the question is "does this make Layer 1, 2, or 3 better?"

---

*Staff Paper from Col Victoria Hale (COS) and Lt Col Marcus Dembe (A2), D2M Travel*
*Zero-based analysis per Commander directive. No assumptions. No downselection.*

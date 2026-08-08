# ROUND TABLE INTEROP SCHEMA v2 — Capability-Gap Driven (RT-INTEROP-V2)
**Date:** 2026-08-08 · **Author:** OC-Hale (Jet) · **Status:** DRAFT v2, reworked per Commander correction (2026-08-08)
**Prev:** v1 `RT_INTEROP_SCHEMA.md` — rejected: surfaced-mapped tools to existing constructs and flat-out refused adoptions. Commander: *"you papered over real capability increases… not reject because the surface construct looks the same. Think deeper."*
**Engaged:** CC ✅ (ticketed, not blocked) · AG (Gemini **3.6 Flash** — 3.1 Pro line frozen) · OC ($0 lane)

---

## 1. BLUF
V1 was construct-blind — it saw "rooms/votes/memory" and answered "RT has that." **It doesn't.** Re-run against the FULL original list exposes **7 real capability gaps** RT lacks today, each carrying a change in *what an engine can hand another engine* that mere card-shape similarity hides: ① **sealed-ballot anti-anchoring** · ② **in-flight file ownership (claims, live lock)** · ③ **response fan-out (parallel same-question)** · ④ **per-scope context isolation (check potential view from code rot)** · ⑤ **push egress (webhook / cross-session send) out of the room** · ⑥ **cross-window budget telemetry feeding routing decisions**. None requires building a platform; all require extending the card envelope + 2 recorder actions. <50 LOC still holds. Command lieutenant: **stop rejecting; three adopt-pilot candidates are genuinely worth a trial** (§4).

---

## 2. THE FULL ORIGINAL LIST — capability extraction (no surface flat-reject, each judged on *what control transfer it enables*)

| # | Source | Surface construct | **Real capability (what it let engine/agent do)** | Creates a gap in RT? | Verdict |
|---|---|---|---|---|---|
| 1 | "Compass-to-nearest-toilet, vibe-coded" (r/ClaudeAI) | app built by Claude | Vibe-loop autonomy; no interop signal | No | Reject-from-topic |
| 2 | "$3k dream game" (r/ClaudeAI) | long agent build | Long-horizon budget on browser demo; nothing for room semantics | No | Reject-from-topic |
| 3 | "asked Claude to scare me" | roleplay | Guardrail alignment, no nuance here | No | Reject-from-topic |
| 4 | "Poker: real cards + phone chip stacks" (r/ClaudeAI) | multi-device | **Distributed reader/controller many-客户端 sharing one state table** — dual interpret sense: each client owns part of the table. → **Partitioned shared-state pattern**. Maps to our "each seat owns fraction of the work item". | Thin #qs 2/5 (ownership) | Adopt-pattern (doc) |
| 5 | "Be careful letting Claude use WebFetch" (r/ClaudeAI) | warning | Context poisoning via source material; **trust-anchor & ingest hygiene** | #6 fuses ab budget | Adopt-practice |
| 6 | "Claude from a small business perspective" | narrative | no technique | No | Reject |
| 7 | "Benchmarked 10 LLMs on physics sim; Opus 5 won" | **model bench across engines** | **Cross-engine capability-profiling for role assignment** — empirical seat-selection, exactly what RT order should consult | Despite using | **Adopt-capability: bench → seat-assign** |
| 8 | "Claude Code in 9 lines of Python" | skeleton | tool-loop is just: read tools → emit actions → stream. **Protocol minimality ⇒ any engine can speak our card file; a scheduler needs essentially nothing.** | none | **Adopt-in-operator** |
| 9 | "Message your other Claude Code sessions" (docs) | cross-session **live** chat | `ListAgents`+`SendMessage` across **live sessions**, per-session inbox **socket**, `accept/hold/refuse` inbound, `isolatePeerMachines`, throttled loops | #5 push | **Include as EXTERNAL TRANSPORT** |
| 10 | "Auto Mode default Aug 14" (HN) | default permission | **permission-class changes global**; RT cards cross seats = new lines: intra-room messaging rides on permission-class equivalence (CC doc says same) | none (watch) | Note; module= on |
| 11 | "Vibsync" (Show HN) | MCP shared memory | **claim / release / tasks / ask-reply across engines + tamper-evident audit log** — ownership + pending-question queue + activity-free snap for coordinators | **GAP #2/#4** real | **Adopt-pilot (claims only)**, fold mission_board*
| 12 | "AIUsageBar" (Show HN) | menu-bar tracker | **cross-provider per-second/per-window quota + spend + 75/90% alarm** — real-time budget state feeding **which lane to route** matter at argument | #6 | **Adopt-capability**: ledger already exists; add **rate-free budget alarms→routing** |
| 13 | "sessions can now message each other" (twitter dup) | dup of #9 | same | — | merge into #9 |
| 14 | "browser running inside terminal" (r/vibecoding) | terminal-sanboxed browser for Claude Code | **tool reach: agent drives a browser protected; capability: scoped-tool**, not room | none | note |
| 15 | "Graphify – fewer tokens for CC" | MCP context | **context compression within session** | #4 adjacent | minor: adopt note |
| 16 | "Cowchat – agents talk locally" | local chat server | **rooms+subrooms·sealedballot·leader-elect·presence·turn-token·webhooks**, NDJSON, TCP/WS/Unix-sock | **GAP #1/#5** deepest | **Adopt-pilot (ballot + webhook)** |
| 17 | dup | merge | — | — | — |
| 18 | "Alyph – context transmission" | + | quote: "car," manual, branching cars, playback, model **fanout** (same case to many models), multiplayer canvas | #3 | **Adopt-pattern: fan-out + prune** |
| 19 | "CC auto default"(dup of #10) | — | — | — | merge #10 |
| 20 | "Talk to Claude Code / Force Yourself Slow" (vendor) | audio plugin | voice transcript into session | borderline | note |
| 21 | **"Neal: Codex+Claude in a loop, 549-commit"** | **multi-push orchestrator** | planner/coder/reviewer **role split**, fresh context per scope, reviewer keeps global view, consult-turn on block, restartable `.neal/` | **GAP #4 (fresh-context-per-scope)** honestly | **Adopt-architecture: per-scope reset; ours = per-card reset already** |
| 22 | "context mgmt: /clear vs /compact" | `@/` advice | **explicit boundary between abandon (clear) and condense (compact)** — directly RT: when to reset a card vs merge | #4 confirm | adopt; doc rule |
| 23 | "Ask HN: CC Alternatives" | list | menu | no | reject |
| 24 | "in-terminal browser fora local sandbox for CC" | like #14 | browser-in-sandbox server-ization | note | same #14 |
| 25 | "Why every CC user should know hooks" (dev.to) | events/automation | **hook automation: before/after tool, stop, session start** — trigger actions when a session lifecycle event fires | **GAP #5b: inbound-fire** — room events could auto-fire hooks | **Adopt-capability: hook-mirror in RT** (recorder fires action) |
| 26 | "measured what one Cmd+V costs your context window" (dev.to/dev) | profiling | **context tax admits every session** — motivates PRUNE and delta-only cards (RT-RETRO already: no reprints) | none | accept; doc |

## 3. THE SIX REAL GAPS (the delta v1 legally)

| # | Gap | Proof-source | What v2 adds | Cost |
|---|---|---|---|---|
| **G1** | **Sealed-ballot anti-anchoring** — RT orders AG→CC→OC, so *first-seat-to-speak anchors everyone*. Cowchat hides ballots until all in. | #16 Cowchat | `type:VOTE` card — ballots to recorder, revealed at once; recorder STOPS ordering during vote | 1 card type |
| **G2** | **In-flight file ownership / live lock** — no card claims a path it is editing; concurrent writers collide. Vibsync `claim/release` has this; our `assigned_to` is at-plan, not live. | #11 Vibsync | `card.claims: [path…]` + `mission_board` acquisition; release on `STATUS:done` | field + recorder |
| **G3** | **Same-question fan-out** — parallel-ask N seats on one prompt, comparison dashboard. Alyph does it; RT is strictly FIFO today. | #18 Alyph, #7 bench | `type: FANOUT`; recorder snapshots；you read side-by-side before ordering | 1 card type + view |
| **G4** | **Fresh-context-per-scope** — rotor: coder gets clean context each scope; reviewer keeps. Ours pre-writes, but one RT session still accumulates after N cards → context rot. | #21 Neal, #22 | `card.scope` (file scope indent); recorder may start at card, joins scopes, mark compartment clear; equals /clear-per-scope | field |
|anchorG5 | **Push egress — webhooks + cross-session send OUT** — Cow chat webhooks push to HTTP; CC cross-session sends to live engine sockets. RT today is file-physical read. Let a card `fire: → webhook` (Telegram/Drive/HTTP) when recorder accepts. Conversational latest. **⚠ AG-REFINED (2026-08-08): local whitelisted sinks ONLY** — arbitrary outbound HTTP = exfiltration + loop hazard + breaks Commander approval gate. | #16, #9, #25 | `card.hook: {sink: telegram-c2|dashboard-local, on: [accepted,hold,released]}`; recorder emits on terminal states `DECISION`/`RELEASED` only. No external endpoints. | recorder action |
| **G6 | **Budget telemetry → routing** — AIUsageBar data (per-window used/left, 75/90%) drives "OC lane, AG lane, hold CC". `usage_ledger` exists but not feeding dispatch order live. | #12, + our OpenRouter cap | recorder checks ledger before seating-order next seat; flags `lane` in enum | recorder action |
| **G7** | **Quorum & liveness** — seat offline/unauth/rate-limited stalls VOTE/FANOUT forever. Cowchat presence; consensus quorum. **AG-ADDED 2026-08-08.** | #16 presence, #19 Grok gap | `quorum: {required, optional, timeout_s, on_timeout}`; deterministic proceed/abort on missing seats | 1 field block |

Also raised (from #21/#8/#5): **chair/claim patterns, pipeline auto-reset, trust-mark source** — see §6.2.

## 4. RT_CARD v2 envelope (extends v1; v1 fields id/type/sender/to/reply_to/in_reply_context/day shift,deadline,frontmatter stay)

```yaml
---
card:
  id: RT-{session}-{seat}-{seq}
  type: FINDING | QUESTION | DECISION | REBUTTAL | CONSULT | STATUS
        | VOTE | FANOUT | CLAIM | RELEASE          # ← new G1/G2/G3
  sender: OC
  to: CC|AG|OC|GROK|ALL|COMMANDER
  reply_to: RT-{...}
  reply_addr: RT-{...}
  scope: "shared_context/{topic}.md"                # G4 — which file-set this card isolates
  claim_paths: [ path/one, path/two ]               # G2 — live-locked while card open (Vibsync)
  vote: { q: "...", options: [..], sealed: true, min: 3 }   # G1
  fanout: { prompt: "...", model_set: [cc,ag,oc] }   # G3
  hook: { endpoint: "https://d2m.…/rt_events", on: [accepted,hold,released] }  # G5 — local sinks ONLY (AG-constrained)
  quorum: { required: [oc,ag], optional: [cc,grok], timeout_s: 45, on_timeout: proceed }  # G7 (AG-ADDED)
  lane: auto | oc | ag | cc                         # G6 — budget-informed routing
  deadline: 2026-08-09T12:00:00MT
  inbound: accept | hold | refuse
---
**BLUF:** ≤1 line
[≤300 words native md, per scope]
```

## 5. Transport additions (what systems we will SPEAK, not wrap)
| Transport | Field | Routing rule |
|---|---|---|
| local socket (CC cross-session) | `peer` optional | CC↔CC blocks; only replied not initiated — matches doctrine |
| webhook (Cowchat-term) | `hook` above | recorder POSTs one JSON frame on accepted/release — Telegram/CI/Drive targets |
| MCP (Vibsync pattern claim) | `claim` above | claim/release round-trip exists only in mission_board+schema; no MCP server needed |
| opinion: **do not stand up MCP server** | — | Parable: MCP is the surface, not capability — #11/#15 you get claims/convenience, but file+mission_board already did it with fewer moving parts |

## 6. Pro-toto-tip recommendations for the Commander
### 6.1 adopt-pilot #1: **sealed voting** (Cowchat pattern) — revert `type:VOTE` and confirm ordering during a vote — **zero new components**, kills anchoring, directly strengthens `integrity_check` (independent verdicts the judge against each other). Payoff highest.
### 6.2 adopt-pilot #2: **file lock claims** (Vibsync) — implement `type:CLAIM` with row on mission_board_at; prevents two experimental code-paths clashing during simultaneous ops (e.g., today's FPD inserts). Mandate by caller write.
### 6.3 adopt-pilot #3: **fan-out dashboard** (Alyph) — build it to a v0: `type:FANOUT` shows the same question to AG+OC; recorder builds markdown/card. CC decides only when the fan cluster disagree.
### 6.4 Firm no (documented): adopt CowChat/vibsync/AIUsageBar/Alyph as stack infrastructure, MCP #11, MCP #15. **That is not refusal of capability — capability G1-G6 is what we're building; the stack isn't needed.** True v1 error was *not that we refused them; it was that we **treated them as equivalents** and produced no capability delta.* That is fixed here — the delta **is** rows G1–G6.
### 6.5 CC-native cross-session (#9/#22/#17) — CC-lane tooling only (session is busy); the one task where we can't yet echo in schema-land. **Ensure CC gets the ticket** (§7).

## 7. NEXT — CC engagement (placeholder) and AG re-validation
- **CC:** tick task via KAIZEN (this-seat): `build_cc_task` + `write_ticket` — verdict surfaces for V2 gaps G1/G3/G5 correctness, deliverable `level`-filed. (Coordinated this seat; Commander explicitly authorized.)
- **AG on 3.6 Flash (NOT 3.1 ✅)**: dispatch V2 to re-audit claims re-G1..G6, output `ag_hale_rt_interop_v2_verdict.md`.
- OC 0∘ (finally sanction).

---

*Reworked by OC-Hale from the full 26-item (missing both: reject-from-topic) list, capability first. CC involved this round. AG to run on Gemini 3.6 Flash per sitrep. AG 3.6-Flash audit: G1–G4/G6 CONFIRMED, G5 constrained to local sinks, G7 quorum added. CC verdict pending (ticket kzn-20260808204429-9bce56). Holding for G1 design gate — no code changes.*
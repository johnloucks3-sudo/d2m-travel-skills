# WAR ROOM — POSITION PAPER
**Author:** HALE-OC (Jet) · **For:** Commander · **Date:** 2026-08-07 · **Status:** CURRENT as of routing update
**Sources:** WAR_ROOM_STANDING.md · ROUND_TABLE_SPEC.md · RT-RETRO · RT-CLAUDEP/RT-TELEGRAM/RT-LOGOFF transcripts · competitive scan

---

## 1. BLUF
War Room is a **standing, 24/7, file-based, cross-engine deliberation system** — Commander-paced playback of pre-written HALE point papers, with per-seat receipts, a recorder-owned transcript, and token discipline by lane. No live-platform build; thin stdlib tooling over existing infra. **Claude lanes run on local Claude MAX; AG runs Gemini 3.6 Flash — never cross-routed.**

## 2. Players
| Player | Engine / model | Role |
|---|---|---|
| Commander | human | presides; sets agenda; approves brief & preview; paced playback; verdict |
| **AG** | **Gemini 3.6 Flash** (contact_ag) | FIRST seat; broad sweep / verification |
| **CC** | **Claude Sonnet (MAX, local)** | precision/judgment; reads AG first |
| **OC (Jet)** | DeepSeek v4 (OpenCode) | data assembly, brief form, deck, recorder, orchestration |
| **Grok** | xAI (omitted until Commander login) | optional seat |

## 3. Dispatch routing (corrected 2026-08-07)
- `/ask` = **Claude Sonnet** (MAX, local `claude -p --model sonnet`)
- `/ask-opus` = **Claude Opus** (MAX, local `--model opus`)
- `/ask-haiku` = **Claude Haiku** (MAX, local `--model haiku`) — cheap MAX lane, NOT for everything
- **AG = Gemini 3.6 Flash only.** Never route Claude to AG (overwhelms AG); never route all Claude to Haiku (crashes Haiku).
- Tool: `scripts/rt_dispatch.py` (AG / CC / HAIKU / OPUS), reports `[TOKEN] in/out` per call.
- Headless `claude -p` fixed (env-pop ANTHROPIC_API_KEY + CLAUDE_CODE_OAUTH_TOKEN + `--mcp-config` + `stdin=DEVNULL`).

## 4. War Room schema (files)
```
OpsCenter/meetroom/
  WAR_ROOM_STANDING.md            standing doctrine
  ROUND_TABLE_SPEC.md             design spec + retro doctrine
  RT-*/                           per-session: BRIEF.md · {seat}_input.txt · TRANSCRIPT.md
    {session}_bluf.md             pre-brief preview (mandatory, 0-token)
    {session}_transcript.md       recorder output + receipts/timeline
  rt_view.py → rt.html            Commander playback deck (d2mluxury.quest/meetroom/rt.html)
  rt_recorder.py                  transcript/recorder (launcher-owned)
  generate_rt_bluf.py             BLUF preview generator
  search_war_room.py              background competitive scan (Poe Perplexity lane)
```

## 5. Procedure — canonical sequence (all players)
1. **Initiating idea** — Commander or any HALE.
2. **OC builds the brief form** → `BRIEF.md` (objective · evidence · asks).
3. **Preview → Commander FIRST** (`{session}_bluf.md`); Commander approves/amends agenda **before any seat speaks**.
4. **Broadcast brief, AG → CC** (AG first; CC reads AG's input before judging); OC files own paper.
5. **Playback** — Commander opens deck: canonical AG→CC→OC, BLUF-then-expand, annotate/rebuttal/skip.
6. **Recorder** — transcript + receipts + timeline (0-token).
7. **Execute + cross-engine verify → git commit.**

## 6. Tool calls / commands available
| Command / tool | Purpose |
|---|---|
| `scripts/rt_dispatch.py AG\|CC\|HAIKU\|OPUS "<prompt>"` | seat dispatch (correct routing + token report) |
| `/ask` · `/ask-opus` · `/ask-haiku` | Claude Sonnet/Opus/Haiku (local MAX) |
| `/ask-gemini` · `/ask-gemini-pro` | AG (Gemini 3.6 Flash / 3.1 Pro) via contact_ag |
| `scripts/generate_rt_bluf.py` | pre-brief BLUF sheet |
| `rt_recorder.py [session]` | transcript + receipts + timeline |
| `OpsCenter/unified_limit_meter.py` | engine limit/GO meter |
| `rt_telegram_24h_check.py` (timer) | RT-TELEGRAM 24h gate |

## 7. Procedures & standing rules
- **Preview-mandatory** — every session, whichever seat invoked, preview before deck.
- **Point papers** — every card is a defense-style BLUF-first paper ≤300 words.
- **Skip rule** — card required only for new finding or disagreement; else one-line concur.
- **Two-seat convergence closes an item** — third = one-liner.
- **Documentation mandatory** — brief, seat inputs, transcript, decision, commit. No chat-scroll-only.
- **Limit governor** — each lane self-monitors (TPM/RPH/RPD); REFUSE / ADVISE / GRACE (self-exclude to healthier lane). Wired via rt_dispatch.
- **Batching** — sequential seats share one brief; parallel share one batch (~15–25% token save).
- **Gates** — design (spec) · build (courtroom/silver) · session (dry-run). Client-send/financial/strategic remain Commander-only.

## 8. Steals adopted (from competitive scan)
Receipts/attribution (ATO) · session replay timeline (AgentOps) · structured debate + referee (llm-war-room) · kill-the-runaway K / rebuttal X on deck · ChatDev 2.0 as web-backplane fallback (prototype evaluated).

## 9. Open / next
- GO↔ZEN decouple (GO funding must not gate ZEN free lane) — standing agenda.
- Wire limit governor fully into rt_dispatch (self-exclude/refuse).
- Grok seat once Commander login.
- RT-TELEGRAM 24h watch gate (06:48 MT, MISSION-795).

— Victory (HALE-OC) · position paper current 2026-08-07
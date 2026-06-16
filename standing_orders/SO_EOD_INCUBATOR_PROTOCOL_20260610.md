# STANDING ORDER — EOD BRIEF + INCUBATOR PROTOCOL
**SO-EOD-INCUBATOR-20260610**
**Effective:** 2026-06-10
**Authority:** Commander Loucks
**Owner:** Hale (COS) — Sterling (A7) audits

---

## PURPOSE

Defines the evening operational rhythm: EOD brief format, incubator search protocol, and the 1730 nomination/execute cycle. Applies to ALL Hale instantiations (Claude Code, OpenCode, Telegram, Claude Desktop).

---

## EOD BRIEF — FORMAT (LOCKED 2026-06-10)

**Send:** d2mconcierge → johnloucks3 · **Time:** 1800 MT daily · **Script:** `agents/thunderbird_eod_brief.py`

Four sections. Exact order. No combining. Suppress empty sections 1 and 4 only — sections 2 and 3 always present.

```
🦅 THUNDERBIRD // [Day Date] · Evening MT

━━━ BEFORE YOU SLEEP ━━━━━━━━━━━━━━━━━━━━━━━━
[Items needing Commander action TONIGHT — suppress if nothing urgent]

━━━ WHAT WE DID TODAY ━━━━━━━━━━━━━━━━━━━━━━━
[Warm prose — 3-5 sentences. Not bullets. The day's wins with meaning and context.
Pull from daily_output_log.json → fallback to mission_board completions.]
[Drive link — today's outputs folder]

━━━ TONIGHT'S SEARCH — Sectors [A] · [B] · [C] ━━━
→ [find 1] — [one-line description]
→ [find 2] — [one-line description]
→ [find 3] — [one-line description]
Gate: [candidate] → [owner] overnight ✓ / Nothing passed tonight
[Drive link — full findings]

━━━ OVERNIGHT QUEUE ━━━━━━━━━━━━━━━━━━━━━━━━━
[Auto-executing missions — suppress if queue empty]
```

**Tone rule:** "What We Did Today" must feel like a trusted deputy briefing the Commander before he steps away. Not a data dump. Not bullets. Warm, direct, genuine. Commander should feel the day was worth it.

---

## 1730 NOMINATION PROTOCOL

**Time:** 1730 MT daily · **Script:** `agents/thunderbird_1730_nomination.py` · **Channel:** Telegram (D2MC2C_bot → Commander ID 7554895206)

**Format:**
```
🦅 1730 — Tonight's sectors: [A] · [B] · [C]
Gate candidate: [name] → [owner] build
Executing in 5 unless redirected.
```

**Execute window:** 5 minutes from send. If Commander does not respond, Wing executes the gate candidate immediately. No second confirmation.

**Override:** Commander replies with redirect/cancel via Telegram → Wing pivots. One reply = one override for that night only.

---

## INCUBATOR SECTOR LIST (10 SECTORS — rotate 3/night)

| # | Sector | What Wing watches |
|---|---|---|
| A | Claude Code | New features, hooks, MCP releases, slash commands |
| B | OpenCode | Updates, capability gaps vs. CC |
| C | CC/OC Augmentation | MCP servers, plugins, bridges |
| D | Agentic Apps | New agent frameworks, orchestration tools |
| E | GitHub New Releases | Trending AI repos, last 7 days, >50 stars |
| F | LLM Releases | New models, API changes, pricing shifts — all providers |
| G | Travel Tech B2B | Cruise/air/hotel APIs, booking tools, supplier portals |
| H | AI Voice/Multimodal | Voice agents, client-facing presentation tools |
| I | Competitor Intel | What luxury + AI travel shops are building |
| J | CRM/Comms Tools | Client follow-up automation, outreach, pipeline tools |

**Rotation rule:** Wing nominates 3 sectors each evening. Fast-moving sectors (A, E, F) rotate more frequently. Commander and Hale confirm nightly at the 1730 ping. If no Commander reply in 5 minutes, Wing executes the nominations.

**⚠️ NO GATE ON SEARCH — PERMANENT (Commander directive 2026-06-14).** Tech searches have NO screening gate. The purpose of tech search is to look BEYOND our boundaries — a revenue gate defeated that intent and is permanently removed. Surface ALL findings raw; the Commander decides what matters. No 90-day filter, no degrees-from-revenue test, no silent cancellation. **No gate may be re-applied to any tech search without the Commander's express approval.** This applies EVERYWHERE, ALL THE TIME — every sector, every platform, every agent.
*(Build prioritization is a separate, later step — anything we choose to BUILD still respects the three Commander gates. But search/exploration is unfiltered.)*

**Config file:** `OpsCenter/eod_incubator_config.json` — update each evening with tonight's sectors and gate candidate.

---

## FLOW (NIGHTLY)

```
1730 MT  — Wing nominates 3 sectors via Telegram
1735 MT  — No reply = execute. Reply = pivot.
[Evening] — Wing runs sector searches
[Overnight] — Wing builds gate-passing candidate
0600 MT  — AM brief surfaces: what was found + built last night
```

---

## TIMERS

| Timer | File | Fires |
|---|---|---|
| EOD brief | `~/.config/systemd/user/thunderbird-eod-brief.timer` | 1800 MT daily |
| 1730 nomination | `~/.config/systemd/user/thunderbird-1730-nomination.timer` | 1730 MT daily |

Both use `.venv/bin/python3`. Both have date-keyed send locks (`OpsCenter/eod_sent_YYYYMMDD.lock`).

---

## WHAT WAS KILLED

| Script/Timer | Status |
|---|---|
| `wing_eod_routine.py` | No active caller — dead on disk |
| `thunderbird-spsa-eod-brief.timer` | Disabled + stopped |
| `d2m-incubator-evening-review.timer` | Disabled + stopped |

---

## PERSISTENCE — ALL HALE INSTANTIATIONS

This SO is the authoritative protocol. All Hale engines (Claude Code, OpenCode, Telegram, Claude Desktop) reference this file for EOD/incubator behavior. Config state lives in `OpsCenter/eod_incubator_config.json`.

---

*SO-EOD-INCUBATOR-20260610 · Author: Hale (Commander override, PRODUCTION-LOCK bypass, 2026-06-10) · Sterling A7 audits*

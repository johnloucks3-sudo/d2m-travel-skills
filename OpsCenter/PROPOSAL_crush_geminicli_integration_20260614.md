# INTEGRATION PROPOSAL — Crush & Gemini CLI
**For:** Commander (John Loucks) · **Prepared by:** Hale (synthesis) + staff · **Date:** 2026-06-14
**Source:** Sector-A/B unfiltered tech harvest (NO-GATE directive 2026-06-14)

---

## ⚙️ EXECUTION STATUS (updated 2026-06-14 — Hale owns)
- ✅ **Aider retired** — binaries removed + uv-uninstalled, configs archived to `archive/aider_retired_20260614/`, refresh hook cleaned. Reversible.
- 🟡 **Gemini CLI** — v0.46.0 installed + tool verified functional. **Blocked on auth**: both available creds permission-denied. Needs 1 Commander step (interactive `gemini` OAuth login → free 1,500/day Flash tier).
- 🚫 **Crush** — shelved per majority.
- ✅ **Goose KEEP decision** — ELON asked to also delete; NO. Goose is live (runs daily: airline_monitor, x_osint, factbook_refresh + GooseD2M Telegram bot). Not a kill candidate.

## BOTTOM LINE
- **Gemini CLI → ADOPT (conditional, 30-day).** Free Haiku-tier offload that relieves Claude MAX weekly-bucket pressure at $0 marginal. Rides credential surface we already maintain (MISSION-127 complete). Condition: scope to ROUTINE work only + it should CONSOLIDATE the existing Gemini plumbing, not append to it.
- **Crush → PASS / PILOT-narrow.** Majority PASS. One narrow exception: Sterling would PILOT it on the Chromebook/ttyd path only (Go single-binary survives where Node engines die), fenced from protected files, with intent to retire Aider there. Defer unless that specific need is named.
- **Independent action (ELON kill-audit):** **Retire Aider (all 3 variants — `aider`, `aider-gemini`, `aider-max`).** 30 days zero usage. Subtraction = addition. Do this regardless of the add decision.

---

## STAFF MATRIX

| Seat | Crush | Gemini CLI | Key contribution |
|---|---|---|---|
| 🛠️ Sterling (A7) | **PILOT** (Chromebook only, fenced) | **ADOPT** | Verified FSL-1.1-MIT = non-issue; flagged AGENTS.md context-collision risk |
| ⚡ ELON (A12) | **PASS** | conditional yes (consolidate, don't add) | No capability gap; nominates Aider kill |
| 💰 Harlan (A9) | **PASS** | **ADOPT** (conditional) | Corrected quota: 1,500/day Flash, 50/day Pro; offload = bucket relief not $ |
| 🎯 Castillo (A5) | **decline/defer** | adopt as offload only | ttyd already solves mobility; resilience = insurance not oxygen |

**Consensus:** Gemini CLI yes (scoped). Crush no/defer (one narrow pilot dissent). Aider = kill.

---

## CORRECTED FACTS (load-bearing — earlier brief was stale)
1. **Gemini free tier:** 1,500 req/day Flash/Flash-Lite (Haiku-tier); 2.5 Pro gated to **50/day**. Offload is for routine work, NOT synthesis/client copy.
2. **Crush license:** FSL-1.1-MIT. Restricts only "competing use" (shipping a rival dev-CLI product). D2M internal use = fully clear. Auto-converts to MIT 2yr post-release.
3. **MISSION-127 = COMPLETE.** `core/ai_infra/gemini_client.py`, `gemini_file_reader.py`, `OpsCenter/gemini_direct_dispatcher.py` live; 1M-context tier active; cost-guard logging on. Gemini CLI is a new doorway to owned infra.
4. **Usage band:** ~34% weekly / ~41% Sonnet (snapshot 2026-06-09, ~6d stale — refresh before citing). We are NOT pinned to the Anthropic ceiling.

---

## REPO HARD DATA (pulled 2026-06-15)
| | Crush (charmbracelet/crush) | Gemini CLI (google-gemini/gemini-cli) |
|---|---|---|
| Stars | 25.4K | 105.3K |
| License | FSL-1.1-MIT | Apache-2.0 |
| Lang | Go (single binary) | TypeScript (Node) |
| Latest release | v0.77.0 (Jun 14) | v0.46.0 (Jun 10) |
| Last push | Jun 15 (today) | Jun 15 (today) |
| Commits since Jun 1 | 65 | 21 |
| Health | Very active | Very active, ~3,600+ contributors |

---

## RECOMMENDED ACTION (if Commander approves)
**Phase 1 — Gemini CLI pilot (Sterling owns, 30-day)**
- [ ] Auth on existing free Google account; one headless digest prompt
- [ ] Verify $0 OpenRouter + $0 Claude bucket hit (usage ledger before/after)
- [ ] Benchmark one digest vs OpenCode/DeepSeek (quality + latency)
- [ ] Wire as Hale Brain "free routine/large-context lane" behind approved spawn wrapper
- **Metric:** ≥50% of routine digest jobs moved off paid budget within 30 days
- **Consolidation condition (ELON):** retire the ad-hoc MISSION-127 dispatch sprawl + pick ONE free-reasoning lane (Gemini OR OpenCode-DeepSeek, not both)

**Phase 2 — Aider retirement (ELON/Sterling)**
- [ ] Confirm zero usage in logs (30-day), archive configs, uninstall 3 variants
- [ ] Log in hale_decisions.md

**Phase 3 — Crush (DEFERRED)**
- Shelf unless a specific on-device/offline coding need emerges that ttyd cannot meet. Trigger documented; no build until then.

---

## GATES CHECK
None of this hits the three Commander gates (client send / financial / strategic) — all internal infra, $0. Hale executes Phases 1–2 on Commander GO. Crush stays shelved.

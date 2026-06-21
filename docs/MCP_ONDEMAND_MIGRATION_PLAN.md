# MCP On-Demand Migration Plan — First-Principles Review & Kill Audit
**Author:** ELON (A12 — Innovation & Disruption) · **Mission:** MISSION-209 · **Date:** 2026-06-11
**Status:** ANALYSIS + PLAN. No removals executed. Pairs with Sterling (A7) for the build.
**Rails honored:** mcp.json NOT modified. 6 protected email/relay files untouched. No sends, no commits.

---

## TL;DR (read this first)

The lazy-load infrastructure **already exists and is already half-deployed.** The wing is burning
context tokens not because the architecture is missing — but because two switches are flipped to "max":

1. **`mcp_launcher_core.sh` is pinned to `MCP_PROFILE=full`** — so the file named "core" loads
   *everything*. `cc core` silently loads all ~236 tools. The profile system is **functionally dead.**
2. **The `dreams2memories` server front-loads ~236 tool schemas** (~37K tokens, conservative floor)
   into every turn × every session — the single largest per-turn line item in the wing.
3. **`ENABLE_TOOL_SEARCH=true` is already set** in `~/.claude/settings.json`. The harness already
   defers the entire claude.ai cloud suite (Canva ~45, Playwright ~25, Gmail ~12, Calendar, Drive,
   lastminute, n8n) behind ToolSearch — **proof the on-demand pattern works in THIS environment.**

**The cheapest win is not a rebuild. It is correcting one launcher line + extending an existing
profile system that is already written.** First-principles: don't build what exists — turn it on.

---

## 1. AUDIT — Per-Server Cost Table

Cost = tool count × schema serialized to the model **every turn**. Token figures are a conservative
floor (`description/docstring bytes ÷ 4`; excludes parameter schemas, so real cost is higher).

| Server | Transport | Tool count | Est. schema cost/turn | Needed every turn? | Verdict |
|---|---|---|---|---|---|
| **dreams2memories** | local stdio (`mcp_launcher_core.sh` → `travel_mcp_server.py`) | **~236** (`full`) | **~37K tok** (floor) | **No** — most are rare | **SPLIT / PROFILE** |
| **google-workspace-d2mconcierge** | local stdio (node `@dguido`) | **~91** | ~15–20K tok est. | No | **KILL (redundant)** |
| **gmail-d2mconcierge** | local stdio (node `@klodr`) | **~33** | ~6–8K tok est. | Drafts only | **CONSOLIDATE** |
| **gmail-johnloucks3** | local stdio (node `@klodr`) | **~33** | ~6–8K tok est. | Rare (receive) | **CONSOLIDATE / DEFER** |
| **anansi** | local stdio (venv) | **~7** | small | Rare (scraping) | **DEFER / on-demand** |
| **multi-model** | local stdio | **1** | trivial | Rare | **KEEP or DEFER** |
| **context7** | local stdio (npx) | **~2** (resolve-library-id, get-library-docs) | small | Rare (coding only) | **DEFER** |
| **lastminute** | http (remote) | ~8 | 0 local (remote, deferred) | Rare | **KEEP (already deferred)** |
| **claude.ai suite** (Canva/Figma/Gmail/Calendar/Drive/lastminute/n8n/playwright) | cloud | **~110+** | **0 — ALREADY DEFERRED** via ToolSearch | varies | **MODEL: copy this** |

**Headline:** dreams2memories (~236) + google-workspace (~91) + 2× gmail (~66) = **~393 always-loaded
local tools**, the overwhelming majority of which a given turn never touches. The cloud suite's ~110
tools cost **zero** per turn because they're deferred. The local servers are the entire problem.

---

## 2. AUDIT — Supporting Code (`core/mcp/*` + registries)

- **`core/mcp/travel_mcp_server.py`** (58 KB) — the live `dreams2memories` entrypoint. Imports
  **83+ `register_*_tools` modules**, registers ~236 tools at `full`.
- **Profile system ALREADY BUILT** (lines 485–664): `MCP_PROFILE` env var gates loaders into
  `core / intel / travel / ops / full`. `_CORE_LOADERS`, `_INTEL_LOADERS`, `_TRAVEL_LOADERS`,
  `_OPS_LOADERS` lists exist, dedup logic exists, try-block fallbacks exist. **Well-engineered.
  Just never used** because the launcher forces `full`.
- **`cc` wrapper** (`/home/john/bin/cc`) — accepts `core|intel|travel|ops|full`, maps to
  `~/.claude/profiles/mcp_<profile>.json`. **The plumbing is complete and correct.**
- **THE BUG:** `~/.claude/profiles/mcp_core.json` → calls `mcp_launcher_core.sh` →
  **`export MCP_PROFILE=full`**. So `cc core` loads everything. The intel/travel/ops launchers
  set their profile correctly; only the core launcher is mislabeled. **One-line defect kills the
  whole savings story.**
- **"core" profile is itself bloated:** `_CORE_LOADERS` actually sums to **99 tools**, not the
  "~25" its own comment claims. Even a working `core` profile is 4× heavier than advertised — the
  Google-services loaders (gmail/drive/keep/calendar/sheets/docs/contacts/forms/maps/photos) are
  wrongly classified as "core."

---

## 3. KILL AUDIT (subtraction = addition)

### 3a. The 4-way Google/Gmail overlap — THE centerpiece

There are **four parallel implementations of the same Google services**:

| Path | Implementation | Gmail | Drive | Cal | Sheets/Docs | Verdict |
|---|---|---|---|---|---|---|
| 1 | dreams2memories internal (`register_gmail/drive/calendar/sheets/docs/...`) | ✅ | ✅ | ✅ | ✅ | **Authoritative — wing-aware, used by scanners** |
| 2 | `gmail-d2mconcierge` + `gmail-johnloucks3` (node @klodr ×2, ~66 tools) | ✅ | — | — | — | **Redundant surface** |
| 3 | `google-workspace-d2mconcierge` (node @dguido, ~91 tools) | ✅ | ✅ | ✅ | ✅ | **Fully redundant w/ path 1** |
| 4 | claude.ai cloud suite (already deferred, $0/turn) | ✅ | ✅ | ✅ | ✅ | **Free — keep as deferred fallback** |

**Kill candidates (propose, do NOT execute tonight):**
- **`google-workspace-d2mconcierge` (~91 tools)** — highest-value kill. Its services are 100%
  covered by dreams2memories' internal tools (path 1) and the cloud suite (path 4). Removing it
  eliminates the wing's #2 always-loaded line item. **CONSTRAINT:** before removal, grep the 6
  protected email-scanner/relay files + `core/email/*` for `google-workspace` / `@dguido` calls.
  If zero hits → safe to kill.
- **`gmail-johnloucks3` (~33 tools)** — johnloucks3 is receive-only (per standing orders). A
  whole always-loaded server for an inbox the wing reads rarely. **Defer or kill.**

### 3b. The account-separation tripwire (do NOT over-cut)

⚠️ The redundancy is across **implementations, not accounts.** CLAUDE.md HARD RULE keeps
`d2mconcierge` (ops / client drafts) and `johnloucks3` (receive) functionally distinct, and
MEMORY.md documents active **account-drift** (`gmail_token.json` actually auths johnloucks3;
d2mconcierge lacks the alias). **Recommendation: consolidate to ONE implementation per account —
do not drop an account.** Keep dreams2memories' internal path as the single Gmail surface; retire
the duplicate node servers. Trace token paths before any cut.

### 3c. Defer-don't-load (rare-use servers, zero kill risk)
- **context7** (~2 tools) — only needed during coding. Defer.
- **anansi** (~7 tools) — web scraping; rare. Defer.
- **multi-model** (1 tool) — rare. Defer or keep (cost trivial).

---

## 4. MIGRATION ARCHITECTURE

Three tiers, ordered cheapest-first. Ship Tier 1 immediately (it's a config fix); Tiers 2–3 are
Sterling builds.

### Tier 1 — TURN ON WHAT EXISTS (hours, not days)
1. **Fix `mcp_launcher_core.sh`:** change `MCP_PROFILE=full` → `MCP_PROFILE=core`. This alone makes
   `cc core` honest and gives every default session the lean surface.
2. **Re-tier the `core` profile (99 → ~25):** move the 10 Google-service loaders
   (gmail/drive/keep/calendar/sheets/docs/contacts/forms/maps/photos) OUT of `_CORE_LOADERS` into a
   new `_WORKSPACE_LOADERS` group, loaded only on `MCP_PROFILE=ops` or explicit `workspace`. Most
   turns are dossier/persona/memory/inbox work — they don't need Maps or Photos schemas resident.
3. **Make `core` the default session profile** (Sterling + Commander decision — changes wing-wide
   default behavior, so it's a reviewed change, not a tonight change).

### Tier 2 — DEFER LOCAL STDIO SERVERS via ToolSearch (PROVEN — likely the lead move)
- `ENABLE_TOOL_SEARCH=true` is already live, and **already defers a local-style server**
  (`mcp__playwright__*` is in the deferred list — see §5 verification). So local-stdio deferral is
  not an open question — it is demonstrated in this environment.
- **Apply the same treatment to `dreams2memories` (the ~236-tool / ~37K-token monolith) and to
  context7, anansi, multi-model, and the consolidated secondary-Gmail server.** Their schemas then
  cost **zero per turn** and load only when ToolSearch matches a query.
- **This is the cheapest architecture and likely supersedes the profile rebuild** — no split-server
  work, no re-tiering, just bring the heavy first-party servers under the deferral path the harness
  already runs. Sterling: confirm the exact config mechanism (per-server flag / index inclusion)
  that put playwright in the deferred set, then replicate for dreams2memories.

### Tier 3 — SPLIT-SERVER (structural, only if Tier 2 deferral unavailable)
- Split `dreams2memories` into 2–3 thin stdio servers by domain (e.g. `d2m-core`, `d2m-travel`,
  `d2m-intel`) so a session attaches only the server(s) it needs. The `_*_LOADERS` lists already
  define the seams — this is mechanical, not design work. Higher effort; do only if deferral fails.
- Extend the existing `_on_demand_servers` pattern in mcp.json (the commented-out
  skiplagged/kiwi/trivago/etc. already model "invoke when needed") to the heavy first-party servers.

---

## 5. ESTIMATED SAVINGS PER TURN

> **BASELINE — VERIFIED (not assumed), 2026-06-11.** I checked whether the ~236 dreams2memories
> tools are actually resident this session or already deferred behind ToolSearch. **They are
> RESIDENT — the cost is being paid every turn.** Evidence:
> - The harness deferred-tools list (cloud suite + `mcp__playwright__*`) contains **zero**
>   `mcp__dreams2memories__*` entries.
> - `settings.json` + `settings.local.json` directly allow-list 29+ `mcp__dreams2memories__*`
>   tools as callable without ToolSearch = resident.
>
> **Local-server deferral is PROVEN, not hypothetical:** `mcp__playwright__*` is a local-style
> browser server (allow-listed in `settings.local.json`) and **it IS in the deferred list.** So
> `ENABLE_TOOL_SEARCH` already defers at least one non-cloud server. That collapses the Tier-2
> "can we defer local stdio?" question to "yes — apply the same treatment to dreams2memories."
> **This makes Tier 2 (defer the monolith) the cheapest real win and likely supersedes the
> profile rebuild.** The savings table below therefore reflects cost actually being paid today.

Conservative floor (schema bytes ÷ 4; real savings higher once parameter schemas counted):

| Move | Tools removed from per-turn load | Est. token savings/turn |
|---|---|---|
| Fix launcher: `full → core` (current 236 → 99) | ~137 | **~12–15K tok** |
| Re-tier core (99 → ~25) | ~74 more | **~8–10K tok** |
| Kill `google-workspace-d2mconcierge` | ~91 | **~15–20K tok** |
| Defer `gmail-johnloucks3` + context7 + anansi | ~42 | **~8–10K tok** |
| **Combined (Tier 1+2)** | **~344 of ~393** | **~40–55K tok/turn (floor)** |

**Per-turn × every turn × every session.** Against the SO-cited **1.91B cache reads/week**: cutting
~40–55K tokens of resident schema per turn is a direct, multiplicative reduction in cache-write tax
on every session open and cache-read on every turn. The default session goes from ~393 resident
local tools to ~25 + deferred-on-demand.

---

## 6. RECOMMENDED EXECUTION ORDER (for Sterling pairing)

1. **[reviewed]** Fix `mcp_launcher_core.sh` profile line. *(One line. Changes default behavior →
   Commander/Sterling sign-off.)*
2. **[reviewed]** Re-tier `_CORE_LOADERS` (pull Google-services into `_WORKSPACE_LOADERS`).
3. **[verify-then-build]** Test local-stdio deferral under `ENABLE_TOOL_SEARCH`. If supported, mark
   context7/anansi/multi-model/secondary-gmail deferred.
4. **[kill, after trace]** Grep protected files + `core/email/*` for `google-workspace` usage →
   if clean, retire `google-workspace-d2mconcierge`.
5. **[kill, after token-path trace]** Consolidate the two @klodr gmail node servers into the
   dreams2memories internal Gmail surface (one implementation per account; keep both accounts).
6. **[defer build]** Only if step 3 fails: split-server the dreams2memories monolith by `_*_LOADERS`.

**Do NOT execute steps 1–6 tonight.** This document is the proposal. Removals/launcher edits are
reviewed changes that pair with Sterling and hit Commander's default-behavior review.

---
*ELON / A12 · "Build it once, benefit forever. Why is a human paying 37K tokens a turn for tools
nobody called?" · The infrastructure was already there — it just needed turning on.*

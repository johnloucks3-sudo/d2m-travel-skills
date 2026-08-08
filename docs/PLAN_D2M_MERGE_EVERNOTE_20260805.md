# PLAN: SLIDE ALL TRAVEL NOTEBOOKS INTO D2M — EVERNOTE CONSOLIDATION
**Campaign Code:** OPERATION D2M MERGE
**Date:** 2026-08-05
**Author:** OC (HALE-OC) — survey complete, plan awaiting Commander go
**Status:** **PLAN — SURVEY DONE. NO NOTES MOVED.** Commander approval required before any merge (Evernote moves are irreversible-ish; staging/backup first).
**Skill used:** `evernote-survey` (3 techniques: search-input fill, Virtuoso note-list scroll, Notebooks-grid enumeration)

---

## OVERALL PROGRESS
`[███░░░░░░░░░░░░░░░░░] 10%` — Wave 1 mechanism validated (1 note moved 2026-08-05). Commander approved Option A (no token, delegated batch). ~250 individual note moves remaining across 23 notebooks. Tracking: `output/evernote_merge_tracker.md`.

---

## PURPOSE
Consolidate the 30+ travel-related Evernote notebooks scattered across the account into the **D2M** notebook family, so client travel knowledge lives in one place (mirrors the Obsidian vault reorg + Drive/Gmail schema work in OPERATION LIGHTNING CLEAN).

## BACKGROUND — WHAT THE SURVEY FOUND

**Evernote account (yodainva@gmail.com):**
- **236 notebooks total** (count includes notebook stacks + sub-notebooks)
- **3,869 notes** across all notebooks
- **Inbox: 1,748 notes** (the big consolidation target — inventory extracted to `output/evernote_inbox_titles_full.txt`, ~500 rendered by web sidebar, ~1,248 more only reachable via search/API)

**Confirmed stacks / sub-notebook structure (2026-08-05):**
The web Notebooks grid renders **37 top-level rows**; the "236" total lives inside **collapsed stacks**. Confirmed stack→sub-notebook pairs:
| Stack | Sub-notebooks observed |
|---|---|
| `Client Notebook: Axel LLC` | `Work` (stack parent itself = 0 notes) |
| `Client Notebook: Collins Management` | `Work` |
| `Exams Library` | `School` |
| ⚠️ Other stacks (incl. likely travel ones) | **Not enumerable via browser DOM** — the web grid collapses stacks and the sidebar tree is not exposed to JS. See "Open item" below. |

**Top-level travel notebooks identified (the merge candidates):**

| Group | Notebooks | Notes (approx) |
|---|---|---|
| **Legacy cruises (by date)** | 161031 Oceania Cruise · 190430 Regent Cruise · 210528 RSSC (Cancelled) · 210829 RSSC (Cancelled) · 220430 Regent (Cnxd) · 220925 Oceania Cruising · 221013 Oceania Cruising · 230401 Regent Cruise · 230803 Oceania Cruise · 241025 Regent Cruise · 250330 Regent Cruise · 250330 RSSC Cruise · 250707 Regent Voyager Lon-Lon · 251012 AMA River Cruise · 260520 RSSC Alaska · 270512 Silversea Cruise | ~190 |
| **Personal trips** | 220528 Trip to VA · 220614 Minot Ryan Chg Cmd · 220617-20 Winnipeg · 220907 HHS Reunion · 230626 Iceland Trip · 250601 50th Anniv Hawaii · 2025 Tuscany House | ~10 |
| **General travel** | Travel General · Travel Past/Planned | ~14 |
| **Client notebooks** | Client Notebook: Axel LLC (+Work sub) · Client Notebook: Collins Management (+Work sub) | ~3 |
| **D2M family** | D2M (1) · D2M Clients (96) | 97 |

## OPEN ITEM — SUB-NOTEBOOK INVENTORY GAP (need before Wave 1 executes)

The browser survey confirmed the stack model but could NOT enumerate the full sub-notebook list (web grid collapses stacks; sidebar tree not JS-reachable). Two clean paths to close it:
1. **Evernote developer token** (`evernote.com/DeveloperToken.action`) → use `thunderbird_evernote_backup.py`'s raw-Thrift path or `evernote3` SDK to list stacks+notebooks authoritatively. **Best option.**
2. Browser: expand each stack manually in the Notebooks page sidebar (click stack → click sub-notebook). Slow but zero-dependency.

**Recommendation:** get the developer token — it also unlocks the ~1,248 unreachable Inbox notes (search/API) for Wave 3. Without it, Wave 1 proceeds on the 37 known top-level notebooks only, and stacks are handled per-stack as discovered.

## DISCUSSION — THE PROPOSED MERGE

**Target structure — ONE D2M home for client travel:**

```
D2M                          ← becomes the holding notebook for all travel
├── (merge: all legacy cruises)
├── (merge: personal trips)
├── (merge: Travel General, Travel Past/Planned)
├── (merge: Client Notebook: *)
└── D2M Clients               ← keep separate (active client dossiers, 96 notes)
```

**Merge mechanics (Evernote web app):**
1. **Backup first:** export each source notebook to `.enex` before moving (Evernote export in the notebook More menu → Export notes). Staged to `/home/john/Thunderbird/backups/evernote_merge_20260805/`.
2. **Merge via "Move to notebook"** on each note, OR use Evernote's notebook merge if available. Tag each merged note with its origin notebook name (e.g. `#origin:170925-oceania`) so nothing is lost.
3. **Cancelled/legacy cruises (210528/210829/220430 RSSC):** still merge — they're historical client travel knowledge, tagged with cancelled status.
4. **Inbox (1,748):** classify first via the inventory, then route each note to D2M (travel) or its proper notebook (non-travel). Never auto-purge.
5. **Verify:** note count before == after (no loss), spot-check 10 merged notes retain their origin tag.

**Constraints (inherited from OPERATION LIGHTNING CLEAN):**
- Zero hard deletes, ever. Everything is a move, backup, or staging.
- Client send / financial / strategic gates untouched.
- Blackout 06:30–10:30 MT — no bulk merges during Commander hours.

## OPINION
- The date-keyed legacy cruise notebooks (~16 of them) are the obvious first wave — low risk, clearly travel, clearly historical.
- Do the **Inbox classification** as a separate pass after the notebook merges — it's the largest and most mixed bucket.
- "D2M Clients" should stay its own notebook (96 active notes, distinct purpose) rather than flattening into D2M.

## RECOMMENDATION
1. Commander approves this plan.
2. Wave 1 (safe): merge the 16 legacy cruise + 7 personal trip notebooks into **D2M**, with `.enex` backup + origin tags. RDD: +1h from go.
3. Wave 2: Travel General + Travel Past/Planned + Client Notebooks → D2M. RDD: +30m.
4. Wave 3 (separate plan): Inbox 1,748-note classification. RDD: +2h, needs the full API/search inventory first.
5. Back-gate each wave via `integrity_check.verify_and_record()` (cross-engine, ground truth note counts).

---

> Awaiting Commander go for Wave 1. Nothing moved. Backups will precede every merge.

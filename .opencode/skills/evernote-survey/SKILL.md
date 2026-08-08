# Evernote Survey via bsk

Survey Evernote notebooks/notes using the bsk browser session (logged-in browser). Enumerate notebooks, count notes per notebook, assess Inbox→D2M merges. Zero deletions — survey only.

## Trigger
"survey evernote", "evernote notebook counts", "evernote inbox", "evernote notes", "evernote D2M Main"

## When to use
- Count notes in a specific Evernote notebook (e.g. D2M Clients, Inbox)
- Enumerate the notebook tree
- Assess whether Inbox notes should merge into an existing notebook

## Prerequisites
- bsk daemon running + browser connected (`bsk doctor`)
- Evernote web login available (credentials in `/home/john/Thunderbird/.env`: `EVERNOTE_EMAIL`, `EVERNOTE_PASSWORD`)

## Procedure

### 1. Session lifecycle
```bash
SID=$(bsk session start | tail -1)
# ALWAYS stop the session when done:
bsk session stop "$SID"
```

### 2. Navigate + login check
```bash
bsk navigate "https://www.evernote.com/Home.action" --session "$SID"
# If redirected to accounts.evernote.com/login:
bsk snapshot --session "$SID" | head -40   # find email field (@e3 typically)
bsk fill --value "yodainva@gmail.com" --ref e3 --session "$SID"
bsk click @e2 --session "$SID"             # Continue button
# (Password entry happens in the redirect; snapshot to find the password field)
```

### 3. CRITICAL: the search-input mechanism (lesson learned 2026-08-05)
**`bsk type` IS NOT A SUBCOMMAND — it fails silently.** The correct tool is:
```bash
bsk fill --value '<text>' --ref eX --session "$SID"
```
- `bsk fill` needs `--value` (NOT a positional) and the target as `--ref eX` or a CSS selector.
- The Evernote search input is a **textbox "Search or ask a question..."** (ref @e3 in the search dropdown). Snapshot to find the live ref — refs invalidate after every navigation/render.
- After fill: `bsk press "Enter" --session "$SID"`, then `sleep 3` for the SPA to render.

### 4. Count notes in a notebook (the reliable path)
```bash
# Open the search dropdown, find the textbox, fill the notebook query:
bsk click @e1 --session "$SID"            # "Edit search" button
sleep 1
bsk snapshot --session "$SID" | grep -iE "searchbox|textbox \"Search"
# → textbox "Search or ask a question..." = @e3
bsk fill --value 'notebook:"D2M Main"' --ref e3 --session "$SID"
bsk press "Enter" --session "$SID"
sleep 3
bsk snapshot --session "$SID" | grep -iE "heading \"|StaticText \"[0-9]+\""
# → heading "D2M Clients96" / StaticText "96" = note count
```

### 5. Notebook name resolution (quirk)
`notebook:"D2M Main"` may resolve to a different actual notebook name. Observed 2026-08-05:
- "D2M Main" → actual notebook **"D2M Clients"** (96 notes)
- "Inbox" → actual notebook **"Inbox"** (10 notes)
- Notebooks view shows total count: `main "Notebooks 236"` (236 notebooks exist)
If a query returns an unexpected notebook, snapshot the heading — it names the actual notebook resolved.

### 6. Inspect Inbox contents (for merge assessment)
```bash
bsk fill --value 'notebook:"Inbox"' --ref e3 --session "$SID"
bsk press "Enter" --session "$SID"
sleep 3
bsk snapshot --session "$SID" | grep -iE "button \"" | grep -viE "searchbox|textbox|Home|Tasks|Notebooks|Tags|Notes|Shared|Templates|Files|Trash|More|Edit|New|What's|Account|expand|AI|arrow"
```

## Output
Write findings to `output/evernote_survey_YYYYMMDD.md`:
- Total notebook count
- Per-target-notebook note counts
- Inbox note list + merge recommendation (only propose — never move notes; Commander decides)

## Rules
- **Survey only. Never move, delete, or tag notes** — that's the Commander's call.
- Always `bsk session stop` at the end (5-min idle timeout is not reliable).
- Re-snapshot after every action — refs invalidate constantly in the Evernote SPA.
- If navigation times out (SPA-heavy), go back via `bsk click @e1` (Edit search) rather than re-navigating the URL.

## Virtualized note list — the correct scroll technique (lesson #2, 2026-08-05)

Evernote's note list is a **React Virtualized grid**. Note-title buttons live inside `DIV.ReactVirtualized__Grid__innerScrollContainer` — but that inner div does **NOT** scroll (no overflow). The scrollable parent is the **outer grid element** (has `overflow-y` + `scrollHeight > clientHeight + 500`).

**What FAILED (do not repeat):**
- Setting `scrollTop` on the inner container or on *every* div matching `scrollHeight > clientHeight + 300` — the grid re-renders and snaps back; you capture the same ~11 visible titles every cycle.
- `bsk press End` / keyboard scrolling — focus lands on the wrong element.

**The working pattern — find the single scroll element, then page it:**
```bash
# 1. Find the real scroll container (the grid's overflow parent):
bsk evaluate "(() => { const inner=document.querySelector('.ReactVirtualized__Grid__innerScrollContainer'); let el=inner; while(el&&!(el.scrollHeight>el.clientHeight+500)) el=el.parentElement; return {cls:el.className, sh:el.scrollHeight, ch:el.clientHeight}; })()" --session $SID
# → returns the ONE div with overflow + big scrollHeight (e.g. sh=14000, ch=740)

# 2. Scroll THAT element only, in N steps, extracting titles each step:
#    (grab its unique class or use a persistent selector; step = sh/N * i)
```

**Also learned:** the "Smart results (10)" count is NOT the notebook total. Always click the actual notebook (`@e42 button "Inbox"`) or read the `heading "Inbox1748"` — that number (1748) is the real note count. Search `notebook:"X"` returns "1000+ notes found" (capped display), so read the notebook heading instead for exact totals.

## Notebook list enumeration (lesson #3, 2026-08-05)

The **Notebooks page** (`main "Notebooks 236"`) is also React Virtualized. The `heading "Notebooks 236"` count includes **stacked/collapsed sub-notebooks** — the visible scroll window only renders top-level notebooks (~37). To enumerate:
1. Open Notebooks view, then find the scroll element:
```bash
bsk evaluate "(() => { const g=document.querySelector('.ReactVirtualized__Grid'); let el=g; while(el&&!(el.scrollHeight>el.clientHeight+100)) el=el.parentElement; el.setAttribute('data-nbscroll','1'); return {sh:el.scrollHeight,ch:el.clientHeight}; })()" --session $SID
```
2. Page it in steps, reading `.ReactVirtualized__Grid__innerScrollContainer button` innerText (name = first line, count = next line):
```bash
bsk evaluate "const el=document.querySelector('[data-nbscroll=1]'); if(el) el.scrollTop=el.scrollHeight/30*$i;" --session $SID
# separate read call after each scroll
```
**Pitfall:** top-level-only renders even when the total says 236 — the extra are notebook STACKS. If you need stacked notebooks, expand stacks in the sidebar tree; the Notebooks page grid shows only top level.

**Observed top-level travel notebooks (2026-08-05):** legacy cruise notebooks keyed by date (161031 Oceania, 190430 Regent, 210528 RSSC, 220925 Oceania Cruising, 230401 Regent, 250330 RSSC, 270512 Silversea, etc.), trip notebooks (220528 Trip to VA, 230626 Iceland, 250601 Hawaii, 2025 Tuscany), `Travel General`, `Travel Past/Planned`, `Client Notebook: <name>`, plus `D2M` (1 note) and `D2M Clients` (96 notes).

## Stacks & sub-notebooks (lesson #4, 2026-08-05)

Evernote **stacks** (folder groups) contain sub-notebooks. The web Notebooks page renders **top-level rows only** — the heading total (e.g. "236") counts stacks' sub-notebooks too, but the grid does NOT render them collapsed. Confirmed pattern: `Client Notebook: Axel LLC` (stack, 0 notes itself) → `Work` (sub-notebook). Sub-notebook rows appear as separately-named buttons under the stack row in the grid when expanded.

**Limitations discovered (do not re-fight):**
- The sidebar notebook tree is NOT reachable via JS `[role=treeitem]` — the 12 treeitems are app chrome with empty labels.
- The Notebooks grid has no expandable stack rows reachable via click/evaluate (row click navigates instead).
- `notebook:"Stack Name"` search on a stack returns "No notes found" (stack itself has no notes; sub-notebooks do).
- **Full sub-notebook enumeration requires the Evernote developer token** (`evernote.com/DeveloperToken.action`) + `evernote3` SDK or raw-Thrift (`api/thunderbird_evernote_backup.py` has the pattern). Browser DOM cannot list them reliably.

**For plans:** treat stack parents as 0-note containers; route merge work at the sub-notebook level. Flag the token as a prerequisite for complete inventories.

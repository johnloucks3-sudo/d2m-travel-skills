# HOTWASH AAR — ELY / NICHOLS / FURLOW VALIDATION PIPELINE FAILURE
**Thunderbird Wing | 2026-06-04 | Hale (COS) | Commander-directed**

---

## BLUF

The validation email pipeline for Ely, Nichols, and Furlow failed across 7 days and 4+ revision cycles because of **one structural coding defect**: corrections given verbally by Commander in the main session context were never written back to the dossier before headless agents were spawned. Each creative chain agent read the SAME stale/wrong dossier, and Dani (running in-context, not headless) had the corrections but no mechanism to propagate them backward. The fix is a Correction Capture Protocol with pre-chain dossier lock and post-chain correction verification. No process changes required — this is code.

---

## EVIDENCE CHAIN — WHAT HAPPENED, IN ORDER

### Failure 1: Dossier had wrong hotel for Ely (Haymarket vs. At Six)
- **Git commit `f5fe8e06`** (Jun 2): "add actual specialty dining reservations + At Six hotel/transfer updates" — this was SUPPOSED to fix the hotel in all three dossiers
- **Result**: Ely dossier was partially updated (KEY DATES shows At Six, hotel/transfers table shows At Six + cancel flags), but **Nichols dossier KEY DATES still shows "Aug 27 | Haymarket check-in"** — the commit was incomplete
- **Impact**: Any agent reading the Nichols dossier after Jun 2 would produce Haymarket-based output

### Failure 2: Insurance kept reappearing despite Commander saying "eliminate"
- Commander said "ELIMINATE ALL INSURANCE FOR BOTH" during today's session
- This correction existed ONLY in the main session context
- Reyes (experience layer), Luna (narrative), Naia (brand pass) — all three were spawned as headless agents; none received the correction
- Each produced output that included insurance sections because the dossier has insurance info
- Dani (running in main context) correctly omitted insurance — but by then the earlier stages had already contaminated the draft

### Failure 3: Creative chain agents received stale dossier at spawn time, no corrections
- Current pipeline: Read dossier → spawn Reyes → spawn Luna → spawn Naia → spawn Dani → build HTML
- Headless agents (Reyes, Luna, Naia) receive dossier file content at spawn time
- Commander corrections in the main session context are NOT passed to spawned agents
- Result: Dani's output was correct; Reyes/Luna/Naia output was wrong; the HTML mixed both

### Failure 4: No correction propagation mechanism (the root code defect)
- There is no `{client}_corrections.md` file or equivalent
- There is no `correction_capture.py` or pre-chain dossier lock
- There is no post-chain validation that checks each Commander correction is in the final draft
- The only mechanism for corrections is Commander verbally saying them multiple times

### Failure 5: Nichols dossier KEY DATES still wrong as of today
- `dossiers/Nichols_Regent_3078056.md` line: `Aug 27 | Haymarket check-in`
- Should be: `Aug 27 | At Six Stockholm check-in`
- This means the dossier will produce wrong output again on the next run

### Failure 6: Dossier corruption history (contributing factor)
- `f48cd22b` — Furlow dossier had 1530-line copy-paste corruption
- `4a1e0c8e` — Ely/Darrow dossier "repair" committed
- `75bed7a3` — "dossier remediation + data corruption" fix
- The dossiers have been corrupted and repaired multiple times; no automated corruption check exists

---

## ROOT CAUSES (RANKED BY IMPACT)

### RC-1 [CODE] — No correction capture mechanism
When Commander gives a verbal correction, nothing writes it to disk before agents are spawned. The correction lives only in the main session context window and is invisible to all headless spawns.

### RC-2 [CODE] — No pre-chain dossier lock
Before spawning Reyes/Luna/Naia/Dani, no script verifies the dossier is current. No snapshot is taken. Each agent reads the raw dossier independently — no single controlled input.

### RC-3 [CODE] — No post-chain correction verification
Before creating the Gmail draft, no script checks: "Is each Commander correction reflected in the draft?" The gap between Commander's instructions and the final HTML is verified only by Commander manually reading the draft.

### RC-4 [PROCESS — also fixable in code] — Dani runs last, can't propagate corrections backward
Dani has the best client voice context and runs in the main session. Her corrections to earlier stages have no path back into the HTML. The chain is linear/one-pass with no feedback loop.

### RC-5 [CODE] — Nichols dossier not updated (active defect)
`Nichols_Regent_3078056.md` KEY DATES still shows "Haymarket" — not "At Six." This will cause the same failure on the next run.

---

## THE FIX — 3 SCRIPTS, 1 PROTOCOL

### Script 1: `scripts/correction_capture.py` (NEW)
```python
# Called IMMEDIATELY when Commander gives any correction
# Usage: python3 scripts/correction_capture.py --client Nichols --correction "At Six both nights"
# Writes to: dossiers/{client}_corrections.md (timestamped)
# Also patches the dossier directly using a key→value map
```
Called at the START of any exchange where Commander gives factual corrections.

### Script 2: `scripts/dossier_preflight.py` (NEW)
```python
# Run BEFORE spawning any creative chain agent
# 1. Reads base dossier
# 2. Reads {client}_corrections.md
# 3. Produces {client}_locked_snapshot.md — THE ONLY FILE agents receive
# 4. Logs: "Snapshot locked at [timestamp]. [N] corrections applied."
```
All headless spawns (Reyes, Luna, Naia, Dani) receive ONLY the locked snapshot, not the raw dossier.

### Script 3: `scripts/validate_draft_corrections.py` (NEW)
```python
# Run AFTER TALON+JET, BEFORE create_gmail_draft_direct.py
# 1. Reads {client}_corrections.md
# 2. Reads the final draft HTML
# 3. For each correction, checks the draft reflects it
# 4. Returns: PASS (create draft) or FAIL: missing [correction] — BLOCK
```
If this script returns FAIL, the draft is not created. Commander is notified: "Draft blocked — correction '[X]' not found in draft."

### Protocol change: Dani-first brief (OPTIONAL — addresses RC-4)
Before spawning Reyes/Luna/Naia, Dani produces a 200-word "client context brief" from the locked snapshot. This brief goes into Reyes/Luna/Naia context. Dani's voice guidance front-loads the chain instead of only appearing at step 4.

---

## IMMEDIATE ACTIONS

| # | Action | Owner | Urgency |
|---|--------|-------|---------|
| 1 | Fix Nichols dossier — KEY DATES: Haymarket → At Six | Hale (code) | NOW |
| 2 | Build `correction_capture.py` | Sterling | This session |
| 3 | Build `dossier_preflight.py` | Sterling | This session |
| 4 | Build `validate_draft_corrections.py` | Sterling | This session |
| 5 | Wire all three scripts into the validation email workflow | Sterling | Before next client product |
| 6 | Add `{client}_corrections.md` files for Ely, Nichols, Furlow with today's corrections | Hale | NOW |

---

## METRIC — HOW WE KNOW IT'S FIXED

**Pass condition:** Commander gives one verbal correction → one script call → dossier updated → locked snapshot produced → all chain agents receive the correction → validate script confirms correction in draft → draft created on first pass.

**Target:** 0 revision cycles due to correction propagation failure. The 4-cycle problem goes to 0 when the pipeline enforces a single source of truth.

---

## DANI NOTE — Why She Had Better Info

Dani runs in the main session context, not as a headless spawn. She sees Commander's corrections in the conversation. The other agents (Reyes, Luna, Naia) are headless and only see what's passed to them at spawn time. This is a structural asymmetry — Dani's "better info" is actually just: she's the only in-context agent. The fix (locked snapshot + correction capture) levels the field by giving all agents the same corrected context.

---

*Authored: Hale (COS) | 2026-06-04 | Sterling will own the code builds | Hale routes*
*Status: Awaiting Commander review and build authorization*

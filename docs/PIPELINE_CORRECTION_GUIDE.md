# PIPELINE CORRECTION GUIDE
## Thunderbird Wing | A7 Sterling | 2026-06-04
### Three-Script Correction Capture Protocol

---

## WHY THIS EXISTS

From AAR OpsCenter/AAR_ELY_NICHOLS_FURLOW_20260604.md: verbal corrections from Commander
(e.g., "eliminate insurance", "At Six both nights") were never written to disk before headless
agents (Reyes, Luna, Naia) were spawned. Those agents received only the raw dossier — the
corrections were invisible to them. Four revision cycles resulted.

This protocol eliminates that gap. One correction capture call writes the correction to disk
and patches the dossier before any agent is spawned. One preflight call produces a locked
snapshot that ALL agents receive — raw dossier is no longer passed to headless agents.
One validation call gates the draft before Gmail draft creation.

---

## THREE-SCRIPT FLOW

```
Commander gives correction
         |
         v
[Script 1] correction_capture.py
    - Writes correction to corrections/{client}_corrections.md (audit trail)
    - Patches dossier with idempotent LIVE CORRECTIONS section
         |
         v
[Script 2] dossier_preflight.py           <-- called BEFORE any agent spawn
    - Reads dossier + all corrections
    - Produces corrections/{client}_preflight_snapshot.md
    - ALL agents receive ONLY the snapshot path — not the raw dossier
         |
    Reyes --> Luna --> Naia --> Dani --> HTML draft produced
         |
         v
[Script 3] validate_draft_corrections.py  <-- called BEFORE Gmail draft creation
    - Reads corrections/{client}_corrections.md
    - Reads final HTML draft
    - PASS (exit 0): all corrections accounted for -- proceed to create_gmail_draft_direct.py
    - FAIL (exit 1): correction missing -- BLOCK -- notify Commander
```

---

## SCRIPT 1: correction_capture.py

**When to call:** The moment Hale captures any verbal correction from Commander.
Before ANY other action. Before agent spawn. Before research. Before anything.

```bash
python3 scripts/correction_capture.py --client "Ely" --correction "At Six both nights, eliminate insurance"
python3 scripts/correction_capture.py --client "Nichols" --correction "CFAR dropped, At Six Night 1 confirmed"
```

**What it does:**
- Appends correction entry to `corrections/{client}_corrections.md` (never overwrites — full audit trail)
- Regenerates the `## LIVE CORRECTIONS` section in the client dossier (idempotent — single section always)
- Prints `[OK]` confirmation + total corrections on file

**Output file:** `corrections/{client}_corrections.md`

---

## SCRIPT 2: dossier_preflight.py

**When to call:** Before spawning ANY creative chain agent (Reyes, Luna, Naia, Dani).

```bash
python3 scripts/dossier_preflight.py --client "Ely"
# Returns stdout: /home/john/Thunderbird/corrections/Ely_preflight_snapshot.md
```

**What it does:**
- Finds the primary client dossier (handles ambiguous multi-file matches by preferring booking-ref files)
- Reads all corrections from `corrections/{client}_corrections.md`
- Produces `corrections/{client}_preflight_snapshot.md` — a single merged file with:
  - Locked timestamp header: `## PREFLIGHT LOCKED SNAPSHOT — {ts} — USE THIS, NOT THE RAW DOSSIER`
  - Active corrections block: `## ACTIVE CORRECTIONS (override dossier where they conflict)`
  - Full base dossier content

**Agent prompt integration:**
```python
import subprocess, sys
snapshot_path = subprocess.check_output([
    sys.executable, "scripts/dossier_preflight.py", "--client", client
]).decode().strip()
# Inject snapshot_path into each agent's context — never the raw dossier path
```

**Output file:** `corrections/{client}_preflight_snapshot.md`

---

## SCRIPT 3: validate_draft_corrections.py

**When to call:** After the creative chain completes, before `create_gmail_draft_direct.py`.

```bash
python3 scripts/validate_draft_corrections.py --client "Ely" --draft output/Ely_TripValidation_v4_gmail.html
# exit 0 = PASS, exit 1 = FAIL/BLOCKED
```

**What it does:**
- Loads all corrections from `corrections/{client}_corrections.md`
- Strips HTML from draft (handles tags that can split phrases across markup boundaries)
- For each correction, splits on commas into clauses, classifies each clause:
  - EXPECT-ABSENT: clause contains a negation marker (eliminate, drop, remove, cancel, omit, etc.)
  - EXPECT-PRESENT: all other clauses (including "deferred" — deferred is a status, not a negation)
- Extracts the key term per clause (prefers capitalized proper noun phrases)
- Prints polarity and term for every check (auditable — no black box)
- Returns PASS/FAIL per check, then a final verdict

**Shell gate integration:**
```bash
python3 scripts/validate_draft_corrections.py --client Ely --draft $DRAFT_PATH || {
    echo "BLOCKED: Correction validation failed. Fix draft before creating Gmail draft."
    exit 1
}
python3 scripts/create_gmail_draft_direct.py --html $DRAFT_PATH --to $CLIENT_EMAIL --subject "$SUBJECT"
```

---

## CORRECTIONS DIRECTORY

```
corrections/
  {client}_corrections.md          # Append-only audit trail of all captured corrections
  {client}_preflight_snapshot.md   # Locked merged snapshot for agent consumption
```

**Key rules:**
- `_corrections.md` is append-only — do not edit manually
- `_preflight_snapshot.md` is regenerated fresh each preflight call — use the latest one
- If Commander reverses a prior correction, the new correction wins (latest entry governs)
  If two active corrections contradict each other, manual review required — validate_draft will
  flag the conflict as a FAIL, which is the correct behavior.

---

## DOSSIER GLOB RESOLUTION

Scripts 1 and 2 use identical dossier-finding logic to guarantee they operate on the same file:
1. Search `dossiers/*.md` for files containing the client name (case-insensitive)
2. Exclude supplemental/backup files: `.bak`, `_Coverage_Brief`, `_Tips_Guide`, `DOSSIER_`
3. If one match: use it
4. If multiple matches: prefer files with a 5+ digit booking reference in the filename
5. If still ambiguous: FAIL LOUD — do not pick arbitrarily

Example: `--client Nichols` → matches `Nichols_Regent_3078056.md` and `Nichols_Allianz_Coverage_Brief.md`.
Step 4 resolves to `Nichols_Regent_3078056.md` (contains `3078056`). Coverage brief is excluded.

---

## POLARITY KEYWORD REFERENCE

These words trigger EXPECT-ABSENT classification on a clause:

```
eliminate, drop, dropped, remove, removed, cancel, cancelled,
omit, exclude, excluded, without, no longer, absent, none,
delete, deleted, strip, stripped, suppress, suppressed
```

"Deferred" is NOT a negation marker. "Deferred payment" = the payment arrangement is deferred,
which should appear in the draft.

All negation markers are matched at **word boundaries** (not substring). This prevents "cancel"
from matching inside "cancellation" or "drop" matching inside "backdrop." CFAR = "Cancel For Any
Reason" — a correction "CFAR dropped" classifies as EXPECT-ABSENT on the literal word "dropped",
which correctly expects the CFAR content to be gone.

---

## KNOWN LIMITATIONS (Residual Risk — Hale must understand before trusting a PASS)

**Limitation 1 — Literal term only, not concept.**
EXPECT-ABSENT checks that the *literal term* is absent from the draft. It does NOT check that
the *concept* is absent. If Commander says "eliminate insurance" and the draft uses "travel
protection plan" instead of "insurance," the gate will PASS — even though the concept is still
present. PASS = the literal word is confirmed absent. PASS does not mean the concept is gone.

Implication: Hale must read the draft with human eyes before accepting a PASS on any EXPECT-ABSENT
check for domain paraphrases (insurance / travel protection / coverage are common synonyms).

**Limitation 2 — Phrase corrections must use exact draft terms.**
Corrections should use the *exact token that will appear in the draft* for reliable matching.
"At Six both nights" works because drafts say "At Six." A correction like "Hotel At Six both
nights" also works — but "At Six Night 1 deferred" will extract a truncated term due to the
ordinal-digit stop logic.

If a PASS or FAIL result looks unexpected: check the "term=" audit output in the validate_draft
report. That shows exactly what token was searched for. Adjust the correction wording if needed.

**Limitation 3 — Gate is passive until wired into the pipeline.**
`validate_draft_corrections.py` blocks when called, but it is NOT yet called automatically
before `create_gmail_draft_direct.py`. Active enforcement requires wiring (AAR action #5 —
Sterling backlog). Until wired: Hale must call it manually before any Gmail draft creation.

---

## METRICS

| Metric | Target | Owner |
|--------|--------|-------|
| Correction propagation failures | 0 per client product | Sterling (A7) |
| Drafts created without validate_draft pass | 0 | Sterling (A7) |
| Corrections captured before agent spawn | 100% | Hale routes |
| Revision cycles due to stale correction data | 0 | Sterling audits |

Weekly Baldrige sweep includes: scan for `create_gmail_draft_direct.py` calls in session logs
not preceded by a `validate_draft_corrections.py` exit-0 call. Any gap = finding.

---

*A7 Sterling | 2026-06-04 | Compounding rule applied: this protocol is now the permanent standard.*
*Sourced from: OpsCenter/AAR_ELY_NICHOLS_FURLOW_20260604.md*

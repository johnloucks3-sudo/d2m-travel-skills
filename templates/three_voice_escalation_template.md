# THREE VOICE ARBITRATION — ESCALATION SUBMISSION TEMPLATE

Use this template to submit a Castillo/Harlan/Sterling conflict for arbitration.
Fill it in, send to Hale (email or Telegram — see the guide), and pick ONE
button at the bottom: **[ ARBITRATION ]** or **[ ESCALATE ]**.

Full protocol: `docs/THREE_VOICE_ARBITRATION_PROTOCOL.md`
How-to: `docs/THREE_VOICE_ARBITRATION_GUIDE.md`
Engine: `core/ops/three_voice_arbitration.py`

---

## BLANK TEMPLATE

```
TO:      Victoria Hale, Chief of Staff
FROM:    [submitter name]
DATE:    [date]
RE:      THREE VOICE ARBITRATION — [one-line issue title]
CC:      Castillo, Harlan, Sterling (all three must see this)

ISSUE STATEMENT
[One paragraph. What decision hangs on this disagreement? Why does it matter?]

WHICH VOICES DISAGREE (check all that apply)
[ ] Castillo (Strategy/Time)
[ ] Harlan (Finance/ROI)
[ ] Sterling (Process/Measurement)

CASTILLO POSITION (Strategy/Time) — max 200 words
Position: [Castillo's case, in his own voice]
Recommendation: [what he's asking for]
Time horizon: [days/hours of commitment or delay he's asking for]
Cost of being wrong: [what happens if we skip his scenario testing]

HARLAN POSITION (Finance/ROI) — max 200 words
Position: [Harlan's case, in his own voice]
Recommendation: [what he's asking for]
Financial impact: [$ figure — cost of delay, ROI gap, or budget exposure]
Cost of being wrong: [what happens if we wait / if we spend]

STERLING POSITION (Process/Measurement) — max 200 words
Position: [Sterling's case, in his own voice]
Recommendation: [what he's asking for]
Process gap: [what's missing — baseline, metric, measurement charter]
Baseline gap material? [YES / NO — Sterling's own call]
Cost of being wrong: [what happens if we implement without measurement rigor]

SUBMITTER SUMMARY
[Your synthesis. Is this a TIMING conflict (same direction, different speed),
a DIRECTION conflict (different outcomes), or a PROCESS-GATE (one voice hitting
an authority ceiling)? Which expert's view matters most here, and why?]

SUBMIT AS:
[ ARBITRATION ]  — Hale decides now, inside her authority (timing/process)
[ ESCALATE ]     — Direction conflict or >$5K / >90-day exposure, Commander decides

---
```

---

## FILLED EXAMPLE

```
TO:      Victoria Hale, Chief of Staff
FROM:    Dembe (A2)
DATE:    2026-07-06
RE:      THREE VOICE ARBITRATION — Scandinavia Portal Release Timing
CC:      Castillo, Harlan, Sterling

ISSUE STATEMENT
The three Grandeur Scandinavia client portals (Furlow/Ely-Darrow/Nichols) are
built and staged. Castillo wants a 72-hour scenario test before release.
Harlan says every day of delay costs real money in unconfirmed logistics
exposure. This is holding up a send the Commander is expecting.

WHICH VOICES DISAGREE (check all that apply)
[x] Castillo (Strategy/Time)
[x] Harlan (Finance/ROI)
[ ] Sterling (Process/Measurement)

CASTILLO POSITION (Strategy/Time)
Position: I need 72 hours to run the three-scenario test — cross-couple data
bleed, image accuracy, and dependency timing (the ARN transfer booking) all
need to check clean before this goes out under the D2M name.
Recommendation: Hold the release 72 hours.
Time horizon: 72 hours.
Cost of being wrong: We ship a portal with a data-bleed error or a broken
dependency link, and it's client-facing — the trust cost is much higher than
72 hours of delay.

HARLAN POSITION (Finance/ROI)
Position: The cost of delay here isn't abstract — it's $2,000/day in lost
booking-desk momentum on three live TPs, and it compounds the closer we get
to the Jul 20 target send.
Recommendation: Move within 24 hours, not 72.
Financial impact: $2,000/day estimated cost of delay; $6,000 total if the
full 72 hours is taken.
Cost of being wrong: We wait the full 72 hours and lose $6,000 in momentum we
can't easily recover on three TPs already running behind.

STERLING POSITION (Process/Measurement)
Position: (not invoked — no measurement/baseline dispute on this one)
Recommendation: —
Process gap: —
Baseline gap material? N/A
Cost of being wrong: —

SUBMITTER SUMMARY
This is a TIMING conflict, not a DIRECTION conflict — both Castillo and
Harlan want the same outcome (a clean, on-brand send), they disagree on
speed. Harlan's $6,000 total exposure is under the $5K single-day threshold
in the escalation matrix per day, but the full-delay total crosses it —
worth flagging for Hale to weigh the full-hold cost, not just the daily rate.

SUBMIT AS:
[x] ARBITRATION  — Hale decides now, inside her authority (timing/process)
[ ] ESCALATE
```

**Engine call for this example:**

```python
from core.ops.three_voice_arbitration import ConflictSubmission, VoicePosition, run_arbitration

sub = ConflictSubmission(
    submitter="Dembe (A2)",
    issue_title="Scandinavia Portal Release Timing",
    disagreement_summary="Castillo wants 72h scenario test; Harlan says delay costs $2K/day.",
    castillo=VoicePosition(
        position="I need 72 hours for the three-scenario test before release.",
        recommendation="Hold release 72 hours.",
    ),
    harlan=VoicePosition(
        position="Cost of delay is $2,000 per day in lost booking-desk momentum.",
        recommendation="Move within 24 hours.",
    ),
    financial_impact_usd=6000,   # full-hold total, per submitter's flag
)
result = run_arbitration(sub)
print(result.recommendation)   # escalate-to-commander ($6,000 > $5,000 threshold)
```

# THREE VOICE ARBITRATION — HOW-TO GUIDE FOR STAFF

**Audience:** Castillo (A5), Harlan (A9), Sterling (A7), and any staff member
who submits a conflict on their behalf (e.g. Dembe as escalator).
**Full protocol (binding):** `docs/THREE_VOICE_ARBITRATION_PROTOCOL.md`
**Engine:** `core/ops/three_voice_arbitration.py`
**Template:** `templates/three_voice_escalation_template.md`
**Log:** `OpsCenter/arbitration_log.md`

---

## 1. WHEN TO INVOKE

Invoke Three Voice Arbitration when **all three of these are true**:

1. Two or more of Castillo, Harlan, Sterling have taken positions that conflict.
2. The conflict is blocking a decision — not a data dispute, not a feasibility
   question (those route elsewhere, see Section II of the protocol).
3. Informal resolution hasn't worked, or the conflict is clean enough to skip
   straight to formal arbitration.

**Examples that qualify:**
- Castillo wants 72 hours to scenario-test a release; Harlan says every day of
  delay has a real dollar cost.
- Sterling says there's no baseline to measure success; Castillo says the
  strategy is ready to publish now.
- Harlan says a supplier exit costs too much; Castillo says the exit is
  strategically essential.
- Anyone says explicitly: "I need this escalated to Hale per Three Voice
  Protocol."

**Examples that do NOT qualify (route elsewhere instead):**
- A disagreement about what the numbers actually are → that's Sterling's
  measurement rigor, not arbitration. Get the facts first.
- A disagreement about the math itself → Harlan's spreadsheet settles it.
- A disagreement about whether something is technically feasible → that's
  Hale/ops territory directly, no arbitration needed.

---

## 2. HOW TO SUBMIT

1. Open `templates/three_voice_escalation_template.md` and fill in the blank
   template — issue statement, each voice's position in their own words,
   the structured fields the matrix needs (financial impact, time horizon,
   baseline materiality), and your own synthesis.
2. Send it to Hale via **email** (preferred — full prose, threaded) or
   **Telegram** (short conflicts only, per channel discipline).
3. CC all three voices — nobody sees an edited version of anyone else's
   position.
4. Pick one button: **[ARBITRATION]** (you believe Hale can decide this) or
   **[ESCALATE]** (you believe this is already a Commander-level Direction
   conflict). Hale's engine will confirm or overrule your pick — this is a
   starting signal, not a binding choice.

**Minimum required fields** (the engine will bounce anything missing these):
- Submitter name
- One-line disagreement summary
- At least one voice's position filled in

---

## 3. WHAT TO EXPECT

| Step | Timing |
|---|---|
| Acknowledgment from Hale | Within 24 hours |
| Arbitration run through `three_voice_arbitration.py` | Same day as acknowledgment |
| Decision (resolve-unilaterally or escalate) | Within 48 hours of submission |
| Logged to `OpsCenter/arbitration_log.md` and `hale_decisions.md` | Same day as decision |
| Notification to all three voices + submitter | Same day as decision |

If Hale escalates, the Commander sees the full escalation memo intact — not a
summary. Escalated conflicts wait for Commander direction; there is no
default timeline on those.

**No relitigating after the decision gate closes** (per protocol Section IX).
New information can be raised at the next checkpoint, not as a re-argument of
the same facts.

---

## 4. THE DECISION MATRIX (what the engine actually checks)

```
IF Castillo(time) + Harlan(cost) + financial_impact_usd > $5,000:
    → ESCALATE TO COMMANDER

IF Sterling(baseline gap) + Castillo(ready to publish):
    → Hale ARBITRATES — rules on whether the baseline can wait
      or needs to be built in parallel (needs Sterling's materiality call)

IF Harlan(cost exceeds benefit) + Castillo(strategic/multi-year) +
   time_horizon_days > 90:
    → ESCALATE TO COMMANDER (this is a Direction conflict)

ELSE:
    → Hale ARBITRATES (inside her existing authority)
```

Missing a structured field the matrix needs (e.g. Harlan's dollar figure, or
Sterling's materiality call) does not produce a wrong answer — the engine
returns `request-more-info` and names exactly what's missing.

---

## 5. TWO REAL EXAMPLES

### Example A — RESOLVED UNILATERALLY (Hale's authority)

**Issue:** Should the Wing build an automated dossier system? (2026-05-31)

Castillo recommended Option B (cache + daily sweep) as strategically
resilient. Harlan confirmed Option B's ROI beat every alternative. Sterling
agreed with the direction but wanted a measurement charter before any build
landed, so the Wing would actually know if it worked.

Dembe (A2), escalating on their behalf, correctly identified this as a
**TIMING conflict, not a DIRECTION conflict** — all three wanted the same
outcome, they disagreed on sequencing. Running it through the matrix:

- Pattern detected: Sterling (baseline gap) + Castillo (ready to publish).
- Sterling confirmed the baseline gap was material — but material didn't mean
  *before*, it meant *in parallel*.
- Recommendation: `resolve-unilaterally`.

**Hale's decision:** Option B build approved immediately, 30-day timeline.
Sterling's measurement charter ran in parallel (baseline by 2026-06-07), not
as a blocking precondition. Logged to `hale_decisions.md` same day; no
Commander involvement needed.

Full memo and decision text: `docs/THREE_VOICE_ARBITRATION_PROTOCOL.md` §VIII.

---

### Example B — ESCALATED TO COMMANDER (Direction conflict)

**Issue:** Should the Wing exit its current cruise-line preferred-supplier
relationship in favor of a higher-commission alternative?

- **Castillo:** "Exiting this supplier is strategically essential — the
  current relationship caps our commission tier structure for the next
  several booking cycles. This is a multi-year capability decision."
  Recommendation: exit. Time horizon: 365+ days (multi-year commitment).
- **Harlan:** "This costs more than the benefit justifies — exit fees and
  transition costs run to 40% of our operational budget for the quarter
  before any new-tier commission gain offsets it." Recommendation: don't
  exit, or delay until the new tier's gain is proven.
- **Sterling:** did not take a position — no measurement dispute here.

Running it through the matrix:
- Pattern detected: Harlan (cost exceeds benefit) + Castillo (strategic,
  multi-year).
- `time_horizon_days = 365` > 90-day threshold.
- Recommendation: `escalate-to-commander`.

**Why this escalates and Example A didn't:** Example A was the same outcome,
different speed — Hale's lane. This one is two different outcomes (exit vs.
stay) with a multi-year capability commitment attached — Commander's lane,
per the S/O/T doctrine (>90 days OR >$5K). Hale's role here is synthesis and
recommendation, not decision: she surfaces all three positions intact to the
Commander, flags where the tension actually is, and waits for direction.

---

## 6. FOR HALE — RUNNING A SUBMISSION

```python
from core.ops.three_voice_arbitration import ConflictSubmission, VoicePosition, run_arbitration

sub = ConflictSubmission(
    submitter="...",
    issue_title="...",
    disagreement_summary="...",
    castillo=VoicePosition(position="...", recommendation="...", cost_of_being_wrong="..."),
    harlan=VoicePosition(position="...", recommendation="...", cost_of_being_wrong="..."),
    sterling=VoicePosition(position="...", recommendation="...", cost_of_being_wrong="..."),
    financial_impact_usd=None,      # fill in if Harlan named a $ figure
    time_horizon_days=None,         # fill in if Castillo named a commitment length
    baseline_gap_material=None,     # fill in if Sterling made a materiality call
)
result = run_arbitration(sub)   # arbitrates AND logs to OpsCenter/arbitration_log.md

if result.recommendation == "resolve-unilaterally":
    # reply with the decision, log to hale_decisions.md, move forward
    ...
elif result.recommendation == "escalate-to-commander":
    # notify Commander + all three voices, wait for direction
    ...
else:  # "request-more-info"
    # reply asking specifically for result.missing_fields
    ...
```

See `Personas/hale_cos.md` for the standing integration instruction.

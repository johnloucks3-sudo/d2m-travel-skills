# Exercise AAR — Telegram Claude Timeout Investigation + Engine Architecture Fix
Date: 2026-07-02 (AAR authored) · Exercise ran 2026-05-17
Score: 42% (quality_score 42/100, recorded by Sterling/A7 at Gate 5)
Exercise ID: 1778990025 · Tier: T2 · Group: all · Staff invoked: Castillo (A5), Sterling (A7), ELON (A12)
Domain owner: Sterling (A7) — process/tech/metrics lead at Gate 5; classification by Castillo (A5)

## What happened
The only exercise in `OpsCenter/quality_log.json` is the 2026-05-17 T2 "Telegram Claude timeout investigation + engine architecture fix." Sterling scored it **42/100** at the Gate-5 quality review. The dashboard (`a7_metrics_dashboard.json`) averages all logged exercises — with only this one on the books, the Wing-wide `exercise_quality_score_pct` reads 42%, below the 60% red threshold. This is the "one exercise with no audit trail" the dashboard flags: **it never received its formal AAR artifact** (contrast MISSION-172, which has `output/MISSION-172_WING_EXERCISE_AAR_20260609.md`). This document is that missing audit trail.

The exercise did produce work: Castillo made the tier call, Sterling ran a 6-gate audit (score 42/100), ELON gave a hybrid recommendation, and infra was built (`ROUTE_ALL_OPENCODE` toggle, `command_signal.md`). But per the log note, the built infra was **"Not deployed per Commander directive."**

## Root cause
The 42% is **intrinsic, not a stale-datapoint artifact.** From the Gate-5 record:
- `success_criteria_met: false` — the exercise did not meet its own success criteria.
- `metrics_tracked: false` — no metrics were tracked during execution.
- (`etc_accurate: true`, `artifact_delivered: true`, `qm_fields_defined: true` — the other three of six gates passed.)

Two failed gates out of six ≈ the 42% score. The deeper reason both failed: the exercise's deliverable (an engine-routing architecture change) was **shelved by Commander directive before deployment**, so success criteria could not be met and runtime metrics were never collected. The exercise was, in effect, a design study that got overtaken by a command decision — legitimate, but it scores as an incomplete exercise under the anti-theater rubric.

**Systemic finding (larger than this one score):** the filesystem holds many exercises — MISSION-172, T2_EXERCISE_DEMBE_CRUISE_INTELLIGENCE, multiple hotwashes and charters in `output/` and `docs/retros/` — yet `quality_log.json` contains **only 1**. Sterling's Gate-5 quality logging is not happening for most exercises. The dashboard therefore reports on a single unrepresentative datapoint. The measurement discipline is broken, which is a bigger risk than any single red score.

## Lessons
1. **A shelved deliverable is still a scorable exercise — record it as such and write the AAR.** Not writing the AAR is the actual "no audit trail" failure. (Fixed by this document.)
2. **Gate-5 logging must be near-100%, not 1-of-many.** A quality metric computed from one exercise is noise. Every T1+ exercise on disk needs a `quality_log.json` entry, backfilled and going forward.
3. **`success_criteria_met`/`metrics_tracked` are the two gates that actually move the score** — future exercises should define measurable success criteria and instrument at least one runtime metric before Step 2, or expect a red score.
4. **Do not "fix" the metric by editing the score.** The 42% is accurate for what was logged; the fix is more/better logging, not a number change. `quality_log.json` left untouched.

## Doctrine change required: no
The Wing Exercise Protocol (SO_WING_EXERCISE_PROTOCOL_20260516) and the anti-theater rule are sound. The gap is **enforcement of existing doctrine** (Gate-5 logging discipline), not the doctrine itself.

## SO needed: no — but a standing enforcement action is required
No new SO. Instead, task Sterling (A7, domain owner of Gate 5) with a one-time backfill + ongoing discipline:
- **Action:** Backfill `quality_log.json` with Gate-5 entries for every exercise artifact already on disk (MISSION-172, T2_EXERCISE_DEMBE, the hotwashes/charters in `output/` and `docs/retros/`), then log every future T1+ exercise at Gate 5. Target: `total_exercises` in the dashboard matches the count of exercise artifacts.
- **Metric of done:** dashboard `exercise_quality_score_pct` computed over ≥ the number of exercises actually run; single-datapoint red condition cleared.
- If a candidate SO title is ever wanted: *SO_GATE5_QUALITY_LOGGING_ENFORCEMENT* — but this is an execution/discipline fix, not new policy, so it stays a Sterling action item rather than an SO.

*Anti-theater compliance: this AAR is the durable artifact for exercise 1778990025, satisfying the rule that every formal exercise produces a durable record. Authored within the exercise-quality review, filed to OpsCenter/state.*

*— V. Hale, VCS · Thunderbird Wing · 2026-07-02*

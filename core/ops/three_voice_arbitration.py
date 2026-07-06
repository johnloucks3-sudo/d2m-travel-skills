#!/usr/bin/env python3
"""Three Voice Arbitration Engine — Castillo (Strategy) / Harlan (Finance) /
Sterling (Process) conflict resolution.

Implements the decision matrix from docs/THREE_VOICE_ARBITRATION_PROTOCOL.md
and docs/THREE_VOICE_ARBITRATION_GUIDE.md. Hale runs every arbitration
submission through `run_arbitration()` before replying.

Run standalone: python3 core/ops/three_voice_arbitration.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path("/home/john/Thunderbird")
ARBITRATION_LOG = REPO_ROOT / "OpsCenter" / "arbitration_log.md"

# Recommendation outcomes
RESOLVE_UNILATERALLY = "resolve-unilaterally"
ESCALATE_TO_COMMANDER = "escalate-to-commander"
REQUEST_MORE_INFO = "request-more-info"

# Financial / time thresholds (aligned with S/O/T doctrine: >90 days OR >$5K)
FINANCIAL_IMPACT_THRESHOLD_USD = 5000
STRATEGIC_HORIZON_THRESHOLD_DAYS = 90

_TIME_KEYWORDS = ("more time", "scenario test", "48", "72", "hours", "need time", "not ready")
_COST_KEYWORDS = ("cost of delay", "costs", "waiting costs", "opportunity cost", "$", "per day", "/day")
_BASELINE_KEYWORDS = ("no baseline", "baseline", "cannot measure", "measurement", "how will we know")
_READY_KEYWORDS = ("ready to publish", "ready", "publish", "move forward", "proceed")
_BENEFIT_EXCEED_KEYWORDS = ("costs more than", "exceeds the benefit", "roi", "doesn't justify", "not worth")
_STRATEGIC_KEYWORDS = ("strategically essential", "strategic priority", "capability portfolio", "long-term", "multi-year")

PATTERN_1_TIME_VS_COST = "castillo_time_vs_harlan_cost"
PATTERN_2_BASELINE_VS_READY = "sterling_baseline_vs_castillo_ready"
PATTERN_3_COST_VS_STRATEGIC = "harlan_cost_vs_castillo_strategic"
PATTERN_4_EXPLICIT_INVOKE = "explicit_invoke"


@dataclass
class VoicePosition:
    """One expert's position in their own voice."""
    position: str = ""
    recommendation: str = ""
    cost_of_being_wrong: str = ""

    def text(self) -> str:
        return " ".join([self.position, self.recommendation, self.cost_of_being_wrong]).lower()

    def is_empty(self) -> bool:
        return not (self.position or self.recommendation or self.cost_of_being_wrong)


@dataclass
class ConflictSubmission:
    """Input to the arbitration engine — one Three Voice escalation."""
    submitter: str = ""
    issue_title: str = ""
    disagreement_summary: str = ""
    castillo: VoicePosition = field(default_factory=VoicePosition)
    harlan: VoicePosition = field(default_factory=VoicePosition)
    sterling: VoicePosition = field(default_factory=VoicePosition)

    # Structured data the matrix needs to actually decide (not inferred from prose)
    financial_impact_usd: Optional[float] = None       # Harlan's named cost of delay / ROI gap
    time_horizon_days: Optional[int] = None             # Castillo's named commitment horizon
    baseline_gap_material: Optional[bool] = None        # Sterling's call on whether the gap matters

    explicit_invoke: bool = False                       # "escalated to Hale per Three Voice Protocol"


@dataclass
class ArbitrationRecord:
    issue_title: str
    submitter: str
    timestamp: str
    patterns_detected: list
    decision_case: str          # TIMING | PROCESS-GATE | DIRECTION | NONE | INCOMPLETE
    recommendation: str         # resolve-unilaterally | escalate-to-commander | request-more-info
    rationale: str
    missing_fields: list = field(default_factory=list)


def _matches_any(text: str, keywords) -> bool:
    return any(k in text for k in keywords)


def detect_patterns(sub: ConflictSubmission) -> list:
    """Recognize the 4 conflict patterns from the protocol's trigger conditions."""
    patterns = []

    castillo_text = sub.castillo.text()
    harlan_text = sub.harlan.text()
    sterling_text = sub.sterling.text()

    if _matches_any(castillo_text, _TIME_KEYWORDS) and _matches_any(harlan_text, _COST_KEYWORDS):
        patterns.append(PATTERN_1_TIME_VS_COST)

    if _matches_any(sterling_text, _BASELINE_KEYWORDS) and _matches_any(castillo_text, _READY_KEYWORDS):
        patterns.append(PATTERN_2_BASELINE_VS_READY)

    if _matches_any(harlan_text, _BENEFIT_EXCEED_KEYWORDS) and _matches_any(castillo_text, _STRATEGIC_KEYWORDS):
        patterns.append(PATTERN_3_COST_VS_STRATEGIC)

    if sub.explicit_invoke:
        patterns.append(PATTERN_4_EXPLICIT_INVOKE)

    return patterns


def _validate(sub: ConflictSubmission) -> list:
    """Return a list of missing fields required before the matrix can run."""
    missing = []
    if not sub.submitter:
        missing.append("submitter")
    if not sub.disagreement_summary:
        missing.append("disagreement_summary")
    if sub.castillo.is_empty() and sub.harlan.is_empty() and sub.sterling.is_empty():
        missing.append("at least one voice position (castillo/harlan/sterling)")
    return missing


def arbitrate(sub: ConflictSubmission) -> ArbitrationRecord:
    """Apply the Three Voice decision matrix. Pure function — no I/O, no logging."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    missing = _validate(sub)
    if missing:
        return ArbitrationRecord(
            issue_title=sub.issue_title or "(untitled)",
            submitter=sub.submitter or "(unknown)",
            timestamp=timestamp,
            patterns_detected=[],
            decision_case="INCOMPLETE",
            recommendation=REQUEST_MORE_INFO,
            rationale=f"Submission missing required field(s): {', '.join(missing)}. "
                      f"Cannot run the decision matrix without them.",
            missing_fields=missing,
        )

    patterns = detect_patterns(sub)

    # Pattern 1 — Castillo time vs Harlan cost. Escalate only above the $5K threshold.
    if PATTERN_1_TIME_VS_COST in patterns:
        if sub.financial_impact_usd is None:
            return ArbitrationRecord(
                issue_title=sub.issue_title, submitter=sub.submitter, timestamp=timestamp,
                patterns_detected=patterns, decision_case="TIMING",
                recommendation=REQUEST_MORE_INFO,
                rationale="Castillo/Harlan timing conflict detected, but Harlan's financial_impact_usd "
                          "(cost of delay) is not on record. Cannot apply the $5K escalation threshold "
                          "without it.",
                missing_fields=["financial_impact_usd"],
            )
        if sub.financial_impact_usd > FINANCIAL_IMPACT_THRESHOLD_USD:
            return ArbitrationRecord(
                issue_title=sub.issue_title, submitter=sub.submitter, timestamp=timestamp,
                patterns_detected=patterns, decision_case="TIMING",
                recommendation=ESCALATE_TO_COMMANDER,
                rationale=f"Castillo wants time, Harlan's cost of delay (${sub.financial_impact_usd:,.0f}) "
                          f"exceeds the ${FINANCIAL_IMPACT_THRESHOLD_USD:,} threshold. Per S/O/T doctrine "
                          f"this crosses into Commander territory.",
            )
        # Financial impact at or below threshold falls through to Hale's own authority.

    # Pattern 2 — Sterling baseline gap vs Castillo ready-to-publish. Hale arbitrates either way,
    # but she needs Sterling's materiality call to know which way to rule.
    if PATTERN_2_BASELINE_VS_READY in patterns:
        if sub.baseline_gap_material is None:
            return ArbitrationRecord(
                issue_title=sub.issue_title, submitter=sub.submitter, timestamp=timestamp,
                patterns_detected=patterns, decision_case="PROCESS-GATE",
                recommendation=REQUEST_MORE_INFO,
                rationale="Sterling/Castillo baseline-vs-ready conflict detected, but Sterling has not "
                          "flagged whether the baseline gap is material. Need that call before Hale rules "
                          "on whether to proceed without it.",
                missing_fields=["baseline_gap_material"],
            )
        verdict = ("baseline is material — build it in parallel with the launch, not before"
                   if sub.baseline_gap_material else
                   "baseline gap is not material — proceed, measurement runs post-decision")
        return ArbitrationRecord(
            issue_title=sub.issue_title, submitter=sub.submitter, timestamp=timestamp,
            patterns_detected=patterns, decision_case="PROCESS-GATE",
            recommendation=RESOLVE_UNILATERALLY,
            rationale=f"Process-gate conflict — inside Hale's authority per protocol Section VII. "
                      f"Sterling's materiality call: {verdict}.",
        )

    # Pattern 3 — Harlan cost-exceeds-benefit vs Castillo strategic-essential. Escalate only if
    # Castillo's ask is a genuine multi-year (>90 day) commitment.
    if PATTERN_3_COST_VS_STRATEGIC in patterns:
        if sub.time_horizon_days is None:
            return ArbitrationRecord(
                issue_title=sub.issue_title, submitter=sub.submitter, timestamp=timestamp,
                patterns_detected=patterns, decision_case="DIRECTION",
                recommendation=REQUEST_MORE_INFO,
                rationale="Harlan/Castillo cost-vs-strategic conflict detected, but Castillo's "
                          "time_horizon_days (commitment length) is not on record. Cannot apply the "
                          "90-day strategic threshold without it.",
                missing_fields=["time_horizon_days"],
            )
        if sub.time_horizon_days > STRATEGIC_HORIZON_THRESHOLD_DAYS:
            return ArbitrationRecord(
                issue_title=sub.issue_title, submitter=sub.submitter, timestamp=timestamp,
                patterns_detected=patterns, decision_case="DIRECTION",
                recommendation=ESCALATE_TO_COMMANDER,
                rationale=f"Castillo's ask commits the wing for {sub.time_horizon_days} days "
                          f"(> {STRATEGIC_HORIZON_THRESHOLD_DAYS}-day threshold) against Harlan's "
                          f"cost objection. This is a Direction conflict — Commander owns direction, "
                          f"per S/O/T doctrine.",
            )
        # Short-horizon disagreement falls through to Hale's own authority.

    # Nothing above forced an escalation or an info request — Hale arbitrates.
    if patterns:
        rationale = (f"Pattern(s) detected ({', '.join(patterns)}) but none crossed an escalation "
                     f"threshold. Inside Hale's authority — timing/process decision, not direction.")
        decision_case = "TIMING" if PATTERN_1_TIME_VS_COST in patterns else \
                         "PROCESS-GATE" if PATTERN_2_BASELINE_VS_READY in patterns else \
                         "DIRECTION" if PATTERN_3_COST_VS_STRATEGIC in patterns else "NONE"
    else:
        rationale = ("No recognized Three Voice conflict pattern matched. Treated as a routine "
                     "operational disagreement inside Hale's existing authority.")
        decision_case = "NONE"

    return ArbitrationRecord(
        issue_title=sub.issue_title, submitter=sub.submitter, timestamp=timestamp,
        patterns_detected=patterns, decision_case=decision_case,
        recommendation=RESOLVE_UNILATERALLY, rationale=rationale,
    )


def log_arbitration(record: ArbitrationRecord, log_path: Path = ARBITRATION_LOG) -> None:
    """Append the arbitration record to OpsCenter/arbitration_log.md."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not log_path.exists()
    with log_path.open("a", encoding="utf-8") as f:
        if is_new:
            f.write("# THREE VOICE ARBITRATION LOG\n")
            f.write("*Auto-appended by core/ops/three_voice_arbitration.py — do not hand-edit entries.*\n\n---\n\n")
        f.write(f"### {record.timestamp} — {record.issue_title}\n\n")
        f.write(f"**Submitted by:** {record.submitter}\n\n")
        f.write(f"**Patterns detected:** {', '.join(record.patterns_detected) if record.patterns_detected else 'none'}\n\n")
        f.write(f"**Decision case:** {record.decision_case}\n\n")
        f.write(f"**Recommendation:** `{record.recommendation}`\n\n")
        f.write(f"**Rationale:** {record.rationale}\n\n")
        if record.missing_fields:
            f.write(f"**Missing fields:** {', '.join(record.missing_fields)}\n\n")
        f.write("---\n\n")


def run_arbitration(sub: ConflictSubmission, log: bool = True) -> ArbitrationRecord:
    """Main entry point: arbitrate + log."""
    record = arbitrate(sub)
    if log:
        log_arbitration(record)
    return record


if __name__ == "__main__":
    demo = ConflictSubmission(
        submitter="Dembe (A2)",
        issue_title="Demo — Dossier Automation Option B vs Baseline",
        disagreement_summary="Castillo wants Option B now; Sterling wants a baseline first.",
        castillo=VoicePosition(
            position="Option B is strategically resilient and ready to publish now.",
            recommendation="Approve Option B build immediately.",
        ),
        harlan=VoicePosition(
            position="Option B breaks even in 2 months.",
            recommendation="Approve Option B build immediately.",
        ),
        sterling=VoicePosition(
            position="We have no baseline — cannot measure success without one.",
            recommendation="Approve with a parallel measurement charter.",
        ),
        baseline_gap_material=True,
    )
    result = run_arbitration(demo, log=False)
    print(f"Recommendation: {result.recommendation}")
    print(f"Decision case: {result.decision_case}")
    print(f"Rationale: {result.rationale}")
    sys.exit(0)

"""
core/oversight/mast.py — the Wing's failure taxonomy.

We do NOT invent a Thunderbird failure taxonomy. We adopt MAST wholesale:

    "Why Do Multi-Agent LLM Systems Fail?"
    Cemri, Pan, Yang, Agrawal, Chopra, Tiwari, Keutzer, Parameswaran, Klein,
    Ramchandran, Zaharia, Gonzalez, Stoica — UC Berkeley
    arXiv:2503.13657 (v3)  ·  https://arxiv.org/abs/2503.13657

14 fine-grained failure modes in 3 categories, derived from 150 expert-annotated
traces, validated at inter-annotator agreement kappa=0.88, applied across a
dataset of 1600+ traces from 7 MAS frameworks.

Why adopt rather than invent: we have single-digit annotated traces; Berkeley has
1600+. A taxonomy invented here would be an unvalidated vocabulary that makes our
failure counts incomparable to anyone else's and un-benchmarkable against our own
past. The definitions below are quoted from Appendix A of the paper.

CRITICAL USAGE RULE — why this is an enum and not a free-text field:
Research on LLM-as-judge reliability finds judges are strong on BINARY
success/fail (~89-97% agreement with humans) but weak on categorizing WHICH
failure occurred (~58% type agreement). Therefore:

  * `mast_code` is a closed enum. Never free text.
  * Prefer `classify_mechanically()` — rule-based assignment from observed
    facts — over asking a model.
  * A model may PROPOSE a code (`proposed_mast_code`); only a rule or a human
    may FINALIZE one. See core/oversight/spans.py.

MAST is explicitly not claimed exhaustive by its authors. Where an observed
Thunderbird failure genuinely has no MAST home, we record it under the
WING_* extension codes below rather than bending a MAST definition to fit —
keeping our extensions separable from the validated taxonomy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

PAPER_URL = "https://arxiv.org/abs/2503.13657"
PAPER_CITE = (
    "Cemri et al., 'Why Do Multi-Agent LLM Systems Fail?', arXiv:2503.13657 "
    "(UC Berkeley). 14 modes / 3 categories, kappa=0.88."
)


@dataclass(frozen=True)
class FailureMode:
    code: str
    category: str
    name: str
    definition: str
    # Share of annotated failure instances in MAST-Data, where the paper
    # reports one. None = not separately reported in the text we verified.
    prevalence_pct: Optional[float] = None
    stage: str = ""  # pre-execution | execution | post-execution


# --- FC1. System Design Issues -------------------------------------------
# "failures that arise from deficiencies in the design of the system
#  architecture, poor conversation management, unclear task specifications or
#  violation of constraints, and inadequate definition or adherence to the
#  roles and responsibilities of the agents."
FC1 = "FC1: System Design Issues"
FC2 = "FC2: Inter-Agent Misalignment"
FC3 = "FC3: Task Verification"

MODES: dict[str, FailureMode] = {
    "FM-1.1": FailureMode(
        "FM-1.1", FC1, "Disobey task specification",
        "Failure to adhere to the specified constraints or requirements of a "
        "given task, leading to suboptimal or incorrect outcomes.",
        stage="pre-execution"),
    "FM-1.2": FailureMode(
        "FM-1.2", FC1, "Disobey role specification",
        "Failure to adhere to the defined responsibilities and constraints of "
        "an assigned role, potentially leading to an agent behaving like another.",
        stage="pre-execution"),
    "FM-1.3": FailureMode(
        "FM-1.3", FC1, "Step repetition",
        "Unnecessary reiteration of previously completed steps in a process, "
        "potentially causing delays or errors in task completion.",
        stage="execution"),
    "FM-1.4": FailureMode(
        "FM-1.4", FC1, "Loss of conversation history",
        "Unexpected context truncation, disregarding recent interaction history "
        "and reverting to an antecedent conversational state.",
        stage="execution"),
    "FM-1.5": FailureMode(
        "FM-1.5", FC1, "Unaware of termination conditions",
        "Lack of recognition or understanding of the criteria that should "
        "trigger the termination of the agents' interaction, potentially "
        "leading to unnecessary continuation.",
        stage="execution"),

    # --- FC2. Inter-Agent Misalignment -----------------------------------
    # "failures arising from ineffective communication, poor collaboration,
    #  conflicting behaviors among agents, and gradual derailment from the
    #  initial task."
    "FM-2.1": FailureMode(
        "FM-2.1", FC2, "Conversation reset",
        "Unexpected or unwarranted restarting of a dialogue, potentially losing "
        "context and progress made in the interaction.",
        prevalence_pct=2.20, stage="execution"),
    "FM-2.2": FailureMode(
        "FM-2.2", FC2, "Fail to ask for clarification",
        "Inability to request additional information when faced with unclear or "
        "incomplete data, potentially resulting in incorrect actions.",
        prevalence_pct=6.80, stage="execution"),
    "FM-2.3": FailureMode(
        "FM-2.3", FC2, "Task derailment",
        "Deviation from the intended objective or focus of a given task, "
        "potentially resulting in irrelevant or unproductive actions.",
        prevalence_pct=7.40, stage="execution"),
    "FM-2.4": FailureMode(
        "FM-2.4", FC2, "Information withholding",
        "Failure to share or communicate important data or insights that an "
        "agent possess and could impact decision-making of other agents if shared.",
        prevalence_pct=0.85, stage="execution"),
    "FM-2.5": FailureMode(
        "FM-2.5", FC2, "Ignored other agent's input",
        "Disregarding or failing to adequately consider input or recommendations "
        "provided by other agents in the system, potentially leading to "
        "suboptimal decisions or missed opportunities for collaboration.",
        prevalence_pct=1.90, stage="execution"),
    "FM-2.6": FailureMode(
        "FM-2.6", FC2, "Reasoning-action mismatch",
        "Discrepancy between the logical reasoning process and the actual "
        "actions taken by the agent, potentially resulting in unexpected or "
        "undesired behaviors.",
        prevalence_pct=13.20, stage="execution"),

    # --- FC3. Task Verification ------------------------------------------
    # "failures resulting from premature execution termination, as well as
    #  insufficient mechanisms to guarantee the accuracy, completeness, and
    #  reliability of interactions, decisions, and outcomes."
    "FM-3.1": FailureMode(
        "FM-3.1", FC3, "Premature termination",
        "Ending a dialogue, interaction or task before all necessary information "
        "has been exchanged or objectives have been met, potentially resulting "
        "in incomplete or incorrect outcomes.",
        stage="post-execution"),
    "FM-3.2": FailureMode(
        "FM-3.2", FC3, "No or incomplete verification",
        "(partial) omission of proper checking or confirmation of task outcomes "
        "or system outputs, potentially allowing errors or inconsistencies to "
        "propagate undetected.",
        stage="post-execution"),
    "FM-3.3": FailureMode(
        "FM-3.3", FC3, "Incorrect verification",
        "Failure to adequately validate or cross-check crucial information or "
        "decisions during the iterations, potentially leading to errors or "
        "vulnerabilities in the system.",
        stage="post-execution"),
}

# --- Thunderbird extensions ----------------------------------------------
# Kept deliberately separate from MAST so our numbers stay comparable to the
# published taxonomy. Only add here when no MAST mode honestly fits.
WING_MODES: dict[str, FailureMode] = {
    "WING-1": FailureMode(
        "WING-1", "WING: Wing-specific", "Silent success",
        "Work completed and artifacts written, but the worker exited without "
        "reporting, leaving the result undiscoverable by the orchestrator. "
        "Distinct from FM-3.1 (premature termination) because the WORK is "
        "complete; only the report was dropped. Observed live 2026-07-29 10:08 "
        "when a research agent wrote a 23KB deliverable then went idle silently.",
        stage="post-execution"),
    "WING-2": FailureMode(
        "WING-2", "WING: Wing-specific", "Orphaned capability",
        "A shipped oversight//capability function has zero call sites, so the "
        "control it implements never executes while documentation asserts it "
        "does. Audit 2026-07-29 found six. Root cause of green-on-silence.",
        stage="pre-execution"),
    "WING-3": FailureMode(
        "WING-3", "WING: Wing-specific", "Fabricated precision",
        "Reporting a specific figure, citation, or identifier that the cited "
        "source does not support. Superset of 'no citations supplied'. "
        "Distinct from FM-3.3 because nothing was verified incorrectly — the "
        "claim was manufactured.",
        stage="execution"),
}

ALL_MODES: dict[str, FailureMode] = {**MODES, **WING_MODES}

CATEGORIES = (FC1, FC2, FC3, "WING: Wing-specific")

# Codes that indicate the OVERSIGHT layer itself failed, not the worker.
# Tracked separately so "the watchmen" are measured too.
OVERSIGHT_FAILURE_CODES = ("FM-3.2", "FM-3.3", "WING-2")


def is_valid(code: str) -> bool:
    return code in ALL_MODES


def get(code: str) -> Optional[FailureMode]:
    return ALL_MODES.get(code)


def describe(code: str) -> str:
    m = ALL_MODES.get(code)
    if not m:
        return f"{code} (UNKNOWN CODE — not in MAST or Wing extensions)"
    return f"{m.code} {m.name} [{m.category}] — {m.definition}"


def classify_mechanically(
    *,
    declared_done: bool,
    artifacts_exist: bool,
    acceptance_criteria_met: Optional[bool],
    heartbeat_stale: bool,
    reported_result: bool,
    verification_ran: bool,
) -> Optional[str]:
    """Rule-based MAST assignment from OBSERVED FACTS — no model in the loop.

    This is the preferred classifier. It exists because LLM judges agree with
    humans only ~58% of the time on failure CATEGORY (vs ~89-97% on binary
    pass/fail), so a model's category guess is barely better than a coin flip
    across 14 classes. Every input here is a ground-truth observation the
    oversight layer can make without asking anyone.

    Returns None when the facts don't determine a code — in which case a model
    may PROPOSE one for human confirmation, but must not finalize it.
    """
    # Worker vanished mid-flight.
    if heartbeat_stale and not declared_done:
        return "FM-3.1"          # premature termination

    # Work is on disk but nobody was told. Observed 2026-07-29.
    if artifacts_exist and not reported_result and not declared_done:
        return "WING-1"          # silent success

    # Claimed done, nothing to show for it. The "false success" case.
    if declared_done and not artifacts_exist:
        return "FM-1.1"          # disobey task specification

    # Claimed done, artifacts exist, but nothing ever checked them.
    if declared_done and artifacts_exist and not verification_ran:
        return "FM-3.2"          # no or incomplete verification

    # Verification ran, passed it, but the criteria demonstrably were not met.
    if declared_done and verification_ran and acceptance_criteria_met is False:
        return "FM-3.3"          # incorrect verification

    return None


def category_of(code: str) -> str:
    m = ALL_MODES.get(code)
    return m.category if m else "UNKNOWN"


def is_oversight_failure(code: str) -> bool:
    """True when this code indicts the oversight layer rather than the worker."""
    return code in OVERSIGHT_FAILURE_CODES

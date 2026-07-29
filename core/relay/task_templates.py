"""
core/relay/task_templates.py — per-engine tasking-clarity builders.

Commander directive 2026-07-29: specs must be precise enough that Gemini
Flash and DeepSeek (via OC) can pick work up safely, not just Gemini 3.1 Pro
or Claude. Principle: a spec is safe for a weak model exactly when its
acceptance criteria pass Silver's own checkability test
(core.silver.gate.is_checkable) — reuse that bar rather than inventing a
second heuristic.

Note on PII: scripts/opencode_worker.py (the module with a PII_TOKENS fence)
is dead code — it imports a nonexistent `brain_bridge` module and is not the
live worker. The REAL live OC worker (scripts/oc_worker.py,
opencode-worker.service) has NO PII fence today. build_oc_task() below still
carries a PII reminder in the prompt text — but that's a courtesy instruction
to the model, not an enforced fence like the dead module's. Flagged, not
silently assumed fixed; fencing OC dispatch for real is a separate follow-up.
"""
from __future__ import annotations

from typing import Optional

from core.silver.gate import is_checkable

# Same category of tokens the (dead) opencode_worker.py fenced on — kept here
# as a prompt-level reminder only, not an enforced check (see module docstring).
_PII_REMINDER_TERMS = ("client names", "email addresses", "booking numbers", "PII")


def _checkability_warning(acceptance_criteria: str) -> str:
    if is_checkable(acceptance_criteria):
        return ""
    return (
        "\n\n⚠ WARNING: the stated 'done' condition above doesn't name anything "
        "checkable (no count, path, ref, or artifact) — a second seat won't be "
        "able to verify this without asking you. Consider tightening it before "
        "dispatch; this task still sends as-is (soft warning, not a block)."
    )


def build_ag_task(
    task: str,
    *,
    deliverable_path: Optional[str] = None,
    from_seat: str = "CC",
    verdict_tag: str = "AG",
    strengths: str = "your independent-engine read and large-context reach",
    acceptance_criteria: str = "",
) -> str:
    """AG (Talon/Gemini 3.1 Pro, or the Claude-via-agy fallback lane) can
    take real ambiguity — thin wrapper around the existing
    contact_ag.peer_prompt(), with a non-blocking checkability warning."""
    from core.relay.contact_ag import peer_prompt
    prompt = peer_prompt(
        task, deliverable_path=deliverable_path, from_seat=from_seat,
        verdict_tag=verdict_tag, strengths=strengths,
    )
    if acceptance_criteria:
        prompt += f"\n\nAcceptance criteria: {acceptance_criteria}"
        prompt += _checkability_warning(acceptance_criteria)
    return prompt


def build_oc_task(
    task: str,
    *,
    acceptance_criteria: str,
    deliverable_path: Optional[str] = None,
    steps: Optional[list[str]] = None,
) -> str:
    """OC (Jet/DeepSeek-lane, dispatched via core.relay.dispatch_oc) is cheap
    but not judgment-capable — ambiguity, not model IQ, is the real risk.
    Numbered bounded steps, explicit absolute output path, explicit
    stop-and-report condition instead of an open-ended judgment call."""
    lines = [
        "OC task — execute the numbered steps exactly. Do not improvise "
        "beyond what's written; if a step is unclear or blocked, STOP and "
        "report why instead of guessing.",
        "",
        f"TASK: {task}",
    ]
    if steps:
        lines.append("\nSTEPS:")
        lines.extend(f"  {i}. {s}" for i, s in enumerate(steps, 1))
    if deliverable_path:
        lines.append(f"\nWrite your result to the ABSOLUTE path: {deliverable_path}")
    lines.append(f"\nACCEPTANCE CRITERIA (this defines done): {acceptance_criteria}")
    lines.append(
        f"\nPII reminder: if this task involves {', '.join(_PII_REMINDER_TERMS)}, "
        "stop and report rather than proceeding — this lane is not PII-cleared."
    )
    lines.append(_checkability_warning(acceptance_criteria))
    return "\n".join(l for l in lines if l)


def build_flash_task(
    task: str,
    *,
    acceptance_criteria: str,
    deliverable_path: Optional[str] = None,
    literal_steps: Optional[list[str]] = None,
) -> str:
    """The weakest-model variant — every step a literal command or literal
    text to produce, zero interpretation required. Definition-of-done is one
    is_checkable()-passing sentence. If acceptance_criteria doesn't already
    pass, this raises rather than warning — Flash needs the harder guarantee
    a stronger model can work around but Flash cannot."""
    if not is_checkable(acceptance_criteria):
        raise ValueError(
            f"build_flash_task requires checkable acceptance_criteria "
            f"(a count, path, ref, or artifact) — got {acceptance_criteria!r}. "
            f"Flash cannot safely fill this gap the way AG/OC might."
        )
    lines = [
        "Flash task — follow the literal steps below exactly, in order. "
        "Every step is either a command to run or exact text to produce. "
        "Do not interpret, summarize, or add anything not listed.",
        "",
        f"TASK: {task}",
    ]
    if literal_steps:
        lines.append("\nLITERAL STEPS:")
        lines.extend(f"  {i}. {s}" for i, s in enumerate(literal_steps, 1))
    if deliverable_path:
        lines.append(f"\nWrite your result to the ABSOLUTE path: {deliverable_path}")
    lines.append(f"\nDONE means exactly: {acceptance_criteria}")
    return "\n".join(lines)

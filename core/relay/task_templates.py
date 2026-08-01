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

SO-METERED-SPEND-2026 Article 9: Every task builder requires an explicit
spend_ceiling parameter and emits a top-level CONSTRAINTS block containing:
  1. Spend ceiling string (or 'zero spend — read-only')
  2. Forbidden models/services (imported from engine_limits.py)
  3. The instruction: 'if this appears to require spend beyond your ceiling, STOP and report'
"""
from __future__ import annotations

from typing import Optional

from core.silver.gate import is_checkable
from core.relay.engine_limits import POE_BROKEN_VIA_OPENCODE, POE_WHITELIST

# Same category of tokens the (dead) opencode_worker.py fenced on — kept here
# as a prompt-level reminder only, not an enforced check (see module docstring).
_PII_REMINDER_TERMS = ("client names", "email addresses", "booking numbers", "PII")


def _build_constraints_block(spend_ceiling: str) -> str:
    """Build Article 9 CONSTRAINTS block for top of prompt text."""
    if not spend_ceiling or not isinstance(spend_ceiling, str) or not spend_ceiling.strip():
        raise ValueError(
            "spend_ceiling parameter is required and must be a non-empty string "
            "(e.g., 'zero', 'zero spend — read-only', or explicit point/dollar limit)."
        )

    cleaned = spend_ceiling.strip()
    if cleaned.lower() in ("zero", "0", "zero spend", "zero spend - read-only", "zero spend -- read-only", "zero spend — read-only"):
        ceiling_display = "zero spend — read-only"
    else:
        ceiling_display = cleaned

    broken_models = ", ".join(sorted(POE_BROKEN_VIA_OPENCODE))
    whitelist_models = ", ".join(sorted(POE_WHITELIST))

    return (
        "=== MANDATORY SPEND & ENGINE CONSTRAINTS ===\n"
        f"SPEND CEILING: {ceiling_display}\n"
        f"FORBIDDEN MODELS / SERVICES: Broken via OpenCode ({broken_models}); any Poe model not in whitelist ({whitelist_models}).\n"
        "OVER-BUDGET INSTRUCTION: if this appears to require spend beyond your ceiling, STOP and report.\n"
        "MANDATORY DELIVERABLES & PROGRESS FORMAT: Non-trivial work MUST produce durable markdown artifacts (<plan_name>.md and walkthrough.md). Status updates, plans, and reports MUST feature ASCII/Unicode visual progress bars ([████████░░░░░░░░░░░░] 40%) (SO 2026-07-31).\n"
        "============================================="
    )



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
    spend_ceiling: str,
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
    constraints = _build_constraints_block(spend_ceiling)
    prompt = peer_prompt(
        task, deliverable_path=deliverable_path, from_seat=from_seat,
        verdict_tag=verdict_tag, strengths=strengths,
    )
    if acceptance_criteria:
        prompt += f"\n\nAcceptance criteria: {acceptance_criteria}"
        prompt += _checkability_warning(acceptance_criteria)
    return f"{constraints}\n\n{prompt}"


def build_oc_task(
    task: str,
    *,
    spend_ceiling: str,
    acceptance_criteria: str,
    deliverable_path: Optional[str] = None,
    steps: Optional[list[str]] = None,
) -> str:
    """OC (Jet/DeepSeek-lane, dispatched via core.relay.dispatch_oc) is cheap
    but not judgment-capable — ambiguity, not model IQ, is the real risk.
    Numbered bounded steps, explicit absolute output path, explicit
    stop-and-report condition instead of an open-ended judgment call."""
    constraints = _build_constraints_block(spend_ceiling)
    lines = [
        constraints,
        "",
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
    spend_ceiling: str,
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
    constraints = _build_constraints_block(spend_ceiling)
    lines = [
        constraints,
        "",
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


def build_haiku_task(
    task: str,
    *,
    deliverable_path: str,
    acceptance_criteria: str,
    literal_steps: Optional[list[str]] = None,
) -> str:
    """Headless Claude Haiku (claude-haiku-4-5-20251001) — the CC-side
    counterpart to build_flash_task(). Closes the gap flagged in
    docs/CROSS_HALE_TASK_DELEGATION_DESIGN_20260716.md §1.7: the
    Haiku-vs-Sonnet-vs-Opus choice was happening ad hoc at the headless-spawn
    --model flag with no spec discipline, while OC/AG already had
    build_oc_task()/build_flash_task() gating them.

    UNLIKE build_oc_task/build_ag_task: Haiku draws the SAME Claude MAX/OAuth
    meter as interactive CC work (per the design doc's usage analysis — "CC
    and OC draw the SAME MAX meter... only AG adds throughput without
    touching the MAX bucket"). Delegating to Haiku buys precision-at-low-
    complexity and parallelism, NOT budget relief. Do not reach for it under
    the assumption it is free the way OC or AG's own meter is.

    No spend_ceiling param — this lane has no metered/points cost model,
    only the shared MAX weekly cap tracked separately.

    Mirrors build_flash_task's hard gate: raises immediately on
    non-checkable acceptance criteria rather than warning, and additionally
    REQUIRES deliverable_path — per docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md /
    .claude/CLAUDE.md, a headless Haiku prompt with no explicit WRITE [PATH]
    instruction silently loses its output. There is no optional/no-deliverable
    form of this builder for that reason."""
    if not deliverable_path or not deliverable_path.strip():
        raise ValueError(
            "build_haiku_task requires deliverable_path — a headless Haiku "
            "spawn with no explicit WRITE [PATH] instruction silently loses "
            "its output (docs/HEADLESS_CLAUDE_SPAWN_GUIDE.md)."
        )
    if not is_checkable(acceptance_criteria):
        raise ValueError(
            f"build_haiku_task requires checkable acceptance_criteria "
            f"(a count, path, ref, or artifact) — got {acceptance_criteria!r}. "
            f"Haiku cannot safely fill this gap the way CC/Sonnet/Opus might."
        )
    lines = [
        "Haiku task — follow the literal steps below exactly, in order. "
        "Do not interpret, summarize, or add anything not listed. If a step "
        "is unclear or blocked, STOP and report why instead of guessing.",
        "",
        f"TASK: {task}",
    ]
    if literal_steps:
        lines.append("\nLITERAL STEPS:")
        lines.extend(f"  {i}. {s}" for i, s in enumerate(literal_steps, 1))
    lines.append(f"\nWRITE your result to the ABSOLUTE path: {deliverable_path}")
    lines.append(
        "(Mandatory — if this prompt does not end with an explicit WRITE "
        "instruction naming an absolute path, your output is discarded.)"
    )
    lines.append(f"\nDONE means exactly: {acceptance_criteria}")
    return "\n".join(lines)


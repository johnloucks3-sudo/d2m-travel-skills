"""
tests/test_task_templates_ceiling.py — unit tests for Article 9 spend ceiling in task_templates.py.

SO-METERED-SPEND-2026 Article 9 requirements:
  (a) Spend ceiling parameter required & emitted (e.g. 'zero spend — read-only')
  (b) Forbidden model/service list emitted
  (c) The instruction 'if this appears to require spend beyond your ceiling, STOP and report' emitted
  (d) Constraints block positioned at TOP of generated prompt
  (e) Missing ceiling raises (TypeError or ValueError)
"""
from __future__ import annotations

import pytest

from core.relay.task_templates import (
    build_ag_task,
    build_oc_task,
    build_flash_task,
)
from core.relay.engine_limits import POE_BROKEN_VIA_OPENCODE, POE_WHITELIST


def test_builder_without_ceiling_raises():
    """Calling builders without spend_ceiling must fail loudly (TypeError or ValueError)."""
    with pytest.raises((TypeError, ValueError)):
        build_ag_task("Test task")  # type: ignore[call-arg]

    with pytest.raises((TypeError, ValueError)):
        build_oc_task("Test task", acceptance_criteria="file /tmp/test.txt exists")  # type: ignore[call-arg]

    with pytest.raises((TypeError, ValueError)):
        build_flash_task("Test task", acceptance_criteria="file /tmp/test.txt exists")  # type: ignore[call-arg]


def test_builder_with_empty_ceiling_raises():
    """Calling builders with empty/invalid spend_ceiling string must raise ValueError."""
    with pytest.raises(ValueError):
        build_ag_task("Test task", spend_ceiling="")

    with pytest.raises(ValueError):
        build_oc_task("Test task", spend_ceiling="   ", acceptance_criteria="file /tmp/test.txt exists")

    with pytest.raises(ValueError):
        build_flash_task("Test task", spend_ceiling="", acceptance_criteria="file /tmp/test.txt exists")


def test_builder_zero_ceiling_emits_article_9_elements():
    """Calling builders with spend_ceiling='zero' must emit all Article 9 elements."""
    prompt = build_ag_task(
        "Analyze repo structure",
        spend_ceiling="zero",
        acceptance_criteria="deliverable written to /tmp/out.md",
    )

    # (a) Spend ceiling element
    assert "SPEND CEILING: zero spend — read-only" in prompt

    # (b) Forbidden models/services element
    assert "FORBIDDEN MODELS / SERVICES:" in prompt
    for model in POE_BROKEN_VIA_OPENCODE:
        assert model in prompt
    for model in POE_WHITELIST:
        assert model in prompt

    # (c) Over-budget instruction element (verbatim)
    assert "if this appears to require spend beyond your ceiling, STOP and report" in prompt

    # (d) Positioned at TOP
    assert prompt.startswith("=== MANDATORY SPEND & ENGINE CONSTRAINTS ===")


def test_all_builders_emit_article_9():
    """Verify build_ag_task, build_oc_task, and build_flash_task all emit top constraints."""
    builders = [
        lambda: build_ag_task("AG task", spend_ceiling="zero", acceptance_criteria="path /tmp/a exists"),
        lambda: build_oc_task("OC task", spend_ceiling="zero", acceptance_criteria="path /tmp/b exists"),
        lambda: build_flash_task("Flash task", spend_ceiling="zero", acceptance_criteria="path /tmp/c exists"),
    ]

    for builder in builders:
        prompt = builder()
        assert prompt.startswith("=== MANDATORY SPEND & ENGINE CONSTRAINTS ===")
        assert "zero spend — read-only" in prompt
        assert "if this appears to require spend beyond your ceiling, STOP and report" in prompt
        assert "FORBIDDEN MODELS / SERVICES:" in prompt


def test_custom_spend_ceiling():
    """Verify custom spend ceiling strings pass through properly."""
    prompt = build_oc_task(
        "Custom spend task",
        spend_ceiling="50 points max",
        acceptance_criteria="path /tmp/d exists",
    )
    assert "SPEND CEILING: 50 points max" in prompt
    assert "if this appears to require spend beyond your ceiling, STOP and report" in prompt

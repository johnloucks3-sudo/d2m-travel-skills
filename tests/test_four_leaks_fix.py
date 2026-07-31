"""
tests/test_four_leaks_fix.py — Unit test for 4-leak background spend fixes
"""

import json
import tempfile
from pathlib import Path
import pytest

import json
import tempfile
from pathlib import Path
import pytest

import OpsCenter.hale_brain_monitor_12h as hbm
from OpsCenter.hale_incident_router import compute_signature, RULE_1, COMMANDER_GATE_SERVICES
from OpsCenter.hale_dispatcher import classify_task


def test_brain_monitor_opencode_free_lane():
    """Verify test_opencode_headless_dispatch runs without spawning Claude CLI."""
    manifest = "# TEST MANIFEST\nRule: test"
    result = hbm.test_opencode_headless_dispatch(manifest)
    assert result["status"] == "PASS"
    assert result["platform"] == "OpenCode Headless"
    assert len(result["test_results"]) == 3
    assert result["model"] == "opencode-free-lane"


def test_incident_router_rule1():
    """Verify incident router constants and signature logic."""
    sig = compute_signature("thunderbird-telegram-gw", "Error details test")
    assert len(sig) == 12
    assert RULE_1 == "auto_heal_success_never_pages_commander"
    assert "hale-draft-engine" in COMMANDER_GATE_SERVICES


def test_dispatcher_classification():
    """Verify Hale dispatcher task classification."""
    assert classify_task("visual dashboard summary") == "visual"
    assert classify_task("hello") == "self"


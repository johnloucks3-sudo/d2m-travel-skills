"""Regression test for core/monitoring/telegram_dedup_gate.py.

REGRESSION (2026-07-16): 90+ scripts each POST directly to api.telegram.org
with zero shared rate-limiting or dedup, so a crash-looping service (or any
per-cycle alert) paged the Commander every run forever -- "hundreds of
notices about system outages... dedupe/silence." This gate suppresses
muted topics and cooldown-window repeats at the network layer so no
individual script needs to change.
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.monitoring.telegram_dedup_gate as gate  # noqa: E402


def _reset_state(tmp_path):
    gate.STATE_DIR = tmp_path
    gate.MUTED_TOPICS_FILE = tmp_path / "telegram_muted_topics.json"
    gate.DEDUP_STATE_FILE = tmp_path / "telegram_dedup_state.json"
    gate.SUPPRESSED_LOG = tmp_path / "telegram_suppressed.log"


def test_muted_topic_is_suppressed(tmp_path):
    _reset_state(tmp_path)
    gate._ensure_seed_mute_list()
    reason = gate.should_suppress("123", "Nancy Lyons FPD overdue again")
    assert reason == "muted:Lyons"


def test_identical_repeat_within_cooldown_is_suppressed(tmp_path):
    _reset_state(tmp_path)
    text = "Service X failed at 2026-07-16 08:00:00 attempt #1"
    repeat_text = "Service X failed at 2026-07-16 09:14:22 attempt #47"

    first = gate.should_suppress("123", text)
    second = gate.should_suppress("123", repeat_text)

    assert first is None, "first occurrence of a new signature must not be suppressed"
    assert second == "cooldown", "near-identical repeat within cooldown window must be suppressed"


def test_distinct_messages_are_not_suppressed(tmp_path):
    _reset_state(tmp_path)
    assert gate.should_suppress("123", "Service X failed") is None
    assert gate.should_suppress("123", "Completely different content here") is None


def test_different_chat_ids_do_not_cross_suppress(tmp_path):
    _reset_state(tmp_path)
    assert gate.should_suppress("111", "Same alert text") is None
    assert gate.should_suppress("222", "Same alert text") is None

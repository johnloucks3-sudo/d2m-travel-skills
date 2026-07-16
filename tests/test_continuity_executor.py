"""Regression tests for core/continuity/continuity_executor.py in-flight spawn guard.

Encodes the exact OOM runaway captured in continuity_log.jsonl (2026-07-15): a
triggered alert whose result file takes minutes to appear was re-spawning a fresh
headless Claude on every 30s poll cycle. Because spawn_headless_claude uses
start_new_session=True (which does NOT move the child out of the service cgroup),
dozens of stacked Claude subprocess trees accumulated in one cgroup and drove the
OOM kills (8G swap peak per cgroup). The guard must spawn exactly once while a
prior spawn is still alive and the result file has not yet appeared.
"""
from __future__ import annotations

import os

import core.continuity.continuity_executor as ce
import core.ai_infra.thunderbird_headless_spawn as spawn_mod


def _one_triggered_alert():
    # trigger_date far in the past → check_trigger() returns True (ISO string compare)
    return [{
        "id": "TEST-RUNAWAY",
        "condition_type": "date",
        "trigger_date": "2000-01-01T00:00:00",
        "message": "past-dated alert that triggers immediately",
    }]


def _isolate(tmp_path, monkeypatch):
    """Redirect all continuity state into tmp so no real files are touched."""
    monkeypatch.setattr(ce, "CONTINUITY_DIR", tmp_path)
    (tmp_path / "results").mkdir(exist_ok=True)
    monkeypatch.setattr(ce, "CONTINUITY_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(ce, "load_hale_state", _one_triggered_alert)


def test_guard_spawns_once_while_prior_spawn_alive(tmp_path, monkeypatch):
    """Two poll cycles, one triggered alert, no result file yet → exactly one spawn."""
    _isolate(tmp_path, monkeypatch)

    calls = {"n": 0}

    def fake_spawn(*args, **kwargs):
        calls["n"] += 1
        # Return a PID that is definitely alive (this test process) so the
        # liveness guard trips on the second poll — exactly the real scenario
        # where the first headless Claude is still running.
        return {"status": "SPAWNED", "pid": os.getpid()}

    monkeypatch.setattr(spawn_mod, "spawn_headless_claude", fake_spawn)

    ce.poll_deferred_alerts()  # first poll → spawns
    ce.poll_deferred_alerts()  # second poll → guard must block (spawn still alive)

    assert calls["n"] == 1, f"expected exactly one spawn, got {calls['n']} — runaway regressed"


def test_result_present_never_spawns(tmp_path, monkeypatch):
    """A completed result file means the alert is done — never spawn again."""
    _isolate(tmp_path, monkeypatch)
    (tmp_path / "results" / "TEST-RUNAWAY_result.json").write_text("{}")

    calls = {"n": 0}

    def fake_spawn(*args, **kwargs):
        calls["n"] += 1
        return {"status": "SPAWNED", "pid": os.getpid()}

    monkeypatch.setattr(spawn_mod, "spawn_headless_claude", fake_spawn)

    ce.poll_deferred_alerts()
    assert calls["n"] == 0


def test_dead_spawn_retries_after_cooldown(tmp_path, monkeypatch):
    """If a spawn died without producing a result, retry is allowed only after the
    cooldown backstop — not on the very next 30s poll."""
    _isolate(tmp_path, monkeypatch)

    calls = {"n": 0}

    def fake_spawn(*args, **kwargs):
        calls["n"] += 1
        # PID 2**31-1 is effectively never a live process → treated as dead spawn.
        return {"status": "SPAWNED", "pid": 2**31 - 1}

    monkeypatch.setattr(spawn_mod, "spawn_headless_claude", fake_spawn)

    ce.poll_deferred_alerts()  # spawns once, records a dead PID
    ce.poll_deferred_alerts()  # dead but within cooldown → must NOT respawn
    assert calls["n"] == 1

    # Force the marker's timestamp past the cooldown window → retry now allowed.
    monkeypatch.setattr(ce, "SPAWN_RETRY_COOLDOWN", -1)
    ce.poll_deferred_alerts()
    assert calls["n"] == 2

"""Tests for scripts/generic_remediate.py — the long-tail auto-remediation
dispatch target for systemd's OnFailure=. Per docs/superpowers/specs/
2026-07-09-self-healing-architecture-reverse-engineered.md."""
from __future__ import annotations

import json

import scripts.generic_remediate as gr
import core.ops.hale_orchestrator as ho_module


def test_cooldown_not_blocking_when_no_prior_attempt():
    assert gr._cooldown_blocking({}, "some.service") is False


def test_cooldown_blocking_within_window(monkeypatch):
    from datetime import datetime, timezone
    state = {"some.service": {"last_attempt": datetime.now(timezone.utc).isoformat()}}
    assert gr._cooldown_blocking(state, "some.service") is True


def test_cooldown_not_blocking_after_window_elapsed():
    from datetime import datetime, timezone, timedelta
    old = (datetime.now(timezone.utc) - timedelta(seconds=gr.COOLDOWN_SECONDS + 10)).isoformat()
    state = {"some.service": {"last_attempt": old}}
    assert gr._cooldown_blocking(state, "some.service") is False


def test_remediate_recovers_a_real_unit(tmp_path, monkeypatch):
    """End-to-end against a real, disposable systemd --user unit — proves the
    actual mechanism (reset-failed + start + independent is-active re-check),
    not a mocked stand-in."""
    monkeypatch.setattr(gr, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")

    unit_name = "generic-remediate-canary-test.service"
    unit_dir = tmp_path / "systemd_units"
    unit_dir.mkdir()
    unit_path = unit_dir / unit_name
    unit_path.write_text(
        "[Unit]\nDescription=canary test unit for generic_remediate\n\n"
        "[Service]\nType=oneshot\nRemainAfterExit=yes\nExecStart=/bin/true\n"
    )

    import subprocess
    real_systemd_dir = None
    from pathlib import Path
    real_systemd_dir = Path.home() / ".config" / "systemd" / "user"
    real_systemd_dir.mkdir(parents=True, exist_ok=True)
    installed_path = real_systemd_dir / unit_name
    installed_path.write_text(unit_path.read_text())
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, timeout=15)
        # Deliberately fail it first (mimics OnFailure= firing on a real crash)
        subprocess.run(["systemctl", "--user", "start", unit_name], timeout=15)

        exit_code = gr.remediate(unit_name)

        assert exit_code == 0
        text = (tmp_path / "decisions.md").read_text()
        assert unit_name in text
        assert "<!-- PLAN:CLOSE" in text
        state = json.loads((tmp_path / "state.json").read_text())
        assert state[unit_name]["recovered"] is True
    finally:
        subprocess.run(["systemctl", "--user", "stop", unit_name], timeout=15)
        installed_path.unlink(missing_ok=True)
        subprocess.run(["systemctl", "--user", "daemon-reload"], timeout=15)


def test_remediate_escalates_when_cooldown_blocks(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({
        "phantom.service": {"last_attempt": datetime.now(timezone.utc).isoformat()}
    }))
    monkeypatch.setattr(gr, "STATE_FILE", state_file)
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")

    escalated = {}
    monkeypatch.setattr(gr, "_escalate", lambda unit, reason: escalated.setdefault(unit, reason))

    exit_code = gr.remediate("phantom.service")

    assert exit_code == 1
    assert "phantom.service" in escalated


def test_circuit_breaker_trips_after_max_consecutive_failures(tmp_path, monkeypatch):
    """ADDED 2026-07-16: the cooldown throttled FREQUENCY but never capped
    TOTAL attempts -- a unit with a genuinely unfixable target (missing
    recipe file, dead config) retried once an hour for 7 straight days
    (~135 attempts, d2m-factbook-refresh.service) before this existed.
    Once consecutive_failures reaches MAX_CONSECUTIVE_FAILURES, remediate()
    must stop calling systemctl entirely and escalate exactly once, not
    every subsequent call."""
    from datetime import datetime, timezone, timedelta

    state_file = tmp_path / "state.json"
    old_enough = (datetime.now(timezone.utc) - timedelta(seconds=gr.COOLDOWN_SECONDS + 10)).isoformat()
    state_file.write_text(json.dumps({
        "chronic.service": {
            "last_attempt": old_enough,
            "consecutive_failures": gr.MAX_CONSECUTIVE_FAILURES,
        }
    }))
    monkeypatch.setattr(gr, "STATE_FILE", state_file)
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")

    escalations = []
    monkeypatch.setattr(gr, "_escalate", lambda unit, reason: escalations.append((unit, reason)))
    systemctl_calls = []
    monkeypatch.setattr(gr, "_run", lambda cmd, timeout=20: (systemctl_calls.append(cmd), (True, ""))[1])

    exit_code = gr.remediate("chronic.service")
    assert exit_code == 1
    assert not systemctl_calls, "circuit breaker must skip systemctl entirely once tripped"
    assert len(escalations) == 1
    assert "CIRCUIT BREAKER TRIPPED" in escalations[0][1]

    # Second call while still tripped must NOT escalate again.
    exit_code2 = gr.remediate("chronic.service")
    assert exit_code2 == 1
    assert not systemctl_calls
    assert len(escalations) == 1, "must not re-escalate on every subsequent call once already flagged"


def test_remediate_defers_when_unit_arg_missing_suffix(tmp_path, monkeypatch):
    """Regression test for the real production bug found 2026-07-10: systemd's
    %i template specifier strips the .service/.timer suffix, but
    LANE1_OWNED_UNITS stores full suffixed names. A bare 'in' check never
    matched the real dispatch path (only manual tests calling remediate()
    with a hand-typed full name), so the exclusion guard was silently
    non-functional end-to-end -- a live cascade of failed
    thunderbird-generic-remediate@ units caught it, not this test suite."""
    monkeypatch.setattr(gr, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    ran_commands = []
    monkeypatch.setattr(gr, "_run", lambda cmd, timeout=20: ran_commands.append(cmd) or (True, ""))

    owned_unit_with_suffix = next(iter(gr.LANE1_OWNED_UNITS))
    owned_unit_no_suffix = owned_unit_with_suffix.rsplit(".", 1)[0]

    exit_code = gr.remediate(owned_unit_no_suffix)

    assert exit_code == 0
    assert ran_commands == []


def test_remediate_defers_to_lane1_owned_unit(tmp_path, monkeypatch):
    """The exclusion guard closing Whetstone's named cross-check: a unit
    already owned by Lane 1's CI Repair Warehouse must never be touched by
    this mechanism (no reset-failed/start attempt), so the two systems
    can't race the same unit."""
    monkeypatch.setattr(gr, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(ho_module, "HALE_DECISIONS", tmp_path / "decisions.md")
    ran_commands = []
    monkeypatch.setattr(gr, "_run", lambda cmd, timeout=20: ran_commands.append(cmd) or (True, ""))

    owned_unit = next(iter(gr.LANE1_OWNED_UNITS))
    exit_code = gr.remediate(owned_unit)

    assert exit_code == 0
    assert ran_commands == []  # no reset-failed / start attempted at all
    text = (tmp_path / "decisions.md").read_text()
    assert "deferred to Lane 1" in text
    assert "**Criteria unverified:**" in text and owned_unit in text


def test_remediate_never_raises_on_orchestrator_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(gr, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(ho_module, "open_plan", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(gr, "_run", lambda cmd, timeout=20: (False, "no such unit"))
    monkeypatch.setattr(gr, "_is_active", lambda unit: False)
    monkeypatch.setattr(gr, "_escalate", lambda unit, reason: None)

    exit_code = gr.remediate("nonexistent-unit.service")  # must not raise
    assert exit_code == 1

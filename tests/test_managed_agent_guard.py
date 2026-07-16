"""Guard tests for core.ai_infra.managed_agent_client — the Managed Agents API
is absent on the installed anthropic SDK (0.86.0); callers must fail loudly with
root cause, not a cryptic AttributeError. No network."""
import types

import pytest

from core.ai_infra import managed_agent_client as mac


class _FakeBeta:
    def __init__(self, attrs):
        for a in attrs:
            setattr(self, a, object())


class _FakeClient:
    def __init__(self, beta_attrs):
        self.beta = _FakeBeta(beta_attrs)


def test_supported_false_on_installed_sdk_surface():
    """0.86.0 beta surface (no sessions/agents/environments) -> unsupported."""
    client = _FakeClient(["files", "messages", "models", "skills"])
    assert mac._managed_agents_supported(client) is False


def test_supported_true_when_api_present():
    client = _FakeClient(["environments", "agents", "sessions", "messages"])
    assert mac._managed_agents_supported(client) is True


def test_require_raises_with_actionable_message():
    client = _FakeClient(["files", "messages"])
    with pytest.raises(RuntimeError) as exc:
        mac._require_managed_agents(client)
    msg = str(exc.value)
    assert "Managed Agents API unavailable" in msg
    assert "claude -p" in msg  # points callers at the working fallback


def test_get_or_create_agent_guarded(monkeypatch):
    """_get_or_create_agent (called directly by self_observability) preflights the API."""
    inst = mac.WingAgentClient.__new__(mac.WingAgentClient)
    inst._client = _FakeClient(["files", "messages"])
    inst._agent_ids = {}
    with pytest.raises(RuntimeError):
        inst._get_or_create_agent("haiku")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

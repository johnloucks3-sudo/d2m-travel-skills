"""P5c — Scoped subagent graceful degradation (continuity build, 2026-06-11).

Pattern (stolen from Atomic Claude's agent architecture): every dispatched
subagent should carry a MACHINE-READABLE fallback path inline in its prompt, so
when its primary tool/source is unavailable it degrades to a documented
secondary instead of failing or silently escalating to the parent.

Usage:
    from core.ai_infra.agent_fallback import with_fallback
    prompt = with_fallback(
        task="Find where X is configured.",
        primary="atomic/qdrant semantic search",
        fallback="ripgrep over the repo, then read the top 3 hits",
        on_total_failure="report 'unresolved: searched A and B, found nothing' — do NOT guess",
    )

The returned prompt appends a standard DEGRADATION block the subagent must obey.
This makes self-healing explicit at the prompt level: the agent knows what to do
when its primary tool fails, without bubbling the failure up.
"""
from __future__ import annotations


DEGRADATION_TEMPLATE = (
    "\n\n--- GRACEFUL DEGRADATION (mandatory) ---\n"
    "PRIMARY approach: {primary}\n"
    "IF the primary tool/source is unavailable, errors, or returns nothing: "
    "fall back to → {fallback}\n"
    "IF both fail: {on_total_failure}\n"
    "Do not silently escalate to the parent and do not fabricate. State which "
    "path you used (primary/fallback/none) in your result."
)


def with_fallback(task: str, primary: str, fallback: str,
                  on_total_failure: str = "report the gap explicitly; do not guess") -> str:
    """Append a standard graceful-degradation clause to a dispatch prompt."""
    return task.rstrip() + DEGRADATION_TEMPLATE.format(
        primary=primary, fallback=fallback, on_total_failure=on_total_failure,
    )


if __name__ == "__main__":
    # Self-test / certification: prove the degradation block is injected and
    # carries all three paths.
    out = with_fallback(
        task="Locate the credential keepalive timer.",
        primary="systemctl --user list-timers",
        fallback="grep ~/.config/systemd/user for *keepalive*.timer",
        on_total_failure="report 'no keepalive timer found' — do not assume one exists",
    )
    assert "GRACEFUL DEGRADATION" in out
    assert "systemctl --user list-timers" in out  # primary
    assert "grep ~/.config/systemd/user" in out   # fallback
    assert "do not assume one exists" in out       # total-failure
    assert "Do not silently escalate" in out
    print("P5c PASS — degradation block injects primary + fallback + total-failure paths")

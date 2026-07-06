#!/usr/bin/env python3
"""Channel Router — Telegram vs AgentMail Rules of Engagement (2026-07-06).

Codifies Sterling's dividing line from docs/TELEGRAM_AGENTMAIL_ROE_20260706.md:
durable artifact vs signal. Anything with substance the Commander re-reads
(proposal, research reply, draft) is an AgentMail artifact. Anything that's
just a nudge (notify, ack, status, "look now") rides Telegram.

The five rules this module enforces:
  1. Content on email, control on Telegram.
  2. Notify-and-wait is always Telegram.
  3. One thread, one medium — silent channel-switching is flagged as an anomaly.
  4. Daily digest rides Telegram, sourced from the AgentMail log.
  5. The five named-waiver correspondents never route through Telegram.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

WAIVERS_PATH = Path("/home/john/Thunderbird/config/wf17_named_waivers.json")
DECISIONS_LOG = Path("/home/john/Thunderbird/hale_decisions.md")
CONTEXT_MISS_STATE = Path("/home/john/Thunderbird/OpsCenter/state/channel_context_miss.json")

TELEGRAM = "telegram"
AGENTMAIL = "agentmail"

# message_type -> fixed channel(s). A tuple of length 2 means "both, monitored" (gate_veto).
MESSAGE_TYPE_CHANNELS = {
    "notify": (TELEGRAM,),
    "proposal": (AGENTMAIL,),
    "research_reply": (AGENTMAIL,),
    "daily_digest": (TELEGRAM,),
    "gate_veto": (TELEGRAM, AGENTMAIL),
}


class SilentSwitchError(RuntimeError):
    """Raised when a routing decision would open a new channel mid-thread
    without an explicit handoff phrase — rule 3 violation."""


def _is_named_waiver_recipient(recipient_email: str | None) -> bool:
    """Rule 5 — the five named-waiver correspondents never route through
    Telegram, regardless of message type. Quota there is mission-critical."""
    if not recipient_email:
        return False
    try:
        waivers = json.loads(WAIVERS_PATH.read_text())["waivers"]
    except (OSError, json.JSONDecodeError, KeyError):
        return False
    bare = recipient_email.strip().lower()
    for w in waivers:
        if bare in {e.lower() for e in w["emails"]}:
            return True
    return False


def route_by_content_type(message_type: str, has_substance: bool | None = None,
                           recipient_email: str | None = None) -> str | tuple:
    """Decide which channel a message rides.

    message_type: one of MESSAGE_TYPE_CHANNELS' keys, or any other string for
      ad-hoc content — falls back to the has_substance heuristic (rule 1).
    has_substance: only consulted when message_type isn't a known fixed type.
      True -> AgentMail (durable artifact). False/None -> Telegram (signal).
    recipient_email: when set and on the named-waiver allowlist, forces
      AgentMail regardless of message_type (rule 5 overrides everything else).

    Returns a single channel string, or a 2-tuple ("telegram", "agentmail")
    for gate_veto — both channels must be monitored, per the auto-execute
    cross-channel veto fix in core/ops/confirmed_auto_execute.py.
    """
    if _is_named_waiver_recipient(recipient_email):
        return AGENTMAIL

    if message_type in MESSAGE_TYPE_CHANNELS:
        channels = MESSAGE_TYPE_CHANNELS[message_type]
        return channels[0] if len(channels) == 1 else channels

    return AGENTMAIL if has_substance else TELEGRAM


def check_thread_handoff(prior_channel: str, next_channel: str, handoff_announced: bool) -> None:
    """Rule 3 — one thread, one medium. Raises SilentSwitchError if a
    conversation is about to move to a different channel without an explicit
    handoff ("continuing on Telegram"). Call this before opening a new
    channel mid-conversation; on error, log the anomaly and hold the switch."""
    if prior_channel != next_channel and not handoff_announced:
        _log_context_miss(
            f"Silent channel switch detected: {prior_channel} -> {next_channel} "
            "without an explicit handoff announcement."
        )
        raise SilentSwitchError(
            f"Switching {prior_channel} -> {next_channel} requires an explicit "
            f"handoff (e.g. 'continuing on Telegram') before opening the new channel."
        )


def _load_context_miss_state() -> dict:
    if not CONTEXT_MISS_STATE.exists():
        return {"total_messages": 0, "miss_events": []}
    try:
        return json.loads(CONTEXT_MISS_STATE.read_text())
    except (OSError, json.JSONDecodeError):
        return {"total_messages": 0, "miss_events": []}


def _save_context_miss_state(state: dict) -> None:
    CONTEXT_MISS_STATE.parent.mkdir(parents=True, exist_ok=True)
    CONTEXT_MISS_STATE.write_text(json.dumps(state, indent=2))


def record_message_sent() -> None:
    """Increment the denominator for the cross-channel context-miss metric."""
    state = _load_context_miss_state()
    state["total_messages"] = state.get("total_messages", 0) + 1
    _save_context_miss_state(state)


def _log_context_miss(detail: str) -> None:
    """Rule 3 anomaly / Commander confusion event — increments the numerator
    for the cross-channel context-miss rate metric."""
    state = _load_context_miss_state()
    state.setdefault("miss_events", []).append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "detail": detail,
    })
    _save_context_miss_state(state)


def record_context_miss(detail: str) -> None:
    """Public entry point — call when the Commander replies asking
    'what?' or 'where is this?' (a live context-miss event)."""
    _log_context_miss(detail)


def context_miss_rate() -> float:
    state = _load_context_miss_state()
    total = state.get("total_messages", 0)
    misses = len(state.get("miss_events", []))
    if total == 0:
        return 0.0
    return misses / total


def log_weekly_context_miss_metric() -> str:
    """Appends the current cross-channel context-miss rate to hale_decisions.md.
    Reviewed weekly in the Baldrige sweep per the ROE doc's metric line."""
    state = _load_context_miss_state()
    total = state.get("total_messages", 0)
    misses = len(state.get("miss_events", []))
    rate = context_miss_rate()
    status = "OK" if rate < 0.02 else "BREACH (target <2%)"
    now = datetime.now(timezone.utc).isoformat()
    entry = (
        f"\n## {now[:10]} — Cross-channel context-miss rate (weekly)\n"
        f"**Metric:** {misses}/{total} messages ({rate:.2%}) — {status}. "
        f"Source: `OpsCenter/state/channel_context_miss.json`. "
        f"Doctrine: `docs/TELEGRAM_AGENTMAIL_ROE_20260706.md`.\n"
    )
    with DECISIONS_LOG.open("a") as f:
        f.write(entry)
    return entry


if __name__ == "__main__":
    print(route_by_content_type("notify"))

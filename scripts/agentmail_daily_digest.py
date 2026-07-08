#!/usr/bin/env python3
"""AgentMail Daily Digest — Bold Use #6 + ROE rule 4 (2026-07-06).

Rule 4 of the Telegram/AgentMail ROE says the daily digest rides Telegram,
sourced from the AgentMail log. This is that script — reads everything
sent/received across all AgentMail inboxes (CONDOR, WIND, Sterling, and
any future persona inboxes) in the last 24h, and pushes one summary to
Telegram. The summary is a signal; the underlying items stay retrievable
in email, per the ROE's own dividing line.

Extends to weekly/monthly via --period.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

from core.email.agentmail_client import AgentMailClient
from core.ops.confirmed_auto_execute import send_telegram_notification

PERIOD_HOURS = {"daily": 24, "weekly": 24 * 7, "monthly": 24 * 30}

_BRIDGE_STATE = Path("/home/john/Thunderbird/OpsCenter/state/gmail_agentmail_bridge.json")


def _build_gmail_section(period: str = "daily") -> str:
    """Pull d2mconcierge Gmail threads from the bridge state for the digest.

    Reads the bridge JSONL queue and bridge state to surface:
    - How many client threads were forwarded to AgentMail in the period
    - Any quota warnings
    Uses local state only — no Gmail API call (digest should be fast and zero-quota-cost).
    """
    lines = ["\n--- Client Gmail (d2mconcierge) ---"]
    try:
        if not _BRIDGE_STATE.exists():
            lines.append("  (bridge not yet initialized -- run gmail_agentmail_bridge_poller.py)")
            return "\n".join(lines)
        state = json.loads(_BRIDGE_STATE.read_text())
        forwarded = state.get("forwarded_thread_ids", [])
        synced = state.get("synced_send_ids", [])
        pushed = state.get("pushed_draft_thread_ids", [])
        last_poll = state.get("last_processed_ts", "never")
        last_reply = state.get("last_sent_sync_ts", "never")

        # Count activity in the period window (forwarded IDs don't have timestamps,
        # so we report totals and last-poll time as the availability signal)
        lines.append(f"  Last inbound poll: {last_poll[:19] if last_poll and last_poll != 'never' else 'never'}")
        lines.append(f"  Last reply sync:   {last_reply[:19] if last_reply and last_reply != 'never' else 'never'}")
        lines.append(f"  Forwarded to AgentMail (total): {len(forwarded)} threads")
        lines.append(f"  Commander replies synced (total): {len(synced)} messages")
        lines.append(f"  Drafts pushed to Gmail (total): {len(pushed)} drafts")

        # AgentMail quota status
        quota_path = Path("/home/john/Thunderbird/OpsCenter/state/agentmail_quota.json")
        if quota_path.exists():
            q = json.loads(quota_path.read_text())
            day_count = q.get("day_count", 0)
            lines.append(f"  AgentMail quota today: {day_count}/90 buffer (100 hard cap)")
    except Exception as e:
        lines.append(f"  (bridge state read error: {e})")
    return "\n".join(lines)


def build_digest(period: str = "daily") -> str:
    client = AgentMailClient()
    since = datetime.now(timezone.utc) - timedelta(hours=PERIOD_HOURS[period])
    inboxes = client.list_inboxes()

    lines = [f"⚡ AgentMail {period.capitalize()} Digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n"]
    total_sent, total_received = 0, 0

    for ib in inboxes.inboxes:
        messages = client.list_messages(ib.inbox_id, limit=50)
        sent = [m for m in messages.messages if "sent" in m.labels and m.timestamp >= since]
        received = [m for m in messages.messages if "received" in m.labels and m.timestamp >= since]
        if not sent and not received:
            continue
        total_sent += len(sent)
        total_received += len(received)
        lines.append(f"\n<b>{ib.display_name}</b> ({ib.inbox_id})")
        for m in sent[:5]:
            lines.append(f"  → sent: {m.subject} (to {', '.join(m.to)})")
        for m in received[:5]:
            lines.append(f"  ← received: {m.subject} (from {m.from_})")
        if len(sent) > 5 or len(received) > 5:
            lines.append(f"  ...+{max(0, len(sent)-5)} more sent, +{max(0, len(received)-5)} more received")

    lines.append(f"\n<b>Total: {total_sent} sent, {total_received} received across {len(inboxes.inboxes)} inboxes</b>")
    if total_sent == 0 and total_received == 0:
        lines.append("(quiet period — nothing to report)")
    lines.append(_build_gmail_section(period))
    return "\n".join(lines)


def main():
    period = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if period not in PERIOD_HOURS:
        print(f"Usage: {sys.argv[0]} [daily|weekly|monthly]")
        sys.exit(1)
    digest = build_digest(period)
    print(digest)
    result = send_telegram_notification(digest)
    print(f"telegram send: delivered={result['delivered']}")


if __name__ == "__main__":
    main()

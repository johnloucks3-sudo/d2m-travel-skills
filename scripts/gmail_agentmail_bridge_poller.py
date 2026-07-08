#!/usr/bin/env python3
"""gmail_agentmail_bridge_poller.py — systemd timer entry point for the bridge.

Runs every 5 minutes via d2m-gmail-agentmail-bridge.timer.
Calls poll_and_forward() (#1) and sync_commander_replies() (#3) in sequence.

Install the timer:
  python3 scripts/create_systemd_timer.py \\
    --name "d2m-gmail-agentmail-bridge" \\
    --description "AgentMail<->Gmail d2mconcierge inbound bridge and reply sync" \\
    --command "python3 /home/john/Thunderbird/scripts/gmail_agentmail_bridge_poller.py" \\
    --on-calendar "*:0/5" \\
    --enable

Manual run (dry-run):
  python3 scripts/gmail_agentmail_bridge_poller.py --dry-run
"""
import sys
import argparse
from datetime import datetime, timezone

sys.path.insert(0, "/home/john/Thunderbird")

from core.email.agentmail_gmail_bridge import poll_and_forward, sync_commander_replies


def main():
    parser = argparse.ArgumentParser(description="AgentMail<->Gmail bridge poller")
    parser.add_argument("--dry-run", action="store_true", help="No sends, print only")
    args = parser.parse_args()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[bridge-poller] {ts} -- starting cycle")

    r1 = poll_and_forward(dry_run=args.dry_run)
    print(
        f"[bridge-poller] inbound: forwarded={r1['forwarded']} "
        f"skipped={r1['skipped']} quota_stopped={r1['quota_stopped']}"
    )
    if r1["quota_stopped"]:
        print("[bridge-poller] WARNING: per-poll burst cap hit -- some threads deferred to next cycle")

    r3 = sync_commander_replies(dry_run=args.dry_run)
    print(f"[bridge-poller] replies: synced={r3['synced']} skipped={r3['skipped']}")

    print(f"[bridge-poller] cycle complete")


if __name__ == "__main__":
    main()

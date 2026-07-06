#!/usr/bin/env python3
"""c2-fabric-roundtrip CI probe — Whetstone's spec (2026-07-06 retroactive T3 input).

Not a presence/heartbeat check. Asserts a CONFIRMED round-trip on each leg of
the Unified C2 Fabric:
  1. hale_bus_state.json: write a canary entry, read it back, assert match.
  2. AgentMail: send a canary message to hale-thunderbird's own inbox and
     assert it is retrievable via the API (confirmed receipt, not just
     accepted-for-delivery).

A single failure on EITHER leg means: exit 1, and the caller (confirmed_auto_execute
consumers) must treat that channel's silence=GO as suspended until this probe
passes again. This does NOT wait for the standard 3-consecutive/5-in-7d REPLACE
threshold — a single silent drop on a silence=GO path can mis-fire an
unapproved action, so the bar here is stricter than normal CI replacement.
"""
import json
import sys
import time
import uuid

sys.path.insert(0, "/home/john/Thunderbird")

from core.hale_bus.hale_bus_write import append_channel_activity, read_channel_activity


def probe_bus_roundtrip() -> bool:
    canary_id = f"canary-{uuid.uuid4().hex[:8]}"
    append_channel_activity("console", "ci_probe_canary", canary_id, ref=canary_id)
    found = [e for e in read_channel_activity() if e.get("ref") == canary_id]
    return len(found) == 1


def probe_agentmail_roundtrip() -> bool:
    from core.email.agentmail_client import AgentMailClient
    client = AgentMailClient()
    canary_id = f"canary-{uuid.uuid4().hex[:8]}"
    sent = client.send_message(
        inbox_id="hale-thunderbird@agentmail.to",
        to=["hale-thunderbird@agentmail.to"],
        subject=f"[CI PROBE] c2-fabric-roundtrip {canary_id}",
        text=f"CI roundtrip canary {canary_id}",
    )
    time.sleep(3)
    messages = client.list_messages("hale-thunderbird@agentmail.to", limit=5)
    return any(canary_id in (m.subject or "") for m in messages.messages)


def main() -> int:
    bus_ok = probe_bus_roundtrip()
    try:
        agentmail_ok = probe_agentmail_roundtrip()
    except Exception as e:
        agentmail_ok = False
        print(f"agentmail leg exception: {e}", file=sys.stderr)

    result = {
        "probe": "c2-fabric-roundtrip",
        "bus_roundtrip_confirmed": bus_ok,
        "agentmail_roundtrip_confirmed": agentmail_ok,
        "ok": bus_ok and agentmail_ok,
        "silence_go_action": "SUSPEND on any leg failure — does not wait for 3-fail REPLACE threshold",
    }
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

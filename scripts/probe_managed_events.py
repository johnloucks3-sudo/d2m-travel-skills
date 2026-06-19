#!/usr/bin/env python3
"""Probe Managed Agents stream events to find token usage fields."""
import os, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(str(Path(__file__).parent.parent / ".env"))

import anthropic

client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    default_headers={"anthropic-beta": "managed-agents-2026-04-01"},
)

env_id = json.loads((Path(__file__).parent.parent / "OpsCenter" / ".managed_env.json").read_text())["env_id"]
agent_id = json.loads((Path(__file__).parent.parent / "OpsCenter" / ".managed_agent_haiku.json").read_text())["agent_id"]

sess = client.beta.sessions.create(agent=agent_id, environment_id=env_id, title="tok-probe")

user_event = [{"type": "user.message", "content": [{"type": "text", "text": "Reply with: PONG"}]}]
client.beta.sessions.events.send(sess.id, events=user_event)

print(f"Session: {sess.id}")
print("Streaming events...")

with client.beta.sessions.events.stream(sess.id) as stream:
    for ev in stream:
        et = getattr(ev, "type", "?")
        print(f"  EVENT: {et}")
        for attr in ["usage", "stats", "thread_stats", "content", "stop_reason"]:
            val = getattr(ev, attr, None)
            if val is not None:
                print(f"    .{attr}: {val}")
        if et == "session.status_idle":
            break

print("Done.")

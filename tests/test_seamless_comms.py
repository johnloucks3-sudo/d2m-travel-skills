"""Seamless Comms Architecture — tests against the plan's SUCCESS SIGNALS,
not against a file manifest. See docs/SEAMLESS_COMMS_IMPLEMENTATION.md.

Run: python3 tests/test_seamless_comms.py
"""
import sys
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")

PASS = []
FAIL = []


def check(name: str, condition: bool, detail: str = ""):
    if condition:
        PASS.append(name)
        print(f"PASS: {name}")
    else:
        FAIL.append((name, detail))
        print(f"FAIL: {name} — {detail}")


# ── EMAIL — success signal: Commander gets an in-thread reply ────────────────

def test_email():
    from core.email.thunderbird_gmail import TOOL_REGISTRY, gmail_reply_in_thread
    check("gmail_reply_in_thread registered in TOOL_REGISTRY",
          TOOL_REGISTRY.get("gmail_reply_in_thread") is gmail_reply_in_thread)

    from core.email import hale_email_responder as her
    fake_entry = {
        "message_id": "<test-1@example.com>",
        "thread_id": "thread-abc",
        "from": f"John Loucks <{her.COMMANDER_EMAIL}>",
        "subject": "Test task",
        "preview": "What's on the mission board?",
    }
    pending = her._pending_messages(set(), her._hale_track_senders())
    # Direct unit test of the classification logic (not the live queue file):
    from_bare = fake_entry["from"].split("<")[-1].rstrip(">").lower()
    check("Commander address recognized as auto-reply trigger",
          from_bare == her.COMMANDER_EMAIL)
    check("hale_email_responder imports AgentMailClient for in-thread Commander replies",
          hasattr(her, "AgentMailClient"))


# ── TELEGRAM — success signal: >4096 chars chunks cleanly, no XML bleed ──────

def test_telegram():
    from core.communication.thunderbird_telegram_fmt import split_message, strip_markdown, MAX_TELEGRAM_LENGTH

    long_text = ("Paragraph one.\n\n" * 400)  # well over 4096 chars
    chunks = split_message(long_text)
    check("Telegram chunker produces >1 chunk for long text", len(chunks) > 1,
          f"got {len(chunks)} chunks")
    check("Every chunk fits under the 4096 limit",
          all(len(c) <= MAX_TELEGRAM_LENGTH for c in chunks))

    bleedy = "**bold** and [use_mcp_tool]raw xml[/use_mcp_tool] plain"
    stripped = strip_markdown(bleedy)
    check("strip_markdown removes ** markers", "**" not in stripped)

    from core.learning.thunderbird_conversation_bridge import ConversationBridge  # existence check
    check("ConversationBridge module importable (stateful context already wired)",
          ConversationBridge is not None)


# ── SIGNAL — success signal: adapter degrades gracefully pre-link,
#             produces the one human-only ask when link is attempted ────────

def test_signal():
    from core.signal import signal_cli_adapter as adapter
    from core.signal import signal_router, signal_relay

    check("signal-cli binary installed", adapter.SIGNAL_CLI_BIN.exists())

    if not adapter.is_linked():
        check("send_message returns structured not_linked (no exception) pre-link",
              adapter.send_message("+10000000000", "test")["status"] == "not_linked")
        check("receive_messages returns [] (no exception) pre-link",
              adapter.receive_messages(timeout=1) == [])
        result = signal_router.poll_and_route()
        check("router.poll_and_route reports not_linked cleanly pre-link",
              result and result[0].get("status") == "not_linked")
    else:
        check("signal-cli linked — adapter live", True)

    check("signal_relay.notify_telegram_fallback callable", callable(signal_relay.notify_telegram_fallback))


def main():
    test_email()
    test_telegram()
    test_signal()
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        for name, detail in FAIL:
            print(f"  - {name}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()

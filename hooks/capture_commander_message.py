#!/usr/bin/env python3
"""UserPromptSubmit hook — capture Commander's message to the directive ledger."""

import json
import sys

sys.path.insert(0, "/home/john/Thunderbird")

# The harness injects its own content through UserPromptSubmit — background-task
# events, system reminders, local slash-command output. Captured verbatim on
# 2026-07-30, a <task-notification> block landed in the ledger stamped
# source="commander". A mandate ledger that cannot tell the Commander's words
# from the harness's is worse than an empty one: plan-mode surfaces the noise as
# though he had said it. Anything matching these is machine chatter, not a directive.
_NOT_COMMANDER_PREFIXES = (
    "<task-notification>",
    "[SYSTEM NOTIFICATION",
    "<local-command-",
    "<system-reminder>",
    "<teammate-message",
)


def _is_commander_text(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return not t.startswith(_NOT_COMMANDER_PREFIXES)


def main():
    try:
        data = json.load(sys.stdin)
        prompt_text = data.get("prompt", "")
    except Exception:
        prompt_text = ""

    if not _is_commander_text(prompt_text):
        sys.exit(0)

    try:
        from core.staffing.directive_ledger import capture
        capture(prompt_text, source="commander")
    except Exception:
        # never block a session on a hook error
        pass

    sys.exit(0)

if __name__ == "__main__":
    main()

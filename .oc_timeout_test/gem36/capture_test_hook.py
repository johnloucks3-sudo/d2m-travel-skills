#!/usr/bin/env python3
"""UserPromptSubmit test hook script."""

import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/john/Thunderbird")


def main():
    try:
        import core.staffing.directive_ledger as directive_ledger
        # Monkeypatch LEDGER path to ensure writes stay inside .oc_timeout_test/gem36/
        directive_ledger.LEDGER = Path(__file__).parent / "test_mandatory_directives.jsonl"
    except Exception:
        directive_ledger = None

    try:
        data = json.load(sys.stdin)
        prompt_text = data.get("prompt") if isinstance(data, dict) else None
    except Exception:
        prompt_text = None

    if prompt_text and directive_ledger is not None:
        try:
            directive_ledger.capture(prompt_text, source="commander")
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)

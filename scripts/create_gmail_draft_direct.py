#!/usr/bin/env python3
"""CLI wrapper: create a Gmail draft for Commander review.
Usage:
    python3 scripts/create_gmail_draft_direct.py \\
        --to email@example.com \\
        --subject "Subject" \\
        --body "Plain text body"
    python3 scripts/create_gmail_draft_direct.py \\
        --html /path/to/draft.html \\
        --to email@example.com \\
        --subject "Subject"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.email.thunderbird_gmail import gmail_create_draft_sync


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("--html", default="")
    args = parser.parse_args()

    if args.html:
        body = Path(args.html).read_text(encoding="utf-8")
    else:
        body = args.body

    result = gmail_create_draft_sync(
        to=args.to,
        subject=args.subject,
        body=body,
        label_review=True,
    )
    print(f"Draft created: {result.get('draft_id', 'unknown')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

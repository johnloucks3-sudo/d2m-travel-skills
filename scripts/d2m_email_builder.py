#!/usr/bin/env python3
"""
D2M Email Builder — Universal canonical dark navy email generator.
Wraps any body HTML in the D2M canonical template and stages to johnloucks3 drafts.

Template: storage/templates/d2m_canonical_darknavy.html
Usage:
  python3 scripts/d2m_email_builder.py \\
    --body drafts/body_amy_darrow.html \\
    --to amy.darrow@me.com \\
    --subject "Travel Insurance — June 26 Deadline" \\
    [--name "Amy"]           # prepends "Hi Amy," greeting if body doesn't have one

MANDATORY for all D2M client emails. Never build email HTML from scratch.
Source template: Kuklinski Panama December email sent 2026-06-20 (Commander directive canonical).
"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent
TEMPLATE_PATH = THUNDERBIRD / "storage" / "templates" / "d2m_canonical_darknavy.html"
BODY_PLACEHOLDER = "{{BODY_CONTENT}}"


def build_email_html(body_html: str) -> str:
    """Wrap body_html in the canonical D2M dark navy template."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if BODY_PLACEHOLDER not in template:
        raise ValueError(f"Template missing placeholder: {BODY_PLACEHOLDER}")
    return template.replace(BODY_PLACEHOLDER, body_html)


def stage_draft(
    full_html: str,
    to_email: str,
    subject: str,
    output_path: Path,
):
    """Stage to johnloucks3 drafts via create_johnloucks3_draft.py."""
    output_path.write_text(full_html, encoding="utf-8")
    print(f"Built email HTML: {len(full_html)} chars → {output_path}")

    # Call the existing draft creator
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            str(THUNDERBIRD / "scripts" / "create_johnloucks3_draft.py"),
            "--html", str(output_path),
            "--to", to_email,
            "--subject", subject,
        ],
        capture_output=False,
        cwd=str(THUNDERBIRD),
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Build canonical D2M dark navy email and stage to johnloucks3 drafts"
    )
    parser.add_argument("--body", required=True, help="Path to body HTML (just content, no template)")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--name", help="Client first name — prepends Hi [Name], greeting if body lacks one")
    parser.add_argument("--output", help="Output HTML file path (default: drafts/built_[timestamp].html)")
    args = parser.parse_args()

    body_path = Path(args.body)
    if not body_path.exists():
        print(f"ERROR: Body file not found: {args.body}")
        sys.exit(1)

    body_html = body_path.read_text(encoding="utf-8")

    # Optionally prepend greeting
    if args.name and "<p" not in body_html[:200].lower():
        body_html = f'<p style="margin:0 0 20px 0">Hi {args.name},</p>\n\n' + body_html

    # Wrap in canonical template
    full_html = build_email_html(body_html)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        import time
        ts = int(time.time())
        output_path = THUNDERBIRD / "drafts" / f"built_{ts}.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Stage draft
    success = stage_draft(full_html, args.to, args.subject, output_path)

    if success:
        print(f"\n✅ D2M canonical email built and staged to johnloucks3 drafts.")
        print(f"   Template: storage/templates/d2m_canonical_darknavy.html")
        print(f"   Built file: {output_path}")
    else:
        print("❌ Draft staging failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

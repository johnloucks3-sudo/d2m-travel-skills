#!/usr/bin/env python3
"""Capture the diff between drafted and sent validation emails.

Run after Commander has edited and sent the Gmail drafts.
Compares sent versions against baseline HTML, extracts principles,
and saves as a learning rule.

Usage:
    python3 scripts/capture_validation_diff.py
"""
import sys
import json
import difflib
import re
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime, timezone

ROOT = Path.home() / "Thunderbird"
sys.path.insert(0, str(ROOT))

MANIFEST = ROOT / "output" / "validation_emails" / "draft_manifest_20260325.json"
BASELINE_DIR = ROOT / "output" / "validation_emails" / "baseline_20260325"


class TextExtractor(HTMLParser):
    """Strip HTML tags, return readable text."""
    def __init__(self):
        super().__init__()
        self._chunks = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False
        if tag in ("p", "li", "td", "div", "br", "h1", "h2", "h3"):
            self._chunks.append("\n")

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if text:
                self._chunks.append(text)

    def get_text(self):
        return " ".join(c for c in self._chunks if c.strip())


def html_to_text(html: str) -> str:
    p = TextExtractor()
    p.feed(html)
    return p.get_text()


def _get_service():
    from thunderbird_gmail import _get_gmail_service
    return _get_gmail_service()


def fetch_sent_today(service, subject_fragment: str) -> str | None:
    """Search Gmail sent for a message matching subject_fragment sent today."""
    today = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    results = service.users().messages().list(
        userId="me",
        q=f'in:sent subject:"{subject_fragment}" after:{today.replace("/", "/")}'
    ).execute()
    messages = results.get("messages", [])
    if not messages:
        return None
    msg = service.users().messages().get(
        userId="me", id=messages[0]["id"], format="full"
    ).execute()
    # Find HTML part
    def find_html(parts):
        for part in parts:
            if part.get("mimeType") == "text/html":
                import base64
                data = part["body"].get("data", "")
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            if "parts" in part:
                result = find_html(part["parts"])
                if result:
                    return result
        return None
    payload = msg.get("payload", {})
    html = find_html(payload.get("parts", [payload]))
    return html


def diff_texts(before: str, after: str) -> list[str]:
    """Return unified diff lines."""
    b_lines = before.splitlines()
    a_lines = after.splitlines()
    return list(difflib.unified_diff(b_lines, a_lines, lineterm="",
                                     fromfile="drafted", tofile="sent"))


def extract_changes(diff_lines: list[str]) -> dict:
    """Pull out added/removed lines from diff."""
    added = [l[1:].strip() for l in diff_lines if l.startswith("+") and not l.startswith("+++")]
    removed = [l[1:].strip() for l in diff_lines if l.startswith("-") and not l.startswith("---")]
    return {"added": [l for l in added if l], "removed": [l for l in removed if l]}


def main():
    manifest = json.loads(MANIFEST.read_text())
    service = _get_service()
    report = []

    for entry in manifest["drafts"]:
        client = entry["client"]
        baseline_path = ROOT / "output" / "validation_emails" / entry["baseline_file"]
        if not baseline_path.exists():
            print(f"⚠ Baseline not found for {client}: {baseline_path}")
            continue

        print(f"\n── {client} ──────────────────────────")
        baseline_html = baseline_path.read_text(encoding="utf-8")
        baseline_text = html_to_text(baseline_html)

        # Try to fetch sent version from Gmail
        subject_hint = entry["client"]
        sent_html = fetch_sent_today(service, subject_hint)
        if not sent_html:
            print(f"  No sent message found yet for {client}")
            report.append({"client": client, "status": "not_sent_yet"})
            continue

        sent_text = html_to_text(sent_html)
        diff = diff_texts(baseline_text, sent_text)
        changes = extract_changes(diff)

        if not changes["added"] and not changes["removed"]:
            print(f"  ✓ Sent unchanged")
            report.append({"client": client, "status": "unchanged"})
        else:
            print(f"  REMOVED ({len(changes['removed'])} lines):")
            for r in changes["removed"][:10]:
                print(f"    - {r[:120]}")
            print(f"  ADDED ({len(changes['added'])} lines):")
            for a in changes["added"][:10]:
                print(f"    + {a[:120]}")
            report.append({
                "client": client,
                "status": "edited",
                "removed": changes["removed"],
                "added": changes["added"],
            })

    # Save report
    report_path = ROOT / "output" / "validation_emails" / f"diff_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n✓ Report saved: {report_path}")

    # Summarize for rule extraction
    edited = [r for r in report if r.get("status") == "edited"]
    if edited:
        print(f"\n{'='*60}")
        print(f"RULE EXTRACTION SUMMARY — {len(edited)} email(s) edited")
        print(f"{'='*60}")
        for r in edited:
            print(f"\n{r['client']}:")
            if r["removed"]:
                print(f"  Commander removed: {r['removed'][0][:200]}")
            if r["added"]:
                print(f"  Commander added:   {r['added'][0][:200]}")
        print(f"\n→ Run learning_capture_diff MCP with this report to inject rules.")
    else:
        print("\nNo edits detected — nothing to learn yet.")

    return report


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Travel Survey Generator — post-voyage survey email staging.
Scans dossiers for clients whose voyage returned within a configurable window,
stages a survey email draft to johnloucks3, and writes state.

WF-17: all drafts stage to johnloucks3@gmail.com — never to client addresses.
"""

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

THUNDERBIRD = Path(__file__).parent.parent
STATE_FILE = THUNDERBIRD / "OpsCenter" / "state" / "travel_survey_state.json"
DRAFTS_DIR = THUNDERBIRD / "drafts"
JOHNLOUCKS3 = "johnloucks3@gmail.com"
FORM_URL = "https://docs.google.com/forms/d/1Ni_MKR8gqfpVVlaNt3RUBfDFd4hcy4U5SSTse4RUpo8/viewform"

sys.path.insert(0, str(THUNDERBIRD))
from core.booking.thunderbird_tp_scheduler import scan_dossiers
from scripts.d2m_email_builder import build_email_html, stage_draft


def _state_key(rec) -> str:
    return f"{rec.path}|{rec.return_date}"


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"entries": {}}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _build_body(client_name: str) -> str:
    first = client_name.split()[0] if client_name else client_name
    return f"""<p style="color:#e8f1ff;font-family:Georgia,serif;font-size:16px;">Dear {first},</p>
<p style="color:#e8f1ff;font-family:Georgia,serif;font-size:15px;">Your voyage has returned and we'd love to hear how it went. Your feedback helps us craft an even better experience for your next adventure.</p>
<p style="color:#e8f1ff;font-family:Georgia,serif;font-size:15px;">Please take a few minutes to share your thoughts:</p>
<div style="text-align:center;margin:24px 0;">
  <a href="{FORM_URL}"
     style="background:#4a90d9;color:#ffffff;padding:14px 28px;border-radius:6px;font-family:Georgia,serif;font-size:16px;text-decoration:none;display:inline-block;">
    Share Your Feedback &rarr;
  </a>
</div>
<p style="color:#a8c4f0;font-family:Georgia,serif;font-size:13px;font-style:italic;">If the button above doesn't work, copy this link: {FORM_URL}</p>
<p style="color:#e8f1ff;font-family:Georgia,serif;font-size:15px;">Thank you for trusting Dreams2Memories Travel with your voyage.</p>"""


def run(window: int = 30, dry_run: bool = False, force: bool = False) -> None:
    today = date.today()
    state = _load_state()
    entries = state.get("entries", {})

    records = scan_dossiers()
    eligible = [
        r for r in records
        if r.return_date is not None
        and 1 <= (today - r.return_date).days <= window
    ]

    evaluated = len(eligible)
    staged = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for rec in eligible:
        key = _state_key(rec)
        if key in entries and not force:
            print(f"SKIP (already staged): {rec.client}")
            continue

        body_html = _build_body(rec.client)
        subject = f"How Was Your Voyage? — {rec.client} Post-Trip Survey"
        output_path = DRAFTS_DIR / f"survey_{rec.path.stem}.html"

        if dry_run:
            print(f"DRY-RUN: would stage survey for {rec.client} (returned {rec.return_date})")
            continue

        try:
            full_html = build_email_html(body_html)
        except Exception as exc:
            print(f"ERROR building email for {rec.client}: {exc}")
            continue

        success = stage_draft(full_html, JOHNLOUCKS3, subject, output_path)
        if success:
            entries[key] = {
                "client": rec.client,
                "return_date": str(rec.return_date),
                "staged_at": now_iso,
            }
            staged += 1
            print(f"STAGED: {rec.client} → {JOHNLOUCKS3}")
        else:
            print(f"ERROR: staging failed for {rec.client}")

    state["last_run"] = now_iso
    state["evaluated"] = evaluated
    state["staged"] = staged
    state["entries"] = entries
    if not dry_run:
        _save_state(state)
        print(f"State written → {STATE_FILE} (evaluated={evaluated}, staged={staged})")
    else:
        print(f"DRY-RUN complete: {evaluated} eligible, {staged} would-stage")


def main():
    parser = argparse.ArgumentParser(description="Stage post-voyage survey emails to johnloucks3")
    parser.add_argument("--window", type=int, default=30,
                        help="Days after return_date to include (default 30)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print without staging or writing state")
    parser.add_argument("--force", action="store_true",
                        help="Re-stage clients already in state")
    args = parser.parse_args()
    run(window=args.window, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()

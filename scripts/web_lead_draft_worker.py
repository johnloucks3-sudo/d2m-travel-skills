#!/usr/bin/env python3
"""
web_lead_draft_worker.py — D2M web lead proposal draft generator
Runs as detached subprocess spawned by app/lead_pipeline.py.

Flow:
  1. Read lead JSON from arg
  2. Call Claude Sonnet to draft HTML proposal email
  3. Call create_gmail_draft_direct.py → Gmail Commander-Review draft
  4. Send Telegram completion alert to Commander
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

CLAUDE_BIN = "/home/john/.local/bin/claude"
GMAIL_DRAFT_SCRIPT = "/home/john/Thunderbird/scripts/create_gmail_draft_direct.py"
COMMANDER_ID = 7554895206
ENV_FILE = Path("/home/john/Thunderbird/.env")
OUTPUT_DIR = Path("/home/john/Thunderbird/output")
KNOWN_LINES = ["silversea", "regent", "seabourn", "viking", "oceania", "cunard", "ama", "ponant"]


def _lookup_cruise_pricing(lead: dict) -> str:
    """
    Ask Claude Sonnet for a cruise fare range estimate.
    Returns a short pricing summary or "" if cruise is too vague.
    """
    cruise = (lead.get("cruise_interest") or "").strip()
    if not cruise or not any(line in cruise.lower() for line in KNOWN_LINES):
        return ""

    cabin = lead.get("cabin_preference") or "standard cabin"
    window = lead.get("travel_window") or ""
    party = lead.get("party") or "2 guests"

    prompt = (
        f"You are a luxury cruise pricing specialist. "
        f"Give a realistic per-person fare range in USD for: "
        f"{cruise}"
        + (f", departing {window}" if window else "")
        + f", {cabin} category, {party}. "
        f"Include typical inclusions for this cruise line. "
        f"2-3 sentences, specific numbers, no hedging."
    )

    env = _load_oauth_env()
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--model", "claude-sonnet-4-6", "--output-format", "text"],
            capture_output=True, text=True, env=env, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception as exc:
        print(f"[pricing] Sonnet lookup failed: {exc}")
    return ""


def _load_tg_token() -> str:
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("TELEGRAM_D2MC2C_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("TELEGRAM_D2MC2C_TOKEN", "")


def _tg_send(text: str) -> None:
    token = _load_tg_token()
    if not token:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": COMMANDER_ID, "text": text, "parse_mode": "HTML"},
            timeout=8,
        )
    except Exception:
        pass


def _load_oauth_env() -> dict:
    env = dict(os.environ)
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if creds_path.exists():
        try:
            creds = json.loads(creds_path.read_text(encoding="utf-8"))
            token = creds.get("claudeAiOauth", {}).get("accessToken")
            if token:
                env["CLAUDE_CODE_OAUTH_TOKEN"] = token
                env.pop("ANTHROPIC_API_KEY", None)
        except Exception:
            pass
    return env


def _build_draft_prompt(lead: dict, output_html: Path, pricing_intel: str = "") -> str:
    name = lead.get("name") or "our guest"
    email = lead.get("email") or ""
    cruise = lead.get("cruise_interest") or "luxury cruise"
    party = lead.get("party") or ""
    cabin = lead.get("cabin_preference") or ""
    window = lead.get("travel_window") or ""
    budget = lead.get("budget_signal") or ""
    conversation = lead.get("conversation_context") or "No chat context — came via intake form."
    pricing_block = pricing_intel if pricing_intel else "(none available — use placeholder per requirement 4)"

    return f"""You are drafting a D2M luxury travel proposal email for a web inquiry.

LEAD DATA:
- Name: {name}
- Email: {email}
- Cruise interest: {cruise}
- Party: {party}
- Cabin preference: {cabin}
- Travel window: {window}
- Budget signal: {budget}

CONVERSATION CONTEXT (Dani chat transcript):
{conversation}

PRICING INTEL (live web lookup — verify before quoting client):
{pricing_block}

TASK: Write a personalized D2M proposal email as John A. Loucks III.

REQUIREMENTS:
1. Voice: warm, specific, direct. No "I'm thrilled" or "Great news!" Lead with the answer.
2. Open by referencing exactly what they asked about (ship name, destination, specific dates if mentioned)
3. Body includes: why this cruise line fits what they described, cabin recommendation with one specific reason, 1-2 excursion suggestions for the itinerary
4. Pricing — use the PRICING INTEL block below if provided. Present the range naturally in the email body (e.g., "current fares are running $X,XXX–$X,XXX per person"). If no pricing intel, include this exact placeholder instead: [John: verify current {cabin} pricing for {cruise}]
5. What happens next: John will confirm pricing and availability, ask if they have questions
6. Sign: John A. Loucks III, CEO · Dreams2Memories Travel · 719-291-0742 · concierge@d2mluxury.quest

HTML STATIONERY SPEC:
- Full HTML document (<html> to </html>)
- Max-width 600px, centered, font-family Georgia serif
- Header bar: background #001f5b (navy), 16px padding, white text "Dreams2Memories Travel"
- Body background: #f7f3ea (cream)
- Body padding: 32px
- Links: color #0000ff
- Footer: small gray text, company name + contact

Write ONLY the complete HTML. No markdown, no explanation, no wrapper text.

After the closing </html> tag, on separate lines, write exactly:
GMAIL_TO: {email}
GMAIL_SUBJECT: Your {cruise} Proposal — Dreams2Memories Travel

WRITE your complete output to {output_html}
"""


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: web_lead_draft_worker.py <lead_json_file>")
        return 1

    lead_file = Path(sys.argv[1])
    if not lead_file.exists():
        print(f"Lead file not found: {lead_file}")
        return 1

    lead = json.loads(lead_file.read_text(encoding="utf-8"))
    lead_id = lead.get("lead_id", datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    name = lead.get("name") or "the visitor"
    email = lead.get("email") or ""
    cruise = lead.get("cruise_interest") or "cruise"

    output_html = OUTPUT_DIR / f"web_lead_draft_{lead_id}.html"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Step 0: Live pricing lookup via Perplexity Sonar
    print(f"[{lead_id}] Looking up live pricing for: {cruise}...")
    pricing_intel = _lookup_cruise_pricing(lead)
    if pricing_intel:
        print(f"[{lead_id}] Pricing intel acquired ({len(pricing_intel)} chars)")
    else:
        print(f"[{lead_id}] No pricing intel — using placeholder")

    # Step 1: Generate draft via Claude
    prompt = _build_draft_prompt(lead, output_html, pricing_intel=pricing_intel)
    env = _load_oauth_env()

    print(f"[{lead_id}] Generating draft for {name} ({email})...")
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt, "--model", "claude-sonnet-4-6", "--output-format", "text"],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        _tg_send(f"⚠️ Draft worker timed out for lead {lead_id} ({name})")
        return 1
    except FileNotFoundError:
        _tg_send(f"⚠️ Draft worker: claude binary not found")
        return 1

    if result.returncode != 0 or not result.stdout.strip():
        _tg_send(f"⚠️ Draft generation failed for {name}. Check logs/web_lead_{lead_id}.log")
        return 1

    raw = result.stdout.strip()

    # Parse HTML and metadata from output
    gmail_to = email
    gmail_subject = f"Your {cruise} Proposal — Dreams2Memories Travel"

    lines = raw.splitlines()
    for line in lines:
        if line.startswith("GMAIL_TO:"):
            gmail_to = line.split(":", 1)[1].strip()
        elif line.startswith("GMAIL_SUBJECT:"):
            gmail_subject = line.split(":", 1)[1].strip()

    # Strip metadata lines, keep HTML
    html_lines = [l for l in lines if not l.startswith(("GMAIL_TO:", "GMAIL_SUBJECT:"))]
    html_body = "\n".join(html_lines).strip()

    if not html_body:
        _tg_send(f"⚠️ Draft worker got empty HTML for lead {lead_id}")
        return 1

    output_html.write_text(html_body, encoding="utf-8")
    print(f"[{lead_id}] Draft HTML written to {output_html}")

    # Step 2: Create Gmail draft
    draft_created = False
    try:
        dr = subprocess.run(
            [
                "python3", GMAIL_DRAFT_SCRIPT,
                "--html", str(output_html),
                "--to", gmail_to,
                "--subject", gmail_subject,
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/home/john/Thunderbird",
        )
        draft_created = dr.returncode == 0
        if not draft_created:
            print(f"[{lead_id}] Gmail draft script failed:\n{dr.stdout}\n{dr.stderr}")
    except Exception as exc:
        print(f"[{lead_id}] Gmail draft exception: {exc}")

    # Step 3: Telegram completion alert
    if draft_created:
        _tg_send(
            f"✅ <b>Proposal draft ready — Commander-Review</b>\n\n"
            f"<b>For:</b> {name}\n"
            f"<b>To:</b> {gmail_to}\n"
            f"<b>Subject:</b> {gmail_subject}\n\n"
            f"Add pricing + personal note, then send."
        )
        print(f"[{lead_id}] Draft created. Commander notified.")
    else:
        _tg_send(
            f"⚠️ <b>Draft generated, Gmail step failed</b>\n\n"
            f"<b>For:</b> {name} ({gmail_to})\n"
            f"HTML saved at: output/web_lead_draft_{lead_id}.html\n\n"
            f"Manual draft: run scripts/create_gmail_draft_direct.py"
        )
        print(f"[{lead_id}] HTML saved but Gmail draft failed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())

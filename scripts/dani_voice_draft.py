#!/usr/bin/env python3
"""
Dani Voice Draft — Flesh Out Lifecycle Email Stubs with Real Voice
===================================================================
Dreams2Memories Travel, LLC | scripts/dani_voice_draft.py

Reads lifecycle_draft_queue.jsonl for "queued" entries, spawns headless
Claude Sonnet with Dani persona to write real voiced email content, then
updates the existing Gmail draft with the finished copy.

Status flow: queued → voice_drafted (or voice_error)

Usage:
    python3 scripts/dani_voice_draft.py             # Process all queued drafts
    python3 scripts/dani_voice_draft.py --dry-run   # Show what would be drafted
    python3 scripts/dani_voice_draft.py --client Kuklinski
    python3 scripts/dani_voice_draft.py --status    # Show queue state
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import re
import sys
import tempfile
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import yaml

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))
sys.path.insert(0, str(THUNDERBIRD / "core" / "ai_infra"))

QUEUE_LOG = THUNDERBIRD / "storage" / "lifecycle_draft_queue.jsonl"
GMAIL_TOKEN = THUNDERBIRD / "gmail_token.json"
DANI_PERSONA = THUNDERBIRD / "Personas" / "a3_dani_personality.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s DANI-VOICE %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            str(THUNDERBIRD / "logs" / "dani_voice_draft.log"), mode="a"
        ),
    ],
)
logger = logging.getLogger("dani_voice")

# TP context descriptions — what each touchpoint covers so Dani knows what to write
TP_CONTEXT = {
    "0.5": (
        "Welcome and booking validation. Celebrate the booking. Confirm the suite/cabin, "
        "cruise line, ship, and departure date. State the final payment due date and amount. "
        "Tell them what happens next. Warm, celebratory, operationally crisp."
    ),
    "3.1": (
        "Pre-voyage brief — sent 3-4 weeks before departure. This is the comprehensive "
        "trip packet. Coincides with online check-in opening. Cover: check-in instructions, "
        "packing guidance, what to expect embarkation day, key onboard highlights, "
        "recommended ports of call moments. Make them excited."
    ),
    "3.2": (
        "Final confirmation — sent 1-2 weeks before departure. All logistics are locked. "
        "Confirm: flights, hotel if applicable, embarkation details (terminal, time, "
        "documents to bring). Tell them what printed confirmations to carry. "
        "Calm, reassuring, thorough."
    ),
    "3.3": (
        "Send-off / bon voyage — sent 3-5 days before departure. Warm, personal send-off. "
        "Check current weather at embarkation port. One or two 'don't miss' moments. "
        "Tell them you'll be thinking of them. Short and warm."
    ),
    "4.1": (
        "Payment reminder #1 — sent 3 weeks before final payment due. State the balance "
        "amount clearly, the due date, and how to pay (portal link or agent contact). "
        "Friendly reminder tone, not alarm."
    ),
    "4.2": (
        "Payment reminder #2 — sent 2 weeks before final payment due. More urgent but "
        "still warm. Restate balance, due date, and payment method. Note that the "
        "booking may be at risk if payment is not received."
    ),
    "4.3": (
        "Final payment reminder — sent 1 week before due. Clear urgency. State the "
        "exact amount due, exact date, and exact payment method. Brief and direct."
    ),
    "5.1": (
        "Welcome home — sent 2 days after return. Ask how the voyage was. "
        "Invite them to share a photo or story. Plant the seed for the next adventure. "
        "Warm, brief, personal."
    ),
    "5.2": (
        "Post-voyage review request — sent 1 week after return. Ask for a review "
        "on Google or TripAdvisor. Make it easy — include the link. Express gratitude "
        "for their trust and business."
    ),
    "5.3": (
        "Referral ask — sent 2-3 weeks after return. Gentle ask: do they know anyone "
        "who would love a luxury cruise? Reference a specific moment from their voyage "
        "if known. Keep it light and genuine."
    ),
}

D2M_STATIONERY_HEADER = """<div style="background:#1a3557;color:#fff;padding:12px 20px;margin-bottom:20px;">
  <strong style="font-size:16px;">Dreams2Memories Travel, LLC</strong><br>
  <small>Luxury Travel Concierge · John Loucks, Founder</small>
</div>"""

DANI_SIGNATURE = """<p style="margin-top:24px;">Warmly,</p>
<p><strong>Dani Moreau</strong><br>
<em>Your Travel Concierge</em><br>
Dreams2Memories Travel, LLC<br>
<a href="mailto:concierge@d2mluxury.quest" style="color:#0000ff;">concierge@d2mluxury.quest</a></p>"""


# ---------------------------------------------------------------------------
# Queue helpers
# ---------------------------------------------------------------------------

def load_queued_entries(client_filter: Optional[str] = None) -> list[dict]:
    if not QUEUE_LOG.exists():
        return []
    entries = []
    for line in QUEUE_LOG.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            if e.get("status") != "queued":
                continue
            if client_filter and client_filter.lower() not in e.get("client", "").lower():
                continue
            if e.get("draft_id"):
                entries.append(e)
        except Exception:
            pass
    return entries


def _update_queue_status(client: str, tp_id: str, new_status: str, extra: dict | None = None) -> None:
    """Rewrite queue log updating matching entry status."""
    if not QUEUE_LOG.exists():
        return
    lines = QUEUE_LOG.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        try:
            e = json.loads(line)
            if e.get("client") == client and e.get("tp_id") == tp_id and e.get("status") == "queued":
                e["status"] = new_status
                e["voiced_at"] = datetime.now().isoformat()
                if extra:
                    e.update(extra)
                line = json.dumps(e)
        except Exception:
            pass
        out.append(line)
    QUEUE_LOG.write_text("\n".join(out) + "\n", encoding="utf-8")


def _route_to_naia_brand_pass(client: str, tp_id: str, draft_id: str, subject: str) -> None:
    """Auto-route voice_drafted client draft to Naia for brand-pass gate (SO 2026-05-13).

    Creates entry in naia_brand_pass_queue.jsonl for Naia persona to process.
    Marks original entry as brand_pass_queued.
    """
    NAIA_QUEUE = THUNDERBIRD / "storage" / "naia_brand_pass_queue.jsonl"

    queue_entry = {
        "ts": datetime.now().isoformat(),
        "client": client,
        "tp_id": tp_id,
        "draft_id": draft_id,
        "subject": subject,
        "routed_by": "dani_voice_draft",
        "next_gate": "wf17_after_naia_approval",
    }

    # Append to Naia's queue
    NAIA_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with open(NAIA_QUEUE, "a", encoding="utf-8") as f:
        f.write(json.dumps(queue_entry, ensure_ascii=False) + "\n")

    # Mark original entry as brand_pass_queued
    _update_queue_status(client, tp_id, "brand_pass_queued", {"routed_to_naia_ts": datetime.now().isoformat()})

    logger.info(f"NAIA ROUTE: {client} TP {tp_id} — brand-pass gate triggered. SLA: <4h")


# ---------------------------------------------------------------------------
# Gmail draft update
# ---------------------------------------------------------------------------

def _get_gmail_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    data = json.loads(GMAIL_TOKEN.read_text(encoding="utf-8"))
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", ["https://www.googleapis.com/auth/gmail.modify"]),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def update_gmail_draft(draft_id: str, to: str, subject: str, body_html: str, service=None) -> bool:
    """Replace draft body with voiced content. Preserves to/subject/label."""
    if service is None:
        service = _get_gmail_service()

    msg = MIMEMultipart("alternative")
    msg["to"] = to
    msg["from"] = "d2mconcierge@gmail.com"
    msg["subject"] = subject
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    try:
        service.users().drafts().update(
            userId="me",
            id=draft_id,
            body={"message": {"raw": raw}},
        ).execute()
        return True
    except Exception as exc:
        logger.error(f"Draft update failed for {draft_id}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Voice generation — headless Claude Sonnet with Dani persona
# ---------------------------------------------------------------------------

def _load_dani_persona_excerpt() -> str:
    """Load key Dani personality sections for the prompt."""
    if not DANI_PERSONA.exists():
        return "Dani is warm, personal, operationally precise. She writes to one person."
    text = DANI_PERSONA.read_text(encoding="utf-8")
    # Extract: IDENTITY SNAPSHOT, TEMPERAMENT, VOICE SIGNATURE
    sections = []
    for header in ["## IDENTITY SNAPSHOT", "## TEMPERAMENT", "## VOICE SIGNATURE"]:
        idx = text.find(header)
        if idx == -1:
            continue
        next_header = text.find("\n## ", idx + len(header))
        section = text[idx: next_header if next_header != -1 else idx + 800]
        sections.append(section.strip())
    return "\n\n".join(sections[:3]) if sections else text[:1200]


def build_dani_prompt(entry: dict, dossier_fm: dict) -> str:
    """Construct the Dani voice generation prompt."""
    full_name = entry.get("full_name") or entry.get("client", "")
    first_name = full_name.split()[0] if full_name else entry.get("client", "")
    tp_id = entry["tp_id"]
    phase_label = entry.get("phase_label", "")
    subject = entry.get("subject", "")
    deadline = entry.get("deadline", "")
    client_email = entry.get("client_email", "")

    cruise_line = dossier_fm.get("cruise_line", "")
    ship = dossier_fm.get("ship", "")
    departure_raw = dossier_fm.get("departure", "")
    fpd_raw = dossier_fm.get("fpd", "")
    booking_num = dossier_fm.get("booking", "")

    def fmt_date(d) -> str:
        if not d:
            return ""
        try:
            if isinstance(d, str):
                d = date.fromisoformat(d)
            return d.strftime("%B %-d, %Y")
        except Exception:
            return str(d)

    departure_str = fmt_date(departure_raw)
    fpd_str = fmt_date(fpd_raw)

    tp_guidance = TP_CONTEXT.get(tp_id, f"Lifecycle touchpoint {tp_id}: {phase_label}")
    persona = _load_dani_persona_excerpt()

    return f"""You are Major Danielle "Dani" Moreau — the sole client-facing voice of Dreams2Memories Travel, LLC.

{persona}

---

YOUR TASK: Write a complete, client-ready HTML email for the following lifecycle touchpoint.

CLIENT DETAILS:
- Full name: {full_name}
- First name: {first_name}
- Cruise line: {cruise_line}
- Ship: {ship}
- Departure: {departure_str}
{"- Final payment due: " + fpd_str if fpd_str else ""}
{"- Email address: " + client_email if client_email and "@tbd" not in client_email else ""}

TOUCHPOINT: TP {tp_id} — {phase_label}
EMAIL SUBJECT: {subject}
TOUCHPOINT GUIDANCE: {tp_guidance}

WRITING RULES:
1. Write directly to {first_name} — warm, personal, as if writing to a trusted friend
2. Use contractions naturally (you're, we're, it's, don't)
3. Never sound like a brochure or form letter
4. Include all relevant client-specific details from the context above
5. Close with Dani's warm signature (already included in the wrapper — just write the body)
6. 150-250 words for the body paragraphs (not counting greeting/close)
7. Do NOT include <html>, <head>, <body> tags — just the inner content divs/paragraphs

OUTPUT FORMAT: Write ONLY the inner HTML email body — the paragraphs between the greeting and signature. Start with a <p> tag for the greeting line. Do not include any explanation, commentary, or metadata — just the HTML.

The output will be wrapped in D2M stationery automatically. Write only what goes between the banner header and the signature block.

WRITE the complete HTML email body content to: {{OUTPUT_PATH}}"""


def _extract_html_from_output(raw: str) -> str:
    """Extract HTML content from headless Claude output."""
    raw = raw.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```html\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^```\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    # Remove any leading prose before first <p> tag
    p_idx = raw.find("<p")
    if p_idx > 0:
        raw = raw[p_idx:]
    return raw.strip()


def generate_voiced_content(entry: dict, dossier_fm: dict, timeout: int = 120) -> Optional[str]:
    """Run headless Claude Sonnet and return voiced HTML body."""
    try:
        from thunderbird_headless_spawn import spawn_headless_claude
    except ImportError as exc:
        logger.error(f"Cannot import thunderbird_headless_spawn: {exc}")
        return None

    with tempfile.NamedTemporaryFile(
        suffix=".html", prefix=f"dani_draft_{entry['client']}_tp{entry['tp_id']}_",
        dir=str(THUNDERBIRD / "logs"), mode="w", delete=False
    ) as tf:
        output_path = tf.name

    prompt = build_dani_prompt(entry, dossier_fm)
    prompt = prompt.replace("{OUTPUT_PATH}", output_path)

    logger.info(f"Spawning Sonnet for {entry['client']} TP {entry['tp_id']}")
    result = spawn_headless_claude(
        prompt=prompt,
        output_file=output_path,
        model="claude-sonnet-4-6",
        task_name=f"dani_voice_{entry['client']}_tp{entry['tp_id']}".replace(" ", "_"),
        background=False,
        timeout=timeout,
    )

    if result.get("status") in ("FATAL_PREREQ", "error"):
        logger.error(f"Spawn failed: {result}")
        return None

    # Read output file
    try:
        raw = Path(output_path).read_text(encoding="utf-8")
        return _extract_html_from_output(raw)
    except Exception as exc:
        logger.error(f"Output read failed: {exc}")
        return None


def _wrap_voiced_body(voiced_inner: str, full_name: str, first_name: str, tp_id: str, phase_label: str) -> str:
    """Wrap voiced inner content with D2M stationery."""
    return f"""<div style="font-family: Georgia, serif; color: #1a3557; background: #f7f3ea; padding: 24px; max-width: 640px;">

{D2M_STATIONERY_HEADER}

{voiced_inner}

{DANI_SIGNATURE}

<p style="font-size: 10px; color: #aaa; margin-top: 24px; border-top: 1px solid #ddd; padding-top: 8px;">
  Dreams2Memories Travel, LLC · Luxury Cruise Concierge<br>
  <em>Voiced by Dani · TP {tp_id} · {phase_label}</em>
</p>
</div>"""


def _load_dossier_fm(client: str) -> dict:
    """Read dossier frontmatter for the given client slug."""
    for path in sorted(THUNDERBIRD.glob("dossiers/*.md")):
        if client.lower() in path.stem.lower():
            try:
                text = path.read_text(encoding="utf-8")
                m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
                if m:
                    return yaml.safe_load(m.group(1)) or {}
            except Exception:
                pass
    return {}


# ---------------------------------------------------------------------------
# Main processing loop
# ---------------------------------------------------------------------------

def process_drafts(
    dry_run: bool = False,
    client_filter: Optional[str] = None,
    timer_mode: bool = False,
) -> list[dict]:
    entries = load_queued_entries(client_filter)

    if not entries:
        if not timer_mode:
            print("No queued drafts to voice.")
        return []

    if not timer_mode:
        print(f"\nDani Voice Draft — {date.today().isoformat()}")
        if dry_run:
            print("MODE: DRY-RUN\n")
        print(f"Found {len(entries)} queued draft(s)\n")

    service = None
    if not dry_run:
        try:
            service = _get_gmail_service()
        except Exception as exc:
            logger.error(f"Gmail auth failed: {exc}")
            if not timer_mode:
                print(f"ERROR: Gmail auth failed — {exc}")
            return []

    results = []

    for entry in entries:
        client = entry["client"]
        tp_id = entry["tp_id"]
        draft_id = entry["draft_id"]
        phase_label = entry.get("phase_label", "")
        subject = entry.get("subject", "")
        client_email = entry.get("client_email", "")
        full_name = entry.get("full_name") or client
        first_name = full_name.split()[0] if full_name else client

        if dry_run:
            print(
                f"  [DRY-RUN] {client} TP {tp_id} — {phase_label}\n"
                f"    Draft ID: {draft_id}\n"
                f"    Would spawn Sonnet to voice this draft"
            )
            results.append({"client": client, "tp_id": tp_id, "status": "dry_run"})
            continue

        # Load dossier for extra context
        dossier_fm = _load_dossier_fm(client)

        # Generate voiced content
        voiced_inner = generate_voiced_content(entry, dossier_fm)
        if not voiced_inner:
            logger.error(f"Voice generation failed: {client} TP {tp_id}")
            _update_queue_status(client, tp_id, "voice_error", {"error": "generation_failed"})
            results.append({"client": client, "tp_id": tp_id, "status": "voice_error"})
            if not timer_mode:
                print(f"  ❌ {client} TP {tp_id} — voice generation failed")
            continue

        # Wrap with stationery
        full_html = _wrap_voiced_body(voiced_inner, full_name, first_name, tp_id, phase_label)

        # Update Gmail draft
        ok = update_gmail_draft(draft_id, client_email, subject, full_html, service)
        if ok:
            _update_queue_status(client, tp_id, "voice_drafted")
            # Auto-route client-facing draft to Naia brand-pass gate (SO 2026-05-13)
            _route_to_naia_brand_pass(client, tp_id, draft_id, subject)
            results.append({"client": client, "tp_id": tp_id, "status": "brand_pass_queued"})
            logger.info(f"Voiced draft updated: {client} TP {tp_id} draft_id={draft_id} → routed to Naia")
            if not timer_mode:
                print(f"  ✅ {client} TP {tp_id} — voiced, updated in Gmail, routed to Naia for brand pass")
        else:
            _update_queue_status(client, tp_id, "voice_error", {"error": "gmail_update_failed"})
            results.append({"client": client, "tp_id": tp_id, "status": "voice_error"})
            if not timer_mode:
                print(f"  ❌ {client} TP {tp_id} — Gmail draft update failed")

    return results


def print_status() -> None:
    if not QUEUE_LOG.exists():
        print("Queue log empty.")
        return
    lines = [l for l in QUEUE_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    counts: dict[str, int] = {}
    print(f"\nLIFECYCLE DRAFT QUEUE — {len(lines)} entries\n")
    print(f"{'CLIENT':<20} {'TP':>5}  {'STATUS':<16}  PHASE LABEL")
    print("-" * 75)
    for line in lines:
        try:
            e = json.loads(line)
            status = e.get("status", "?")
            counts[status] = counts.get(status, 0) + 1
            icon = {"queued": "🟡", "voice_drafted": "✅", "voice_error": "❌", "completed": "✔️"}.get(status, "·")
            print(f"  {icon} {e.get('client','?'):<18} {e.get('tp_id','?'):>5}  {status:<16}  {e.get('phase_label','')}")
        except Exception:
            pass
    print()
    for s, n in sorted(counts.items()):
        print(f"  {s}: {n}")


def main() -> None:
    p = argparse.ArgumentParser(description="Dani Voice Draft — flesh out lifecycle email stubs")
    p.add_argument("--dry-run", action="store_true", help="Preview only")
    p.add_argument("--client", help="Filter by client name")
    p.add_argument("--status", action="store_true", help="Show queue state")
    p.add_argument("--timer", action="store_true", help="Silent systemd timer mode")
    args = p.parse_args()

    if args.status:
        print_status()
        return

    results = process_drafts(
        dry_run=args.dry_run,
        client_filter=args.client,
        timer_mode=args.timer,
    )

    if not args.timer:
        voiced = [r for r in results if r["status"] == "voice_drafted"]
        errors = [r for r in results if "error" in r["status"]]
        dry = [r for r in results if r["status"] == "dry_run"]
        if args.dry_run:
            print(f"\n{len(dry)} draft(s) would be voiced.")
        else:
            print(f"\n{len(voiced)} voiced, {len(errors)} errors.")


if __name__ == "__main__":
    main()

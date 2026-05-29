#!/usr/bin/env python3
"""
Lifecycle Calendar Engine — Auto-Queue Client Email Drafts at WF-17 Gate
=========================================================================
Dreams2Memories Travel, LLC | scripts/lifecycle_calendar_engine.py

Reads all active dossiers, computes actionable touchpoints from the
23-TP canonical lifecycle, and auto-creates Gmail drafts (d2mconcierge,
THUNDERBIRD-Commander-Review label) for client-facing TPs due within
the configured horizon.

Deduplication: never queues two drafts for the same (client, tp_id).
Completed TPs: reads `completed_tps` list from dossier YAML frontmatter.
Payment TPs: skipped if dossier `payment_status` is paid_in_full.

Commander reviews and approves drafts via /drafts command. Drafts are
stubs — subject, client facts, TP context — for Dani to flesh out or
Commander to approve as-is.

Usage:
    python3 scripts/lifecycle_calendar_engine.py              # Run + queue
    python3 scripts/lifecycle_calendar_engine.py --dry-run    # Preview only
    python3 scripts/lifecycle_calendar_engine.py --horizon 30 # 30-day window
    python3 scripts/lifecycle_calendar_engine.py --client Nichols
    python3 scripts/lifecycle_calendar_engine.py --status     # Show queue log
    python3 scripts/lifecycle_calendar_engine.py --timer      # Silent systemd mode
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import re
import sys
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import yaml

THUNDERBIRD = Path.home() / "Thunderbird"
sys.path.insert(0, str(THUNDERBIRD))
sys.path.insert(0, str(THUNDERBIRD / "core" / "booking"))

from thunderbird_tp_scheduler import (
    DossierRecord,
    ScheduledTP,
    TPStatus,
    scan_dossiers,
    generate_schedule,
    get_actionable_tps,
)

GMAIL_TOKEN = THUNDERBIRD / "gmail_token.json"
QUEUE_LOG = THUNDERBIRD / "storage" / "lifecycle_draft_queue.jsonl"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s LIFECYCLE %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            str(THUNDERBIRD / "logs" / "lifecycle_calendar_engine.log"), mode="a"
        ),
    ],
)
logger = logging.getLogger("lifecycle")

# ---------------------------------------------------------------------------
# TPs that produce client-facing email drafts at the WF-17 gate
# ---------------------------------------------------------------------------

CLIENT_DRAFT_TPS: dict[str, dict] = {
    "0.5": {
        "subject": "Welcome to Dreams2Memories — {voyage} Booking Confirmed",
        "phase_label": "Welcome / Booking Validation",
    },
    "3.1": {
        "subject": "Your {voyage} Pre-Voyage Brief — Everything You Need",
        "phase_label": "Pre-Voyage Brief",
    },
    "3.2": {
        "subject": "Final Confirmation — {voyage} Departure {departure}",
        "phase_label": "Final Confirmation",
    },
    "3.3": {
        "subject": "Bon Voyage! Your {voyage} Journey Starts Soon",
        "phase_label": "Send-Off / Bon Voyage",
    },
    "4.1": {
        "subject": "Friendly Reminder — {voyage} Final Payment Due {fpd}",
        "phase_label": "Payment Reminder #1",
        "skip_if_paid": True,
    },
    "4.2": {
        "subject": "Final Payment Approaching — {voyage} — Due {fpd}",
        "phase_label": "Payment Reminder #2",
        "skip_if_paid": True,
    },
    "4.3": {
        "subject": "Last Chance — {voyage} Final Payment Due {fpd}",
        "phase_label": "Payment Goal",
        "skip_if_paid": True,
    },
    "5.1": {
        "subject": "Welcome Home — {voyage} — We Want to Hear Everything",
        "phase_label": "Welcome Home",
    },
    "5.2": {
        "subject": "How Was Your {voyage}? Share Your Experience",
        "phase_label": "Survey / Review Request",
    },
    "5.3": {
        "subject": "Thank You for Sailing With Us — {voyage}",
        "phase_label": "Thank You + Referral",
    },
}


# ---------------------------------------------------------------------------
# Dossier metadata (extends what thunderbird_tp_scheduler reads)
# ---------------------------------------------------------------------------

def _read_dossier_meta(path: Path) -> dict:
    """Extract fields not in DossierRecord: completed_tps, email, payment_status."""
    try:
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return {}
        fm = yaml.safe_load(match.group(1)) or {}
        completed = fm.get("completed_tps", []) or []
        email = fm.get("email", "")
        payment_status = str(fm.get("payment_status", "")).lower()

        # Fallback: extract primary email from body table rows
        if not email:
            body_after_fm = text[match.end():]
            email_row = re.search(r"\|\s*[Ee]mail\s*\|\s*([^\s|@]+@[^\s|]+)", body_after_fm)
            if email_row:
                email = email_row.group(1).strip()

        # Infer client full name from frontmatter
        full_name = str(fm.get("full_name", fm.get("client", "")))

        return {
            "completed_tps": set(str(t) for t in completed),
            "email": email,
            "payment_status": payment_status,
            "full_name": full_name,
        }
    except Exception as exc:
        logger.warning(f"Meta read error [{path.name}]: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Queue log — deduplication
# ---------------------------------------------------------------------------

def load_queue_log() -> set[tuple[str, str]]:
    """Return set of (client, tp_id) pairs already in the queue (non-cancelled)."""
    queued: set[tuple[str, str]] = set()
    if not QUEUE_LOG.exists():
        return queued
    for line in QUEUE_LOG.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
            if entry.get("status") != "cancelled":
                queued.add((entry["client"], entry["tp_id"]))
        except Exception:
            pass
    return queued


def append_queue_entry(entry: dict) -> None:
    QUEUE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Gmail draft creation
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


def _get_commander_review_label_id(service) -> Optional[str]:
    """Look up the THUNDERBIRD-Commander-Review label ID."""
    try:
        labels = service.users().labels().list(userId="me").execute()
        for label in labels.get("labels", []):
            if label["name"] == "THUNDERBIRD-Commander-Review":
                return label["id"]
    except Exception as exc:
        logger.warning(f"Label lookup failed: {exc}")
    return None


def create_gmail_draft(
    to: str,
    subject: str,
    body_html: str,
    service=None,
    label_id: Optional[str] = None,
) -> dict:
    """Create draft in d2mconcierge, tag THUNDERBIRD-Commander-Review."""
    if service is None:
        service = _get_gmail_service()
    if label_id is None:
        label_id = _get_commander_review_label_id(service)

    msg = MIMEMultipart("alternative")
    msg["to"] = to if to else "FILL_CLIENT_EMAIL@tbd.invalid"
    msg["from"] = "d2mconcierge@gmail.com"
    msg["subject"] = subject
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": {"raw": raw}})
        .execute()
    )

    draft_id = draft["id"]
    message_id = draft.get("message", {}).get("id", "")

    if label_id and message_id:
        try:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": [label_id]},
            ).execute()
        except Exception as exc:
            logger.warning(f"Label apply failed for draft {draft_id}: {exc}")

    return {"draft_id": draft_id, "message_id": message_id}


# ---------------------------------------------------------------------------
# Email body template builder
# ---------------------------------------------------------------------------

def _format_date(d: Optional[date]) -> str:
    return d.strftime("%B %-d, %Y") if d else "TBD"


def build_draft_body(
    tp: ScheduledTP,
    rec: DossierRecord,
    full_name: str,
    tp_config: dict,
) -> str:
    """Build stub HTML email body for WF-17 review."""
    voyage = rec.ship or "your voyage"
    cruise_line = rec.cruise_line or "Cruise Line"
    departure_str = _format_date(rec.departure)
    fpd_str = _format_date(rec.fpd)
    deadline_str = _format_date(tp.deadline)
    first_name = full_name.split()[0] if full_name else rec.client
    phase_label = tp_config.get("phase_label", tp.label)

    return f"""<div style="font-family: Georgia, serif; color: #1a3557; background: #f7f3ea; padding: 20px; max-width: 640px;">
<p style="font-size: 11px; color: #888; border-bottom: 1px solid #ccc; padding-bottom: 8px; margin-bottom: 16px;">
  ⚠️ <strong>WF-17 DRAFT — Awaiting Commander Review</strong><br>
  TP {tp.tp_id} · {phase_label} · Deadline: {deadline_str}<br>
  Auto-queued by Lifecycle Calendar Engine · Dani to review voice before send
</p>

<p>Dear {first_name},</p>

<p>[DANI — DRAFT THIS SECTION based on TP {tp.tp_id}: {phase_label}]</p>

<p><em>Trip context for drafting:</em></p>
<ul>
  <li><strong>Client:</strong> {full_name or rec.client}</li>
  <li><strong>Cruise:</strong> {cruise_line} {voyage}</li>
  <li><strong>Departure:</strong> {departure_str}</li>
  {"<li><strong>Final Payment Due:</strong> " + fpd_str + "</li>" if rec.fpd else ""}
  <li><strong>Staff Lead:</strong> {tp.tp_def.staff_lead}</li>
  {"<li><strong>Notes:</strong> " + tp.tp_def.notes + "</li>" if tp.tp_def.notes else ""}
</ul>

<p>[CLOSE — Dani signature block]</p>

<p style="font-size: 10px; color: #aaa; margin-top: 24px; border-top: 1px solid #ddd; padding-top: 8px;">
  Thunderbird Wing · Dreams2Memories Travel, LLC<br>
  Internal reference: TP {tp.tp_id} · {rec.client} · {deadline_str}
</p>
</div>"""


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

def run_engine(
    horizon_days: int = 30,
    client_filter: Optional[str] = None,
    dry_run: bool = False,
    timer_mode: bool = False,
) -> list[dict]:
    today = date.today()
    logger.info(
        f"Lifecycle engine starting — horizon={horizon_days}d "
        f"client={client_filter or 'all'} dry_run={dry_run}"
    )

    records = scan_dossiers()
    queued_pairs = load_queue_log()

    # Build Gmail service once (skip in dry-run)
    service = label_id = None
    if not dry_run:
        try:
            service = _get_gmail_service()
            label_id = _get_commander_review_label_id(service)
        except Exception as exc:
            logger.error(f"Gmail auth failed: {exc}")
            if not timer_mode:
                print(f"ERROR: Gmail auth failed — {exc}")
                print("Run with --dry-run to preview without Gmail access.")
            return []

    results = []

    for rec in records:
        if not rec.is_schedulable:
            continue
        if client_filter and client_filter.lower() not in rec.client.lower():
            continue
        if rec.parse_error:
            logger.warning(f"Dossier error [{rec.path.name}]: {rec.parse_error}")
            continue

        meta = _read_dossier_meta(rec.path)
        completed_tps = meta.get("completed_tps", set())
        client_email = meta.get("email", "")
        payment_status = meta.get("payment_status", "")
        full_name = meta.get("full_name", rec.client)
        is_paid = payment_status in ("paid_in_full", "paid", "complete")

        schedule = generate_schedule(rec, today)
        actionable = get_actionable_tps(schedule, horizon_days, today)

        for stp in actionable:
            tp_id = stp.tp_id

            # Only process client-draft TPs
            if tp_id not in CLIENT_DRAFT_TPS:
                continue

            tp_config = CLIENT_DRAFT_TPS[tp_id]

            # Skip completed TPs
            if tp_id in completed_tps:
                continue

            # Skip payment reminders for paid clients
            if tp_config.get("skip_if_paid") and is_paid:
                continue

            # Skip already queued (dedup)
            if (rec.client, tp_id) in queued_pairs:
                continue

            subject = tp_config["subject"].format(
                voyage=rec.ship or rec.cruise_line or "your voyage",
                departure=_format_date(rec.departure),
                fpd=_format_date(rec.fpd),
            )

            entry: dict = {
                "ts": datetime.now().isoformat(),
                "client": rec.client,
                "full_name": full_name,
                "tp_id": tp_id,
                "phase_label": tp_config["phase_label"],
                "subject": subject,
                "deadline": stp.deadline.isoformat() if stp.deadline else None,
                "status": "pending",
                "draft_id": None,
                "client_email": client_email or "[FILL_CLIENT_EMAIL]",
            }

            if dry_run:
                entry["status"] = "dry_run"
                results.append(entry)
                print(
                    f"  [DRY-RUN] {rec.client} TP {tp_id} — {tp_config['phase_label']}\n"
                    f"    Subject: {subject}\n"
                    f"    To: {client_email or '[FILL_CLIENT_EMAIL]'}\n"
                    f"    Deadline: {entry['deadline']}"
                )
                continue

            # Create Gmail draft
            try:
                body_html = build_draft_body(stp, rec, full_name, tp_config)
                draft_result = create_gmail_draft(
                    to=client_email,
                    subject=subject,
                    body_html=body_html,
                    service=service,
                    label_id=label_id,
                )
                entry["draft_id"] = draft_result["draft_id"]
                entry["status"] = "queued"
                queued_pairs.add((rec.client, tp_id))  # prevent double-queue in same run

                logger.info(
                    f"Draft queued: {rec.client} TP {tp_id} "
                    f"draft_id={draft_result['draft_id']}"
                )
                if not timer_mode:
                    print(
                        f"  ✅ {rec.client} TP {tp_id} — {tp_config['phase_label']}\n"
                        f"     Draft: {draft_result['draft_id']}"
                    )
            except Exception as exc:
                entry["status"] = "error"
                entry["error"] = str(exc)
                logger.error(f"Draft failed {rec.client} TP {tp_id}: {exc}")

            append_queue_entry(entry)
            results.append(entry)

    return results


# ---------------------------------------------------------------------------
# Status report
# ---------------------------------------------------------------------------

def print_status() -> None:
    if not QUEUE_LOG.exists():
        print("Queue log empty — no drafts queued yet.")
        return
    lines = [l for l in QUEUE_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\nLIFECYCLE DRAFT QUEUE — {len(lines)} entries\n")
    print(f"{'CLIENT':<16} {'TP':>5}  {'PHASE LABEL':<30} {'STATUS':<10}  DEADLINE")
    print("-" * 90)
    for line in lines:
        try:
            e = json.loads(line)
            print(
                f"{e.get('client','?'):<16} {e.get('tp_id','?'):>5}  "
                f"{e.get('phase_label','?'):<30} {e.get('status','?'):<10}  "
                f"{e.get('deadline','?')}"
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description="Lifecycle Calendar Engine — auto-queue Dani drafts at WF-17"
    )
    p.add_argument("--dry-run", action="store_true", help="Preview only — no drafts created")
    p.add_argument("--horizon", type=int, default=30, help="Horizon in days (default 30)")
    p.add_argument("--client", help="Filter by client name (partial match)")
    p.add_argument("--status", action="store_true", help="Show queue log and exit")
    p.add_argument("--timer", action="store_true", help="Silent systemd timer mode")
    args = p.parse_args()

    if args.status:
        print_status()
        return

    if not args.timer:
        print(f"\nLifecycle Calendar Engine — {date.today().isoformat()}")
        if args.dry_run:
            print("MODE: DRY-RUN (no drafts will be created)\n")

    results = run_engine(
        horizon_days=args.horizon,
        client_filter=args.client,
        dry_run=args.dry_run,
        timer_mode=args.timer,
    )

    queued = [r for r in results if r["status"] == "queued"]
    errors = [r for r in results if r["status"] == "error"]
    dry = [r for r in results if r["status"] == "dry_run"]

    if not args.timer:
        if args.dry_run:
            print(f"\n{len(dry)} draft(s) would be queued.")
        else:
            print(f"\n{len(queued)} draft(s) queued at WF-17 gate.")
            if errors:
                print(f"{len(errors)} error(s) — check logs/lifecycle_calendar_engine.log")

    logger.info(
        f"Engine complete — queued={len(queued)} errors={len(errors)} dry={len(dry)}"
    )


if __name__ == "__main__":
    main()

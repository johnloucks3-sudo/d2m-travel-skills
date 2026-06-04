#!/usr/bin/env python3
"""
ETB-003: D2M Lifecycle Email Scheduler
=======================================
Reads Blackboard YAML, calculates due lifecycle phases, generates Gmail DRAFTS.
NEVER auto-sends — all drafts require Commander approval (WF-17 gate).

Usage:
  python3 lifecycle_scheduler.py [--dry-run] [--client CLIENT_ID] [--date YYYY-MM-DD]

Schedule: Daily at 0600 MT via n8n cron / systemd timer
Output:   Gmail drafts labeled THUNDERBIRD-Commander-Review
          OpsCenter/logs/lifecycle_audit.jsonl
          Telegram notification to Commander
"""

import sys
import json
import yaml
import logging
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
BLACKBOARD_DIR = Path("/home/john/Thunderbird/Blackboard/clients")
AUDIT_LOG = Path("/home/john/Thunderbird/OpsCenter/logs/lifecycle_audit.jsonl")
TEMPLATES_DIR = Path("/home/john/Thunderbird/core/lifecycle/templates")
THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LIFECYCLE] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)


# ── Email Templates (22 TPs) ──────────────────────────────────────────────────

def get_template(phase_id: str, client: dict, booking: dict) -> Optional[dict]:
    """Return subject + HTML body for a given lifecycle phase."""
    names = client.get("client_names", "Valued Traveler")
    first = names.split("&")[0].strip().split()[0] if "&" in names else names.split()[0]
    ship = booking.get("ship", "your vessel")
    voyage = booking.get("voyage_name", "your voyage")
    depart = booking.get("embarkation_date", "")
    depart_port = booking.get("embarkation_port", "")
    disembark = booking.get("disembarkation_date", "")
    supplier = booking.get("supplier", "your cruise line")
    cabin = f"Suite {booking.get('cabin_number', 'TBD')}"

    # Format departure date nicely
    try:
        dep_dt = datetime.strptime(str(depart), "%Y-%m-%d")
        dep_pretty = dep_dt.strftime("%B %d, %Y")
    except Exception:
        dep_pretty = str(depart)

    templates = {
        "TP_0.5": {
            "subject": f"Welcome Aboard — Your {voyage} Voyage Is Confirmed",
            "body": f"""<p>Dear {names},</p>
<p>Wonderful news — your reservation aboard the <strong>{ship}</strong> is confirmed. We are delighted to have you sailing with {supplier} and honored to serve as your travel partner for this journey.</p>
<p>Your voyage departs <strong>{dep_pretty}</strong> from {depart_port}. Your accommodation is confirmed as <strong>{cabin}</strong>.</p>
<p>Over the coming weeks, you will hear from us with planning touchpoints — flights, hotels, shore excursions, specialty dining, and everything in between. Our goal is that you arrive at the pier with nothing left to do but enjoy the journey.</p>
<p>Please do not hesitate to reach out with any questions at any time. We are here for you.</p>""",
        },
        "TP_1": {
            "subject": f"Quick Request — Guest Profiles & Emergency Contacts | {voyage}",
            "body": f"""<p>Dear {names},</p>
<p>As we begin planning your {voyage} voyage, we want to make sure we have complete profiles for all travelers in your party. This allows us to anticipate your needs, coordinate any dietary accommodations, and ensure we have current emergency contact information on file.</p>
<p>When you have a moment, please complete your guest profile through the link below. It takes just a few minutes and makes an enormous difference in the quality of service we can provide.</p>
<p>We look forward to building the perfect voyage for you.</p>""",
        },
        "TP_2": {
            "subject": f"Travel Insurance — A Word Before Your {voyage} Voyage",
            "body": f"""<p>Dear {first},</p>
<p>Before we dive into the exciting parts of voyage planning, we want to take a moment to discuss travel insurance — not as a formality, but because it genuinely matters.</p>
<p>Your investment in this voyage is significant. Comprehensive travel insurance protects that investment against cancellation, medical emergencies, missed connections, and evacuation. Many of our clients choose Allianz Travel Insurance; others leverage existing credit card benefits through Chase Sapphire Reserve or similar programs.</p>
<p><strong>Important note:</strong> If your policy includes pre-existing condition coverage, most insurers require purchase within 14–21 days of your initial deposit. Please review your timeline.</p>
<p>We are happy to discuss options that make sense for your situation. Just reply to this message.</p>""",
        },
        "TP_3": {
            "subject": f"Flights & Air Travel — Let's Talk About Getting You to {depart_port}",
            "body": f"""<p>Dear {names},</p>
<p>With your {voyage} voyage departure from {depart_port} on <strong>{dep_pretty}</strong>, now is a good time to think about flights.</p>
<p>We recommend arriving at your embarkation port at least one day early — this protects against flight delays and gives you time to settle in. We are happy to research flight options, suggest routing, and coordinate pre-cruise hotel stays.</p>
<p>If you have existing flight bookings, please share the details so we can ensure everything is coordinated. If you are still planning, we can help with route analysis and timing recommendations.</p>
<p>Let us take the complexity out of the journey to the ship.</p>""",
        },
        "TP_4.1": {
            "subject": f"Payment Planning — {voyage} Final Payment Coming Up",
            "body": f"""<p>Dear {first},</p>
<p>A quick note as your final payment date for the {voyage} voyage approaches. We want to make sure nothing catches you off guard.</p>
<p>Your cruise line will send their own reminder, but we like to give our clients advance notice so final payment is on your schedule, not theirs.</p>
<p>Please reply if you have any questions about the payment process or if you would like us to verify the current balance on your booking.</p>""",
        },
        "TP_4.2": {
            "subject": f"Payment Reminder — {voyage} Final Payment Window",
            "body": f"""<p>Dear {first},</p>
<p>Your final payment for the {voyage} voyage is approaching. We want to make sure this is on your radar.</p>
<p>If you have any questions about the balance due, payment methods, or the portal, please do not hesitate to reach out. We are here to make this seamless.</p>""",
        },
        "TP_4.3": {
            "subject": f"Final Payment — Action Required | {voyage}",
            "body": f"""<p>Dear {first},</p>
<p>Your final payment for the {voyage} voyage is now due. Please ensure payment is made before the deadline to protect your reservation and avoid cancellation penalties.</p>
<p>If you experience any issues with the payment portal, contact us immediately and we will assist in resolving the situation with {supplier} directly.</p>
<p>Once your final payment is confirmed, we will send you a payment confirmation and begin your pre-departure planning in earnest.</p>""",
        },
        "TP_5": {
            "subject": f"Hotels & Pre-Cruise Planning | {voyage}",
            "body": f"""<p>Dear {names},</p>
<p>With flights underway, let us turn to hotels and pre-cruise logistics for your {voyage} voyage.</p>
<p>We strongly recommend arriving at your embarkation city one to two nights early. This provides a buffer against travel delays and allows you to begin the holiday mood before boarding the {ship}.</p>
<p>We have researched several excellent options near {depart_port} and would be delighted to share recommendations tailored to your preferences. Simply let us know if you would like to explore options or if you have already secured accommodations.</p>""",
        },
        "TP_6": {
            "subject": f"Shore Excursions — Planning Your Ports of Call | {voyage}",
            "body": f"""<p>Dear {names},</p>
<p>Your {voyage} voyage itinerary offers a remarkable collection of ports — each one an opportunity for discovery. We would love to help you make the most of every day ashore.</p>
<p>We have access to both {supplier}'s curated excursion program and independent options that can offer more flexibility, smaller groups, and in many cases, comparable or superior experiences.</p>
<p>Please let us know if you would like excursion recommendations for specific ports. We are happy to research options that match your pace and interests.</p>""",
        },
        "TP_7": {
            "subject": f"Specialty Dining — Reserve Your Tables Now | {voyage}",
            "body": f"""<p>Dear {first},</p>
<p>Specialty dining aboard the {ship} opens for reservations — and the most popular tables fill quickly.</p>
<p>We recommend reserving your preferred restaurants now to avoid disappointment. If you need guidance on which venues are worth the early reservation, we are happy to share what we know about each dining experience.</p>
<p>Log in to your {supplier} account to make reservations, or let us know if you would like assistance navigating the portal.</p>""",
        },
        "TP_8": {
            "subject": f"Passports & Visas — Quick Checklist | {voyage}",
            "body": f"""<p>Dear {names},</p>
<p>As your {voyage} departure approaches, we want to confirm a few important documents.</p>
<p><strong>Passports:</strong> Please ensure all travelers have passports valid for at least six months beyond your return date of {disembark}. If any passport expires within the next year, now is the time to begin renewal.</p>
<p><strong>Visas:</strong> We have reviewed the port requirements for your itinerary. Please reply to confirm you have reviewed any visa or entry requirements relevant to your citizenship.</p>
<p>If you need any guidance on the renewal process or entry requirements for specific ports, we are here to help.</p>""",
        },
        "TP_9": {
            "subject": f"Packing & Preparation — Getting Ready for {voyage}",
            "body": f"""<p>Dear {names},</p>
<p>Your {voyage} voyage is getting closer, and it is time to start thinking about preparation and packing.</p>
<p>We have put together some tailored recommendations for your specific itinerary — appropriate attire for each port, essentials for the climate, and a few items our most experienced travelers never leave home without.</p>
<p>As always, we are available to answer any questions about what to expect on board or at your ports of call.</p>""",
        },
        "TP_10": {
            "subject": f"Online Check-In Is Open — Complete It Now | {voyage}",
            "body": f"""<p>Dear {names},</p>
<p>Online check-in for your {voyage} voyage is now open. Completing check-in early ensures you receive priority boarding and saves time on embarkation day.</p>
<p>Log in to your {supplier} account and complete the check-in process for all travelers. You will need passport details, credit card for onboard expenses, and emergency contact information.</p>
<p>If you encounter any issues with the process, please reach out and we will assist.</p>""",
        },
        "TP_11": {
            "subject": f"30 Days Out — Final Countdown | {voyage}",
            "body": f"""<p>Dear {names},</p>
<p>Thirty days from today, you will be departing for your {voyage} voyage aboard the {ship}. The anticipation is real.</p>
<p>Let us do a quick status check together. At this stage, we want to confirm:</p>
<ul>
<li>All flights confirmed and seats assigned</li>
<li>Hotel reservations confirmed</li>
<li>Shore excursions booked for priority ports</li>
<li>Online check-in complete</li>
<li>Travel insurance active</li>
<li>Passports current</li>
</ul>
<p>Please reply and let us know how you are feeling about the voyage. We are here if anything needs attention.</p>""",
        },
        "TP_12": {
            "subject": f"Emergency & Logistics Briefing | {voyage}",
            "body": f"""<p>Dear {names},</p>
<p>Twenty days before your {voyage} departure, we want to make sure you have all the logistics clearly in hand.</p>
<p>Included with this message is a summary of your complete travel plan: embarkation details, transfer arrangements, hotel confirmations, and emergency contacts. Please review and flag anything that needs updating.</p>
<p>Most importantly — save our contact information in your phone. If anything goes sideways during travel, we want to hear from you immediately so we can help resolve it.</p>""",
        },
        "TP_13": {
            "subject": f"7-Day Checklist — Final Preparations | {voyage}",
            "body": f"""<p>Dear {names},</p>
<p>One week from today, the {voyage} voyage begins. Here is your final checklist:</p>
<ul>
<li>✅ Confirm all flight times and terminal/gate information</li>
<li>✅ Confirm hotel check-in details and transfer arrangements</li>
<li>✅ Review {supplier} boarding pass and travel documents</li>
<li>✅ Charge and pack all electronics</li>
<li>✅ Confirm travel insurance policy documents are accessible</li>
<li>✅ Pack medications in carry-on luggage</li>
<li>✅ Notify your bank of international travel dates</li>
</ul>
<p>You are ready. We cannot wait to hear about this voyage when you return.</p>""",
        },
        "TP_14": {
            "subject": f"48 Hours — You Are Almost There | {voyage}",
            "body": f"""<p>Dear {first},</p>
<p>In 48 hours you will be on your way. A few final reminders:</p>
<ul>
<li>Reconfirm your flight times this morning (delays sometimes update overnight)</li>
<li>Have your travel documents accessible — cruise documents, passport, hotel confirmation</li>
<li>Your transfer to the embarkation port is arranged — details in your travel summary</li>
</ul>
<p>Travel safely. We will be thinking of you as you board the {ship}.</p>""",
        },
        "TP_15": {
            "subject": f"Bon Voyage — Have a Wonderful {voyage}!",
            "body": f"""<p>Dear {names},</p>
<p>Today is the day. Bon voyage — and what a voyage it is going to be.</p>
<p>The {ship} awaits. May this journey exceed every expectation, bring you moments you will carry for years, and remind you why the world is worth exploring.</p>
<p>We will be here when you return — and cannot wait to hear everything.</p>""",
        },
        "TP_16": {
            "subject": f"Mid-Voyage Check-In — How Is the {voyage}?",
            "body": f"""<p>Dear {first},</p>
<p>We hope you are settling in beautifully aboard the {ship}. We are thinking of you as you sail through some of the world's most extraordinary waters.</p>
<p>If anything needs attention — a question about a port, assistance with a booking, or anything at all — please do not hesitate to reach out. We are here even while you are at sea.</p>
<p>Enjoy every moment.</p>""",
        },
        "TP_17": {
            "subject": f"Welcome Home — We Hope {voyage} Was Everything You Imagined",
            "body": f"""<p>Dear {names},</p>
<p>Welcome home. We hope the {voyage} voyage aboard the {ship} was everything you hoped for — and perhaps more.</p>
<p>When you have had a chance to decompress, we would love to hear about your experience. Your feedback helps us serve future clients with the same destinations, and it helps us continue to improve the planning process for you.</p>
<p>Thank you for trusting us with such a meaningful journey. It is genuinely our privilege.</p>""",
        },
        "TP_18": {
            "subject": f"Post-Travel Debrief — A Few Questions | {voyage}",
            "body": f"""<p>Dear {first},</p>
<p>Now that you have had a week to settle back in, we have a few questions about your {voyage} experience.</p>
<ul>
<li>What was your favorite moment of the voyage?</li>
<li>Were there any aspects of the planning or voyage that fell short?</li>
<li>Were there any shore excursions or dining experiences that particularly stood out?</li>
<li>Is there anything you wish you had known before departing?</li>
</ul>
<p>Your answers genuinely shape how we plan for future clients — and for your own future travels. Thank you for taking a few minutes.</p>""",
        },
        "TP_19": {
            "subject": f"Loyalty Points — Have They Posted? | {voyage}",
            "body": f"""<p>Dear {first},</p>
<p>A few weeks have passed since your {voyage} voyage concluded. {supplier} loyalty points should be posting to your account around this time.</p>
<p>We recommend logging in to your loyalty account to confirm the nights and points from your voyage have been credited. If there are any discrepancies, now is the time to raise them while your voyage is recent.</p>
<p>If you have any questions about your loyalty status or upcoming tier thresholds, we are happy to help you understand the program.</p>""",
        },
        "TP_20": {
            "subject": "Where to Next? — Let Us Start Planning",
            "body": f"""<p>Dear {names},</p>
<p>The afterglow of the {voyage} voyage never fully fades — but the best remedy for the post-voyage blues is planning the next one.</p>
<p>We have been keeping an eye on itineraries that might align with your tastes, and we would love to share a few thoughts when you are ready.</p>
<p>There is no obligation, no rush. Just a conversation about where the world might take you next.</p>""",
        },
        "TP_21": {
            "subject": f"One Year On — Checking In | Dreams2Memories",
            "body": f"""<p>Dear {names},</p>
<p>It has been a year since your {voyage} voyage. We hope the memories are still vivid.</p>
<p>We are reaching out because we value the relationship we have built, and because the travel calendar has some extraordinary itineraries opening for the year ahead.</p>
<p>If you are thinking about travel — whether a cruise, a land journey, or something in between — we would be honored to be part of the planning. Just say the word.</p>""",
        },
        "TP_22": {
            "subject": f"Loyalty Milestone — Celebrating Your Journey | Dreams2Memories",
            "body": f"""<p>Dear {first},</p>
<p>We want to take a moment to celebrate a milestone. Your loyalty as a D2M client and your passion for extraordinary travel deserve recognition.</p>
<p>Thank you for trusting us. The relationships we build with clients like you are exactly why we do this work. We look forward to many more voyages together.</p>""",
        },
    }

    t = templates.get(phase_id)
    if not t:
        return None
    return {
        "subject": t["subject"],
        "html_body": t["body"]
    }


# ── Gmail Draft Creation ───────────────────────────────────────────────────────

def create_gmail_draft(to_email: str, subject: str, html_body: str, client_names: str) -> Optional[str]:
    """Create a Gmail draft via d2mconcierge. Returns message ID or None on failure."""
    try:
        sys.path.insert(0, str(THUNDERBIRD_ROOT / "core" / "email"))
        from thunderbird_gmail import gmail_create_draft_sync

        full_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  body {{ font-family: Georgia, serif; background: #f7f3ea; color: #003087; margin: 0; padding: 0; }}
  .container {{ max-width: 600px; margin: 0 auto; padding: 32px 24px; }}
  p {{ line-height: 1.7; margin-bottom: 14px; color: #003087; }}
  ul {{ line-height: 1.7; color: #003087; }}
  .sig {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid #003087; }}
  .sig-name {{ font-weight: bold; color: #003087; }}
  .sig-title {{ color: #555; font-size: 13px; }}
</style></head>
<body><div class="container">
{html_body}
<div class="sig">
  <div class="sig-name">Danielle "Dani" Moreau</div>
  <div class="sig-title">Luxury Travel Concierge · Dreams2Memories Travel, LLC</div>
  <div class="sig-title">concierge@d2mluxury.quest · 719-291-0742</div>
</div>
</div></body></html>"""

        result = gmail_create_draft_sync(
            to=to_email,
            subject=subject,
            body=full_html
        )
        if result:
            return result.get("id") or result.get("message", {}).get("id")
    except Exception as e:
        log.error(f"Gmail draft creation failed: {e}")
    return None


# ── Telegram Notification ─────────────────────────────────────────────────────

def send_telegram_notification(message: str) -> None:
    """Send Telegram message to Commander via D2MC2C bot."""
    try:
        sys.path.insert(0, str(THUNDERBIRD_ROOT / "OpsCenter"))
        import requests
        import os

        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_COMMANDER_ID", "7554895206")

        if not token:
            # Try loading from .env.d2m
            env_file = Path("/home/john/.env.d2m")
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip('"').strip("'")

        if token:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
                timeout=10
            )
    except Exception as e:
        log.warning(f"Telegram notification failed (non-critical): {e}")


# ── Audit Logging ─────────────────────────────────────────────────────────────

def audit_log(entry: dict) -> None:
    """Append an audit entry to lifecycle_audit.jsonl."""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps({**entry, "timestamp": datetime.utcnow().isoformat() + "Z"}) + "\n")


# ── Phase Due-Date Calculation ────────────────────────────────────────────────

def calculate_due_phases(lifecycle: dict, check_date: date) -> list:
    """Return phases whose due_date is today (check_date)."""
    due = []
    for phase in lifecycle.get("phases", []):
        due_str = phase.get("due_date")
        if not due_str or due_str in ("NEEDED", "TBD", "null", None):
            continue
        try:
            phase_date = date.fromisoformat(str(due_str))
            if phase_date == check_date:
                status = phase.get("status", "")
                if status == "scheduled":
                    due.append(phase)
        except ValueError:
            continue
    return due


# ── Main Scheduler ────────────────────────────────────────────────────────────

def run_scheduler(check_date: date, dry_run: bool = False, client_filter: Optional[str] = None) -> dict:
    """Main scheduler loop. Returns summary dict."""
    log.info(f"Lifecycle scheduler starting — date={check_date} dry_run={dry_run}")
    results = {"date": str(check_date), "processed": 0, "drafts_created": 0, "errors": [], "skipped": 0}

    if not BLACKBOARD_DIR.exists():
        log.error(f"Blackboard directory not found: {BLACKBOARD_DIR}")
        results["errors"].append("Blackboard directory missing")
        return results

    client_files = sorted(BLACKBOARD_DIR.glob("*.yaml"))
    if client_filter:
        client_files = [f for f in client_files if client_filter in f.stem]

    draft_notifications = []

    for client_file in client_files:
        try:
            with open(client_file) as f:
                client = yaml.safe_load(f)

            if not isinstance(client, dict):
                continue

            client_id = client.get("client_id", client_file.stem)
            status = client.get("status", "")
            if status not in ("active", "pre_departure"):
                log.info(f"Skipping {client_id} — status={status}")
                results["skipped"] += 1
                continue

            results["processed"] += 1
            lifecycle = client.get("lifecycle", {})
            due_phases = calculate_due_phases(lifecycle, check_date)

            if not due_phases:
                log.info(f"{client_id} — no phases due today")
                continue

            # Find primary contact email + primary cruise booking
            primary_email = None
            for c in client.get("contacts", []):
                if c.get("role") == "primary" and c.get("email") not in (None, "TBD", "NEEDED"):
                    primary_email = c.get("email")
                    break

            cruise_booking = next(
                (b for b in client.get("bookings", []) if b.get("booking_type") == "cruise"),
                {}
            )

            for phase in due_phases:
                phase_id = phase.get("phase_id", "UNKNOWN")
                log.info(f"{client_id} — phase {phase_id} due today")

                template = get_template(phase_id, client, cruise_booking)
                if not template:
                    log.warning(f"No template for phase {phase_id} — skipping")
                    audit_log({"event": "template_missing", "client_id": client_id, "phase_id": phase_id})
                    continue

                if dry_run:
                    log.info(f"[DRY RUN] Would create draft: {template['subject']} → {primary_email}")
                    audit_log({
                        "event": "dry_run",
                        "client_id": client_id,
                        "phase_id": phase_id,
                        "subject": template["subject"],
                        "to": primary_email
                    })
                    results["drafts_created"] += 1
                    continue

                if not primary_email:
                    log.warning(f"{client_id} {phase_id} — no primary email, cannot create draft")
                    audit_log({"event": "no_email", "client_id": client_id, "phase_id": phase_id})
                    results["errors"].append(f"{client_id}/{phase_id}: no primary email")
                    continue

                # Create Gmail draft — DRAFT ONLY, never send
                draft_id = create_gmail_draft(
                    to_email=primary_email,
                    subject=template["subject"],
                    html_body=template["html_body"],
                    client_names=client.get("client_names", "")
                )

                if draft_id:
                    results["drafts_created"] += 1
                    draft_notifications.append(
                        f"• {client.get('client_names')} — {phase_id}: {template['subject']}"
                    )
                    audit_log({
                        "event": "draft_created",
                        "client_id": client_id,
                        "phase_id": phase_id,
                        "subject": template["subject"],
                        "to": primary_email,
                        "draft_id": draft_id,
                        "label": "THUNDERBIRD-Commander-Review"
                    })
                    log.info(f"Draft created: {draft_id}")
                else:
                    results["errors"].append(f"{client_id}/{phase_id}: draft creation failed")
                    audit_log({
                        "event": "draft_failed",
                        "client_id": client_id,
                        "phase_id": phase_id,
                        "subject": template["subject"],
                        "to": primary_email
                    })

        except Exception as e:
            log.error(f"Error processing {client_file.name}: {e}")
            results["errors"].append(f"{client_file.name}: {str(e)[:100]}")

    # Telegram notification
    if draft_notifications and not dry_run:
        msg_lines = [f"🦅 *LIFECYCLE SCHEDULER — {check_date}*", ""]
        msg_lines.append(f"*{len(draft_notifications)} draft(s) ready for Commander review:*")
        msg_lines.extend(draft_notifications)
        msg_lines.append("")
        msg_lines.append("Check drafts → label: THUNDERBIRD-Commander-Review")
        msg_lines.append("⚠️ Do NOT send without Commander approval (WF-17 gate)")
        send_telegram_notification("\n".join(msg_lines))

    log.info(f"Scheduler complete: {results}")
    audit_log({"event": "scheduler_complete", "summary": results})
    return results


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="D2M Lifecycle Email Scheduler — ETB-003")
    parser.add_argument("--dry-run", action="store_true", help="Calculate due phases without creating drafts")
    parser.add_argument("--client", help="Filter to specific client_id")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD), default=today")
    args = parser.parse_args()

    check_date = date.today()
    if args.date:
        check_date = date.fromisoformat(args.date)

    result = run_scheduler(check_date=check_date, dry_run=args.dry_run, client_filter=args.client)

    print(json.dumps(result, indent=2, default=str))
    if result["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

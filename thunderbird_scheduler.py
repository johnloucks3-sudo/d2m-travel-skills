"""
Dreams2Memories Intel Scheduler
================================

Automated delivery of intelligence reports on a daily/weekly schedule.
Runs as a standalone service (systemd) alongside the MCP server.

Reports:
- Ship Intelligence Sweep: 2x daily (7AM, 5PM MT)
- World Intelligence Sweep: daily (6AM MT)
- Tech Monitor: daily (8AM MT)
- Weekly Client Report: Monday 7AM MT

Delivery:
- Saves reports to Google Drive (Thunderbird_Intel folder)
- Creates Gmail drafts with attachments for review
- Logs all runs to Google Sheets

Usage:
  python3 thunderbird_scheduler.py              # Run scheduler daemon
  python3 thunderbird_scheduler.py --run-now    # Run all sweeps immediately
  python3 thunderbird_scheduler.py --test       # Test one sweep and exit
"""

import json
import logging
import asyncio
import os
import sys
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Import sweep functions directly (not through MCP)
sys.path.insert(0, str(Path(__file__).parent))
from thunderbird_ship_intel import run_ship_intelligence_sweep
from thunderbird_world_intel import run_world_intelligence_sweep
from thunderbird_tech_monitor import run_daily_tech_monitor
from thunderbird_weekly_report import (
    ClientReportRequest, ReportConfig,
    generate_html_report, generate_pdf_report
)

# Drive upload + Gmail draft
from thunderbird_drive import _get_drive_service, authorize_drive
from thunderbird_gmail import _get_gmail_service
from thunderbird_morning_briefing import run_briefing as run_morning_email_briefing
from thunderbird_payment_alerts import check_and_alert as check_payment_alerts
from thunderbird_sync import sync as run_drive_sync
from thunderbird_email_classifier import classify_and_route as run_email_classifier
from thunderbird_email_intel import run_email_intel_sweep, refresh_voice_profile
from thunderbird_calendar_sync import sync_bookings_to_calendar as run_calendar_sync
from thunderbird_followup_reminders import scan_and_remind as run_followup_scan
from thunderbird_nova import run_weekly_audit as run_nova_audit
from thunderbird_heartbeat import (
    run_cos_exec_heartbeat, run_daily_heartbeats, run_weekly_heartbeat
)
from thunderbird_evernote_backup import run_weekly_backup as run_evernote_backup
# Groq eliminated — Claude Opus via Max plan ($0). Intel Crew replaces batch pre-gen
from thunderbird_intel_crew import IntelCrew
from thunderbird_overwatch import run_sentinel_sweep, run_judge_assessment
from thunderbird_switchblade import run_switchblade
from thunderbird_sms_monitor import check_inbound_sms as run_sms_monitor
from thunderbird_dani_email import dani_email_sweep as run_dani_email_sweep
from thunderbird_commander_inbox import run_commander_inbox_sweep as run_commander_inbox_sweep
from thunderbird_concierge_monitor import poll_once as run_concierge_monitor
from thunderbird_concierge_monitor import poll_commander_directives as run_commander_directives
from thunderbird_fare_watch import list_watches as fw_list_watches
from thunderbird_outside_agents import (
    _connect_cdp, _find_portal_tab, _notify_commander,
    _load_state, _save_state, _screenshot_path,
    ODY_BOOKINGS, TESS_COMMISSIONS, TESS_CLIENTS,
)

import subprocess
import base64
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# ============================================================================
# CONFIGURATION
# ============================================================================

THUNDERBIRD_DIR = Path(__file__).parent
OUTPUT_DIR = THUNDERBIRD_DIR / "output" / "scheduled_reports"
LOG_FILE = THUNDERBIRD_DIR / "scheduler.log"

# Drive folder IDs for report delivery
DRIVE_INTEL = "1joXoapQQjnGsKzxxvpDhZnO6czlCQGqj"        # Thunderbird_Intel
DRIVE_FINANCE = "1k2-DOzj5GEN6hjIlMND19hk4fQhUq-Tm"       # Thunderbird_Finance

# Commander's personal inbox — drafts and reports delivered here
OWNER_EMAIL = "johnloucks3@gmail.com"
# D2M ops account — authenticated sender (gmail_token.json authenticates as d2mconcierge)
OPS_EMAIL = "d2mconcierge@gmail.com"

# Timezone
TZ = "America/Denver"  # Mountain Time

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
logger = logging.getLogger("thunderbird_scheduler")

# ============================================================================
# HELPERS
# ============================================================================

def _save_report(content: str, filename: str, subfolder: str = "") -> Path:
    """Save report content to local file."""
    target_dir = OUTPUT_DIR / subfolder if subfolder else OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def _upload_to_drive(local_path: Path, folder_id: str) -> Optional[str]:
    """Upload a file to Google Drive, return file ID or None."""
    try:
        from googleapiclient.http import MediaFileUpload
        service = _get_drive_service()
        mime_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"
        metadata = {"name": local_path.name, "parents": [folder_id]}
        media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
        uploaded = service.files().create(
            body=metadata, media_body=media, fields="id, webViewLink"
        ).execute()
        logger.info(f"Uploaded to Drive: {local_path.name} -> {uploaded.get('webViewLink')}")
        return uploaded.get("id")
    except Exception as e:
        logger.error(f"Drive upload failed: {e}")
        return None


def _create_draft(subject: str, body: str, attachment_paths: list = None):
    """Create a Gmail draft with optional attachments."""
    try:
        service = _get_gmail_service()

        message = MIMEMultipart()
        message["to"] = OWNER_EMAIL
        message["from"] = OPS_EMAIL
        message["subject"] = subject
        message.attach(MIMEText(body, "plain"))

        if attachment_paths:
            for file_path in attachment_paths:
                fp = Path(file_path)
                if not fp.exists():
                    continue
                content_type = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
                main_type, sub_type = content_type.split("/", 1)
                with open(fp, "rb") as f:
                    part = MIMEBase(main_type, sub_type)
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=fp.name)
                message.attach(part)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        draft = service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()
        logger.info(f"Gmail draft created: {subject} (ID: {draft['id']})")
    except Exception as e:
        logger.error(f"Gmail draft failed: {e}")


# ============================================================================
# SCHEDULED JOBS
# ============================================================================

async def job_ship_intel():
    """Ship Intelligence Sweep — runs 2x daily."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Ship Intelligence Sweep")
    logger.info("=" * 60)
    try:
        result = await run_ship_intelligence_sweep()
        ts = datetime.now().strftime("%Y%m%d_%H%M")

        # Save JSON result
        report_path = _save_report(
            json.dumps(result, indent=2),
            f"Ship_Intel_{ts}.json",
            subfolder="ship_intel"
        )

        # Upload to Drive
        _upload_to_drive(report_path, DRIVE_INTEL)

        # Draft if there are alerts
        alerts = result.get("pricing_alerts", 0) + result.get("availability_alerts", 0)
        if alerts > 0:
            _create_draft(
                subject=f"Ship Intel Alert — {alerts} alerts ({ts})",
                body=(
                    f"Ship Intelligence Sweep completed.\n\n"
                    f"Voyages scraped: {result.get('voyages_scraped', 0)}\n"
                    f"Pricing alerts: {result.get('pricing_alerts', 0)}\n"
                    f"Availability alerts: {result.get('availability_alerts', 0)}\n\n"
                    f"Full report attached."
                ),
                attachment_paths=[str(report_path)],
            )

        logger.info(f"Ship Intel complete: {result.get('voyages_scraped', 0)} voyages, {alerts} alerts")
    except Exception as e:
        logger.error(f"Ship Intel FAILED: {e}", exc_info=True)


async def job_world_intel():
    """World Intelligence Sweep — runs daily."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: World Intelligence Sweep")
    logger.info("=" * 60)
    try:
        result = await run_world_intelligence_sweep()
        ts = datetime.now().strftime("%Y%m%d_%H%M")

        report_path = _save_report(
            json.dumps(result, indent=2),
            f"World_Intel_{ts}.json",
            subfolder="world_intel"
        )

        _upload_to_drive(report_path, DRIVE_INTEL)

        # Always draft the morning briefing
        high_advisories = result.get("high_level_advisories", 0)
        weather_alerts = result.get("weather_alerts", 0)
        news_count = result.get("news_articles", 0)

        _create_draft(
            subject=f"Morning Intel Briefing — {datetime.now().strftime('%b %d')}",
            body=(
                f"World Intelligence Sweep completed.\n\n"
                f"Travel advisories: {result.get('travel_advisories_total', 0)} "
                f"({high_advisories} high-level)\n"
                f"Weather forecasts: {result.get('weather_forecasts', 0)} "
                f"({weather_alerts} alerts)\n"
                f"News articles: {news_count} "
                f"({result.get('urgent_news', 0)} urgent)\n\n"
                f"Full report attached."
            ),
            attachment_paths=[str(report_path)],
        )

        logger.info(f"World Intel complete: {result.get('travel_advisories_total', 0)} advisories, {news_count} news")
    except Exception as e:
        logger.error(f"World Intel FAILED: {e}", exc_info=True)


async def job_tech_monitor():
    """Tech Monitor — runs daily."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Tech Monitor Sweep")
    logger.info("=" * 60)
    try:
        result = await run_daily_tech_monitor()
        ts = datetime.now().strftime("%Y%m%d_%H%M")

        # The tech monitor already saves an HTML digest
        digest_file = result.get("digest_file")
        attachments = []
        if digest_file and Path(digest_file).exists():
            attachments.append(digest_file)

        recent = result.get("recent_articles", 0)
        categories = result.get("top_categories", {})
        cat_summary = ", ".join(f"{k}: {v}" for k, v in categories.items())

        _create_draft(
            subject=f"Tech Digest — {recent} articles ({datetime.now().strftime('%b %d')})",
            body=(
                f"Tech Monitor sweep completed.\n\n"
                f"Articles found: {result.get('total_articles_found', 0)}\n"
                f"Recent (24h): {recent}\n"
                f"Categories: {cat_summary}\n\n"
                f"HTML digest attached."
            ),
            attachment_paths=attachments,
        )

        logger.info(f"Tech Monitor complete: {recent} recent articles")
    except Exception as e:
        logger.error(f"Tech Monitor FAILED: {e}", exc_info=True)


async def job_weekly_report():
    """Weekly Client Report — runs Monday mornings."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Weekly Client Intelligence Report")
    logger.info("=" * 60)
    try:
        request = ClientReportRequest(
            client_name="John Loucks",
            target_ships=ReportConfig.DEFAULT_SHIPS,
            target_destinations=ReportConfig.DEFAULT_DESTINATIONS,
            output_format="both",
        )

        html = generate_html_report(request)
        ts = datetime.now().strftime("%Y%m%d")

        # Save HTML
        html_path = _save_report(html, f"Weekly_Report_{ts}.html", subfolder="weekly")

        # Generate PDF
        pdf_path = OUTPUT_DIR / "weekly" / f"Weekly_Report_{ts}.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        generate_pdf_report(html, pdf_path)

        # Upload both to Drive
        _upload_to_drive(html_path, DRIVE_INTEL)
        if pdf_path.exists():
            _upload_to_drive(pdf_path, DRIVE_INTEL)

        _create_draft(
            subject=f"Weekly Intelligence Report — {datetime.now().strftime('%b %d, %Y')}",
            body=(
                f"Your weekly intelligence report is ready.\n\n"
                f"Ships monitored: {', '.join(request.target_ships)}\n"
                f"Regions: {', '.join(request.target_destinations)}\n\n"
                f"PDF and HTML attached."
            ),
            attachment_paths=[str(pdf_path), str(html_path)] if pdf_path.exists() else [str(html_path)],
        )

        logger.info("Weekly Report complete")
    except Exception as e:
        logger.error(f"Weekly Report FAILED: {e}", exc_info=True)


async def job_branded_morning_email():
    """Branded Morning Briefing Email — the HTML email with all intel sections."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Branded Morning Briefing Email")
    logger.info("=" * 60)
    try:
        result = run_morning_email_briefing(preview=False, weekly=False)
        logger.info(f"Branded Morning Email sent: {result}")
    except Exception as e:
        logger.error(f"Branded Morning Email FAILED: {e}", exc_info=True)


async def job_payment_alerts():
    """Payment deadline SMS alerts — checks upcoming deadlines."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Payment Deadline Alerts")
    logger.info("=" * 60)
    try:
        alerts_sent = check_payment_alerts()
        logger.info(f"Payment alerts: {alerts_sent} alerts sent")
    except Exception as e:
        logger.error(f"Payment Alerts FAILED: {e}", exc_info=True)


async def job_claude_code_digest():
    """Claude Code articles digest — scrapes news sources and generates HTML page."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Claude Code Digest")
    logger.info("=" * 60)
    try:
        import importlib
        mod = importlib.import_module("thunderbird_claude_code_digest")
        mod.main()
        logger.info("Claude Code Digest generated")
    except Exception as e:
        logger.error(f"Claude Code Digest FAILED: {e}", exc_info=True)


async def job_drive_sync():
    """Drive Mirror — incremental sync of ~/Thunderbird/ to Google Drive."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Drive Mirror Sync")
    logger.info("=" * 60)
    try:
        run_drive_sync(full=False)
        logger.info("Drive Mirror Sync complete")
    except Exception as e:
        logger.error(f"Drive Mirror Sync FAILED: {e}", exc_info=True)


async def job_email_classifier():
    """Email Auto-Classification — process THUNDERBIRD-Process label."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Email Classifier")
    logger.info("=" * 60)
    try:
        run_email_classifier()
        logger.info("Email classification complete")
    except Exception as e:
        logger.error(f"Email Classifier FAILED: {e}", exc_info=True)


async def job_calendar_sync():
    """Calendar Sync — create events from Booking Master."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Calendar Sync")
    logger.info("=" * 60)
    try:
        run_calendar_sync()
        logger.info("Calendar sync complete")
    except Exception as e:
        logger.error(f"Calendar Sync FAILED: {e}", exc_info=True)


async def job_followup_scan():
    """Client Follow-Up Scanner — flag inactive clients."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Follow-Up Scan")
    logger.info("=" * 60)
    try:
        run_followup_scan()
        logger.info("Follow-up scan complete")
    except Exception as e:
        logger.error(f"Follow-Up Scan FAILED: {e}", exc_info=True)


async def job_cos_exec_heartbeat():
    """COS-EXEC Synced Heartbeat — every 30 min during business hours."""
    logger.info("HEARTBEAT: COS-EXEC scan")
    try:
        run_cos_exec_heartbeat()
        logger.info("COS-EXEC heartbeat complete")
    except Exception as e:
        logger.error(f"COS-EXEC heartbeat FAILED: {e}", exc_info=True)


async def job_daily_heartbeats():
    """Daily persona heartbeats — A2, A3, A9, A10, A6 in sequence."""
    logger.info("HEARTBEAT: Running all daily persona heartbeats")
    try:
        run_daily_heartbeats()
        logger.info("Daily heartbeats complete")
    except Exception as e:
        logger.error(f"Daily heartbeats FAILED: {e}", exc_info=True)


async def job_weekly_heartbeat():
    """CH Washington weekly wisdom — Friday only."""
    logger.info("HEARTBEAT: CH Washington weekly")
    try:
        run_weekly_heartbeat()
        logger.info("Weekly heartbeat complete")
    except Exception as e:
        logger.error(f"Weekly heartbeat FAILED: {e}", exc_info=True)


async def job_evernote_backup():
    """Weekly Evernote + USB code backup."""
    logger.info("BACKUP: Evernote + USB weekly code backup")
    try:
        result = run_evernote_backup()
        logger.info(f"Evernote backup complete: {result}")
    except Exception as e:
        logger.error(f"Evernote backup FAILED: {e}", exc_info=True)


async def job_rsync_to_dv7():
    """Rsync Thunderbird codebase from YOGA to dv7 (always-on server)."""
    logger.info("SYNC: rsync YOGA → dv7")
    try:
        excludes = [
            '.venv', 'venv', '__pycache__', 'node_modules', '.git', '.claude',
            'credentials.json', 'gmail_token.json', 'drive_token.json',
            'calendar_token.json', 'gmail_oauth_credentials.json',
            '*.pyc', 'output/', 'screenshots/',
        ]
        cmd = [
            'rsync', '-az', '--delete',
            *[f'--exclude={e}' for e in excludes],
            str(THUNDERBIRD_DIR) + '/',
            'dv7:~/Thunderbird/',
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            logger.info("rsync to dv7 complete")
        else:
            logger.error(f"rsync to dv7 failed (rc={result.returncode}): {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("rsync to dv7 timed out (120s)")
    except Exception as e:
        logger.error(f"rsync to dv7 FAILED: {e}", exc_info=True)


async def job_nova_audit():
    """Nova Weekly Audit — ELON (A12) reviews system health and generates improvement tickets."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Nova Weekly Audit")
    logger.info("=" * 60)
    try:
        result = run_nova_audit()
        logger.info(f"Nova audit complete: {result.get('tickets_created', 0)} tickets created")
    except Exception as e:
        logger.error(f"Nova Audit FAILED: {e}", exc_info=True)


async def job_morning_briefing():
    """Consolidated Morning Briefing — world intel + ship intel in one email."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Morning Briefing (combined)")
    logger.info("=" * 60)
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        date_display = datetime.now().strftime("%A, %B %d %Y")
        attachments = []

        # Run world intel
        logger.info("Running World Intel...")
        world_result = await run_world_intelligence_sweep()
        world_path = _save_report(
            json.dumps(world_result, indent=2),
            f"World_Intel_{ts}.json", subfolder="morning"
        )
        _upload_to_drive(world_path, DRIVE_INTEL)
        attachments.append(str(world_path))

        # Run ship intel
        logger.info("Running Ship Intel...")
        ship_result = await run_ship_intelligence_sweep()
        ship_path = _save_report(
            json.dumps(ship_result, indent=2),
            f"Ship_Intel_{ts}.json", subfolder="morning"
        )
        _upload_to_drive(ship_path, DRIVE_INTEL)
        attachments.append(str(ship_path))

        # Build briefing summary
        advisories = world_result.get("travel_advisories_total", 0)
        high_adv = world_result.get("high_level_advisories", 0)
        weather_alerts = world_result.get("weather_alerts", 0)
        news = world_result.get("news_articles", 0)
        urgent = world_result.get("urgent_news", 0)
        voyages = ship_result.get("voyages_scraped", 0)
        price_alerts = ship_result.get("pricing_alerts", 0)
        avail_alerts = ship_result.get("availability_alerts", 0)

        body = (
            f"THUNDERBIRD MORNING BRIEFING\n"
            f"{date_display}\n"
            f"{'=' * 40}\n\n"
            f"WORLD INTELLIGENCE\n"
            f"  Travel advisories: {advisories} ({high_adv} high-level)\n"
            f"  Weather alerts: {weather_alerts}\n"
            f"  Cruise news: {news} articles ({urgent} urgent)\n\n"
            f"SHIP INTELLIGENCE\n"
            f"  Voyages tracked: {voyages}\n"
            f"  Pricing alerts: {price_alerts}\n"
            f"  Availability alerts: {avail_alerts}\n\n"
        )

        if price_alerts > 0 or avail_alerts > 0:
            body += "*** ACTION ITEMS: Check ship intel report for alerts ***\n\n"

        if high_adv > 0:
            top_alerts = world_result.get("top_alerts", [])
            body += "HIGH-LEVEL ADVISORIES:\n"
            for a in top_alerts:
                body += f"  - {a.get('country', '?')}: Level {a.get('level', '?')}\n"
            body += "\n"

        body += "Full reports attached. Review and send as needed."

        _create_draft(
            subject=f"Thunderbird Morning Briefing — {datetime.now().strftime('%b %d')}",
            body=body,
            attachment_paths=attachments,
        )

        logger.info(f"Morning Briefing complete: {news} news, {voyages} voyages, "
                     f"{price_alerts + avail_alerts} total alerts")
    except Exception as e:
        logger.error(f"Morning Briefing FAILED: {e}", exc_info=True)


# ============================================================================
# ============================================================================
# CONSOLIDATED JOBS (5 total — replaces 18 individual jobs)
# ============================================================================
# Item #10: Consolidate heartbeat system from 18 scheduled jobs down to 5.
# Old jobs are preserved below (commented out) in build_scheduler_legacy().

async def consolidated_morning_brief():
    """
    MORNING BRIEF (0630 daily)
    Consolidates: morning_briefing, daily_heartbeats, branded_morning_email,
                  payment_alerts, followup_scan, world_intel, ship_intel (AM)

    Runs all morning persona heartbeats and intel sweeps, then delivers
    a single consolidated email to the Commander.
    """
    logger.info("=" * 60)
    logger.info("CONSOLIDATED: Morning Brief (0630)")
    logger.info("=" * 60)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    date_display = datetime.now().strftime("%A, %B %d %Y")
    sections = []
    attachments = []
    errors = []

    # ── Intel Crew Pipeline (Groq eliminated — Claude Opus via Max plan) ──
    logger.info("[Morning Brief] Running Intel Crew pipeline (A2→A1→COS)...")
    intel_package = None
    try:
        crew = IntelCrew()
        intel_package = crew.run()

        cos_review = intel_package.get("cos_review", "")
        analysis = intel_package.get("analysis", "")
        audit_report = intel_package.get("audit_report", "")
        airline_impacts = intel_package.get("airline_impacts", [])

        # Client alerts section (TOP of the brief)
        if airline_impacts:
            alert_section = "## CLIENT ALERTS (PRIORITY)\n"
            for impact in airline_impacts[:5]:
                alert_section += (
                    f"  [{impact['severity']}] {impact.get('client', '?')}: "
                    f"{impact.get('title', '?')}\n"
                    f"  Airport: {impact.get('airport', '?')} | "
                    f"Source: {impact.get('source', '?')}\n\n"
                )
            sections.insert(0, alert_section)  # Insert at TOP

        # Full analysis section
        if analysis:
            sections.append(f"## INTELLIGENCE ANALYSIS (A2 — Dembe)\n{analysis}\n")

        # Audit findings
        if audit_report:
            sections.append(f"## AUDIT (A1 — Radar)\n{audit_report}\n")

        # COS synthesis
        if cos_review:
            sections.append(f"## COS SYNTHESIS (Hale)\n{cos_review}\n")

        logger.info(f"Intel Crew pipeline complete — {intel_package.get('raw_item_counts', {})}")
    except Exception as e:
        errors.append(f"Intel Crew pipeline: {e}")
        logger.error(f"Morning Brief — Intel Crew FAILED: {e}", exc_info=True)

    # ── A3 Moreau: Booking Operations ────────────────────────────────────
    logger.info("[Morning Brief] A3 — Payment alerts & follow-up scan...")
    try:
        alerts_sent = check_payment_alerts()
        sections.append(
            f"## OPERATIONS (A3 — Moreau)\n"
            f"  Payment alerts sent: {alerts_sent}\n"
        )
    except Exception as e:
        errors.append(f"A3 payment alerts: {e}")
        logger.error(f"Morning Brief — A3 payment alerts FAILED: {e}")

    try:
        run_followup_scan()
        sections.append("  Follow-up scan: complete — overdue items flagged\n")
    except Exception as e:
        errors.append(f"A3 follow-up scan: {e}")
        logger.error(f"Morning Brief — A3 follow-up scan FAILED: {e}")

    # ── A9 Harlan: Finance ───────────────────────────────────────────────
    logger.info("[Morning Brief] A9 — Commission pipeline status...")
    # A9's heartbeat runs inside daily_heartbeats — we capture it there

    # ── A2 Dembe: Intelligence (standalone — only if Intel Crew failed) ──
    if intel_package is None:
        logger.info("[Morning Brief] A2 — World & Ship intelligence sweeps (fallback)...")
        try:
            world_result = await run_world_intelligence_sweep()
            world_path = _save_report(
                json.dumps(world_result, indent=2),
                f"World_Intel_{ts}.json", subfolder="morning"
            )
            _upload_to_drive(world_path, DRIVE_INTEL)
            attachments.append(str(world_path))

            advisories = world_result.get("travel_advisories_total", 0)
            high_adv = world_result.get("high_level_advisories", 0)
            weather_alerts = world_result.get("weather_alerts", 0)
            news = world_result.get("news_articles", 0)
            urgent = world_result.get("urgent_news", 0)

            intel_section = (
                f"## INTELLIGENCE (A2 — Dembe)\n"
                f"  Travel advisories: {advisories} ({high_adv} high-level)\n"
                f"  Weather alerts: {weather_alerts}\n"
                f"  Cruise news: {news} articles ({urgent} urgent)\n"
            )
            if high_adv > 0:
                top_alerts = world_result.get("top_alerts", [])
                for a in top_alerts:
                    intel_section += f"  ** {a.get('country', '?')}: Level {a.get('level', '?')}\n"
            sections.append(intel_section)
        except Exception as e:
            errors.append(f"A2 world intel: {e}")
            logger.error(f"Morning Brief — A2 world intel FAILED: {e}", exc_info=True)

        try:
            ship_result = await run_ship_intelligence_sweep()
            ship_path = _save_report(
                json.dumps(ship_result, indent=2),
                f"Ship_Intel_{ts}.json", subfolder="morning"
            )
            _upload_to_drive(ship_path, DRIVE_INTEL)
            attachments.append(str(ship_path))

            voyages = ship_result.get("voyages_scraped", 0)
            price_alerts = ship_result.get("pricing_alerts", 0)
            avail_alerts = ship_result.get("availability_alerts", 0)

            sections.append(
                f"  Ship intel: {voyages} voyages tracked, "
                f"{price_alerts} pricing alerts, {avail_alerts} availability alerts\n"
            )
        except Exception as e:
            errors.append(f"A2 ship intel: {e}")
            logger.error(f"Morning Brief — A2 ship intel FAILED: {e}", exc_info=True)

    # ── Email Intelligence Sweep ─────────────────────────────────────────
    logger.info("[Morning Brief] Email Intelligence sweep (overnight emails)...")
    try:
        intel_result = run_email_intel_sweep(lookback_hours=12)
        intel_processed = intel_result.get("processed", 0)
        intel_drafts = intel_result.get("drafts_created", 0)
        intel_papers = intel_result.get("staff_papers_sent", 0)
        sections.append(
            f"## EMAIL INTELLIGENCE\n"
            f"  Emails analyzed: {intel_processed}\n"
            f"  Supplier: {intel_result.get('supplier_emails', 0)} | "
            f"Client: {intel_result.get('client_emails', 0)} | "
            f"General: {intel_result.get('general_emails', 0)}\n"
            f"  Drafts created: {intel_drafts} | Staff papers sent: {intel_papers}\n"
        )
    except Exception as e:
        errors.append(f"Email Intel: {e}")
        logger.error(f"Morning Brief — Email Intel FAILED: {e}")

    # ── A10 Ikeda: Logistics ─────────────────────────────────────────────
    logger.info("[Morning Brief] A10 — Logistics check (via daily heartbeats)...")
    # A10's heartbeat runs inside daily_heartbeats

    # ── Daily Persona Heartbeats (A2, A3, A9, A10, A6 in sequence) ──────
    logger.info("[Morning Brief] Running daily persona heartbeats...")
    try:
        run_daily_heartbeats()
        sections.append("## PERSONA HEARTBEATS\n  All daily heartbeats complete (A2, A3, A9, A10, A6)\n")
    except Exception as e:
        errors.append(f"Daily heartbeats: {e}")
        logger.error(f"Morning Brief — daily heartbeats FAILED: {e}")

    # ── COS Hale: Priority Synthesis ─────────────────────────────────────
    logger.info("[Morning Brief] COS — Priority synthesis...")
    try:
        run_cos_exec_heartbeat()
        sections.append("## PRIORITIES (COS — Hale)\n  COS-EXEC priority scan complete\n")
    except Exception as e:
        errors.append(f"COS-EXEC heartbeat: {e}")
        logger.error(f"Morning Brief — COS-EXEC heartbeat FAILED: {e}")

    # ── Branded HTML Morning Email ───────────────────────────────────────
    logger.info("[Morning Brief] Sending branded morning email...")
    try:
        result = run_morning_email_briefing(preview=False, weekly=False)
        sections.append(f"## BRANDED EMAIL\n  Morning briefing email sent: {result}\n")
    except Exception as e:
        errors.append(f"Branded morning email: {e}")
        logger.error(f"Morning Brief — branded email FAILED: {e}")

    # ── Commander Inbox Status ────────────────────────────────────────────
    try:
        from thunderbird_commander_inbox import get_inbox_briefing_line
        inbox_line = get_inbox_briefing_line()
        sections.append(f"## COMMANDER INBOX (johnloucks3)\n  {inbox_line}\n")
    except Exception as e:
        logger.debug(f"Morning Brief — Commander inbox status skipped: {e}")

    # ── Compose consolidated summary draft ───────────────────────────────
    if errors:
        error_section = "## ERRORS\n" + "\n".join(f"  ! {e}" for e in errors) + "\n"
        sections.append(error_section)

    cos_stamp = "COS-APPROVED" if intel_package else "FALLBACK-MODE"
    body = (
        f"THUNDERBIRD COMMAND BRIEF — {date_display} — {cos_stamp}\n"
        f"{'=' * 60}\n\n"
        + "\n".join(sections)
        + "\nFull intel reports attached."
    )

    _create_draft(
        subject=f"THUNDERBIRD COMMAND BRIEF // {datetime.now().strftime('%b %d')} — {cos_stamp}",
        body=body,
        attachment_paths=attachments if attachments else None,
    )

    logger.info(f"Command Brief complete — {len(sections)} sections, {len(errors)} errors, {cos_stamp}")


async def consolidated_midday_pulse():
    """
    MIDDAY PULSE (1200 daily)
    Consolidates: email_classifier (was every 15 min), payment_alerts (recheck),
                  followup_scan (recheck for overdue)
    Lightweight batch check at noon.
    """
    logger.info("=" * 60)
    logger.info("CONSOLIDATED: Midday Pulse (1200)")
    logger.info("=" * 60)
    errors = []

    # ── Email Intelligence Sweep (replaces old classifier) ───────────────
    logger.info("[Midday Pulse] Email Intelligence sweep...")
    try:
        result = run_email_intel_sweep(lookback_hours=6)
        logger.info(f"Email Intel: {result.get('processed', 0)} processed, "
                     f"{result.get('drafts_created', 0)} drafts, "
                     f"{result.get('staff_papers_sent', 0)} papers")
    except Exception as e:
        errors.append(f"Email Intel: {e}")
        logger.error(f"Midday Pulse — Email Intel FAILED: {e}")

    # ── Payment recheck (anything due today) ─────────────────────────────
    logger.info("[Midday Pulse] Payment alert recheck...")
    try:
        alerts = check_payment_alerts()
        logger.info(f"Payment alerts recheck: {alerts} sent")
    except Exception as e:
        errors.append(f"Payment alerts: {e}")
        logger.error(f"Midday Pulse — payment alerts FAILED: {e}")

    # ── Follow-up scan for overdue items ─────────────────────────────────
    logger.info("[Midday Pulse] Follow-up scan recheck...")
    try:
        run_followup_scan()
        logger.info("Follow-up scan complete")
    except Exception as e:
        errors.append(f"Follow-up scan: {e}")
        logger.error(f"Midday Pulse — follow-up scan FAILED: {e}")

    # ── SMS inbound check ────────────────────────────────────────────────
    logger.info("[Midday Pulse] SMS inbound monitor...")
    try:
        sms_result = run_sms_monitor()
        logger.info(f"SMS monitor: {sms_result.get('processed', 0)} messages processed")
    except Exception as e:
        errors.append(f"SMS monitor: {e}")
        logger.error(f"Midday Pulse — SMS monitor FAILED: {e}")

    # ── COS-EXEC midday heartbeat ────────────────────────────────────────
    logger.info("[Midday Pulse] COS-EXEC midday heartbeat...")
    try:
        run_cos_exec_heartbeat()
        logger.info("COS-EXEC midday heartbeat complete")
    except Exception as e:
        errors.append(f"COS-EXEC heartbeat: {e}")
        logger.error(f"Midday Pulse — COS-EXEC heartbeat FAILED: {e}")

    if errors:
        logger.warning(f"Midday Pulse finished with {len(errors)} errors: {errors}")
    else:
        logger.info("Midday Pulse complete — all clear")


async def consolidated_eod_summary():
    """
    END OF DAY SUMMARY (1700 daily)
    Consolidates: ship_intel (PM), tech_monitor, claude_code_digest
    Afternoon wrap with ship updates, tech news, and action items for tomorrow.
    """
    logger.info("=" * 60)
    logger.info("CONSOLIDATED: End of Day Summary (1700)")
    logger.info("=" * 60)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    sections = []
    attachments = []
    errors = []

    # ── Ship Intel PM update ─────────────────────────────────────────────
    logger.info("[EOD Summary] Ship intel PM sweep...")
    try:
        ship_result = await run_ship_intelligence_sweep()
        ship_path = _save_report(
            json.dumps(ship_result, indent=2),
            f"Ship_Intel_{ts}.json", subfolder="ship_intel"
        )
        _upload_to_drive(ship_path, DRIVE_INTEL)
        attachments.append(str(ship_path))

        voyages = ship_result.get("voyages_scraped", 0)
        price_alerts = ship_result.get("pricing_alerts", 0)
        avail_alerts = ship_result.get("availability_alerts", 0)
        sections.append(
            f"SHIP INTELLIGENCE (PM)\n"
            f"  Voyages: {voyages} | Price alerts: {price_alerts} | Avail alerts: {avail_alerts}\n"
        )
    except Exception as e:
        errors.append(f"Ship intel: {e}")
        logger.error(f"EOD Summary — ship intel FAILED: {e}", exc_info=True)

    # ── Tech Monitor ─────────────────────────────────────────────────────
    logger.info("[EOD Summary] Tech monitor sweep...")
    try:
        tech_result = await run_daily_tech_monitor()
        digest_file = tech_result.get("digest_file")
        if digest_file and Path(digest_file).exists():
            attachments.append(digest_file)
        recent = tech_result.get("recent_articles", 0)
        sections.append(f"TECH MONITOR\n  Articles (24h): {recent}\n")
    except Exception as e:
        errors.append(f"Tech monitor: {e}")
        logger.error(f"EOD Summary — tech monitor FAILED: {e}", exc_info=True)

    # ── Claude Code Digest ───────────────────────────────────────────────
    logger.info("[EOD Summary] Claude Code digest...")
    try:
        import importlib
        mod = importlib.import_module("thunderbird_claude_code_digest")
        mod.main()
        sections.append("CLAUDE CODE DIGEST\n  Generated successfully\n")
    except Exception as e:
        errors.append(f"Claude Code digest: {e}")
        logger.error(f"EOD Summary — Claude Code digest FAILED: {e}")

    # ── COS-EXEC afternoon heartbeat ─────────────────────────────────────
    logger.info("[EOD Summary] COS-EXEC afternoon heartbeat...")
    try:
        run_cos_exec_heartbeat()
        sections.append("COS-EXEC\n  Afternoon priority scan complete\n")
    except Exception as e:
        errors.append(f"COS-EXEC heartbeat: {e}")
        logger.error(f"EOD Summary — COS-EXEC heartbeat FAILED: {e}")

    # ── Compose EOD draft ────────────────────────────────────────────────
    if errors:
        sections.append("ERRORS\n" + "\n".join(f"  ! {e}" for e in errors))

    body = (
        f"THUNDERBIRD END OF DAY SUMMARY\n"
        f"{datetime.now().strftime('%A, %B %d %Y — %I:%M %p')}\n"
        f"{'=' * 50}\n\n"
        + "\n".join(sections)
        + "\nReports attached."
    )

    _create_draft(
        subject=f"Thunderbird EOD Summary — {datetime.now().strftime('%b %d')}",
        body=body,
        attachment_paths=attachments if attachments else None,
    )

    logger.info(f"EOD Summary complete — {len(sections)} sections, {len(errors)} errors")


async def consolidated_evening_sync():
    """
    EVENING SYNC (2100 daily)
    Consolidates: calendar_sync, drive_sync, rsync_to_dv7, briefing cache cleanup
    Background maintenance — no email output unless errors.
    """
    logger.info("=" * 60)
    logger.info("CONSOLIDATED: Evening Sync (2100)")
    logger.info("=" * 60)
    errors = []

    # ── Calendar sync ────────────────────────────────────────────────────
    logger.info("[Evening Sync] Calendar sync...")
    try:
        run_calendar_sync()
        logger.info("Calendar sync complete")
    except Exception as e:
        errors.append(f"Calendar sync: {e}")
        logger.error(f"Evening Sync — calendar sync FAILED: {e}")

    # ── Drive mirror ─────────────────────────────────────────────────────
    logger.info("[Evening Sync] Drive mirror...")
    try:
        run_drive_sync(full=False)
        logger.info("Drive mirror sync complete")
    except Exception as e:
        errors.append(f"Drive mirror: {e}")
        logger.error(f"Evening Sync — drive mirror FAILED: {e}")

    # ── Rsync to dv7 ────────────────────────────────────────────────────
    logger.info("[Evening Sync] Rsync to dv7...")
    try:
        await job_rsync_to_dv7()
        logger.info("Rsync to dv7 complete")
    except Exception as e:
        errors.append(f"Rsync to dv7: {e}")
        logger.error(f"Evening Sync — rsync FAILED: {e}")

    # ── Briefing dedup cache cleanup ─────────────────────────────────────
    logger.info("[Evening Sync] Briefing cache cleanup...")
    try:
        cache_file = THUNDERBIRD_DIR / "briefing_sent.json"
        if cache_file.exists():
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
            # Keep only last 7 days of hashes
            cutoff = (datetime.now() - __import__("datetime").timedelta(days=7)).isoformat()
            if isinstance(cache, dict):
                cleaned = {k: v for k, v in cache.items()
                           if isinstance(v, str) and v >= cutoff}
                cache_file.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
                removed = len(cache) - len(cleaned)
                logger.info(f"Briefing cache: removed {removed} stale entries")
    except Exception as e:
        errors.append(f"Cache cleanup: {e}")
        logger.error(f"Evening Sync — cache cleanup FAILED: {e}")

    if errors:
        _create_draft(
            subject=f"Thunderbird Evening Sync — {len(errors)} errors",
            body="Evening maintenance completed with errors:\n\n"
                 + "\n".join(f"- {e}" for e in errors),
        )
        logger.warning(f"Evening Sync finished with {len(errors)} errors")
    else:
        logger.info("Evening Sync complete — all clear, no email needed")


async def consolidated_weekly_deep_dive():
    """
    WEEKLY DEEP DIVE (Monday 0700)
    Consolidates: weekly_report, weekly_heartbeat (CH Washington),
                  nova_audit (ELON), evernote_backup
    Comprehensive Monday morning review.
    """
    logger.info("=" * 60)
    logger.info("CONSOLIDATED: Weekly Deep Dive (Monday 0700)")
    logger.info("=" * 60)
    sections = []
    errors = []

    # Batch pre-gen removed — Intel Crew handles persona pipeline in morning brief

    # ── Weekly Report ────────────────────────────────────────────────────
    logger.info("[Weekly Deep Dive] Generating weekly report...")
    try:
        await job_weekly_report()
        sections.append("WEEKLY REPORT\n  Generated and drafted successfully\n")
    except Exception as e:
        errors.append(f"Weekly report: {e}")
        logger.error(f"Weekly Deep Dive — weekly report FAILED: {e}", exc_info=True)

    # ── CH Washington Weekly Reflection ──────────────────────────────────
    logger.info("[Weekly Deep Dive] CH Washington weekly wisdom...")
    try:
        run_weekly_heartbeat()
        sections.append("CH WASHINGTON (Weekly Reflection)\n  Wisdom and morale check complete\n")
    except Exception as e:
        errors.append(f"CH Washington: {e}")
        logger.error(f"Weekly Deep Dive — CH Washington FAILED: {e}")

    # ── ELON (Nova) Weekly Audit ─────────────────────────────────────────
    logger.info("[Weekly Deep Dive] ELON Nova weekly audit...")
    try:
        result = run_nova_audit()
        tickets = result.get("tickets_created", 0) if isinstance(result, dict) else 0
        sections.append(f"NOVA AUDIT (ELON — A12)\n  System review complete: {tickets} improvement tickets\n")
    except Exception as e:
        errors.append(f"Nova audit: {e}")
        logger.error(f"Weekly Deep Dive — Nova audit FAILED: {e}")

    # ── Voice Profile Refresh (weekly) ────────────────────────────────────
    logger.info("[Weekly Deep Dive] Refreshing Commander voice profile...")
    try:
        voice_result = refresh_voice_profile(months_back=1)
        emails_analyzed = voice_result.get("emails_analyzed", 0)
        sections.append(
            f"VOICE PROFILE REFRESH\n"
            f"  Analyzed {emails_analyzed} sent emails, profile updated\n"
        )
    except Exception as e:
        errors.append(f"Voice profile: {e}")
        logger.error(f"Weekly Deep Dive — voice profile FAILED: {e}")

    # ── Evernote + USB Backup ────────────────────────────────────────────
    logger.info("[Weekly Deep Dive] Evernote + USB code backup...")
    try:
        result = run_evernote_backup()
        sections.append(f"EVERNOTE BACKUP\n  Code archive complete: {result}\n")
    except Exception as e:
        errors.append(f"Evernote backup: {e}")
        logger.error(f"Weekly Deep Dive — Evernote backup FAILED: {e}")

    # ── Summary draft ────────────────────────────────────────────────────
    if errors:
        sections.append("ERRORS\n" + "\n".join(f"  ! {e}" for e in errors))

    body = (
        f"THUNDERBIRD WEEKLY DEEP DIVE\n"
        f"{datetime.now().strftime('%A, %B %d %Y')}\n"
        f"{'=' * 50}\n\n"
        + "\n".join(sections)
    )

    _create_draft(
        subject=f"Thunderbird Weekly Deep Dive — {datetime.now().strftime('%b %d, %Y')}",
        body=body,
    )

    logger.info(f"Weekly Deep Dive complete — {len(sections)} sections, {len(errors)} errors")


# ============================================================================
# SCHEDULER SETUP — CONSOLIDATED (5 jobs + SMS monitor)
# ============================================================================

def build_scheduler() -> AsyncIOScheduler:
    """Configure and return the scheduler with 5 consolidated jobs + SMS monitor.

    Replaces the original 18 individual jobs. See build_scheduler_legacy()
    for the original configuration (preserved for rollback).
    """
    scheduler = AsyncIOScheduler(timezone=TZ)

    # 0. SMS Inbound Monitor: every 10 min, 24/7
    #    Polls Gmail for inbound SMS-to-email, parses persona prefix, routes
    async def job_sms_monitor():
        logger.info("SMS Monitor: checking inbound texts...")
        try:
            result = run_sms_monitor()
            processed = result.get('processed', 0) if isinstance(result, dict) else 0
            if processed > 0:
                logger.info(f"SMS Monitor: {processed} messages processed")
        except Exception as e:
            logger.error(f"SMS Monitor FAILED: {e}")

    scheduler.add_job(job_sms_monitor,
                      CronTrigger(minute="*/10", timezone=TZ),
                      id="sms_monitor", name="SMS Inbound Monitor (every 10m, 24/7)")

    # 0b. Concierge Email Monitor: every 10 min, 24/7
    #     Polls for inbound replies to concierge@d2mluxury.quest,
    #     classifies, drafts replies via Dani (A3), alerts Commander.
    #     Also processes Commander directives sent to Dani.
    async def job_concierge_monitor():
        logger.info("Concierge Monitor: checking inbound emails...")
        try:
            processed = run_concierge_monitor()
            if processed > 0:
                logger.info(f"Concierge Monitor: {processed} client messages processed")
        except Exception as e:
            logger.error(f"Concierge Monitor (client poll) FAILED: {e}")
        # FIX 2026-03-16: Commander directives were never polled by scheduler.
        # The module's own job_concierge_monitor() calls both poll_once() AND
        # poll_commander_directives(), but the scheduler defined its own wrapper
        # that only called poll_once(). Commander emails to Dani were silently dropped.
        try:
            cmd_processed = run_commander_directives()
            if cmd_processed > 0:
                logger.info(f"Concierge Monitor: {cmd_processed} Commander directive(s) processed")
        except Exception as e:
            logger.error(f"Concierge Monitor (Commander directives) FAILED: {e}")

    scheduler.add_job(job_concierge_monitor,
                      CronTrigger(minute="*/10", timezone=TZ),
                      id="concierge_monitor", name="Concierge Email Monitor (every 10m, 24/7)")

    # 0b1. Session Auto-Save Checkpoint: every 10 min, active hours (0800-2300 MT)
    #      Standing Order 2026-03-16 — COS writes session_autosave_latest.md every 10 min.
    #      Captures: recent git commits, uncommitted files, SSS pending decisions,
    #      learning rules pending validation, recent Telegram C2 log tail, open TODOs,
    #      recently touched dossiers. Prevents continuity loss from battery/power flux.
    from thunderbird_session_checkpoint import job_session_checkpoint

    scheduler.add_job(job_session_checkpoint,
                      CronTrigger(minute="*/10", hour="8-23", timezone=TZ),
                      id="session_checkpoint", name="Session Auto-Save Checkpoint (every 10m, 0800-2300 MT)")

    # 0b2. Dani Email Sweep: every 30 min, 24/7
    #       FIX 2026-03-16: Dani email responder was never scheduled.
    #       Scans d2mconcierge@gmail.com inbox for client emails (not just
    #       concierge@), drafts Dani responses via COS review, notifies Commander.
    async def job_dani_email_sweep():
        logger.info("Dani Email Sweep: scanning inbox for client emails...")
        try:
            result = run_dani_email_sweep()
            drafted = result.get("drafts_created", 0) if isinstance(result, dict) else 0
            found = result.get("emails_found", 0) if isinstance(result, dict) else 0
            if drafted > 0:
                logger.info(f"Dani Email Sweep: {drafted} drafts created from {found} emails")
            elif found > 0:
                logger.info(f"Dani Email Sweep: {found} emails found, 0 new drafts")
        except Exception as e:
            logger.error(f"Dani Email Sweep FAILED: {e}")

    scheduler.add_job(job_dani_email_sweep,
                      CronTrigger(minute="*/30", timezone=TZ),
                      id="dani_email_sweep", name="Dani Email Sweep (every 30m, 24/7)")

    # 0b3. Commander Inbox Scanner: every 2 hours, business hours (0800–2000 MT)
    #       Scans johnloucks3@gmail.com for D2M-relevant emails (client inquiries,
    #       vendor comms, booking confirmations, financial, intel). Tasks to Wing
    #       personas, creates reply drafts in d2mconcierge, notifies COS via Telegram.
    #       Personal / noise emails are silently skipped.
    #       No-ops gracefully if gmail_token_commander.json doesn't exist.
    async def job_commander_inbox():
        """Sweep Commander's personal inbox for D2M-relevant emails."""
        from thunderbird_commander_inbox import run_commander_inbox_sweep
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_commander_inbox_sweep)
        logger.info(f"Commander inbox sweep: {result}")

    scheduler.add_job(job_commander_inbox,
                      CronTrigger(hour="8,10,12,14,16,18,20", minute=15, timezone=TZ),
                      id="commander_inbox", name="Commander Inbox Scanner (every 2h, 0800-2000 MT)")

    # 0c. Concierge Big Picture: every 6 hours, 24/7
    #     Reviews full thread context, unresolved directives, pending tasks
    from thunderbird_concierge_monitor import poll_big_picture as run_big_picture
    async def job_concierge_big_picture():
        logger.info("Concierge Big Picture: 6-hour lookback review...")
        try:
            run_big_picture()
            logger.info("Concierge Big Picture: review complete")
        except Exception as e:
            logger.error(f"Concierge Big Picture FAILED: {e}")

    scheduler.add_job(job_concierge_big_picture,
                      CronTrigger(hour="0,6,12,18", minute=15, timezone=TZ),
                      id="concierge_big_picture", name="Concierge Big Picture (every 6h, 24/7)")

    # (Groq eliminated — Claude Opus handles all model calls via Max plan)

    # 1. Morning Brief: 6:30AM daily
    #    Replaces: morning_briefing, daily_heartbeats, branded_morning_email,
    #              payment_alerts, followup_scan, world_intel (AM), ship_intel (AM)
    #    Now also collects Claude Opus persona results (submitted at 0600).
    scheduler.add_job(consolidated_morning_brief,
                      CronTrigger(hour=6, minute=31, timezone=TZ),
                      id="morning_brief", name="Morning Brief (0631)",
                      misfire_grace_time=300)

    # 2. Midday Pulse: 12:00PM daily
    #    Replaces: email_classifier (was every 15min), payment recheck, followup recheck
    scheduler.add_job(consolidated_midday_pulse,
                      CronTrigger(hour=12, minute=0, timezone=TZ),
                      id="midday_pulse", name="Midday Pulse (1200)")

    # 3. End of Day Summary: 5:00PM daily
    #    Replaces: ship_intel (PM), tech_monitor, claude_code_digest
    scheduler.add_job(consolidated_eod_summary,
                      CronTrigger(hour=17, minute=0, timezone=TZ),
                      id="eod_summary", name="EOD Summary (1700)")

    # 4. Evening Sync: 9:00PM daily
    #    Replaces: calendar_sync, drive_sync, drive_backup, rsync_to_dv7
    scheduler.add_job(consolidated_evening_sync,
                      CronTrigger(hour=21, minute=0, timezone=TZ),
                      id="evening_sync", name="Evening Sync (2100)")

    # 5. Weekly Deep Dive: Monday 7:00AM
    #    Replaces: weekly_report, weekly_heartbeat (CH), nova_audit, evernote_backup
    #    Now also collects Claude Opus persona results (submitted at Mon 0630).
    scheduler.add_job(consolidated_weekly_deep_dive,
                      CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=TZ),
                      id="weekly_deep_dive", name="Weekly Deep Dive (Mon 0700)")

    # 6. Overwatch Sentinel: every 5 min business hours, every 60 min off-hours
    #    Layer 1 quality control — dossier currency, commission math, deadlines,
    #    format compliance, output completeness. Red flags escalate to Judge.
    async def job_sentinel_sweep():
        logger.info("Overwatch Sentinel: running sweep...")
        try:
            report = run_sentinel_sweep(use_llm=False)
            reds = sum(1 for c in report.checks if c.status.value == "RED")
            if reds > 0:
                logger.warning(f"Overwatch Sentinel: {reds} RED flag(s) — escalating to Judge")
                try:
                    run_judge_assessment(trigger="sentinel_escalation")
                except Exception as je:
                    logger.error(f"Overwatch Judge escalation FAILED: {je}")
            else:
                logger.info(f"Overwatch Sentinel: sweep complete — {len(report.checks)} checks, 0 RED")
        except Exception as e:
            logger.error(f"Overwatch Sentinel FAILED: {e}")

    # Business hours: every 5 min (0700-1900 MT)
    scheduler.add_job(job_sentinel_sweep,
                      CronTrigger(minute="*/5", hour="7-18", timezone=TZ),
                      id="overwatch_sentinel_biz", name="Overwatch Sentinel (5min, biz hours)")

    # Off-hours: every 60 min (1900-0659 MT)
    scheduler.add_job(job_sentinel_sweep,
                      CronTrigger(minute=0, hour="0-6,19-23", timezone=TZ),
                      id="overwatch_sentinel_off", name="Overwatch Sentinel (60min, off-hours)")

    # 7. Overwatch Judge: daily at 0600 MT
    #    Layer 2 leadership judgment — tone, morale, corrective action, strategic review
    async def job_judge_daily():
        logger.info("Overwatch Judge: running daily assessment...")
        try:
            report = run_judge_assessment(trigger="daily_0600")
            logger.info(f"Overwatch Judge: daily assessment complete")
        except Exception as e:
            logger.error(f"Overwatch Judge FAILED: {e}")

    scheduler.add_job(job_judge_daily,
                      CronTrigger(hour=6, minute=0, timezone=TZ),
                      id="overwatch_judge_daily", name="Overwatch Judge (daily 0600)")

    # 8. OA Portal Monitor: every 30 min during business hours (7AM-9PM MT)
    #    Checks Odysseus bookings, TESS commissions, and client portal activity.
    #    Diffs against saved state and sends Telegram alerts on changes.
    #    Requires Chrome CDP running with John logged into portals.
    async def job_oa_portal_monitor():
        logger.info("=" * 60)
        logger.info("SCHEDULED: OA Portal Monitor")
        logger.info("=" * 60)
        import hashlib
        changes = []

        try:
            browser, ctx = await _connect_cdp()
        except Exception as e:
            logger.warning(f"OA Portal Monitor: Chrome CDP not available — {e}")
            return

        # --- Check Odysseus Bookings ---
        try:
            page = await _find_portal_tab(ctx, "odysseus")
            if page:
                await page.goto(ODY_BOOKINGS, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                text = await page.evaluate("document.body.innerText")
                current_hash = hashlib.md5(text.encode()).hexdigest()
                previous = _load_state("bookings_monitor")
                if previous.get("text_hash") and current_hash != previous["text_hash"]:
                    changes.append("📋 *Booking data changed* in Odysseus")
                _save_state("bookings_monitor", {
                    "text_hash": current_hash,
                    "checked_at": datetime.now().isoformat(),
                    "text_preview": text[:500],
                })
                logger.info(f"OA Monitor: Bookings checked (hash={current_hash[:8]})")
            else:
                logger.info("OA Monitor: No Odysseus tab open — skipping bookings check")
        except Exception as e:
            logger.error(f"OA Monitor bookings check failed: {e}")

        # --- Check TESS Commissions ---
        try:
            page = await _find_portal_tab(ctx, "tess")
            if page:
                await page.goto(TESS_COMMISSIONS, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)
                text = await page.evaluate("document.body.innerText")
                current_hash = hashlib.md5(text.encode()).hexdigest()
                previous = _load_state("commissions_monitor")
                if previous.get("text_hash") and current_hash != previous["text_hash"]:
                    changes.append("💰 *Commission data changed* in TESS")
                _save_state("commissions_monitor", {
                    "text_hash": current_hash,
                    "checked_at": datetime.now().isoformat(),
                    "text_preview": text[:500],
                })
                logger.info(f"OA Monitor: Commissions checked (hash={current_hash[:8]})")
        except Exception as e:
            logger.error(f"OA Monitor commissions check failed: {e}")

        # --- Check Client Portal Activity ---
        try:
            page = await _find_portal_tab(ctx, "tess")
            if page:
                await page.goto(TESS_CLIENTS, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
                client_data = await page.evaluate("""
                    () => {
                        const rows = document.querySelectorAll('tr, .client-row, [class*="client"]');
                        const clients = [];
                        for (const row of rows) {
                            const text = row.innerText.trim();
                            if (text.length > 5 && text.length < 500) {
                                clients.push(text.replace(/\\n/g, ' | '));
                            }
                        }
                        return clients.slice(0, 50);
                    }
                """)
                current_hash = hashlib.md5(json.dumps(client_data).encode()).hexdigest()
                previous = _load_state("clients_monitor")
                if previous.get("data_hash") and current_hash != previous["data_hash"]:
                    old_set = set(previous.get("clients", []))
                    new_set = set(client_data)
                    added = new_set - old_set
                    detail = f"({len(added)} new/modified entries)" if added else "(content changed)"
                    changes.append(f"👤 *Client portal activity detected* {detail}")
                _save_state("clients_monitor", {
                    "data_hash": current_hash,
                    "clients": client_data,
                    "checked_at": datetime.now().isoformat(),
                })
                logger.info(f"OA Monitor: Clients checked (hash={current_hash[:8]})")
        except Exception as e:
            logger.error(f"OA Monitor client check failed: {e}")

        # --- Send Telegram Alert ---
        if changes:
            msg = "🔔 *OA Portal Changes Detected*\n\n" + "\n".join(changes)
            msg += f"\n\n_Checked at {datetime.now().strftime('%H:%M %b %d')}_"
            _notify_commander(msg)
            logger.info(f"OA Monitor: {len(changes)} changes detected — Commander notified")
        else:
            logger.info("OA Monitor: No changes detected")

    scheduler.add_job(job_oa_portal_monitor,
                      CronTrigger(hour="7-21", minute="*/30", timezone=TZ),
                      id="oa_portal_monitor", name="OA Portal Monitor (30min)")

    # 9. SWITCHBLADE-4: daily at 7:00AM MT
    #    Automated Dani stress test — technical + persona + COS review + staff.
    #    Results sent to Telegram + Gmail draft.
    async def job_switchblade():
        logger.info("=" * 60)
        logger.info("SCHEDULED: SWITCHBLADE-4 — Dani Stress Test")
        logger.info("=" * 60)
        try:
            report = run_switchblade(send_telegram=True, send_gmail=True)
            rate = report.get("pass_rate", "?")
            crit = report.get("critical_failures", 0)
            logger.info(f"SWITCHBLADE-4 complete: {rate}, {crit} critical failures")
        except Exception as e:
            logger.error(f"SWITCHBLADE-4 FAILED: {e}", exc_info=True)

    scheduler.add_job(job_switchblade,
                      CronTrigger(hour=7, minute=0, timezone=TZ),
                      id="switchblade_daily", name="SWITCHBLADE-4 Dani Test (daily 0700)")

    # 9b. SWITCHBLADE-4 overnight run: 3:00AM MT (0900 UTC)
    #     Docstring-specified early-morning run to catch overnight data drift.
    #     Same job function as the 0700 run — separate ID for independent tracking.
    scheduler.add_job(job_switchblade,
                      CronTrigger(hour=3, minute=0, timezone=TZ),
                      id="switchblade_0300", name="SWITCHBLADE-4 Dani Test (0300 MT)")

    # 10. Flight Price Tracker: daily at 9:00AM MT
    #    Searches Google Flights via Playwright for configured routes.
    #    Compares to previous best price, sends Telegram + Gmail on changes.
    #    Config stored in ~/Thunderbird/flight_watch.json
    async def job_flight_price_tracker():
        logger.info("=" * 60)
        logger.info("SCHEDULED: Flight Price Tracker")
        logger.info("=" * 60)
        try:
            await _run_flight_price_check()
        except Exception as e:
            logger.error(f"Flight Price Tracker FAILED: {e}", exc_info=True)

    scheduler.add_job(job_flight_price_tracker,
                      CronTrigger(hour=9, minute=0, timezone=TZ),
                      id="flight_price_tracker", name="Flight Price Tracker (daily 0900)")

    # 11. Airline Alert Scan: every 2 hours during business hours
    #     Fast airline-only scan — checks for client-impacting route changes.
    #     Immediate Telegram alert if match found.
    async def job_airline_alert_scan():
        logger.info("AIRLINE SCAN: Checking for client-impacting route changes...")
        try:
            from thunderbird_airline_monitor import run_airline_scan
            result = await run_airline_scan(alert=True)
            impacts = result.get("client_impacts", 0)
            if impacts > 0:
                logger.warning(f"AIRLINE SCAN: {impacts} client impacts detected — alerts sent")
            else:
                logger.info(f"AIRLINE SCAN: {result.get('articles_scanned', 0)} articles, no client impacts")
        except Exception as e:
            logger.error(f"AIRLINE SCAN FAILED: {e}")

    scheduler.add_job(job_airline_alert_scan,
                      CronTrigger(hour="7-21/2", minute=30, timezone=TZ),
                      id="airline_alert_scan", name="Airline Alert Scan (every 2h, biz hours)")

    # 12. Learning Extraction: daily at 6:30AM MT
    #     Processes recent Commander corrections and extracts voice/style principles.
    #     Feeds the "Capture the Diff → Extract the Principle → Apply Forward" loop.
    async def job_learning_extraction():
        logger.info("=" * 60)
        logger.info("SCHEDULED: Learning Extraction")
        logger.info("=" * 60)
        try:
            from thunderbird_learning import extract_principles
            results = extract_principles()
            logger.info(f"Learning Extraction complete: {len(results)} principles extracted")
        except Exception as e:
            logger.error(f"Learning Extraction FAILED: {e}", exc_info=True)

    scheduler.add_job(job_learning_extraction,
                      CronTrigger(hour=6, minute=30, timezone=TZ),
                      id="learning_extraction", name="Learning Extraction (daily 0630)")

    # 13. Dossier Scanner: daily at 6:45AM MT
    #     Scans all client dossiers for gaps, stale data, missing fields.
    #     Logs alert count for COS morning brief.
    async def job_dossier_scanner():
        logger.info("=" * 60)
        logger.info("SCHEDULED: Dossier Scanner")
        logger.info("=" * 60)
        try:
            from thunderbird_dossier_scanner import scan_all_dossiers, generate_alert_digest
            alerts = scan_all_dossiers()
            logger.info(f"Dossier Scanner complete: {len(alerts)} alerts found")
            if alerts:
                digest = generate_alert_digest()
                logger.info(f"Dossier alert digest:\n{digest}")
        except Exception as e:
            logger.error(f"Dossier Scanner FAILED: {e}", exc_info=True)

    scheduler.add_job(job_dossier_scanner,
                      CronTrigger(hour=6, minute=45, timezone=TZ),
                      id="dossier_scanner", name="Dossier Scanner (daily 0645)")

    # 14. Intel Crew: daily at 5:45AM MT — runs BEFORE the 6:31 morning brief
    #     A2 Dembe (COLLECT) → A2 Dembe (ANALYZE) → A1 Radar (AUDIT) → COS Hale (REVIEW)
    #     Produces intel_package saved to output/intel_crew/ for consolidated_morning_brief.
    async def job_intel_crew():
        """Daily intel crew run — A2 analysis + COS synthesis."""
        logger.info("=" * 60)
        logger.info("SCHEDULED: Intel Crew Pipeline (A2→A1→COS)")
        logger.info("=" * 60)
        try:
            from thunderbird_intel_crew import IntelCrew
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, IntelCrew().run)
            counts = result.get("raw_item_counts", {})
            status = result.get("status", "UNKNOWN")
            logger.info(f"Intel crew complete: status={status}, counts={counts}")
        except Exception as e:
            logger.error(f"Intel Crew FAILED: {e}", exc_info=True)

    scheduler.add_job(job_intel_crew,
                      CronTrigger(hour=5, minute=45, timezone=TZ),
                      id="intel_crew_daily", name="Intel Crew Pipeline (daily 0545)")

    return scheduler


# ============================================================================
# FLIGHT PRICE TRACKER
# ============================================================================

FLIGHT_WATCH_FILE = THUNDERBIRD_DIR / "flight_watch.json"
FLIGHT_WATCH_STATE = THUNDERBIRD_DIR / "output" / "flight_watch_state.json"

def _load_flight_watches() -> list:
    """Load active flight watches from config."""
    if not FLIGHT_WATCH_FILE.exists():
        return []
    try:
        data = json.loads(FLIGHT_WATCH_FILE.read_text(encoding="utf-8"))
        return data.get("watches", [])
    except Exception as e:
        logger.error(f"Failed to load flight watches: {e}")
        return []

def _load_flight_state() -> dict:
    """Load previous price state."""
    if not FLIGHT_WATCH_STATE.exists():
        return {}
    try:
        return json.loads(FLIGHT_WATCH_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_flight_state(state: dict):
    """Save price state."""
    FLIGHT_WATCH_STATE.parent.mkdir(parents=True, exist_ok=True)
    FLIGHT_WATCH_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


async def _run_flight_price_check():
    """Search Google Flights for all watched routes, compare prices, notify."""
    import requests as _req

    watches = _load_flight_watches()
    if not watches:
        logger.info("Flight Price Tracker: no active watches configured")
        return

    state = _load_flight_state()

    # Initialize MCP session for Playwright
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    init_resp = _req.post("http://localhost:8765/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "flight-tracker", "version": "1.0"},
        }
    }, headers=headers, timeout=15)

    sid = init_resp.headers.get("mcp-session-id", "")
    if sid:
        headers["mcp-session-id"] = sid

    _req.post("http://localhost:8765/mcp", json={
        "jsonrpc": "2.0", "method": "notifications/initialized"
    }, headers=headers, timeout=10)

    results = []

    for watch in watches:
        origin = watch["origin"]
        dest = watch["destination"]
        date = watch["date"]
        pax = watch.get("passengers", 2)
        label = watch.get("label", f"{origin}→{dest}")
        filters = watch.get("filters", {})
        min_dep_hour = filters.get("min_departure_hour", 0)
        max_layover_min = filters.get("max_layover_minutes", 999)

        gf_url = (
            f"https://www.google.com/travel/flights?"
            f"q=Flights%20from%20{origin}%20to%20{dest}%20on%20{date}"
            f"%20one%20way%20{pax}%20passengers&curr=USD"
        )

        logger.info(f"Flight Tracker: searching {origin}→{dest} on {date} ({pax} pax)...")

        try:
            resp = _req.post("http://localhost:8765/mcp", json={
                "jsonrpc": "2.0", "id": 100, "method": "tools/call",
                "params": {"name": "browse_url", "arguments": {
                    "url": gf_url,
                    "extract": "text",
                    "wait_seconds": 12,
                    "screenshot": True,
                    "scroll": True,
                    "max_length": 20000,
                }}
            }, headers=headers, timeout=120)

            mcp_result = resp.json()
            page_text = ""
            for item in mcp_result.get("result", {}).get("content", []):
                if isinstance(item, dict) and item.get("type") == "text":
                    data = json.loads(item["text"])
                    page_text = data.get("text", "")

            if not page_text:
                logger.warning(f"Flight Tracker: empty response for {label}")
                continue

            # Parse flight offers from Google Flights text
            flights = _parse_google_flights_text(page_text, min_dep_hour, max_layover_min)

            if not flights:
                logger.info(f"Flight Tracker: no matching flights for {label}")
                results.append({"label": label, "flights": [], "note": "No matching flights found"})
                continue

            # Compare to previous best
            watch_key = f"{origin}-{dest}-{date}"
            prev = state.get(watch_key, {})
            prev_best = prev.get("best_price")
            current_best = flights[0]["price"] if flights else None

            price_change = ""
            if prev_best and current_best:
                diff = current_best - prev_best
                if diff < -5:
                    price_change = f"📉 DOWN ${abs(diff):.0f} (was ${prev_best:.0f})"
                elif diff > 5:
                    price_change = f"📈 UP ${diff:.0f} (was ${prev_best:.0f})"
                else:
                    price_change = f"➡️ STABLE (${current_best:.0f})"
            elif current_best:
                price_change = f"🆕 First check: ${current_best:.0f}"

            # Update state
            state[watch_key] = {
                "best_price": current_best,
                "checked_at": datetime.now().isoformat(),
                "flight_count": len(flights),
                "top_3": flights[:3],
            }

            results.append({
                "label": label,
                "flights": flights[:5],
                "price_change": price_change,
                "best_price": current_best,
            })

            logger.info(f"Flight Tracker: {label} — {len(flights)} flights, best ${current_best:.0f} {price_change}")

        except Exception as e:
            logger.error(f"Flight Tracker: {label} search failed: {e}")
            results.append({"label": label, "error": str(e)})

    _save_flight_state(state)

    # Build notification
    if results:
        _send_flight_report(results, watches)


def _parse_google_flights_text(text: str, min_dep_hour: int = 0, max_layover_min: int = 999) -> list:
    """Parse Google Flights page text into structured flight data.

    Google Flights text format (each flight is a block of lines):
        6:30 AM           <- departure time
         –
        10:15 PM          <- arrival time (may have +1)
        Southwest         <- airline (may include "Operated by...")
        14 hr 45 min      <- total duration
        SEA–COS           <- route
        2 stops           <- or "1 stop" or "Nonstop"
        PHX, DEN          <- or "50 min LAS" or "2 hr 22 min DFW"
        577 kg CO2e       <- emissions (skip)
        +12% emissions    <- (skip)
        2                 <- bags? (skip)
        0                 <- (skip)
        $190              <- price for all passengers
    """
    import re
    flights = []
    lines = text.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for departure time line: "6:30 AM" or "11:05 AM"
        dep_match = re.match(r'^(\d{1,2}:\d{2}\s+[AP]M)\s*$', line)
        if not dep_match:
            i += 1
            continue

        dep_time = dep_match.group(1).strip()

        # Parse departure hour for filtering
        dh_match = re.match(r'(\d{1,2}):(\d{2})\s+([AP]M)', dep_time)
        if dh_match:
            dep_hour = int(dh_match.group(1))
            if dh_match.group(3) == "PM" and dep_hour != 12:
                dep_hour += 12
            if dh_match.group(3) == "AM" and dep_hour == 12:
                dep_hour = 0
        else:
            i += 1
            continue

        # Collect the next ~15 lines as the flight block
        block_lines = []
        for j in range(i + 1, min(len(lines), i + 16)):
            block_lines.append(lines[j].strip())

        # Skip " –" separator, get arrival time
        arr_time = ""
        offset = 0
        for bl in block_lines:
            offset += 1
            if bl in ("–", "-", ""):
                continue
            arr_match = re.match(r'^(\d{1,2}:\d{2}\s+[AP]M(?:\+\d)?)\s*$', bl)
            if arr_match:
                arr_time = arr_match.group(1).strip()
                break

        if not arr_time:
            i += 1
            continue

        # Remaining lines after arrival
        rest = block_lines[offset:]

        # Airline (first non-empty line after arrival)
        airline = ""
        airline_names = ["Southwest", "United", "Delta", "American", "Alaska",
                         "Frontier", "Spirit", "JetBlue", "Hawaiian", "Sun Country"]
        for bl in rest:
            if not bl:
                continue
            for name in airline_names:
                if name.lower() in bl.lower():
                    airline = name
                    break
            if airline:
                rest = rest[rest.index(bl) + 1:]
                break

        # Duration: "5 hr 15 min" or "14 hr 45 min"
        duration = ""
        for bl in rest:
            dur_match = re.match(r'^(\d+)\s+hr\s+(\d+)\s+min$', bl)
            if dur_match:
                duration = f"{dur_match.group(1)}h{dur_match.group(2)}m"
                rest = rest[rest.index(bl) + 1:]
                break

        # Route: "SEA–COS"
        route = ""
        for bl in rest:
            route_match = re.match(r'^([A-Z]{3})[–-]([A-Z]{3})$', bl)
            if route_match:
                route = bl
                rest = rest[rest.index(bl) + 1:]
                break

        # Stops: "Nonstop", "1 stop", "2 stops"
        stops = "unknown"
        for bl in rest:
            if bl.lower() == "nonstop":
                stops = "nonstop"
                rest = rest[rest.index(bl) + 1:]
                break
            stop_match = re.match(r'^(\d)\s+stops?$', bl)
            if stop_match:
                stops = f"{stop_match.group(1)} stop"
                rest = rest[rest.index(bl) + 1:]
                break

        # Layover info: "50 min LAS" or "2 hr 22 min DFW" or "PHX, DEN"
        layover_airport = ""
        layover_min_val = 0
        if stops != "nonstop" and rest:
            lay_line = rest[0] if rest else ""
            # Pattern: "50 min LAS"
            lm = re.match(r'^(\d+)\s+min\s+([A-Z]{3})$', lay_line)
            if lm:
                layover_min_val = int(lm.group(1))
                layover_airport = lm.group(2)
            else:
                # Pattern: "2 hr 22 min DFW"
                lh = re.match(r'^(\d+)\s+hr\s+(\d+)\s+min\s+([A-Z]{3})$', lay_line)
                if lh:
                    layover_min_val = int(lh.group(1)) * 60 + int(lh.group(2))
                    layover_airport = lh.group(3)
                else:
                    # Pattern: "PHX, DEN" (multi-stop, no time given)
                    multi = re.match(r'^([A-Z]{3}(?:,\s*[A-Z]{3})+)$', lay_line)
                    if multi:
                        layover_airport = lay_line

        # Price: find "$XXX" in remaining lines
        price = 0
        for bl in rest:
            price_match = re.match(r'^\$(\d[\d,]*)$', bl)
            if price_match:
                price = float(price_match.group(1).replace(",", ""))
                break

        if price <= 0:
            i += 1
            continue

        # Apply filters
        if dep_hour < min_dep_hour:
            i += 1
            continue

        if max_layover_min < 999 and layover_min_val > max_layover_min and layover_min_val > 0:
            i += 1
            continue

        flights.append({
            "departure": dep_time,
            "arrival": arr_time,
            "airline": airline,
            "duration": duration,
            "stops": stops,
            "layover_airport": layover_airport,
            "layover_minutes": layover_min_val,
            "route": route,
            "price": price,
        })

        i += 1

    # Sort by price
    flights.sort(key=lambda x: x["price"])
    return flights


def _send_flight_report(results: list, watches: list):
    """Send flight price report via Telegram and Gmail draft."""
    ts = datetime.now().strftime("%b %d, %Y %I:%M %p")

    # Build Telegram message
    tg_lines = [f"✈️ *Daily Flight Price Report*", f"_{ts}_\n"]

    for r in results:
        label = r["label"]
        tg_lines.append(f"*{label}*")

        if r.get("error"):
            tg_lines.append(f"  ⚠️ Search failed: {r['error']}")
            continue

        if r.get("price_change"):
            tg_lines.append(f"  {r['price_change']}")

        flights = r.get("flights", [])
        if not flights:
            tg_lines.append("  No matching flights found")
            continue

        for i, f in enumerate(flights[:5], 1):
            lay = f""
            if f.get("layover_airport"):
                h, m = divmod(f["layover_minutes"], 60)
                lay = f" ({h}h{m:02d}m {f['layover_airport']})"
            tg_lines.append(
                f"  {i}. {f['airline']} {f['departure']}→{f['arrival']} "
                f"{f['stops']}{lay} {f['duration']} *${f['price']:.0f}*"
            )
        tg_lines.append("")

    tg_msg = "\n".join(tg_lines)

    # Send Telegram
    try:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        commander_id = os.environ.get("TELEGRAM_COMMANDER_ID", "")
        if bot_token and commander_id:
            import requests as _req
            _req.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": commander_id, "text": tg_msg, "parse_mode": "Markdown"},
                timeout=15,
            )
            logger.info("Flight Tracker: Telegram notification sent")
        else:
            logger.warning("Flight Tracker: Telegram env vars not set")
    except Exception as e:
        logger.error(f"Flight Tracker Telegram failed: {e}")

    # Create Gmail draft
    try:
        email_body = tg_msg.replace("*", "").replace("_", "")
        _create_draft(
            subject=f"Flight Price Report — {datetime.now().strftime('%b %d')}",
            body=email_body,
        )
        logger.info("Flight Tracker: Gmail draft created")
    except Exception as e:
        logger.error(f"Flight Tracker Gmail draft failed: {e}")


async def job_fare_watch_check():
    """Fare Watch — runs 2x daily (8AM + 4PM MT). Logs all active watches; alerts on price drops/spikes."""
    logger.info("=" * 60)
    logger.info("SCHEDULED: Fare Watch Check")
    logger.info("=" * 60)
    try:
        result = fw_list_watches(active_only=True)
        watches = result.get("watches", [])
        count = result.get("count", 0)

        if count == 0:
            logger.info("Fare Watch: no active watches, skipping")
            return

        logger.info(f"Fare Watch: checking {count} active watch(es)")

        # Collect any watches with triggered alerts (price vs alert thresholds)
        alert_lines = []
        for w in watches:
            label = w.get("label", w.get("id", "unknown"))
            vs_baseline = w.get("vs_baseline", "")
            last_checked = w.get("last_checked", "never")
            logger.info(
                f"  {label} | {w.get('price_pp', '?')}/pp | {w.get('total', '?')} | "
                f"vs baseline: {vs_baseline} | last checked: {last_checked}"
            )
            # Flag any watch that has moved negatively vs baseline (price up = bad for client)
            if vs_baseline.startswith("+"):
                alert_lines.append(f"  SPIKE  {label}: {w.get('price_pp')} ({vs_baseline} vs baseline)")
            elif vs_baseline.startswith("-"):
                alert_lines.append(f"  DROP   {label}: {w.get('price_pp')} ({vs_baseline} vs baseline)")

        ts = datetime.now().strftime("%Y%m%d_%H%M")

        # Always save a snapshot log
        report_path = _save_report(
            json.dumps(result, indent=2),
            f"Fare_Watch_{ts}.json",
            subfolder="fare_watch"
        )

        # Telegram alert if any price movement detected
        if alert_lines:
            try:
                bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
                commander_id = os.environ.get("TELEGRAM_COMMANDER_ID", "")
                if bot_token and commander_id:
                    import requests as _req
                    tg_body = (
                        f"*Fare Watch Alert* — {datetime.now().strftime('%b %d %I:%M %p MT')}\n"
                        f"{count} active watch(es)\n\n"
                        + "\n".join(alert_lines)
                    )
                    _req.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": commander_id, "text": tg_body, "parse_mode": "Markdown"},
                        timeout=15,
                    )
                    logger.info(f"Fare Watch: Telegram alert sent ({len(alert_lines)} movement(s))")
                else:
                    logger.warning("Fare Watch: Telegram env vars not set, skipping notification")
            except Exception as e:
                logger.error(f"Fare Watch Telegram failed: {e}")

            # Gmail draft on alerts
            try:
                _create_draft(
                    subject=f"Fare Watch Alert — {len(alert_lines)} price movement(s) ({datetime.now().strftime('%b %d')})",
                    body=(
                        f"Fare Watch automated check completed.\n\n"
                        f"Active watches: {count}\n"
                        f"Price movements detected: {len(alert_lines)}\n\n"
                        + "\n".join(alert_lines)
                        + f"\n\nFull snapshot attached."
                    ),
                    attachment_paths=[str(report_path)],
                )
                logger.info("Fare Watch: Gmail alert draft created")
            except Exception as e:
                logger.error(f"Fare Watch Gmail draft failed: {e}")
        else:
            logger.info(f"Fare Watch: {count} watch(es) checked — no price movements vs baseline")

    except Exception as e:
        logger.error(f"Fare Watch FAILED: {e}", exc_info=True)


# ============================================================================
# LEGACY SCHEDULER (18 jobs — preserved for rollback)
# ============================================================================

def build_scheduler_legacy() -> AsyncIOScheduler:
    """Original 18-job scheduler configuration. Kept for rollback if needed.
    To revert: rename this to build_scheduler() and remove the consolidated version.
    """
    scheduler = AsyncIOScheduler(timezone=TZ)

    # Branded Morning Email: 7:00AM daily — the HTML email briefing
    scheduler.add_job(job_branded_morning_email, CronTrigger(hour=7, minute=0, timezone=TZ),
                      id="branded_morning_email", name="Branded Morning Email (7AM)")

    # Payment Alerts: 7:05AM daily — SMS deadline reminders
    scheduler.add_job(job_payment_alerts, CronTrigger(hour=7, minute=5, timezone=TZ),
                      id="payment_alerts", name="Payment Alerts (7:05AM)")

    # Morning Briefing: 6:30AM daily — combined world + ship intel
    scheduler.add_job(job_morning_briefing, CronTrigger(hour=6, minute=30, timezone=TZ),
                      id="morning_briefing", name="Morning Briefing (Daily)")

    # Ship Intel PM: 5PM — afternoon update
    scheduler.add_job(job_ship_intel, CronTrigger(hour=17, minute=0, timezone=TZ),
                      id="ship_intel_evening", name="Ship Intel (PM)")

    # Tech Monitor: 8AM daily
    scheduler.add_job(job_tech_monitor, CronTrigger(hour=8, minute=0, timezone=TZ),
                      id="tech_monitor_daily", name="Tech Monitor (Daily)")

    # Claude Code Digest: 10AM daily — articles page refresh
    scheduler.add_job(job_claude_code_digest, CronTrigger(hour=10, minute=0, timezone=TZ),
                      id="claude_code_digest", name="Claude Code Digest (10AM)")

    # Weekly Report: Monday 7AM
    scheduler.add_job(job_weekly_report, CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=TZ),
                      id="weekly_report", name="Weekly Report (Monday)")

    # Email Classifier: every 15 min during business hours (8AM-6PM)
    scheduler.add_job(job_email_classifier, CronTrigger(hour="8-18", minute="*/15", timezone=TZ),
                      id="email_classifier", name="Email Classifier (15min)")

    # Follow-Up Scanner: 7:10AM daily — after payment alerts
    scheduler.add_job(job_followup_scan, CronTrigger(hour=7, minute=10, timezone=TZ),
                      id="followup_scan", name="Follow-Up Scanner (7:10AM)")

    # Calendar Sync: 9PM daily — sync booking milestones to calendar
    scheduler.add_job(job_calendar_sync, CronTrigger(hour=21, minute=0, timezone=TZ),
                      id="calendar_sync", name="Calendar Sync (9PM)")

    # Drive Mirror: 11PM daily — sync files to Google Drive
    scheduler.add_job(job_drive_sync, CronTrigger(hour=23, minute=0, timezone=TZ),
                      id="drive_sync", name="Drive Mirror (11PM)")

    # Drive Backup: 3AM daily — full backup mirror
    scheduler.add_job(job_drive_sync, CronTrigger(hour=3, minute=0, timezone=TZ),
                      id="drive_backup_3am", name="Drive Backup (3AM)")

    # COS-EXEC Heartbeat: every 30 min, 0600-2000 — proactive scan
    scheduler.add_job(job_cos_exec_heartbeat, CronTrigger(hour="6-20", minute="*/30", timezone=TZ),
                      id="cos_exec_heartbeat", name="COS-EXEC Heartbeat (30min)")

    # Daily Persona Heartbeats: 0630 — A2, A3, A9, A10, A6 run in sequence
    scheduler.add_job(job_daily_heartbeats, CronTrigger(hour=6, minute=30, timezone=TZ),
                      id="daily_heartbeats", name="Daily Heartbeats (0630)")

    # CH Washington Weekly: Friday 3PM — wisdom and morale
    scheduler.add_job(job_weekly_heartbeat, CronTrigger(day_of_week="fri", hour=15, minute=0, timezone=TZ),
                      id="weekly_heartbeat", name="CH Weekly Heartbeat (Fri 3PM)")

    # Evernote + USB Backup: Sunday 2AM — weekly code archive
    scheduler.add_job(job_evernote_backup, CronTrigger(day_of_week="sun", hour=2, minute=0, timezone=TZ),
                      id="evernote_backup", name="Evernote/USB Backup (Sun 2AM)")

    # Nova Weekly Audit: Sunday 8PM — ELON (A12) system review + improvement tickets
    scheduler.add_job(job_nova_audit, CronTrigger(day_of_week="sun", hour=20, minute=0, timezone=TZ),
                      id="nova_audit", name="Nova Weekly Audit (Sun 8PM)")

    # Rsync to dv7: hourly during work hours + 10:50PM (before Drive mirror)
    scheduler.add_job(job_rsync_to_dv7, CronTrigger(hour="8-20", minute=50, timezone=TZ),
                      id="rsync_dv7_hourly", name="Rsync to dv7 (hourly)")
    scheduler.add_job(job_rsync_to_dv7, CronTrigger(hour=22, minute=50, timezone=TZ),
                      id="rsync_dv7_nightly", name="Rsync to dv7 (pre-mirror)")

    # Fare Watch: 8AM + 4PM MT — check all active watches, alert on price movement
    scheduler.add_job(job_fare_watch_check, CronTrigger(hour=8, minute=0, timezone=TZ),
                      id="fare_watch_morning", name="Fare Watch (8AM)")
    scheduler.add_job(job_fare_watch_check, CronTrigger(hour=16, minute=0, timezone=TZ),
                      id="fare_watch_afternoon", name="Fare Watch (4PM)")

    # Product Intake: 9AM MT daily — scan vendor emails for new cruise/hotel/tour offers
    async def job_product_intake():
        try:
            from thunderbird_product_intake import scan_vendor_emails
            products = scan_vendor_emails(days=3)
            logger.info(f"Product intake: {len(products) if products else 0} new products found")
        except Exception as e:
            logger.error(f"Product intake failed: {e}", exc_info=True)

    scheduler.add_job(job_product_intake, CronTrigger(hour=9, minute=0, timezone=TZ),
                      id="product_intake_daily", name="Product Intake Scan (9AM)")

    # Guest Forms: weekly Monday 9:30 AM MT — send pending guest profile forms
    async def job_guest_forms():
        try:
            from thunderbird_guest_forms import send_all_pending_guest_forms
            result = send_all_pending_guest_forms(window_days=60)
            logger.info(f"Guest forms: {result.get('total_drafts_created', 0)} drafts created")
        except Exception as e:
            logger.error(f"Guest forms failed: {e}", exc_info=True)

    scheduler.add_job(job_guest_forms, CronTrigger(day_of_week="mon", hour=9, minute=30, timezone=TZ),
                      id="guest_forms_weekly", name="Guest Profile Forms (Mon 9:30AM)")

    # Booking Reconciliation: weekly Sunday 8PM MT — full cross-check
    async def job_reconciliation():
        try:
            from thunderbird_reconciliation import reconcile_all_bookings, reconciliation_briefing_line
            reports = reconcile_all_bookings()
            line = reconciliation_briefing_line(reports)
            logger.info(f"Reconciliation: {line}")
        except Exception as e:
            logger.error(f"Reconciliation failed: {e}", exc_info=True)

    scheduler.add_job(job_reconciliation, CronTrigger(day_of_week="sun", hour=20, minute=30, timezone=TZ),
                      id="reconciliation_weekly", name="Booking Reconciliation (Sun 8:30PM)")

    return scheduler


async def run_all_now():
    """Run all consolidated jobs immediately (for testing or manual trigger)."""
    logger.info("Running all consolidated jobs NOW...")
    await consolidated_morning_brief()
    await consolidated_midday_pulse()
    await consolidated_eod_summary()
    await consolidated_evening_sync()
    await consolidated_weekly_deep_dive()
    logger.info("All consolidated jobs complete.")


# ============================================================================
# MAIN
# ============================================================================

def main():
    if "--run-now" in sys.argv:
        asyncio.run(run_all_now())
        return

    if "--test" in sys.argv:
        logger.info("Test mode: running World Intel sweep only...")
        asyncio.run(job_world_intel())
        return

    if "--status" in sys.argv:
        # Use BackgroundScheduler for quick status check (no event loop needed)
        scheduler = BackgroundScheduler(timezone=TZ)
        noop = lambda: None

        # Consolidated 5-job schedule
        scheduler.add_job(noop, CronTrigger(hour=6, minute=30, timezone=TZ),
                          id="morning_brief", name="Morning Brief (0630)")
        scheduler.add_job(noop, CronTrigger(hour=12, minute=0, timezone=TZ),
                          id="midday_pulse", name="Midday Pulse (1200)")
        scheduler.add_job(noop, CronTrigger(hour=17, minute=0, timezone=TZ),
                          id="eod_summary", name="EOD Summary (1700)")
        scheduler.add_job(noop, CronTrigger(hour=21, minute=0, timezone=TZ),
                          id="evening_sync", name="Evening Sync (2100)")
        scheduler.add_job(noop, CronTrigger(day_of_week="mon", hour=7, minute=0, timezone=TZ),
                          id="weekly_deep_dive", name="Weekly Deep Dive (Mon 0700)")

        scheduler.start()
        print("\nThunderbird Consolidated Schedule (5 jobs):")
        print("-" * 60)
        for job in sorted(scheduler.get_jobs(), key=lambda j: str(j.next_run_time)):
            print(f"  {job.name:35s}  next: {job.next_run_time}")
        print("-" * 60)
        print("  (Legacy 18-job config preserved in build_scheduler_legacy())")
        scheduler.shutdown()
        return

    # Daemon mode — run in asyncio event loop
    logger.info("=" * 70)
    logger.info("THUNDERBIRD INTEL SCHEDULER — Starting")
    logger.info(f"Timezone: {TZ}")
    logger.info("=" * 70)

    async def run_daemon():
        scheduler = build_scheduler()
        scheduler.start()

        logger.info("\nScheduled Jobs:")
        for job in scheduler.get_jobs():
            logger.info(f"  {job.name:30s}  next: {job.next_run_time}")
        logger.info("")

        stop_event = asyncio.Event()

        def shutdown(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            scheduler.shutdown()
            stop_event.set()

        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        await stop_event.wait()
        logger.info("Scheduler stopped.")

    asyncio.run(run_daemon())


if __name__ == "__main__":
    main()

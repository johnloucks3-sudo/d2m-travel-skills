"""
Thunderbird Daily Brief — Consolidated Morning Engine
Dreams2Memories Travel, LLC · A7 Sterling build · 2026-06-10

Single authoritative script that:
  1. Checks for feedback replies to yesterday's brief (0555 step)
  2. Collects all data sources (missions, FPDs, outputs, fare watches, RSS)
  3. Builds cream/blue/navy HTML brief
  4. Sends via d2mconcierge → johnloucks3@gmail.com
  5. Writes date-keyed send-lock to prevent duplicate sends
  6. Stores message ID for feedback tracking

Usage:
  python3 agents/thunderbird_daily_brief.py            # Normal send
  python3 agents/thunderbird_daily_brief.py --preview  # Write HTML to /tmp, no send
  python3 agents/thunderbird_daily_brief.py --force    # Ignore send-lock (for testing)

Systemd timer: thunderbird-daily-brief.timer (0600 MT daily)
Lock file: OpsCenter/brief_sent_YYYYMMDD.lock (MT date)
"""

import argparse
import base64
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ---------------------------------------------------------------------------
# BOOTSTRAP — add Thunderbird root and key sub-packages to sys.path
# ---------------------------------------------------------------------------
THUNDERBIRD_DIR = Path(__file__).parent.parent

_EXTRA_PATHS = [
    THUNDERBIRD_DIR,
    THUNDERBIRD_DIR / "core" / "intel",
    THUNDERBIRD_DIR / "core" / "email",
    THUNDERBIRD_DIR / "agents",
    THUNDERBIRD_DIR / "OpsCenter",
    THUNDERBIRD_DIR / "api",
]
for _p in _EXTRA_PATHS:
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
COMMANDER_EMAIL = "johnloucks3@gmail.com"
WING_EMAIL = "d2mconcierge@gmail.com"
LOCK_DIR = THUNDERBIRD_DIR / "OpsCenter"
FEEDBACK_CONFIG_PATH = THUNDERBIRD_DIR / "OpsCenter" / "brief_feedback_config.json"
FEEDBACK_LOG_PATH = THUNDERBIRD_DIR / "OpsCenter" / "brief_feedback_log.jsonl"
OUTPUT_LOG_PATH = THUNDERBIRD_DIR / "OpsCenter" / "daily_output_log.json"
MISSION_BOARD_PATH = THUNDERBIRD_DIR / "OpsCenter" / "mission_board.json"
HALE_STATE_PATH = THUNDERBIRD_DIR / "hale_state.json"
FARE_WATCHES_DIR = THUNDERBIRD_DIR / "OpsCenter" / "fare_watches"
DRAFT_METADATA_PATH = THUNDERBIRD_DIR / "OpsCenter" / "draft_metadata.json"

# Colors
CREAM = "#f7f3ea"
BLUE = "#0000ff"
NAVY = "#003087"
TEXT_DARK = "#1a1a2e"
GOLD = "#C9A84C"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(THUNDERBIRD_DIR / "logs" / "daily_brief.log"), mode="a"),
    ],
)
logger = logging.getLogger("thunderbird_daily_brief")

# ---------------------------------------------------------------------------
# TIMEZONE HELPER
# ---------------------------------------------------------------------------

def _mt_now() -> datetime:
    try:
        import zoneinfo
        return datetime.now(tz=zoneinfo.ZoneInfo("America/Denver"))
    except Exception:
        return datetime.utcnow().replace(tzinfo=timezone.utc)


def _mt_date_str() -> str:
    return _mt_now().strftime("%Y-%m-%d")


def _mt_day_label() -> str:
    """E.g. 'Wednesday Jun 10'"""
    return _mt_now().strftime("%A %b %d")


# ---------------------------------------------------------------------------
# SEND LOCK
# ---------------------------------------------------------------------------

def _lock_path(date_str: str) -> Path:
    return LOCK_DIR / f"brief_sent_{date_str.replace('-', '')}.lock"


def _lock_exists(date_str: str) -> bool:
    return _lock_path(date_str).exists()


def _write_lock(date_str: str):
    p = _lock_path(date_str)
    p.write_text(json.dumps({"date": date_str, "sent_at": datetime.utcnow().isoformat()}))
    logger.info(f"Send-lock written: {p}")


# ---------------------------------------------------------------------------
# FEEDBACK CHECK — runs at start of 0600 window
# ---------------------------------------------------------------------------

def check_feedback_replies() -> list[dict]:
    """Check johnloucks3 inbox for replies to yesterday's brief.

    Returns list of feedback dicts logged and ready to display in brief.
    """
    try:
        cfg = json.loads(FEEDBACK_CONFIG_PATH.read_text()) if FEEDBACK_CONFIG_PATH.exists() else {}
        yesterday_msg_id = cfg.get("last_brief_message_id")
        if not yesterday_msg_id:
            return []

        from thunderbird_google_auth import get_commander_gmail
        svc = get_commander_gmail()

        # Search for replies in thread
        thread_id = cfg.get("last_brief_thread_id")
        if not thread_id:
            return []

        thread = svc.users().threads().get(userId="me", id=thread_id, format="minimal").execute()
        messages = thread.get("messages", [])

        # Messages after the original brief
        new_replies = []
        for msg in messages:
            if msg["id"] == yesterday_msg_id:
                continue
            # Fetch body
            try:
                full = svc.users().messages().get(userId="me", id=msg["id"], format="full").execute()
                payload = full.get("payload", {})
                body_text = ""
                # Try plain text part
                parts = payload.get("parts", [payload])
                for part in parts:
                    if part.get("mimeType") == "text/plain":
                        data = part.get("body", {}).get("data", "")
                        if data:
                            body_text = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
                            break
                if body_text:
                    feedback_entry = {
                        "ts": datetime.utcnow().isoformat(),
                        "message_id": msg["id"],
                        "text": body_text[:2000],
                    }
                    new_replies.append(feedback_entry)
                    # Append to feedback log
                    with FEEDBACK_LOG_PATH.open("a") as f:
                        f.write(json.dumps(feedback_entry) + "\n")
            except Exception as me:
                logger.warning(f"Could not read reply message {msg['id']}: {me}")

        return new_replies

    except Exception as e:
        logger.warning(f"Feedback check failed (non-blocking): {e}")
        return []


# ---------------------------------------------------------------------------
# DATA COLLECTORS
# ---------------------------------------------------------------------------

def collect_commander_actions() -> list[dict]:
    """P0 missions + WF-17 drafts + FPDs due within 15 days.

    P0 mission filter: only surfaces missions that require IMMEDIATE action today.
    Stale in_progress infra missions are suppressed — they don't require Commander
    action. Surfaced if: status is 'active' or 'pending_review', OR has a suspense
    date within 3 days (regardless of status).
    """
    items = []
    today_mt = _mt_now().date()
    three_days_out = today_mt + timedelta(days=3)

    # P0 missions from hale_state.json — only genuinely actionable today
    try:
        hs = json.loads(HALE_STATE_PATH.read_text())
        for task in hs.get("open_tasks", []):
            if task.get("priority") != "P0":
                continue
            status = task.get("status", "")
            if status in ("completed", "archived"):
                continue

            # Surface if status is active/pending_review (needs attention now)
            is_actionable = status in ("active", "pending_review")

            # Also surface any P0 with a near-term suspense date regardless of status
            suspense = task.get("suspense_date", "")
            if suspense and not is_actionable:
                try:
                    sus_date = datetime.strptime(suspense[:10], "%Y-%m-%d").date()
                    if sus_date <= three_days_out:
                        is_actionable = True
                except Exception:
                    pass

            if is_actionable:
                items.append({
                    "type": "P0_MISSION",
                    "id": task.get("id", ""),
                    "title": task.get("title", ""),
                    "status": status,
                })
    except Exception as e:
        logger.warning(f"hale_state P0 missions failed: {e}")

    # WF-17 drafts — primary source: Gmail THUNDERBIRD-Commander-Review label
    # Fallback: draft_metadata.json for non-wing addressed entries
    wf17_found_via_gmail = False
    try:
        from thunderbird_google_auth import get_persona_gmail
        svc = get_persona_gmail()
        # Query drafts with THUNDERBIRD-Commander-Review label
        # Gmail API: list drafts, then filter by label on message
        results = svc.users().drafts().list(userId="me", maxResults=25).execute()
        drafts = results.get("drafts", [])
        for draft_entry in drafts:
            draft_id = draft_entry.get("id", "")
            try:
                draft_full = svc.users().drafts().get(
                    userId="me", id=draft_id, format="metadata",
                    metadataHeaders=["Subject", "To"]
                ).execute()
                msg = draft_full.get("message", {})
                label_ids = msg.get("labelIds", [])
                # Check for Commander-Review label (label name contains THUNDERBIRD or Review)
                is_review = any(
                    "THUNDERBIRD" in lid or "Commander-Review" in lid or "Commander_Review" in lid
                    for lid in label_ids
                )
                # Also catch by label name lookup below if IDs are opaque
                headers = {
                    h["name"].lower(): h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }
                subject = headers.get("subject", "")
                to_addr = headers.get("to", "")
                # Wing-internal drafts should not appear in Commander Action
                if "johnloucks3" in to_addr or "d2mconcierge" in to_addr:
                    continue
                if is_review or to_addr:
                    items.append({
                        "type": "WF17_DRAFT",
                        "id": draft_id[:12],
                        "title": f"Draft ready to send: {subject[:60]}",
                        "to": to_addr,
                    })
                    wf17_found_via_gmail = True
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Gmail WF-17 label query failed (falling back to draft_metadata): {e}")

    # Fallback: draft_metadata.json (catches non-Gmail-drafts queued externally)
    if not wf17_found_via_gmail:
        try:
            dm = json.loads(DRAFT_METADATA_PATH.read_text()) if DRAFT_METADATA_PATH.exists() else {}
            for msg_id, meta in dm.items():
                subject = meta.get("subject", "")
                to_addr = meta.get("to", "")
                if to_addr and "johnloucks3" not in to_addr and "d2mconcierge" not in to_addr:
                    items.append({
                        "type": "WF17_DRAFT",
                        "id": msg_id[:12],
                        "title": f"Draft ready to send: {subject[:60]}",
                        "to": to_addr,
                    })
        except Exception as e:
            logger.warning(f"Draft metadata read failed: {e}")

    # FPDs due within 15 days (from hale_state deferred_alerts + fpd_state)
    try:
        hs = json.loads(HALE_STATE_PATH.read_text())
        fifteen_days_out = today_mt + timedelta(days=15)
        for alert in hs.get("deferred_alerts", []):
            fpd_str = alert.get("fpd", "")
            trigger_str = alert.get("trigger_date", "")
            if fpd_str:
                try:
                    fpd_date = datetime.strptime(fpd_str, "%Y-%m-%d").date()
                    if today_mt <= fpd_date <= fifteen_days_out:
                        items.append({
                            "type": "FPD_DUE",
                            "id": alert.get("id", ""),
                            "title": f"FPD due {fpd_str}: {alert.get('client','')} — ${alert.get('amount',0):,.2f}",
                            "fpd": fpd_str,
                            "amount": alert.get("amount", 0),
                        })
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"FPD collection failed: {e}")

    # Also check fpd_state.json
    try:
        fpd_state_path = THUNDERBIRD_DIR / "OpsCenter" / "state" / "fpd_state.json"
        if fpd_state_path.exists():
            fpd_data = json.loads(fpd_state_path.read_text())
            fifteen_days_out = today_mt + timedelta(days=15)
            for client_name, fdata in fpd_data.items():
                fpd_str = fdata.get("fpd", "")
                status = fdata.get("status", "")
                if status in ("RECEIVED", "paid_in_full"):
                    continue
                if fpd_str and fpd_str not in ("", "N/A"):
                    try:
                        fpd_date = datetime.strptime(fpd_str, "%Y-%m-%d").date()
                        if today_mt <= fpd_date <= fifteen_days_out:
                            items.append({
                                "type": "FPD_DUE",
                                "id": f"fpd-{client_name[:20]}",
                                "title": f"FPD due {fpd_str}: {client_name}",
                                "fpd": fpd_str,
                            })
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"fpd_state.json read failed: {e}")

    return items


def collect_yesterdays_outputs() -> list[dict]:
    """Wing outputs in last 24h from daily_output_log.json."""
    try:
        sys.path.insert(0, str(THUNDERBIRD_DIR))
        from core.output.daily_output_logger import get_outputs_since
        return get_outputs_since(hours=24)
    except Exception as e:
        logger.warning(f"Yesterday's outputs failed: {e}")
        return []


def collect_overnight_missions() -> list[dict]:
    """Mission board tasks updated in last 24h."""
    results = []
    try:
        board = json.loads(MISSION_BOARD_PATH.read_text())
        missions = board.get("missions", board.get("tasks", []))
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=24)

        for m in missions:
            updated_str = m.get("updated_at", "")
            if not updated_str:
                continue
            try:
                updated = datetime.fromisoformat(updated_str)
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                if updated >= cutoff and m.get("status") not in ("archived",):
                    results.append({
                        "id": m.get("id", ""),
                        "title": m.get("title", "")[:80],
                        "status": m.get("status", ""),
                        "owner": m.get("assigned_to", ""),
                    })
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Overnight missions failed: {e}")
    return results


def collect_fare_watches() -> tuple[list[dict], list[dict]]:
    """Returns (client_fares, personal_fares) from fare_watches directory."""
    client_fares = []
    personal_fares = []
    try:
        if not FARE_WATCHES_DIR.exists():
            return [], []
        last_check_path = FARE_WATCHES_DIR / "last_check.json"
        if not last_check_path.exists():
            return [], []
        data = json.loads(last_check_path.read_text())
        results = data.get("results", {})
        alerts = data.get("alerts", [])
        warnings = data.get("warnings", [])
        errors = data.get("errors", [])

        for watch_id, result in results.items():
            # Determine personal vs client
            is_personal = any(kw in watch_id.lower() for kw in ("loucks", "personal", "susie"))
            entry = {
                "watch_id": watch_id,
                "status": result.get("status", "unknown"),
                "best_fare": result.get("best_fare", ""),
                "error": result.get("error", ""),
                "alerts": [a for a in alerts if watch_id in str(a)],
            }
            if is_personal:
                personal_fares.append(entry)
            else:
                client_fares.append(entry)

        # Add global alerts/warnings as synthetic entries
        for w in warnings:
            client_fares.append({
                "watch_id": "SYSTEM",
                "status": "warning",
                "best_fare": "",
                "error": w,
                "alerts": [],
            })

    except Exception as e:
        logger.warning(f"Fare watches failed: {e}")
    return client_fares, personal_fares


def collect_rss_news() -> dict:
    """Fetch RSS feeds. Returns {'cruise': [...], 'geopolitical': [...], 'business': [...]}"""
    results = {"cruise": [], "geopolitical": [], "business": []}
    try:
        from thunderbird_morning_briefing import fetch_direct_rss_feeds, _SOURCE_CATEGORIES
        articles = fetch_direct_rss_feeds()

        # Map categories to our three buckets
        category_map = {
            "Cruise": "cruise",
            "War/Geopolitics": "geopolitical",
            "Politics": "geopolitical",
            "Airline": "business",
            "Aviation": "business",
            "Markets": "business",
            "Maritime": "business",
            "Travel": "cruise",
            "Other": "business",
        }

        for article in articles:
            cat = article.get("category", "Other")
            bucket = category_map.get(cat, "business")
            if len(results[bucket]) < 10:
                results[bucket].append({
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                })
    except Exception as e:
        logger.warning(f"RSS collection failed: {e}")
        # Return empty rather than crash
    return results


def collect_next_24h_missions() -> list[dict]:
    """Active missions with clear completion criteria queued for autonomous overnight run."""
    results = []
    try:
        board = json.loads(MISSION_BOARD_PATH.read_text())
        missions = board.get("missions", board.get("tasks", []))
        for m in missions:
            if m.get("status") == "active":
                desc = m.get("description", "")
                # Include if it has a description (proxy for clear completion criteria)
                if desc and len(desc) > 20:
                    results.append({
                        "id": m.get("id", ""),
                        "title": m.get("title", "")[:80],
                        "owner": m.get("assigned_to", ""),
                        "suspense": m.get("suspense_date", ""),
                        "priority": m.get("priority", ""),
                    })
    except Exception as e:
        logger.warning(f"Next 24h missions failed: {e}")
    return results[:15]  # cap at 15 to keep brief readable


def generate_incubator_proposal() -> str:
    """Generate one incubator proposal from pipeline gaps."""
    # Check hale_state for project tracking gaps
    try:
        hs = json.loads(HALE_STATE_PATH.read_text())
        projects = hs.get("project_tracking", {}).get("active_projects", [])
        for proj in projects:
            if proj.get("status") in ("IN_PROGRESS",) and not proj.get("deadline"):
                return (
                    f"<strong>{proj.get('name', 'Project')}</strong> — "
                    f"{proj.get('notes', 'No notes')[:200]}<br>"
                    f"<em>90-day revenue path: Confirm booking → commission trigger</em>"
                )
    except Exception:
        pass

    # Fallback proposal
    return (
        "<strong>Proactive Air Quote Expansion</strong> — "
        "Survey all active clients for 2027 voyages. Any booking without confirmed air "
        "= research opportunity. Spencer Grand Tour model applies.<br>"
        "<em>90-day revenue path: Quote → client decision → booking within 90 days</em>"
    )


# ---------------------------------------------------------------------------
# HTML BUILDER
# ---------------------------------------------------------------------------

def _section_header(title: str) -> str:
    """Cream bar section separator."""
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin:18px 0 8px 0;">'
        f'<tr>'
        f'<td style="background:{NAVY};padding:6px 14px;font-family:Arial Black,Arial,sans-serif;'
        f'font-size:8.5pt;font-weight:900;letter-spacing:2px;color:#ffffff;'
        f'text-transform:uppercase;">{title}</td>'
        f'</tr>'
        f'</table>'
    )


def _bullet_row(text: str, link: str = "", link_label: str = "source") -> str:
    link_html = (
        f' &nbsp;<a href="{link}" style="color:{BLUE};font-size:8pt;">[{link_label}]</a>'
        if link else ""
    )
    return (
        f'<div style="padding:4px 0 4px 12px;border-left:3px solid {NAVY};'
        f'margin-bottom:5px;font-family:Georgia,serif;font-size:10pt;color:{TEXT_DARK};">'
        f'{text}{link_html}'
        f'</div>'
    )


def _status_badge(status: str) -> str:
    colors = {
        "completed": ("#27AE60", "DONE"),
        "active": (NAVY, "ACTIVE"),
        "failed": ("#C0392B", "FAIL"),
        "pending_review": ("#E67E22", "REVIEW"),
        "auth_error": ("#C0392B", "AUTH ERR"),
        "warning": ("#E67E22", "WARN"),
        "in_progress": (NAVY, "IN PROG"),
    }
    color, label = colors.get(status, ("#888888", status.upper()[:8]))
    return (
        f'<span style="background:{color};color:#fff;font-family:Arial,sans-serif;'
        f'font-size:7pt;font-weight:700;padding:2px 6px;letter-spacing:1px;">{label}</span>'
    )


def build_html_brief(
    date_label: str,
    commander_actions: list,
    yesterdays_outputs: list,
    overnight_missions: list,
    client_fares: list,
    personal_fares: list,
    rss_news: dict,
    next_24h_missions: list,
    incubator_proposal: str,
    feedback_items: list,
) -> str:
    """Build the full cream/blue/navy HTML brief."""

    sections = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    header = f"""
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:{CREAM};font-family:Georgia,serif;">
  <tr>
    <td style="background:{NAVY};padding:20px 28px;text-align:center;">
      <div style="color:#ffffff;font-size:22pt;font-weight:900;letter-spacing:4px;
                  font-family:Arial Black,Arial,sans-serif;">&#x1F985; THUNDERBIRD</div>
      <div style="color:{GOLD};font-size:10pt;letter-spacing:3px;
                  font-family:Arial,sans-serif;margin-top:4px;">
        {date_label} &nbsp;&bull;&nbsp; 0600 MT &nbsp;&bull;&nbsp; DAILY BRIEF
      </div>
    </td>
  </tr>
</table>
"""

    # ── FEEDBACK APPLIED ──────────────────────────────────────────────────────
    if feedback_items:
        fb_rows = "".join(
            _bullet_row(f"Feedback received: {f['text'][:200]}")
            for f in feedback_items
        )
        sections.append(
            _section_header("FEEDBACK APPLIED — YESTERDAY'S REPLY")
            + fb_rows
        )

    # ── COMMANDER ACTION REQUIRED ─────────────────────────────────────────────
    if commander_actions:
        rows = ""
        for item in commander_actions:
            itype = item.get("type", "")
            if itype == "P0_MISSION":
                rows += _bullet_row(
                    f"[{item['id']}] {item['title']} "
                    f"{_status_badge(item.get('status',''))}"
                )
            elif itype == "WF17_DRAFT":
                rows += _bullet_row(
                    f"WF-17 DRAFT PENDING SEND &rarr; {item['title']} "
                    f"&nbsp;<em>to {item.get('to','')}</em>"
                )
            elif itype == "FPD_DUE":
                rows += _bullet_row(
                    f"FPD DUE {item.get('fpd','')} &rarr; {item['title']}"
                )
        if rows:
            sections.append(_section_header("COMMANDER ACTION REQUIRED") + rows)

    # ── YESTERDAY'S OUTPUTS ───────────────────────────────────────────────────
    if yesterdays_outputs:
        rows = ""
        for out in yesterdays_outputs:
            link = out.get("drive_link", "")
            rows += _bullet_row(
                f"{out.get('title','Output')} &nbsp;"
                f"<em style='color:#888;font-size:8pt;'>{out.get('local_path','')[-40:]}</em>",
                link=link,
                link_label="Drive",
            )
        sections.append(_section_header("YESTERDAY'S OUTPUTS") + rows)

    # ── AUTO-EXECUTE LAST 24H RESULTS ─────────────────────────────────────────
    if overnight_missions:
        rows = ""
        for m in overnight_missions:
            rows += _bullet_row(
                f"[{m['id']}] {m['title']} "
                f"{_status_badge(m.get('status',''))} "
                f"&nbsp;<em style='color:#555;font-size:8pt;'>{m.get('owner','')}</em>"
            )
        sections.append(_section_header("AUTO-EXECUTE — LAST 24H RESULTS") + rows)

    # ── CLIENT AIR SCANS ──────────────────────────────────────────────────────
    if client_fares:
        rows = ""
        for fw in client_fares:
            status_badge = _status_badge(fw.get("status", "unknown"))
            fare_str = f" — Best: <strong>{fw['best_fare']}</strong>" if fw.get("best_fare") else ""
            err_str = f" — {fw['error'][:120]}" if fw.get("error") else ""
            rows += _bullet_row(
                f"{fw['watch_id']} {status_badge}{fare_str}{err_str}"
            )
        sections.append(_section_header("CLIENT AIR SCANS") + rows)

    # ── JOHN & SUSIE AIR ──────────────────────────────────────────────────────
    if personal_fares:
        rows = ""
        for fw in personal_fares:
            status_badge = _status_badge(fw.get("status", "unknown"))
            fare_str = f" — Best: <strong>{fw['best_fare']}</strong>" if fw.get("best_fare") else ""
            rows += _bullet_row(f"{fw['watch_id']} {status_badge}{fare_str}")
        sections.append(_section_header("JOHN & SUSIE AIR") + rows)

    # ── CRUISE LINE SCANS ─────────────────────────────────────────────────────
    # For v1: placeholder noting sources — full portal scraping deferred to separate
    # daemon (MISSION-160 Centrav keepalive). Include brief notes.
    cruise_note = _bullet_row(
        "Regent Seven Seas, Atlas Ocean Voyages, Silversea — live portal scans require "
        "authenticated session. Check MISSION-113/157 for cookie status."
    )
    sections.append(_section_header("CRUISE LINE SCANS") + cruise_note)

    # ── WORLD NEWS ────────────────────────────────────────────────────────────
    news_html = ""
    for bucket_key, bucket_label in [
        ("cruise", "TRAVEL &amp; CRUISE"),
        ("geopolitical", "GEOPOLITICAL"),
        ("business", "BUSINESS"),
    ]:
        articles = rss_news.get(bucket_key, [])
        if articles:
            news_html += (
                f'<div style="margin-bottom:6px;font-family:Arial Black,Arial,sans-serif;'
                f'font-size:8pt;font-weight:900;color:{NAVY};letter-spacing:2px;'
                f'text-transform:uppercase;">{bucket_label}</div>'
            )
            for art in articles[:10]:
                news_html += _bullet_row(
                    f"{art.get('source','?')} &mdash; {art.get('title','')}",
                    link=art.get("url", ""),
                    link_label="link",
                )
        else:
            news_html += (
                f'<div style="padding:4px 0;font-family:Arial,sans-serif;font-size:9pt;'
                f'color:#888;">{bucket_label}: No items retrieved</div>'
            )
    # World News is never suppressed
    sections.append(_section_header("WORLD NEWS") + news_html)

    # ── MISSION BOARD — NEXT 24H ──────────────────────────────────────────────
    if next_24h_missions:
        rows = ""
        for m in next_24h_missions:
            sus = f" &nbsp;<em style='color:#888;font-size:8pt;'>Suspense: {m['suspense']}</em>" if m.get("suspense") else ""
            rows += _bullet_row(
                f"[{m['id']}] {m['title']} "
                f"<span style='color:{NAVY};font-size:8pt;font-weight:700;'>{m.get('priority','')}</span>"
                f"{sus}"
            )
        sections.append(_section_header("MISSION BOARD — AUTO-EXECUTE NEXT 24H") + rows)

    # ── INCUBATOR PROPOSAL ────────────────────────────────────────────────────
    sections.append(
        _section_header("INCUBATOR PROPOSAL")
        + f'<div style="padding:8px 14px;background:#fffef5;border-left:4px solid {GOLD};'
        f'font-family:Georgia,serif;font-size:10pt;color:{TEXT_DARK};margin-bottom:8px;">'
        f'{incubator_proposal}'
        f'</div>'
    )

    # ── FOOTER ────────────────────────────────────────────────────────────────
    footer = (
        f'<div style="margin-top:20px;padding:14px 28px;background:{NAVY};'
        f'font-family:Arial,Helvetica,sans-serif;font-size:8pt;color:#aabbcc;'
        f'text-align:center;letter-spacing:1px;">'
        f'Reply to improve this brief &mdash; changes live tomorrow.'
        f'&nbsp;&bull;&nbsp; Thunderbird Wing &nbsp;&bull;&nbsp; Dreams2Memories Travel, LLC'
        f'</div>'
    )

    # ── ASSEMBLE ──────────────────────────────────────────────────────────────
    body_inner = "\n".join(sections)

    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#e8e4dc;">
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:#e8e4dc;padding:16px 0;">
  <tr>
    <td align="center">
      <table width="660" cellpadding="0" cellspacing="0"
             style="background:{CREAM};border:1px solid #d4cfc5;
                    box-shadow:0 2px 8px rgba(0,0,0,0.10);">
        <tr><td>{header}</td></tr>
        <tr>
          <td style="padding:18px 24px 8px 24px;">
            {body_inner}
          </td>
        </tr>
        <tr><td>{footer}</td></tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""

    # Run through premailer to inline CSS (same as _wrap_body_html for full-doc path)
    try:
        import premailer
        full_html = premailer.transform(full_html, remove_classes=False, strip_important=False)
    except Exception as pm_e:
        logger.warning(f"premailer inlining failed (continuing): {pm_e}")

    return full_html


# ---------------------------------------------------------------------------
# SEND
# ---------------------------------------------------------------------------

def _send_brief(subject: str, html_body: str) -> dict:
    """Send brief via d2mconcierge persona token to Commander inbox."""
    from thunderbird_google_auth import get_persona_gmail

    svc = get_persona_gmail()

    msg = MIMEMultipart("alternative")
    msg["to"] = COMMANDER_EMAIL
    msg["from"] = f'"Victory Hale, D2M Travel" <{WING_EMAIL}>'
    msg["reply-to"] = WING_EMAIL
    msg["subject"] = subject

    # Plain text fallback
    plain = f"Thunderbird Daily Brief — {subject}\n\nPlease view in HTML email client."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()

    message_id = result.get("id", "")
    thread_id = result.get("threadId", "")

    # Update feedback config with new message ID
    try:
        cfg = json.loads(FEEDBACK_CONFIG_PATH.read_text()) if FEEDBACK_CONFIG_PATH.exists() else {}
        cfg["last_brief_message_id"] = message_id
        cfg["last_brief_thread_id"] = thread_id
        cfg["last_brief_date"] = _mt_date_str()
        FEEDBACK_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception as fc_e:
        logger.warning(f"Feedback config update failed: {fc_e}")

    return {
        "status": "sent",
        "message_id": message_id,
        "thread_id": thread_id,
        "to": COMMANDER_EMAIL,
        "subject": subject,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Thunderbird Daily Brief")
    parser.add_argument("--preview", action="store_true",
                        help="Write HTML to /tmp/thunderbird_brief_YYYYMMDD.html, do not send")
    parser.add_argument("--force", action="store_true",
                        help="Ignore send-lock (testing only)")
    args = parser.parse_args()

    date_str = _mt_date_str()
    day_label = _mt_day_label()
    subject = f"\U0001F985 THUNDERBIRD // {day_label} · 0600 MT"

    # ── SEND LOCK CHECK ───────────────────────────────────────────────────────
    if not args.preview and not args.force:
        if _lock_exists(date_str):
            logger.info(f"Send-lock exists for {date_str} — brief already sent today. Exiting.")
            return

    # Ensure logs directory exists
    (THUNDERBIRD_DIR / "logs").mkdir(exist_ok=True)

    logger.info(f"Thunderbird Daily Brief — {date_str} — building...")

    # ── STEP 1: FEEDBACK CHECK ────────────────────────────────────────────────
    logger.info("Step 1: Checking feedback replies...")
    feedback_items = check_feedback_replies()
    if feedback_items:
        logger.info(f"  {len(feedback_items)} feedback items found")
    else:
        logger.info("  No feedback replies")

    # ── STEP 2: DATA COLLECTION ───────────────────────────────────────────────
    logger.info("Step 2: Collecting data sources...")

    logger.info("  Commander actions...")
    commander_actions = collect_commander_actions()
    logger.info(f"    {len(commander_actions)} items")

    logger.info("  Yesterday's outputs...")
    yesterdays_outputs = collect_yesterdays_outputs()
    logger.info(f"    {len(yesterdays_outputs)} items")

    logger.info("  Overnight missions...")
    overnight_missions = collect_overnight_missions()
    logger.info(f"    {len(overnight_missions)} items")

    logger.info("  Fare watches...")
    client_fares, personal_fares = collect_fare_watches()
    logger.info(f"    {len(client_fares)} client, {len(personal_fares)} personal")

    logger.info("  RSS news...")
    rss_news = collect_rss_news()
    total_news = sum(len(v) for v in rss_news.values())
    logger.info(f"    {total_news} articles across 3 buckets")

    logger.info("  Next 24h missions...")
    next_24h_missions = collect_next_24h_missions()
    logger.info(f"    {len(next_24h_missions)} missions queued")

    logger.info("  Incubator proposal...")
    incubator_proposal = generate_incubator_proposal()

    # ── STEP 3: BUILD HTML ────────────────────────────────────────────────────
    logger.info("Step 3: Building HTML brief...")
    html = build_html_brief(
        date_label=day_label,
        commander_actions=commander_actions,
        yesterdays_outputs=yesterdays_outputs,
        overnight_missions=overnight_missions,
        client_fares=client_fares,
        personal_fares=personal_fares,
        rss_news=rss_news,
        next_24h_missions=next_24h_missions,
        incubator_proposal=incubator_proposal,
        feedback_items=feedback_items,
    )
    logger.info(f"  HTML built: {len(html):,} bytes")

    # ── STEP 4: PREVIEW OR SEND ───────────────────────────────────────────────
    if args.preview:
        out_path = Path(f"/tmp/thunderbird_brief_{date_str.replace('-','')}.html")
        out_path.write_text(html, encoding="utf-8")
        logger.info(f"PREVIEW written to: {out_path}")
        print(f"Preview: {out_path}")
        return

    logger.info("Step 4: Sending brief...")
    try:
        result = _send_brief(subject, html)
        logger.info(f"  Sent OK — message_id: {result.get('message_id')}")
    except Exception as send_e:
        logger.error(f"Send FAILED: {send_e}")
        raise

    # ── STEP 5: WRITE SEND LOCK ───────────────────────────────────────────────
    _write_lock(date_str)
    logger.info(f"Brief complete — {date_str}")
    print(f"Thunderbird Daily Brief sent — {date_str} — message_id: {result.get('message_id','?')}")


if __name__ == "__main__":
    main()

"""
Thunderbird EOD Brief — End-of-Day Engine
Dreams2Memories Travel, LLC · A7 Sterling build · 2026-06-10

Four-section brief sent at 1800 MT from d2mconcierge → johnloucks3.

Sections:
  1. BEFORE YOU SLEEP      — urgent Commander actions (WF-17 drafts, FPDs <24h); suppressed if empty
  2. WHAT WE DID TODAY     — warm prose summary of today's completed missions
  3. TONIGHT'S SEARCH      — incubator sector nominations from eod_incubator_config.json
  4. OVERNIGHT QUEUE       — auto_execute missions staged for overnight run

Usage:
  python3 agents/thunderbird_eod_brief.py          # Normal send
  python3 agents/thunderbird_eod_brief.py --preview # Write HTML to /tmp, no send
  python3 agents/thunderbird_eod_brief.py --force   # Ignore send-lock

Systemd timer: thunderbird-eod-brief.timer (1800 MT daily)
Lock file: OpsCenter/eod_sent_YYYYMMDD.lock (MT date)
"""

import argparse
import base64
import functools
import json
import logging
import os
import socket
import sys
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


# ---------------------------------------------------------------------------
# BOOTSTRAP
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
OUTPUT_LOG_PATH = THUNDERBIRD_DIR / "OpsCenter" / "daily_output_log.json"
MISSION_BOARD_PATH = THUNDERBIRD_DIR / "OpsCenter" / "mission_board.json"
HALE_STATE_PATH = THUNDERBIRD_DIR / "hale_state.json"
DRAFT_METADATA_PATH = THUNDERBIRD_DIR / "OpsCenter" / "draft_metadata.json"
EOD_CONFIG_PATH = THUNDERBIRD_DIR / "OpsCenter" / "eod_incubator_config.json"
EOD_FEEDBACK_CONFIG_PATH = THUNDERBIRD_DIR / "OpsCenter" / "eod_feedback_config.json"

# AFA Colors (same palette as AM brief)
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
        logging.FileHandler(str(THUNDERBIRD_DIR / "logs" / "eod_brief.log"), mode="a"),
    ],
)
logger = logging.getLogger("thunderbird_eod_brief")

# ---------------------------------------------------------------------------
# TIMEZONE HELPER (identical to AM brief)
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
    return _mt_now().strftime("%A %b %d")


# ---------------------------------------------------------------------------
# SEND LOCK — OpsCenter/eod_sent_YYYYMMDD.lock
# ---------------------------------------------------------------------------

def _lock_path(date_str: str) -> Path:
    return LOCK_DIR / f"eod_sent_{date_str.replace('-', '')}.lock"


def _lock_exists(date_str: str) -> bool:
    return _lock_path(date_str).exists()


def _write_lock(date_str: str):
    p = _lock_path(date_str)
    p.write_text(json.dumps({"date": date_str, "sent_at": datetime.utcnow().isoformat()}))
    logger.info(f"EOD send-lock written: {p}")


# ---------------------------------------------------------------------------
# HTML PRIMITIVES (identical to AM brief — section_header, bullet_row, badge)
# ---------------------------------------------------------------------------

def _section_header(title: str) -> str:
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
        "in_progress": (NAVY, "IN PROG"),
    }
    color, label = colors.get(status, ("#888888", status.upper()[:8]))
    return (
        f'<span style="background:{color};color:#fff;font-family:Arial,sans-serif;'
        f'font-size:7pt;font-weight:700;padding:2px 6px;letter-spacing:1px;">{label}</span>'
    )


# ---------------------------------------------------------------------------
# SECTION 1 — BEFORE YOU SLEEP
# Urgent Commander actions: WF-17 drafts ready, FPDs closing in <24h
# Returns [] if nothing tonight-urgent (section suppressed entirely)
# ---------------------------------------------------------------------------

def collect_tonight_urgent() -> list[dict]:
    """Items needing Commander action tonight. Tighter window than AM brief."""
    items = []
    today_mt = _mt_now().date()
    tomorrow = today_mt + timedelta(days=1)

    # WF-17 drafts pending Commander send — pulled from d2mconcierge Gmail drafts
    try:
        from thunderbird_google_auth import get_persona_gmail
        svc = get_persona_gmail()
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
                is_review = any(
                    "THUNDERBIRD" in lid or "Commander-Review" in lid
                    for lid in label_ids
                )
                headers = {
                    h["name"].lower(): h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }
                subject = headers.get("subject", "")
                to_addr = headers.get("to", "")
                # Skip wing-internal addresses
                if "johnloucks3" in to_addr or "d2mconcierge" in to_addr:
                    continue
                if is_review and to_addr:
                    items.append({
                        "type": "WF17_DRAFT",
                        "title": f"Draft ready: {subject[:70]}",
                        "to": to_addr,
                        "id": draft_id[:12],
                    })
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"WF-17 Gmail query failed: {e}")

    # Fallback: draft_metadata.json
    if not any(i["type"] == "WF17_DRAFT" for i in items):
        try:
            dm = json.loads(DRAFT_METADATA_PATH.read_text()) if DRAFT_METADATA_PATH.exists() else {}
            for msg_id, meta in dm.items():
                subject = meta.get("subject", "")
                to_addr = meta.get("to", "")
                if to_addr and "johnloucks3" not in to_addr and "d2mconcierge" not in to_addr:
                    items.append({
                        "type": "WF17_DRAFT",
                        "title": f"Draft ready: {subject[:70]}",
                        "to": to_addr,
                        "id": msg_id[:12],
                    })
        except Exception as e:
            logger.warning(f"draft_metadata fallback failed: {e}")

    # FPDs due within 24h only (tighter than AM brief's 15 days)
    try:
        hs = json.loads(HALE_STATE_PATH.read_text())
        for alert in hs.get("deferred_alerts", []):
            fpd_str = alert.get("fpd", "")
            if fpd_str:
                try:
                    fpd_date = datetime.strptime(fpd_str, "%Y-%m-%d").date()
                    if today_mt <= fpd_date <= tomorrow:
                        items.append({
                            "type": "FPD_URGENT",
                            "title": f"FPD DUE {fpd_str}: {alert.get('client','')} — ${alert.get('amount',0):,.2f}",
                            "fpd": fpd_str,
                        })
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"FPD <24h check failed: {e}")

    return items


# ---------------------------------------------------------------------------
# SECTION 2 — WHAT WE DID TODAY
# Pull from daily_output_log.json first; fallback to mission_board completed today
# Render as warm prose, not bullets
# ---------------------------------------------------------------------------

def collect_todays_completions() -> list[dict]:
    """Returns list of completed items for today."""
    date_str = _mt_date_str()
    items = []

    # Primary: daily_output_log.json keyed by YYYY-MM-DD
    # File may be an empty list (never had dict entries written) — handle gracefully
    try:
        if OUTPUT_LOG_PATH.exists():
            raw = json.loads(OUTPUT_LOG_PATH.read_text())
            if not isinstance(raw, dict):
                # List or malformed — skip primary source, fall through to mission_board
                raise ValueError(f"daily_output_log is {type(raw).__name__}, expected dict")
            data = raw
            day_entries = data.get(date_str, [])
            for entry in day_entries:
                items.append({
                    "title": entry.get("title", "Unnamed output"),
                    "description": entry.get("description", ""),
                    "drive_link": entry.get("drive_link", ""),
                    "source": "output_log",
                })
    except Exception as e:
        logger.warning(f"daily_output_log read failed: {e}")

    # Fallback (or supplement): mission_board missions completed today
    if not items:
        try:
            board = json.loads(MISSION_BOARD_PATH.read_text())
            missions = board.get("missions", board.get("tasks", []))
            for m in missions:
                if m.get("status") != "completed":
                    continue
                updated = m.get("updated_at", "")
                # Match YYYY-MM-DD prefix — updated_at may or may not have timezone
                if updated.startswith(date_str):
                    items.append({
                        "title": m.get("title", "")[:80],
                        "description": m.get("description", "")[:200],
                        "drive_link": "",
                        "source": "mission_board",
                    })
        except Exception as e:
            logger.warning(f"mission_board completed-today fallback failed: {e}")

    return items


def _humanize_completions(items: list[dict]) -> str:
    """
    Render completed items as warm prose (3-5 sentences).
    No bullets — genuine, tight, conversational.
    """
    if not items:
        return (
            f'<p style="font-family:Georgia,serif;font-size:10pt;color:{TEXT_DARK};'
            f'line-height:1.6;margin:8px 0;">'
            f'Quiet day on the board — no outputs logged and no missions marked complete. '
            f'The watch ran clean. Tomorrow picks up where today left off.'
            f'</p>'
        )

    count = len(items)
    titles = [i["title"] for i in items[:5]]  # cap prose at 5 for readability
    overflow = count - 5 if count > 5 else 0

    # Build warm prose sentence by sentence
    sentences = []

    # Opening: count + first item
    if count == 1:
        sentences.append(f"One item crossed the finish line today: {titles[0]}.")
    elif count == 2:
        sentences.append(
            f"Two items complete today — {titles[0]} and {titles[1]}."
        )
    elif count <= 5:
        listed = ", ".join(titles[:-1]) + f", and {titles[-1]}"
        sentences.append(f"Wing cleared {count} missions today: {listed}.")
    else:
        leading = ", ".join(titles[:3])
        sentences.append(
            f"Productive run — {count} missions closed today. Leading the list: {leading}"
            + (f", plus {overflow} more." if overflow > 0 else ".")
        )

    # Middle: pull a detail from the richest description
    best_desc = ""
    for item in items:
        if len(item.get("description", "")) > len(best_desc):
            best_desc = item["description"]
    if best_desc and len(best_desc) > 30:
        sentences.append(
            f"The work of it: {best_desc[:180].rstrip('.')}."
        )

    # Close
    sentences.append("Wing is clean for the overnight run.")

    # Drive link if present
    drive_links = [i["drive_link"] for i in items if i.get("drive_link")]
    drive_html = ""
    if drive_links:
        drive_html = (
            f' <a href="{drive_links[0]}" style="color:{BLUE};font-size:9pt;">'
            f'[Full outputs in Drive]</a>'
        )

    prose = " ".join(sentences)
    return (
        f'<p style="font-family:Georgia,serif;font-size:10pt;color:{TEXT_DARK};'
        f'line-height:1.6;margin:8px 0;">'
        f'{prose}{drive_html}'
        f'</p>'
    )


# ---------------------------------------------------------------------------
# SECTION 3 — TONIGHT'S SEARCH
# Read sectors and gate candidate from eod_incubator_config.json
# ---------------------------------------------------------------------------

def collect_incubator_config() -> dict:
    """Load tonight's incubator sector config."""
    try:
        if EOD_CONFIG_PATH.exists():
            return json.loads(EOD_CONFIG_PATH.read_text())
    except Exception as e:
        logger.warning(f"eod_incubator_config read failed: {e}")
    # Default if config missing
    return {
        "sectors_tonight": ["Travel Tech B2B", "GitHub New Releases", "Claude Code"],
        "gate_candidate": None,
        "nomination_time": "17:30",
        "last_updated": _mt_date_str(),
    }


def _render_incubator_section(cfg: dict) -> str:
    sectors = cfg.get("sectors_tonight", [])
    gate = cfg.get("gate_candidate")
    nomination_time = cfg.get("nomination_time", "17:30")

    sector_header_text = " &middot; ".join(sectors) if sectors else "Sectors TBD"

    # Three bullet lines, one per sector
    sector_rows = ""
    for sector in sectors[:3]:
        sector_rows += _bullet_row(f"&#x2192; {sector} &mdash; nightly scan")

    # Gate line
    if gate and gate.get("status") == "approved":
        gate_line = _bullet_row(
            f'Gate: <strong>{gate.get("name","?")}</strong> &rarr; '
            f'{gate.get("owner","?")} build overnight &check;'
        )
    elif gate:
        gate_line = _bullet_row(
            f'Gate candidate: {gate.get("name","?")} &mdash; pending nomination at {nomination_time}'
        )
    else:
        gate_line = _bullet_row("Gate: Nothing passed tonight")

    return sector_rows + gate_line


# ---------------------------------------------------------------------------
# SECTION 4 — OVERNIGHT QUEUE
# Missions with auto_execute: true OR explicitly scheduled for overnight
# Falls back to "Wing standing watch." if empty
# ---------------------------------------------------------------------------

def collect_overnight_queue() -> list[dict]:
    """Missions queued for overnight autonomous run."""
    results = []
    try:
        board = json.loads(MISSION_BOARD_PATH.read_text())
        missions = board.get("missions", board.get("tasks", []))
        for m in missions:
            if m.get("status") in ("completed", "archived"):
                continue
            # Include if explicitly flagged auto_execute
            if m.get("auto_execute"):
                results.append({
                    "id": m.get("id", ""),
                    "title": m.get("title", "")[:80],
                    "owner": m.get("assigned_to", ""),
                    "priority": m.get("priority", ""),
                })
    except Exception as e:
        logger.warning(f"Overnight queue collection failed: {e}")
    return results


# ---------------------------------------------------------------------------
# SECTION 1b — API REGISTRY ALERTS (merged into BEFORE YOU SLEEP)
# Surfaces MISSING_KEY / EXPIRED credentials from config/api_registry_status.json
# ---------------------------------------------------------------------------

def collect_registry_alerts() -> list[dict]:
    """Return alert items for credentials with MISSING_KEY or EXPIRED scan status."""
    status_path = THUNDERBIRD_DIR / "config" / "api_registry_status.json"
    items = []
    try:
        if not status_path.exists():
            return []
        data = json.loads(status_path.read_text())
        for cred in data.get("credentials", []):
            scan_status = cred.get("scan_status", "")
            if scan_status in ("MISSING_KEY", "EXPIRED"):
                items.append({
                    "type": "REGISTRY_ALERT",
                    "title": f"API KEY {scan_status}: {cred['name']} ({cred.get('env_var', 'no env_var')})",
                })
    except Exception as e:
        logger.warning(f"Registry alert collection failed: {e}")
    return items


# ---------------------------------------------------------------------------
# HTML BUILDER — EOD BRIEF
# ---------------------------------------------------------------------------

def build_html_eod_brief(
    date_label: str,
    tonight_urgent: list,
    completions_prose: str,
    incubator_cfg: dict,
    overnight_queue: list,
) -> str:
    """Assemble cream/blue/navy HTML EOD brief."""

    sections = []

    # ── HEADER ─────────────────────────────────────────────────────────────────
    header = f"""
<table width="100%" cellpadding="0" cellspacing="0"
       style="background:{CREAM};font-family:Georgia,serif;">
  <tr>
    <td style="background:{NAVY};padding:20px 28px;text-align:center;">
      <div style="color:#ffffff;font-size:22pt;font-weight:900;letter-spacing:4px;
                  font-family:Arial Black,Arial,sans-serif;">&#x1F985; THUNDERBIRD</div>
      <div style="color:{GOLD};font-size:10pt;letter-spacing:3px;
                  font-family:Arial,sans-serif;margin-top:4px;">
        {date_label} &nbsp;&bull;&nbsp; 1800 MT &nbsp;&bull;&nbsp; END OF DAY
      </div>
    </td>
  </tr>
</table>
"""

    # ── SECTION 1: BEFORE YOU SLEEP (suppressed if empty) ─────────────────────
    if tonight_urgent:
        rows = ""
        for item in tonight_urgent:
            itype = item.get("type", "")
            if itype == "WF17_DRAFT":
                rows += _bullet_row(
                    f"WF-17 PENDING SEND &rarr; {item['title']} "
                    f"&nbsp;<em>to {item.get('to','')}</em>"
                )
            elif itype == "FPD_URGENT":
                rows += _bullet_row(
                    f"&#x26A0; FPD DUE TONIGHT/TOMORROW &rarr; {item['title']}"
                )
            elif itype == "REGISTRY_ALERT":
                rows += _bullet_row(
                    f"&#x1F511; {item.get('title', '')}"
                )
            else:
                rows += _bullet_row(item.get("title", ""))
        sections.append(_section_header("BEFORE YOU SLEEP") + rows)

    # ── SECTION 2: WHAT WE DID TODAY ──────────────────────────────────────────
    sections.append(_section_header("WHAT WE DID TODAY") + completions_prose)

    # ── SECTION 3: TONIGHT'S SEARCH ───────────────────────────────────────────
    sectors = incubator_cfg.get("sectors_tonight", [])
    sector_label = " &middot; ".join(sectors) if sectors else "SECTORS TBD"
    sections.append(
        _section_header(f"TONIGHT'S SEARCH &mdash; {sector_label}")
        + _render_incubator_section(incubator_cfg)
    )

    # ── SECTION 4: OVERNIGHT QUEUE ────────────────────────────────────────────
    if overnight_queue:
        rows = ""
        for m in overnight_queue:
            pri = m.get("priority", "")
            owner = m.get("owner", "")
            owner_str = f"&nbsp;<em style='color:#555;font-size:8pt;'>{owner}</em>" if owner else ""
            rows += _bullet_row(
                f"[{m['id']}] {m['title']} "
                f"<span style='color:{NAVY};font-size:8pt;font-weight:700;'>{pri}</span>"
                f"{owner_str}"
            )
        sections.append(_section_header("OVERNIGHT QUEUE") + rows)
    else:
        sections.append(
            _section_header("OVERNIGHT QUEUE")
            + f'<p style="font-family:Georgia,serif;font-size:10pt;color:#888;'
              f'margin:8px 14px;">Wing standing watch.</p>'
        )

    # ── FOOTER ─────────────────────────────────────────────────────────────────
    footer = (
        f'<div style="margin-top:20px;padding:14px 28px;background:{NAVY};'
        f'font-family:Arial,Helvetica,sans-serif;font-size:8pt;color:#aabbcc;'
        f'text-align:center;letter-spacing:1px;">'
        f'Reply to redirect overnight work &mdash; changes catch before 1800.'
        f'&nbsp;&bull;&nbsp; Thunderbird Wing &nbsp;&bull;&nbsp; Dreams2Memories Travel, LLC'
        f'</div>'
    )

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

    try:
        import premailer
        full_html = premailer.transform(full_html, remove_classes=False, strip_important=False)
    except Exception as pm_e:
        logger.warning(f"premailer inlining failed (continuing): {pm_e}")

    return full_html


# ---------------------------------------------------------------------------
# SEND — separate from AM brief to protect AM brief's feedback-config chain
# ---------------------------------------------------------------------------

def _retry_on_transient(max_attempts: int = 3, base_delay: float = 2.0):
    """Decorator: retry on transient Gmail API / network failures.

    Catches DNS failures, network timeouts, and temporary API errors.
    Uses exponential backoff: 2s, 4s, 8s.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except (socket.gaierror, TimeoutError, OSError) as e:
                    last_exception = e
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.warning(
                            f"Transient error on attempt {attempt}/{max_attempts}: {type(e).__name__}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"Final attempt {attempt}/{max_attempts} failed: {type(e).__name__}: {e}"
                        )
                except Exception as e:
                    # Non-transient errors (auth, quota, malformed request) — fail immediately
                    logger.error(f"Non-transient error (no retry): {type(e).__name__}: {e}")
                    raise
            # If we exhausted retries, raise the last transient exception
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


@_retry_on_transient(max_attempts=3, base_delay=2.0)
def _send_eod_brief(subject: str, html_body: str) -> dict:
    """Send EOD brief via d2mconcierge persona token to Commander inbox.

    Intentionally separate from _send_brief in thunderbird_daily_brief.py
    to avoid clobbering last_brief_message_id used for AM feedback-reply tracking.

    Retries transient network/DNS failures up to 3 times with exponential backoff.
    """
    from thunderbird_google_auth import get_persona_gmail

    svc = get_persona_gmail()

    msg = MIMEMultipart("alternative")
    msg["to"] = COMMANDER_EMAIL
    msg["from"] = f'"Thunderbird Wing" <{WING_EMAIL}>'
    msg["reply-to"] = WING_EMAIL
    msg["subject"] = subject

    plain = f"Thunderbird EOD Brief — {subject}\n\nPlease view in HTML email client."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()

    message_id = result.get("id", "")
    thread_id = result.get("threadId", "")

    # Write to EOD-specific feedback config (isolated from AM brief config)
    try:
        cfg = json.loads(EOD_FEEDBACK_CONFIG_PATH.read_text()) if EOD_FEEDBACK_CONFIG_PATH.exists() else {}
        cfg["last_eod_message_id"] = message_id
        cfg["last_eod_thread_id"] = thread_id
        cfg["last_eod_date"] = _mt_date_str()
        EOD_FEEDBACK_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
    except Exception as fc_e:
        logger.warning(f"EOD feedback config update failed: {fc_e}")

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
    parser = argparse.ArgumentParser(description="Thunderbird EOD Brief")
    parser.add_argument("--preview", action="store_true",
                        help="Write HTML to /tmp, do not send")
    parser.add_argument("--force", action="store_true",
                        help="Ignore send-lock (testing only)")
    args = parser.parse_args()

    date_str = _mt_date_str()
    day_label = _mt_day_label()
    subject = f"\U0001F985 THUNDERBIRD // {day_label} · 1800 MT · EOD"

    # ── SEND LOCK CHECK ─────────────────────────────────────────────────────
    if not args.preview and not args.force:
        if _lock_exists(date_str):
            logger.info(f"EOD send-lock exists for {date_str} — already sent today. Exiting.")
            return

    (THUNDERBIRD_DIR / "logs").mkdir(exist_ok=True)
    logger.info(f"Thunderbird EOD Brief — {date_str} — building...")

    # ── DATA COLLECTION ────────────────────────────────────────────────────
    logger.info("Collecting Section 1: tonight-urgent items...")
    tonight_urgent = collect_tonight_urgent()
    registry_alerts = collect_registry_alerts()
    tonight_urgent.extend(registry_alerts)
    logger.info(f"  {len(tonight_urgent)} urgent items ({len(registry_alerts)} registry alerts) "
                f"(section {'visible' if tonight_urgent else 'SUPPRESSED'})")

    logger.info("Collecting Section 2: today's completions...")
    completions = collect_todays_completions()
    logger.info(f"  {len(completions)} completions")
    completions_prose = _humanize_completions(completions)

    logger.info("Collecting Section 3: incubator config...")
    incubator_cfg = collect_incubator_config()
    logger.info(f"  Sectors: {incubator_cfg.get('sectors_tonight')}")

    logger.info("Collecting Section 4: overnight queue...")
    overnight_queue = collect_overnight_queue()
    logger.info(f"  {len(overnight_queue)} missions queued (falling back to 'standing watch' if 0)")

    # ── BUILD HTML ─────────────────────────────────────────────────────────
    logger.info("Building HTML EOD brief...")
    html = build_html_eod_brief(
        date_label=day_label,
        tonight_urgent=tonight_urgent,
        completions_prose=completions_prose,
        incubator_cfg=incubator_cfg,
        overnight_queue=overnight_queue,
    )
    logger.info(f"  HTML built: {len(html):,} bytes")

    # ── PREVIEW OR SEND ────────────────────────────────────────────────────
    if args.preview:
        out_path = Path(f"/tmp/thunderbird_eod_{date_str.replace('-','')}.html")
        out_path.write_text(html, encoding="utf-8")
        logger.info(f"PREVIEW written to: {out_path}")
        print(f"Preview: {out_path}")
        return

    logger.info("Sending EOD brief...")
    try:
        result = _send_eod_brief(subject, html)
        logger.info(f"  Sent OK — message_id: {result.get('message_id')}")
    except Exception as send_e:
        logger.error(f"EOD send FAILED: {send_e}")
        raise

    _write_lock(date_str)
    logger.info(f"EOD brief complete — {date_str}")
    print(f"Thunderbird EOD Brief sent — {date_str} — message_id: {result.get('message_id','?')}")


if __name__ == "__main__":
    main()

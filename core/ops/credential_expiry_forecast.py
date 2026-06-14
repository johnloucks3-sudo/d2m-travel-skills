#!/usr/bin/env python3
"""
thunderbird-credential-expiry-forecast — 14-day forward look on OAuth tokens.

Scans all token files in creds/ and known locations.
Checks expiry fields. Alerts Commander 14 days before expiry.
Runs daily at 04:00 MDT — proactive, before keepalives might fail.

Schedule: Daily 04:00 MDT via systemd timer
Output:   OpsCenter/logs/credential_expiry.log
          hale_decisions.md on alerts
          Gmail draft on any expiry < 14 days
"""

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
CREDS_DIR = ROOT / "creds"
LOG_PATH = ROOT / "OpsCenter/logs/credential_expiry.log"
AUDIT_LOG = ROOT / "OpsCenter/logs/credential_expiry.jsonl"
HALE_DECISIONS = ROOT / "hale_decisions.md"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CRED-EXPIRY] %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_PATH)],
)
log = logging.getLogger(__name__)

WARN_DAYS = 14  # Alert this many days before expiry

# Known token files and their expiry field names
TOKEN_FILES = [
    (CREDS_DIR / "gmail_token.json", "expiry", "johnloucks3 Gmail"),
    (CREDS_DIR / "token.json", "expiry", "d2mconcierge Gmail"),
    (CREDS_DIR / "calendar_token.json", "expiry", "johnloucks3 Calendar"),
    (CREDS_DIR / "d2mconcierge_calendar_token.json", "expiry", "d2mconcierge Calendar"),
    (ROOT / ".env", None, "ENV file"),  # check existence, not expiry
    (CREDS_DIR / "amadeus_credentials.json", None, "Amadeus API"),
    (CREDS_DIR / "hotelbeds_credentials.json", None, "Hotelbeds API"),
]

# Additional JSON token files to auto-scan in creds/
AUTO_SCAN_PATTERNS = ["*token*.json", "*oauth*.json", "*credentials*.json", "*auth*.json"]


def check_json_token(fp: Path, expiry_field: str, label: str) -> dict | None:
    """Check a JSON token file for expiry."""
    if not fp.exists():
        return {"file": str(fp), "label": label, "status": "MISSING", "days_until_expiry": None}

    try:
        data = json.loads(fp.read_text())
    except Exception as e:
        return {"file": str(fp), "label": label, "status": "PARSE_ERROR", "error": str(e), "days_until_expiry": None}

    if expiry_field is None:
        return None  # Static credential file — just check existence

    expiry_val = data.get(expiry_field)
    if not expiry_val:
        return None  # No expiry field — perpetual token or not applicable

    now = datetime.now(tz=timezone.utc)
    try:
        if isinstance(expiry_val, (int, float)):
            expiry_dt = datetime.fromtimestamp(expiry_val, tz=timezone.utc)
        elif isinstance(expiry_val, str):
            # Try various formats
            for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S.%f+00:00", "%Y-%m-%d %H:%M:%S+00:00"):
                try:
                    expiry_dt = datetime.strptime(expiry_val.replace("+00:00", "Z"), fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
            else:
                return None
        else:
            return None

        days_left = (expiry_dt - now).days
        status = "OK" if days_left > WARN_DAYS else ("EXPIRING_SOON" if days_left > 0 else "EXPIRED")

        return {
            "file": str(fp),
            "label": label,
            "expiry": expiry_dt.isoformat(),
            "days_until_expiry": days_left,
            "status": status,
        }
    except Exception as e:
        log.debug(f"Could not parse expiry for {fp}: {e}")
        return None


def scan_all_tokens() -> list[dict]:
    results = []

    # Check known token files
    for fp, expiry_field, label in TOKEN_FILES:
        result = check_json_token(fp, expiry_field, label)
        if result:
            results.append(result)
            if result["status"] != "OK":
                log.warning(f"{label}: {result['status']} — {result.get('days_until_expiry', 'N/A')} days left")
            else:
                log.info(f"{label}: OK — {result.get('days_until_expiry', '?')} days left")

    # Auto-scan creds/ for any additional token files
    if CREDS_DIR.exists():
        known_files = {fp for fp, _, _ in TOKEN_FILES}
        for pattern in AUTO_SCAN_PATTERNS:
            for fp in CREDS_DIR.glob(pattern):
                if fp in known_files:
                    continue
                result = check_json_token(fp, "expiry", fp.name)
                if result and result.get("status") in ("EXPIRING_SOON", "EXPIRED"):
                    results.append(result)

    return results


def write_hale_decision(alerts: list[dict], run_dt: datetime) -> None:
    if not alerts:
        return
    lines = [
        f"\n### {run_dt.strftime('%Y-%m-%d %H:%M:%S')} — Autonomous Decision (Tier T0)\n",
        f"**Decision:** Credential expiry forecast: {len(alerts)} credential(s) require attention\n",
    ]
    for a in alerts:
        lines.append(
            f"  - {a['label']}: {a['status']} — {a.get('days_until_expiry', 'N/A')} days left\n"
        )
    lines.append("**Domain:** Credentials / Token hygiene\n**Type:** proactive alert\n**Outcome:** surfaced to Commander\n")
    with open(HALE_DECISIONS, "a") as f:
        f.writelines(lines)


def draft_expiry_alert(alerts: list[dict]) -> None:
    try:
        sys.path.insert(0, str(ROOT))
        from core.email.thunderbird_gmail import gmail_create_draft_sync

        rows = "\n".join(
            f"<tr><td style='padding:4px;'>{a['label']}</td><td style='padding:4px;color:{'red' if a['status']=='EXPIRED' else 'orange'};'><b>{a['status']}</b></td><td style='padding:4px;'>{a.get('days_until_expiry','N/A')} days</td></tr>"
            for a in alerts
        )
        body = f"""<div style='background:#f7f3ea;padding:20px;font-family:Georgia;color:#0000ff;'>
<p>Commander —</p>
<p><strong>CREDENTIAL EXPIRY ALERT</strong></p>
<p>The following tokens expire within {WARN_DAYS} days or are already expired:</p>
<table border='1' cellpadding='4' style='border-collapse:collapse;color:#0000ff;'>
<tr><th>Credential</th><th>Status</th><th>Days Left</th></tr>
{rows}
</table>
<p>Action required: re-authorize affected tokens before expiry to prevent keepalive failures.</p>
<p>— Hale</p>
</div>"""
        gmail_create_draft_sync(
            to="d2mconcierge@gmail.com",
            subject=f"[CRED EXPIRY] {len(alerts)} Token(s) Expiring — Action Required",
            body=body,
        )
        log.info(f"Gmail draft created for {len(alerts)} expiring credential(s)")
    except Exception as e:
        log.warning(f"Could not create Gmail draft: {e}")


def main() -> int:
    run_dt = datetime.now()
    log.info(f"Credential expiry forecast — {run_dt.date()}")

    results = scan_all_tokens()
    alerts = [r for r in results if r.get("status") in ("EXPIRING_SOON", "EXPIRED", "MISSING")]

    entry = {
        "ts": run_dt.isoformat(),
        "total_checked": len(results),
        "alerts": len(alerts),
        "detail": alerts,
        "all": results,
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    if alerts:
        write_hale_decision(alerts, run_dt)
        draft_expiry_alert(alerts)
        log.warning(f"{len(alerts)} credential alert(s)")
    else:
        log.info(f"All {len(results)} credential(s) healthy")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Google Sheets export for Looker Studio — Claude usage snapshots."""
import json, sqlite3, logging, sys
from pathlib import Path
from datetime import datetime, timezone

THUNDERBIRD = Path.home() / "Thunderbird"
DB = THUNDERBIRD / "storage" / "ai_costs.db"
SHEET_ID_ENV = "D2M_METRICS_SHEET_ID"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

logger = logging.getLogger("sheet_export")


def load_sheet_id() -> str | None:
    import os
    sid = os.environ.get(SHEET_ID_ENV)
    if sid:
        return sid
    env_path = THUNDERBIRD / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith(SHEET_ID_ENV + "="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    return None


def get_client():
    import gspread
    from google.oauth2.credentials import Credentials

    # 1. Drive token — works, has auth/drive scope
    dt = THUNDERBIRD / "creds" / "drive_token.json"
    if dt.exists():
        try:
            data = json.loads(dt.read_text())
            creds = Credentials.from_authorized_user_info(data)
            return gspread.authorize(creds)
        except Exception as e:
            logger.warning(f"Drive token failed: {e}")

    # 2. Service account (if sheet is shared with it)
    sa = THUNDERBIRD / "creds" / "service_account.json"
    if sa.exists():
        try:
            return gspread.service_account(filename=str(sa))
        except Exception as e:
            logger.warning(f"Service account failed: {e}")

    # 3. OAuth token (interactive setup)
    token_path = THUNDERBIRD / "creds" / "sheets_token.json"
    if token_path.exists():
        try:
            return gspread.oauth(
                credentials_filename=str(THUNDERBIRD / "credentials.json"),
                authorized_user_filename=str(token_path),
            )
        except Exception as e:
            logger.warning(f"OAuth token failed: {e}")

    return None


def write_snapshot(pct: float, dollars: float, source: str = "manual") -> bool:
    sid = load_sheet_id()
    if not sid:
        logger.error("No D2M_METRICS_SHEET_ID found")
        return False

    client = get_client()
    if not client:
        logger.error("No working Google auth found — run auth setup first")
        return False

    try:
        sheet = client.open_by_key(sid)
        ws = _ensure_worksheet(sheet)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        row = [ts, round(pct, 1), round(dollars, 2), source]
        ws.append_row(row, value_input_option="USER_ENTERED")
        logger.info(f"Wrote to sheet: {pct}%, ${dollars} ({source})")
        return True
    except Exception as e:
        logger.error(f"Sheet write failed: {e}", exc_info=True)
        return False


def _ensure_worksheet(sheet):
    name = "Claude_Usage"
    for ws in sheet.worksheets():
        if ws.title == name:
            return ws
    ws = sheet.add_worksheet(title=name, rows=1000, cols=10)
    ws.append_row(["timestamp", "weekly_sonnet_pct", "monthly_spent_usd", "source"])
    return ws


def auth_setup():
    """Run this once to authorize gspread.
    Headless-safe: prints a URL, you open it in your browser,
    paste the authorization code back into the terminal."""
    import gspread
    from google_auth_oauthlib.flow import InstalledAppFlow
    from gspread.auth import store_credentials, DEFAULT_SCOPES

    sid = load_sheet_id()
    if not sid:
        print("ERROR: Set D2M_METRICS_SHEET_ID in .env first")
        sys.exit(1)

    creds_file = str(THUNDERBIRD / "credentials.json")
    token_file = THUNDERBIRD / "creds" / "sheets_token.json"

    print("=" * 60)
    print("Google Sheets Authorization — Headless Mode")
    print("=" * 60)
    print()
    print("Step 1: Open the URL below in your browser")
    print("Step 2: Sign in to the Dreams2Memories Google account")
    print("Step 3: Grant permissions")
    print("Step 4: Copy the ENTIRE authorization code")
    print("Step 5: Paste it here and press Enter")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(
        creds_file,
        scopes=DEFAULT_SCOPES,
    )
    auth_url, _ = flow.authorization_url(prompt="consent")
    print(f"URL (open in browser):\n{auth_url}\n")
    code = input("Paste authorization code: ").strip()
    flow.fetch_token(code=code)
    store_credentials(flow.credentials, filename=token_file)

    client = gspread.oauth(
        credentials_filename=creds_file,
        authorized_user_filename=str(token_file),
        scopes=DEFAULT_SCOPES,
    )

    sheet = client.open_by_key(sid)
    _ensure_worksheet(sheet)
    print(f"\nAuth OK. Sheet '{sheet.title}' ready — worksheets: {[w.title for w in sheet.worksheets()]}")
    print(f"Token saved to: creds/sheets_token.json")


def export_all():
    """Read latest snapshots from SQLite and push to sheet."""
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM plan_snapshots ORDER BY ts DESC LIMIT 10"
    ).fetchall()
    conn.close()

    if not rows:
        logger.info("No snapshots to export")
        return True

    client = get_client()
    if not client:
        logger.error("No Google auth available")
        return False

    sid = load_sheet_id()
    if not sid:
        return False

    sheet = client.open_by_key(sid)
    ws = _ensure_worksheet(sheet)

    for r in rows:
        ts = r["ts"]
        pct = round(r.get("monthly_pct") or r.get("weekly_sonnet_pct") or 0, 1)
        dollars = round(r.get("monthly_spent") or 0, 2)
        source = "sqlite_export"
        ws.append_row([ts, pct, dollars, source], value_input_option="USER_ENTERED")

    logger.info(f"Exported {len(rows)} rows to sheet")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if "--auth" in sys.argv:
        auth_setup()
    elif "--export" in sys.argv:
        export_all()
    else:
        print("Usage: python sheet_export.py --auth | --export")

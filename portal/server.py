"""
Dreams2Memories Travel, LLC — Client Portal Server
portal.d2mluxury.quest · Port 8780
FastAPI + magic-link auth + dossier integration
"""

import hashlib
import json
import logging
import os
import re
import secrets
import smtplib
import time
from collections import defaultdict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

# ── Paths ────────────────────────────────────────────────────────────────────

PORTAL_DIR = Path(__file__).parent
DOSSIER_DIR = Path("/home/john/Thunderbird/dossiers")
TOKEN_STORE = PORTAL_DIR / ".token_store.json"   # ephemeral, not committed
SESSION_STORE = PORTAL_DIR / ".session_store.json"

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("d2m-portal")

# ── Config (env overrides) ────────────────────────────────────────────────────

SMTP_HOST   = os.getenv("D2M_SMTP_HOST", "smtp.gmail.com")
SMTP_PORT   = int(os.getenv("D2M_SMTP_PORT", "587"))
SMTP_USER   = os.getenv("D2M_SMTP_USER", "d2mconcierge@gmail.com")
SMTP_PASS   = os.getenv("D2M_SMTP_PASS", "")          # set in environment
PORTAL_URL  = os.getenv("D2M_PORTAL_URL", "https://portal.d2mluxury.quest")
TOKEN_TTL   = int(os.getenv("D2M_TOKEN_TTL", "86400"))   # 24 hours
SESSION_TTL = int(os.getenv("D2M_SESSION_TTL", "604800")) # 7 days
RATE_LIMIT  = int(os.getenv("D2M_RATE_LIMIT", "5"))       # contact msgs/hour

# ── Token / Session persistence ───────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def _prune_expired(store: dict, ttl_key: str = "expires") -> dict:
    now = time.time()
    return {k: v for k, v in store.items() if v.get(ttl_key, 0) > now}


# In-memory stores (loaded from disk on startup)
_tokens: dict   = _prune_expired(_load_json(TOKEN_STORE))
_sessions: dict = _prune_expired(_load_json(SESSION_STORE))
# Rate limit: email → list of timestamps
_contact_rate: dict[str, list] = defaultdict(list)

# ── Client registry from dossiers ────────────────────────────────────────────

def _extract_emails_from_dossier(path: Path) -> list[dict]:
    """
    Parse a dossier markdown file and return a list of client records:
    { email, name, client_key (filename stem) }
    """
    text = path.read_text(errors="ignore")
    # Match lines like: Email: foo@bar.com
    emails = re.findall(r"Email\s*:\s*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", text)
    # Filter out internal/staff addresses
    internal = {"d2mconcierge@gmail.com", "concierge@d2mluxury.quest",
                "johnloucks3@gmail.com", "johnloucks75@gmail.com"}
    records = []
    for email in set(emails):
        if email.lower() not in internal:
            records.append({
                "email": email.lower(),
                "client_key": path.stem,
            })
    return records


def load_client_registry() -> dict[str, list[str]]:
    """
    Returns { normalized_email: [dossier_stem, ...] }
    Allows one email to appear in multiple dossiers (travel party).
    """
    registry: dict[str, list[str]] = defaultdict(list)
    if not DOSSIER_DIR.exists():
        log.warning("Dossier directory not found: %s", DOSSIER_DIR)
        return registry
    for path in DOSSIER_DIR.glob("*.md"):
        if path.name == "CLAUDE.md":
            continue
        for rec in _extract_emails_from_dossier(path):
            registry[rec["email"]].append(rec["client_key"])
    return registry


CLIENT_REGISTRY: dict[str, list[str]] = load_client_registry()
log.info("Client registry loaded: %d known emails", len(CLIENT_REGISTRY))

# ── Dossier parser ────────────────────────────────────────────────────────────

def _parse_date(raw: str) -> Optional[str]:
    """Normalize various date formats to YYYY-MM-DD, return None on failure."""
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y", "%m/%d/%Y",
                "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Handle short forms like "Apr 23, 2026" with ordinals stripped
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", raw)
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _days_until(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (target - datetime.utcnow().date()).days
    except ValueError:
        return None


def parse_dossier(stem: str) -> dict:
    """
    Parse a dossier .md file into structured trip data for the portal.
    Returns a dict with: title, subtitle, embark_date, disembark_date,
    destinations, payment_status, key_dates, documents, raw_excerpt.
    """
    path = DOSSIER_DIR / f"{stem}.md"
    if not path.exists():
        return {}

    text = path.read_text(errors="ignore")
    lines = text.splitlines()

    result: dict = {
        "client_key": stem,
        "title": stem.replace("_", " "),
        "subtitle": "",
        "embark_date": None,
        "disembark_date": None,
        "destinations": [],
        "payment": {
            "total": None,
            "paid": None,
            "balance": None,
            "due_date": None,
            "status": "unknown",
        },
        "key_dates": [],
        "documents": [],
        "raw_excerpt": text[:800],
    }

    # ── Title: first H1 or H2 ──
    for line in lines:
        if line.startswith("# "):
            result["title"] = line.lstrip("# ").strip()
            break
        if line.startswith("## "):
            result["subtitle"] = line.lstrip("# ").strip()
            break

    # ── Trip name from first bold cruise/ship line ──
    m = re.search(r"Trip:\s*(.+)", text)
    if m:
        result["title"] = m.group(1).strip()
    m = re.search(r"Ship:\s*(.+)", text)
    if m:
        result["subtitle"] = m.group(1).strip()

    # ── Dates ──
    for pattern, key in [
        (r"Embarkation[:\s]+([A-Za-z0-9, ]+\d{4})", "embark_date"),
        (r"Disembarkation[:\s]+([A-Za-z0-9, ]+\d{4})", "disembark_date"),
        (r"EMBARKATION[:\s]+([A-Za-z0-9, ]+)", "embark_date"),
        (r"Disembarkation[:\s]+([A-Za-z0-9, ]+)", "disembark_date"),
    ]:
        if not result[key]:
            m = re.search(pattern, text)
            if m:
                result[key] = _parse_date(m.group(1))

    # ── Destinations: pull Route or bullet points with → ──
    m = re.search(r"Route:\s*(.+)", text)
    if m:
        result["destinations"] = [d.strip() for d in re.split(r"[→,]", m.group(1)) if d.strip()]

    # ── Payment info ──
    # Use [^\d]* to skip over bold/italic markdown markers before the dollar amount
    pm = result["payment"]
    m = re.search(r"Total Booking Amount[^\d]*?([\d,]+)", text)
    if m:
        pm["total"] = m.group(1).replace(",", "")
    m = re.search(r"Paid to Date[^\d]*?([\d,]+)", text)
    if m:
        pm["paid"] = m.group(1).replace(",", "")
    m = re.search(r"Balance Due[^\d]*?([\d,]+)", text)
    if m:
        pm["balance"] = m.group(1).replace(",", "")

    # ── Payment due date ──
    for pat in [
        r"DUE\s+(\w+ \d+,? \d{4})",
        r"FINAL PAYMENT DUE[^—\n]*?(\w+ \d+,? \d{4})",
        r"Final Payment[:\s]+(\w+ \d+,? \d{4})",
    ]:
        m = re.search(pat, text)
        if m:
            pm["due_date"] = _parse_date(m.group(1))
            break

    # Status logic
    paid_full = bool(re.search(r"PAID IN FULL|paid in full", text))
    balance = pm.get("balance")
    if paid_full or balance == "0":
        pm["status"] = "paid"
    elif balance and balance != "0":
        pm["status"] = "balance_due"
    elif re.search(r"PAYMENT DUE", text):
        pm["status"] = "balance_due"

    # ── Key dates from markdown table rows ──
    # Look for | Date | Milestone | table pattern
    date_rows = re.findall(
        r"\|\s*([\d]{4}-[\d]{2}-[\d]{2}|\w+ \d+)\s*\|[^|]*\|[^|]*\|\s*([^\|]+)\s*\|",
        text
    )
    # Also look for simpler | Date | Milestone | two-col tables
    date_rows2 = re.findall(
        r"\|\s*([\d]{4}-[\d]{2}-[\d]{2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^|]{1,20})\s*\|\s*([^\|]{5,80})\s*\|",
        text
    )
    seen = set()
    for raw_date, label in (date_rows + date_rows2):
        parsed = _parse_date(raw_date.strip()) or raw_date.strip()
        label = label.strip()
        if label.lower() in ("date", "milestone", "status", "category", "---", ""):
            continue
        key = (parsed, label[:40])
        if key not in seen:
            seen.add(key)
            result["key_dates"].append({
                "date": parsed,
                "days_until": _days_until(parsed if len(parsed) == 10 else None),
                "label": label,
            })

    result["key_dates"].sort(key=lambda x: x["date"])

    # ── Documents: any line mentioning a doc / PDF / confirmation ──
    doc_patterns = [
        r"(Booking Confirmation[^\n]*)",
        r"(E-Ticket[^\n]*)",
        r"(Invoice[^\n]*)",
        r"(Travel Insurance[^\n]*)",
        r"(Itinerary PDF[^\n]*)",
        r"(PNR[s]?[:\s]+[A-Z0-9]+[^\n]*)",
    ]
    for pat in doc_patterns:
        m = re.search(pat, text)
        if m:
            label = m.group(1).strip()[:80]
            if label not in result["documents"]:
                result["documents"].append(label)

    # Countdown
    result["days_until_departure"] = _days_until(result["embark_date"])

    return result


# ── Email helpers ─────────────────────────────────────────────────────────────

def _send_magic_link_email(to_email: str, token: str) -> bool:
    link = f"{PORTAL_URL}/api/auth/verify?token={token}"
    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f7f3ea;font-family:Georgia,serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 20px;">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;overflow:hidden;
                    box-shadow:0 2px 16px rgba(10,22,40,0.10);">
        <tr>
          <td style="background:#0a1628;padding:28px 32px;text-align:center;">
            <div style="color:#c9a94e;font-size:11px;letter-spacing:3px;
                        text-transform:uppercase;font-family:Georgia,serif;">
              Dreams2Memories Travel, LLC
            </div>
            <div style="color:#8a9ab5;font-size:10px;letter-spacing:2px;
                        text-transform:uppercase;margin-top:4px;">
              Luxury Travel, Personally Crafted
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:40px 40px 32px;text-align:center;">
            <p style="font-size:22px;color:#0a1628;margin:0 0 16px;font-weight:normal;">
              Your Portal Access Link
            </p>
            <p style="font-size:15px;color:#555;line-height:1.7;margin:0 0 32px;">
              Click below to sign in to your client portal. This link expires in 24 hours
              and can only be used once.
            </p>
            <a href="{link}"
               style="display:inline-block;background:#0a1628;color:#c9a94e;
                      text-decoration:none;padding:14px 36px;border-radius:6px;
                      font-size:14px;letter-spacing:1px;font-family:Georgia,serif;">
              Access My Portal
            </a>
            <p style="font-size:12px;color:#999;margin:28px 0 0;line-height:1.6;">
              If the button doesn't work, copy this link:<br>
              <span style="color:#0000ff;word-break:break-all;">{link}</span>
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f7f3ea;padding:20px 32px;text-align:center;
                     border-top:1px solid #e8e0d0;">
            <p style="font-size:11px;color:#888;margin:0;">
              If you didn't request this, you can safely ignore it.<br>
              &copy; 2026 Dreams2Memories Travel, LLC &middot; Colorado Springs, CO
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Dreams2Memories Portal Access Link"
    msg["From"]    = f"Dani Moreau — D2M Travel <{SMTP_USER}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(f"Your portal access link: {link}\n\nExpires in 24 hours.", "plain"))
    msg.attach(MIMEText(html, "html"))

    if not SMTP_PASS:
        log.warning("SMTP_PASS not set — magic link email not sent. Link: %s", link)
        return False  # dev mode: link logged above

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as srv:
            srv.ehlo()
            srv.starttls()
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(SMTP_USER, to_email, msg.as_string())
        log.info("Magic link sent to %s", to_email)
        return True
    except Exception as exc:
        log.error("SMTP error sending to %s: %s", to_email, exc)
        return False


def _notify_cos_contact(client_email: str, message: str) -> None:
    """Fire-and-forget email to d2mconcierge notifying COS of portal message."""
    if not SMTP_PASS:
        log.info("COS notify (no SMTP): [%s] %s", client_email, message[:80])
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[Portal Message] from {client_email}"
        msg["From"]    = SMTP_USER
        msg["To"]      = SMTP_USER  # d2mconcierge@gmail.com — COS inbox
        body = (
            f"Portal message received from: {client_email}\n\n"
            f"{'─'*60}\n{message}\n{'─'*60}\n\n"
            "Reply via concierge@d2mluxury.quest"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as srv:
            srv.ehlo(); srv.starttls()
            srv.login(SMTP_USER, SMTP_PASS)
            srv.sendmail(SMTP_USER, SMTP_USER, msg.as_string())
    except Exception as exc:
        log.error("COS notify failed: %s", exc)


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="D2M Client Portal",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[PORTAL_URL, "http://localhost:8780"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Auth helpers ──────────────────────────────────────────────────────────────

def _create_token(email: str) -> str:
    token = secrets.token_urlsafe(32)
    _tokens[token] = {"email": email, "expires": time.time() + TOKEN_TTL}
    _save_json(TOKEN_STORE, _tokens)
    return token


def _consume_token(token: str) -> Optional[str]:
    """Validate and consume a magic-link token. Returns email or None."""
    global _tokens
    _tokens = _prune_expired(_tokens)
    record = _tokens.pop(token, None)
    _save_json(TOKEN_STORE, _tokens)
    if not record:
        return None
    return record["email"]


def _create_session(email: str) -> str:
    sid = secrets.token_urlsafe(32)
    _sessions[sid] = {"email": email, "expires": time.time() + SESSION_TTL}
    _save_json(SESSION_STORE, _sessions)
    return sid


def _get_session_email(session_id: Optional[str]) -> Optional[str]:
    if not session_id:
        return None
    global _sessions
    _sessions = _prune_expired(_sessions)
    record = _sessions.get(session_id)
    return record["email"] if record else None


def require_session(session_id: Optional[str] = Cookie(default=None)) -> str:
    email = _get_session_email(session_id)
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Session expired or invalid. Please request a new magic link.")
    return email

# ── Pydantic request models ───────────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: str

class ContactRequest(BaseModel):
    message: str
    subject: Optional[str] = "Portal Message"

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return JSONResponse({
        "status": "ok",
        "service": "d2m-client-portal",
        "known_clients": len(CLIENT_REGISTRY),
    })


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/auth/request")
async def auth_request(body: AuthRequest, request: Request):
    email = body.email.lower().strip()

    # Validate format minimally
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "Invalid email address.")

    # Check client registry
    if email not in CLIENT_REGISTRY:
        log.info("Auth request for unknown email: %s", email)
        # Security: return same message regardless (don't enumerate clients)
        return JSONResponse({
            "ok": True,
            "message": "If that email is on file, you'll receive a magic link shortly.",
        })

    token = _create_token(email)
    sent = _send_magic_link_email(email, token)

    log.info("Magic link created for %s (sent=%s)", email, sent)
    return JSONResponse({
        "ok": True,
        "message": "If that email is on file, you'll receive a magic link shortly.",
        # Dev convenience: expose token when SMTP not configured
        **({"dev_token": token} if not SMTP_PASS else {}),
    })


@app.get("/api/auth/verify")
async def auth_verify(token: str):
    email = _consume_token(token)
    if not email:
        # Return a proper HTML error page
        return HTMLResponse(
            "<html><body style='font-family:Georgia;text-align:center;padding:60px;'>"
            "<h2 style='color:#0a1628;'>Link Expired</h2>"
            "<p style='color:#555;'>This magic link has expired or already been used.</p>"
            "<a href='/' style='color:#0000ff;'>Request a new link</a>"
            "</body></html>",
            status_code=400
        )

    sid = _create_session(email)
    response = RedirectResponse(url="/#dashboard", status_code=302)
    response.set_cookie(
        key="session_id",
        value=sid,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_TTL,
    )
    log.info("Session created for %s", email)
    return response


@app.post("/api/auth/logout")
async def auth_logout(session_id: Optional[str] = Cookie(default=None)):
    if session_id and session_id in _sessions:
        del _sessions[session_id]
        _save_json(SESSION_STORE, _sessions)
    response = JSONResponse({"ok": True})
    response.delete_cookie("session_id")
    return response


@app.get("/api/auth/me")
async def auth_me(email: str = Depends(require_session)):
    dossier_keys = CLIENT_REGISTRY.get(email, [])
    return JSONResponse({"email": email, "dossier_keys": dossier_keys})


# ── Trips ─────────────────────────────────────────────────────────────────────

@app.get("/api/trips")
async def list_trips(email: str = Depends(require_session)):
    keys = CLIENT_REGISTRY.get(email, [])
    trips = []
    for key in keys:
        data = parse_dossier(key)
        if data:
            # Slim summary for dashboard cards
            trips.append({
                "client_key": data["client_key"],
                "title": data["title"],
                "subtitle": data["subtitle"],
                "embark_date": data["embark_date"],
                "disembark_date": data["disembark_date"],
                "destinations": data["destinations"],
                "days_until_departure": data["days_until_departure"],
                "payment_status": data["payment"]["status"],
                "balance": data["payment"]["balance"],
                "balance_due_date": data["payment"]["due_date"],
            })
    trips.sort(key=lambda t: t["embark_date"] or "9999")
    return JSONResponse({"trips": trips})


@app.get("/api/trips/{client_key}")
async def get_trip(client_key: str, email: str = Depends(require_session)):
    allowed = CLIENT_REGISTRY.get(email, [])
    if client_key not in allowed:
        raise HTTPException(403, "Access denied.")
    data = parse_dossier(client_key)
    if not data:
        raise HTTPException(404, "Trip not found.")
    return JSONResponse(data)


# ── Contact ───────────────────────────────────────────────────────────────────

@app.post("/api/contact")
async def contact(
    body: ContactRequest,
    request: Request,
    email: str = Depends(require_session),
):
    # Rate limit: 5 messages/hour per client email
    now = time.time()
    history = [t for t in _contact_rate[email] if now - t < 3600]
    _contact_rate[email] = history
    if len(history) >= RATE_LIMIT:
        raise HTTPException(429, "Too many messages. Please wait before sending again.")

    _contact_rate[email].append(now)

    if not body.message.strip():
        raise HTTPException(400, "Message cannot be empty.")
    if len(body.message) > 2000:
        raise HTTPException(400, "Message too long (max 2000 characters).")

    _notify_cos_contact(email, body.message)
    log.info("Contact message from %s (%d chars)", email, len(body.message))

    return JSONResponse({
        "ok": True,
        "message": "Your message has been received. Dani will be in touch shortly.",
    })


# ── Static / SPA fallback ─────────────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse(PORTAL_DIR / "index.html", media_type="text/html")


# Serve CSS, JS, images from portal dir
app.mount("/static", StaticFiles(directory=str(PORTAL_DIR)), name="static")


# Catch-all for SPA hash routing (client-side routes return index.html)
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    # Don't intercept API or static routes
    if full_path.startswith("api/") or full_path.startswith("static/"):
        raise HTTPException(404)
    return FileResponse(PORTAL_DIR / "index.html", media_type="text/html")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8780,
        log_level="info",
        reload=False,
    )

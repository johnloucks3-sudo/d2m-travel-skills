"""
Dreams2Memories Travel, LLC — Front Door
A no-auth, no-account request intake for non-technical users.

WHY THIS EXISTS (first principles):
  The client portal (portal/server.py) is magic-link gated and built for
  EXISTING clients with dossiers. A non-technical person with no account and
  no terminal needs a dead-simple way to reach the wing: type a request,
  get a reference number, check status later. That is this.

SAFETY GATE (the load-bearing design decision):
  The live tasking watcher (OpsCenter/thunderbird_tasking_watcher.py) AUTO-SPAWNS
  a headless agent on any inbox entry whose status is in TRIGGER_STATUSES
  (PENDING / UNREAD / ACTIVE-CRITICAL / FLAGGED-OVERDUE / NEXUS:).
  This form is UNAUTHENTICATED. Therefore it must NEVER write a triggering
  status. Front-door submissions land as inert TRIAGE items:
      status: TRIAGE          <- not in TRIGGER_STATUSES, no auto-spawn
      from: Front Door (external)
  A human (Hale/Commander) reads and routes them. Untrusted input never
  impersonates the Commander and never auto-spawns an agent.

SOURCE OF TRUTH for status = requests.jsonl in this directory.
The wing inbox gets a MIRROR copy for human action. We never parse the
markdown inbox back out for the status view.

Port: 8790
"""

import json
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

HERE = Path(__file__).parent
STATIC = HERE / "static"
REQUESTS_FILE = HERE / "requests.jsonl"           # source of truth
WING_INBOX = Path("/home/john/Thunderbird/OpsCenter/collaboration/opencode_inbox.md")

MAX_MSG = 2000
RATE_LIMIT_PER_HOUR = 5
_rate: dict[str, list[float]] = {}

app = FastAPI(title="D2M Front Door", docs_url=None, redoc_url=None)


# ── models ──────────────────────────────────────────────────────────────────
class FrontDoorRequest(BaseModel):
    name: str
    contact: str          # email or phone — free text, we don't gate on format
    message: str


# ── helpers ─────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_ref() -> str:
    # Human-readable, easy to read over the phone: D2M-XXXX
    return "D2M-" + secrets.token_hex(2).upper()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


def _rate_ok(ip: str) -> bool:
    now = time.time()
    hist = [t for t in _rate.get(ip, []) if now - t < 3600]
    _rate[ip] = hist
    if len(hist) >= RATE_LIMIT_PER_HOUR:
        return False
    hist.append(now)
    return True


def _save_request(row: dict) -> None:
    with open(REQUESTS_FILE, "a") as f:
        f.write(json.dumps(row) + "\n")


def _find_request(ref: str) -> dict | None:
    """Last write wins — lets the wing update status by appending a new row."""
    if not REQUESTS_FILE.exists():
        return None
    found = None
    for line in REQUESTS_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("ref") == ref:
            found = row
    return found


# The live watcher (thunderbird_tasking_watcher.py) does WHOLE-FILE substring
# matching against these tokens and auto-spawns a headless agent on a hit.
# A user typing any of these in a field would trip it. We neutralize them in
# all user-derived text before it touches the watched file. Same-line tokens
# matter here, not just newline-forged ones — so this is a substring defang,
# not just a control-char strip.
_TRIGGER_TOKENS = ("status:", "NEXUS:", "UNREAD", "ACTIVE-CRITICAL",
                   "FLAGGED-OVERDUE", "PENDING", "task: |")


def _defang(s: str) -> str:
    out = s
    for tok in _TRIGGER_TOKENS:
        # case-insensitive: split the token with a zero-width-safe space so the
        # watcher's exact-substring match can never see it intact.
        pat = re.compile(re.escape(tok), re.IGNORECASE)
        out = pat.sub(lambda m: m.group(0)[:1] + " " + m.group(0)[1:], out)
    return out


def _mirror_to_wing_inbox(row: dict) -> None:
    """
    Append an INERT triage item to the wing inbox.
    status: TRIAGE is deliberately NOT a trigger status — no auto-spawn.
    User-derived fields are defanged so they cannot carry a trigger token.
    """
    name = _defang(row["name"])
    contact = _defang(row["contact"])
    message = _defang(row["message"])
    entry = (
        f"---\n"
        f"## TASK: FRONTDOOR-{row['ref']}\n"
        f"status: TRIAGE\n"
        f"from: Front Door (external)\n"
        f"to: HALE\n"
        f"priority: P2\n"
        f"persona: HALE\n"
        f"submitted: {row['ts']}\n"
        f"\n"
        f"task: |\n"
        f"  EXTERNAL REQUEST via Front Door — human triage required, do NOT auto-action.\n"
        f"  Ref: {row['ref']}\n"
        f"  Name: {name}\n"
        f"  Contact: {contact}\n"
        f"  Message: {message}\n"
        f"\n"
    )
    WING_INBOX.parent.mkdir(parents=True, exist_ok=True)
    with open(WING_INBOX, "a") as f:
        f.write(entry)


def _clean(s: str, limit: int) -> str:
    s = (s or "").strip()
    # collapse control chars so a submission can't forge inbox structure
    s = re.sub(r"[\x00-\x1f\x7f]+", " ", s)
    return s[:limit]


# ── routes ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"ok": True, "service": "d2m-frontdoor", "port": 8790}


@app.post("/api/request")
async def submit(body: FrontDoorRequest, request: Request):
    ip = _client_ip(request)
    if not _rate_ok(ip):
        raise HTTPException(429, "Too many requests. Please wait a bit and try again.")

    name = _clean(body.name, 120)
    contact = _clean(body.contact, 200)
    message = _clean(body.message, MAX_MSG)
    if not name or not contact or not message:
        raise HTTPException(400, "Please fill in your name, contact, and message.")

    ref = _new_ref()
    row = {
        "ref": ref,
        "name": name,
        "contact": contact,
        "message": message,
        "status": "Received",
        "ts": _now_iso(),
    }
    _save_request(row)            # source of truth first
    try:
        _mirror_to_wing_inbox(row)  # then notify the wing (inert triage)
    except Exception:
        # Never lose a request because the inbox mirror failed — it's in JSONL.
        pass

    return JSONResponse({
        "ok": True,
        "ref": ref,
        "message": "Your request has reached the Dreams2Memories team. "
                   "Save your reference number to check status.",
    })


@app.get("/api/status/{ref}")
async def status(ref: str):
    ref = ref.strip().upper()
    row = _find_request(ref)
    if not row:
        raise HTTPException(404, "No request found for that reference number.")
    return {
        "ref": row["ref"],
        "name": row.get("name", ""),
        "status": row.get("status", "Received"),
        "submitted": row.get("ts", ""),
        "note": row.get("note", ""),
    }


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8790, log_level="info")

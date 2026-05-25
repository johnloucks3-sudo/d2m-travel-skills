import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.db import save_intake
from app.lead_pipeline import notify_intake_form

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))
QUEUE_FILE = Path("/home/john/Thunderbird/app/intake_queue.jsonl")


@router.get("/request-a-voyage", response_class=HTMLResponse)
async def request_form(request: Request):
    return templates.TemplateResponse("intake.html", {"request": request, "submitted": False})


@router.post("/request-a-voyage", response_class=HTMLResponse)
async def submit_intake(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    destination: str = Form(""),
    travel_window: str = Form(""),
    budget: str = Form(""),
    party_size: str = Form(""),
    comments: str = Form(""),
    consent: str = Form("off"),
):
    data = {
        "name": name,
        "email": email,
        "phone": phone,
        "destination": destination,
        "travel_window": travel_window,
        "budget": budget,
        "party_size": party_size,
        "comments": comments,
        "consent": consent == "on",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    row_id = save_intake(data)

    # Write to queue file for Hale pickup
    entry = {**data, "db_id": row_id}
    with open(QUEUE_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Notify Commander via Telegram
    try:
        notify_intake_form(data)
    except Exception as exc:
        logger.warning("Intake form notification failed: %s", exc)

    return templates.TemplateResponse("intake.html", {"request": request, "submitted": True, "name": name})

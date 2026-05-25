from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Optional
from app.db import search_sailings, get_cruise_lines, get_months, get_stats, get_featured_sailings

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: Optional[str] = Query(None),
    line: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    min_days: Optional[int] = Query(None),
    max_days: Optional[int] = Query(None),
):
    results = []
    searched = any([q, line and line != "all", month and month != "all", min_days, max_days])
    if searched:
        results = search_sailings(
            cruise_line=line,
            destination=q,
            month=month,
            min_days=min_days,
            max_days=max_days,
            limit=100,
        )
    return templates.TemplateResponse("search.html", {
        "request": request,
        "results": results,
        "cruise_lines": get_cruise_lines(),
        "months": get_months(),
        "stats": get_stats(),
        "query": q or "",
        "selected_line": line or "all",
        "selected_month": month or "all",
        "min_days": min_days,
        "max_days": max_days,
        "searched": searched,
    })

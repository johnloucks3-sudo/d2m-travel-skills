"""
app.d2mluxury.quest — Dreams2Memories Travel
FastAPI application | Port 8080 on YOGA
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from urllib.parse import quote as urlencode_str

from app.db import init_db, get_featured_sailings, get_stats
from app.routers import cruise, intake, blog

BASE = Path(__file__).parent

app = FastAPI(title="Dreams2Memories Travel", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))
templates.env.filters["urlencode"] = urlencode_str

app.include_router(cruise.router)
app.include_router(intake.router)
app.include_router(blog.router)


@app.on_event("startup")
async def startup():
    init_db()
    # Inject urlencode filter into cruise and intake routers' template envs
    cruise.templates.env.filters["urlencode"] = urlencode_str
    intake.templates.env.filters["urlencode"] = urlencode_str
    blog.templates.env.filters["urlencode"] = urlencode_str


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "featured": get_featured_sailings(6),
        "stats": get_stats(),
    })


@app.get("/health")
async def health():
    return {"status": "ok"}

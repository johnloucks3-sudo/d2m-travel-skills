#!/usr/bin/env python3
"""
D2M Operational Dashboard + Hale Visual Briefs — FastAPI Server
Serves dynamic dashboard at http://localhost:8901
Routes live data from phase1_data.json + phase2_data.json via JSON API
Client-side filtering, real-time polling, exports
Hale Visual Briefs available at /briefs/{date}/ endpoints
"""

import json
import re
import os
import sqlite3
import secrets
from pathlib import Path
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Depends, status, Query, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader
import uvicorn

# Interactive docs disabled — this app is public (Cloudflare-fronted). No /docs, /redoc,
# or /openapi.json schema exposure of internal routes (MISSION-258).
app = FastAPI(
    title="D2M Dashboard + Hale Briefs",
    version="2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# ── HTTP Basic Auth ──────────────────────────────────────────────────────────
_security = HTTPBasic()
_SITE_USER = "john"
_SITE_PASS = "535277-yoda-grandeur"  # change via env D2M_DASH_PASS

def _require_auth(creds: HTTPBasicCredentials = Depends(_security)):
    import os
    expected_pass = os.getenv("D2M_DASH_PASS", _SITE_PASS)
    ok = (
        secrets.compare_digest(creds.username.encode(), _SITE_USER.encode()) and
        secrets.compare_digest(creds.password.encode(), expected_pass.encode())
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic realm='D2M Internal'"},
        )
    return creds.username

# Paths
ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES = Path(__file__).resolve().parent / "templates"
OUTPUT_VISUALS = ROOT / "output" / "visuals"
PHASE1_DATA = OUTPUT_VISUALS / "phase1_data.json"
PHASE2_DATA = OUTPUT_VISUALS / "phase2" / "phase2_data.json"
BRIEFS_OUTPUT = ROOT / "output" / "briefs"
CRUISES_DB    = ROOT / "output" / "cruises.db"
PRICE_REQUESTS_LOG = ROOT / "intel" / "price_requests.json"

MT = timezone(timedelta(hours=-6))

# ── Telegram notifier (fire-and-forget) ─────────────────────────────────────
_TG_TOKEN = os.getenv("TELEGRAM_C2_BOT_TOKEN", "")
_TG_CMDR  = int(os.getenv("TELEGRAM_COMMANDER_ID", "7554895206"))

def _tg_notify(text: str):
    """Send text to Commander via D2MC2C bot. Non-blocking, best-effort."""
    if not _TG_TOKEN:
        return
    try:
        import urllib.request
        payload = json.dumps({"chat_id": _TG_CMDR, "text": text, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{_TG_TOKEN}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


# ── Pydantic models ──────────────────────────────────────────────────────────
class PriceRequestSailing(BaseModel):
    line: str
    ship: str
    departure: str
    nights: int
    route: str = ""
    region: str = ""

class PriceRequest(BaseModel):
    sailings: list[PriceRequestSailing]
    name: str
    email: str
    phone: str = ""
    notes: str = ""


# ── Cruises API helpers ──────────────────────────────────────────────────────
def _sanitize_fts(q: str) -> str:
    """Convert free-text query to FTS5-safe MATCH expression."""
    q = re.sub(r'["\(\)\*\:\^]', ' ', q)
    tokens = [t.strip() for t in q.split() if len(t.strip()) >= 2]
    if not tokens:
        return ''
    return ' AND '.join(f'"{t}"*' for t in tokens)


def _cruise_db():
    if not CRUISES_DB.exists():
        raise HTTPException(status_code=503, detail="Cruise database not built yet")
    conn = sqlite3.connect(CRUISES_DB)
    conn.row_factory = sqlite3.Row
    return conn


# ── Cruises API endpoints (public — no auth required) ───────────────────────
@app.get("/api/cruises/lines")
async def cruises_lines():
    """Return each cruise line with sailing count, year breakdown, and min price."""
    conn = _cruise_db()
    rows = conn.execute("""
        SELECT line,
               COUNT(*) as cnt,
               SUM(CASE WHEN departure >= '2026-01-01' AND departure < '2027-01-01' THEN 1 ELSE 0 END) as c2026,
               SUM(CASE WHEN departure >= '2027-01-01' AND departure < '2028-01-01' THEN 1 ELSE 0 END) as c2027,
               SUM(CASE WHEN departure >= '2028-01-01' THEN 1 ELSE 0 END) as c2028plus,
               MIN(price_ind) as min_price,
               GROUP_CONCAT(DISTINCT ship) as ships_raw
        FROM cruises WHERE line != ''
        GROUP BY line ORDER BY cnt DESC
    """).fetchall()
    conn.close()
    out = []
    for r in rows:
        ships_str = r["ships_raw"] or ""
        ships = list(dict.fromkeys(s.strip() for s in ships_str.split(",") if s.strip()))[:4]
        out.append({
            "line": r["line"], "count": r["cnt"],
            "c2026": r["c2026"] or 0, "c2027": r["c2027"] or 0, "c2028plus": r["c2028plus"] or 0,
            "min_price": r["min_price"],
            "ships": ships,
        })
    return JSONResponse(out)


@app.get("/api/cruises/regions")
async def cruises_regions():
    """Return distinct regions with counts."""
    conn = _cruise_db()
    rows = conn.execute(
        "SELECT region, COUNT(*) as cnt FROM cruises WHERE region != '' "
        "GROUP BY region ORDER BY cnt DESC LIMIT 30"
    ).fetchall()
    conn.close()
    return JSONResponse([{"region": r["region"], "count": r["cnt"]} for r in rows])


@app.get("/api/cruises/search")
async def cruises_search(
    q: str = Query(default=""),
    line: str = Query(default=""),
    region: str = Query(default=""),
    nights_min: int = Query(default=0),
    nights_max: int = Query(default=999),
    departure_after: str = Query(default=""),
    departure_before: str = Query(default=""),
    multi: bool = Query(default=False),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
):
    """Search sailings. FTS5 when q provided, filter-only otherwise."""
    conn = _cruise_db()
    where, params = [], []

    fts = ""
    if q.strip():
        fts = _sanitize_fts(q)
        if fts:
            where.append("cruises_fts MATCH ?")
            params.append(fts)

    if line:
        where.append("c.line = ?" if fts else "line = ?")
        params.append(line)
    if region:
        where.append("c.region = ?" if fts else "region = ?")
        params.append(region)
    if nights_min > 0:
        where.append("c.nights >= ?" if fts else "nights >= ?")
        params.append(nights_min)
    if nights_max < 999:
        where.append("c.nights <= ?" if fts else "nights <= ?")
        params.append(nights_max)
    if departure_after:
        where.append("c.departure >= ?" if fts else "departure >= ?")
        params.append(departure_after)
    if departure_before:
        where.append("c.departure <= ?" if fts else "departure <= ?")
        params.append(departure_before)
    if multi:
        where.append("c.multi = 1" if fts else "multi = 1")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    if q.strip() and any("cruises_fts" in w for w in where):
        base = f"""
            SELECT c.id, c.line, c.ship, c.departure, c.nights,
                   c.from_port, c.route, c.region, c.sources, c.multi,
                   c.price_ind, c.price_ts, c.price_src,
                   c.booking_url, c.booking_label
            FROM cruises c
            JOIN cruises_fts ON cruises_fts.rowid = c.id
            {where_sql}
            ORDER BY c.departure
        """
    else:
        base = f"SELECT * FROM cruises {where_sql} ORDER BY departure"

    count_sql = f"SELECT COUNT(*) FROM ({base})"
    total = conn.execute(count_sql, params).fetchone()[0]

    rows = conn.execute(f"{base} LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
    conn.close()

    results = []
    for r in rows:
        try:
            sources = json.loads(r["sources"]) if r["sources"] else []
        except Exception:
            sources = []
        results.append({
            "id": r["id"],
            "line": r["line"],
            "ship": r["ship"],
            "departure": r["departure"],
            "nights": r["nights"],
            "from_port": r["from_port"],
            "route": r["route"],
            "region": r["region"],
            "sources": sources,
            "multi": bool(r["multi"]),
            "price_ind": r["price_ind"],
            "price_ts": r["price_ts"],
            "price_src": r["price_src"],
            "booking_url": r["booking_url"] if r["booking_url"] else None,
            "booking_label": r["booking_label"] if r["booking_label"] else None,
        })

    return JSONResponse({"total": total, "offset": offset, "limit": limit, "results": results})


@app.post("/api/cruises/price-request")
async def cruises_price_request(req: PriceRequest, background_tasks: BackgroundTasks):
    """Log price request and notify Commander via Telegram. No portal auth required."""
    ts = datetime.now(MT).isoformat()

    # Persist to log
    entry = {
        "ts": ts,
        "name": req.name,
        "email": req.email,
        "phone": req.phone,
        "notes": req.notes,
        "sailings": [s.model_dump() for s in req.sailings],
    }
    log = []
    if PRICE_REQUESTS_LOG.exists():
        try:
            log = json.loads(PRICE_REQUESTS_LOG.read_text())
        except Exception:
            pass
    log.append(entry)
    PRICE_REQUESTS_LOG.write_text(json.dumps(log, indent=2))

    # Build Telegram message
    sailing_lines = "\n".join(
        f"  {i+1}. {s.line} / {s.ship} — {s.departure} — {s.nights}n — {s.region or s.route[:40]}"
        for i, s in enumerate(req.sailings)
    )
    tg_msg = (
        f"🛳️ <b>NEW PRICING REQUEST — D2M Cruise Search</b>\n\n"
        f"<b>From:</b> {req.name} ({req.email})"
        + (f"\n<b>Phone:</b> {req.phone}" if req.phone else "")
        + f"\n\n<b>Selected Sailings:</b>\n{sailing_lines}"
        + (f"\n\n<b>Notes:</b> {req.notes}" if req.notes else "")
        + f"\n\n<i>Source: d2mluxury.quest/cruises · {ts}</i>"
    )
    background_tasks.add_task(_tg_notify, tg_msg)

    return JSONResponse({
        "status": "received",
        "message": "Thank you! Our advisors will respond within 2 business hours.",
    })


# ── Generic Travel Search Framework /api/travel/* ───────────────────────────
# category param selects vertical. Currently only 'cruise' has data.
# Aliases let the frontend migrate to /api/travel/* without breaking /api/cruises/*.

@app.get("/api/travel/lines")
async def travel_lines(category: str = Query(default="cruise")):
    """Lines/operators by vertical. Alias of /api/cruises/lines for category=cruise."""
    if category == "cruise":
        return await cruises_lines()
    return JSONResponse([])


@app.get("/api/travel/regions")
async def travel_regions(category: str = Query(default="cruise")):
    """Regions by vertical. Alias of /api/cruises/regions for category=cruise."""
    if category == "cruise":
        return await cruises_regions()
    return JSONResponse([])


@app.get("/api/travel/search")
async def travel_search(
    category: str = Query(default="cruise"),
    q: str = Query(default=""),
    line: str = Query(default=""),
    region: str = Query(default=""),
    nights_min: int = Query(default=0),
    nights_max: int = Query(default=999),
    departure_after: str = Query(default=""),
    departure_before: str = Query(default=""),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
):
    """Multi-vertical search. Routes to per-category handler."""
    if category == "cruise":
        return await cruises_search(q=q, line=line, region=region,
                                    nights_min=nights_min, nights_max=nights_max,
                                    departure_after=departure_after,
                                    departure_before=departure_before,
                                    limit=limit, offset=offset)
    return JSONResponse({"total": 0, "offset": offset, "limit": limit, "results": [],
                         "note": f"Vertical '{category}' not yet populated."})


@app.post("/api/travel/price-request")
async def travel_price_request(req: PriceRequest, background_tasks: BackgroundTasks):
    """Category-aware price request. Routes to per-category handler."""
    return await cruises_price_request(req, background_tasks)


@app.get("/api/travel/categories")
async def travel_categories():
    """Return active verticals with record counts."""
    conn = _cruise_db()
    cruise_count = conn.execute("SELECT COUNT(*) FROM cruises").fetchone()[0]
    conn.close()
    return JSONResponse([
        {"category": "cruise", "label": "Cruises", "count": cruise_count, "status": "live"},
        {"category": "air", "label": "Flights", "count": 0, "status": "planned"},
        {"category": "excursion", "label": "Excursions", "count": 0, "status": "planned"},
        {"category": "land", "label": "Land Tours", "count": 0, "status": "planned"},
        {"category": "transfer", "label": "Transfers", "count": 0, "status": "planned"},
    ])


# Setup Jinja2 for brief rendering
jinja_env = Environment(loader=FileSystemLoader(TEMPLATES))


@app.get("/")
async def dashboard(_user: str = Depends(_require_auth)):
    """Serve the dashboard HTML."""
    dashboard_file = TEMPLATES / "dashboard.html"
    if not dashboard_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return FileResponse(dashboard_file, media_type="text/html")


@app.get("/api/health")
async def health(_user: str = Depends(_require_auth)):
    """Health check endpoint."""
    return JSONResponse({
        "status": "ok",
        "timestamp": datetime.now(MT).isoformat(),
        "phase1_exists": PHASE1_DATA.exists(),
        "phase2_exists": PHASE2_DATA.exists(),
    })


@app.get("/api/data/phase1")
async def get_phase1_data(_user: str = Depends(_require_auth)):
    """Fetch fresh phase1_data.json with timestamp."""
    if not PHASE1_DATA.exists():
        raise HTTPException(status_code=404, detail="phase1_data.json not found")

    try:
        data = json.loads(PHASE1_DATA.read_text())
        # Inject server timestamp
        data["_served_at"] = datetime.now(MT).isoformat()
        return JSONResponse(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid phase1_data.json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading phase1_data: {str(e)}")


@app.get("/api/data/phase2")
async def get_phase2_data(_user: str = Depends(_require_auth)):
    """Fetch fresh phase2_data.json with timestamp."""
    if not PHASE2_DATA.exists():
        raise HTTPException(status_code=404, detail="phase2_data.json not found")

    try:
        data = json.loads(PHASE2_DATA.read_text())
        # Inject server timestamp
        data["_served_at"] = datetime.now(MT).isoformat()
        return JSONResponse(data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid phase2_data.json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading phase2_data: {str(e)}")


# Hale Visual Briefs — New Endpoints (Port 8902 or /briefs/* routes)

def load_brief_snapshot(date_str: str) -> dict:
    """Load pre-generated brief snapshot JSON."""
    snapshot_file = BRIEFS_OUTPUT / date_str / "snapshot.json"
    if not snapshot_file.exists():
        raise HTTPException(status_code=404, detail=f"Brief snapshot not found for {date_str}")
    try:
        return json.loads(snapshot_file.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading brief: {str(e)}")


@app.get("/briefs/{date}/")
async def brief_landing(date: str, _user: str = Depends(_require_auth)):
    """Landing page with links to all 4 brief visuals."""
    brief_data = load_brief_snapshot(date)
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Hale Brief — {date}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: #f7f3ea;
                margin: 0;
                padding: 20px;
                color: #1a1a1a;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            h1 {{
                text-align: center;
                color: #0000ff;
                margin: 0 0 30px 0;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
            }}
            .card {{
                background: #f9f7f3;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #0000ff;
                text-align: center;
            }}
            .card h2 {{
                margin: 0 0 10px 0;
                font-size: 18px;
                color: #0000ff;
            }}
            .card p {{
                margin: 0 0 15px 0;
                font-size: 13px;
                color: #666;
            }}
            .link {{
                display: inline-block;
                background: #0000ff;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                text-decoration: none;
                font-weight: bold;
                font-size: 13px;
            }}
            .link:hover {{ background: #0000cc; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 HALE OPERATIONAL BRIEF — {date}</h1>
            <div class="grid">
                <div class="card">
                    <h2>📊 Lifecycle Wheel</h2>
                    <p>Client segments, urgency, FPD countdown</p>
                    <a href="/briefs/{date}/lifecycle-wheel/" class="link">View →</a>
                </div>
                <div class="card">
                    <h2>💰 Financial Waterfall</h2>
                    <p>Commission pipeline with Allianz claim</p>
                    <a href="/briefs/{date}/financial-waterfall/" class="link">View →</a>
                </div>
                <div class="card">
                    <h2>🔥 Task Heat Map</h2>
                    <p>Clients × Task types urgency grid</p>
                    <a href="/briefs/{date}/task-heatmap/" class="link">View →</a>
                </div>
                <div class="card">
                    <h2>⚠️ Risk Matrix</h2>
                    <p>Likelihood × Disruption with actions</p>
                    <a href="/briefs/{date}/risk-matrix/" class="link">View →</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)


@app.get("/briefs/{date}/lifecycle-wheel/")
async def brief_lifecycle_wheel(date: str, _user: str = Depends(_require_auth)):
    """Render lifecycle wheel visual."""
    brief_data = load_brief_snapshot(date)
    template = jinja_env.get_template("brief_lifecycle_wheel.html")
    html = template.render(brief_data=brief_data)
    return HTMLResponse(html)


@app.get("/briefs/{date}/financial-waterfall/")
async def brief_financial_waterfall(date: str, _user: str = Depends(_require_auth)):
    """Render financial waterfall visual."""
    brief_data = load_brief_snapshot(date)
    template = jinja_env.get_template("brief_financial_waterfall.html")
    html = template.render(brief_data=brief_data)
    return HTMLResponse(html)


@app.get("/briefs/{date}/task-heatmap/")
async def brief_task_heatmap(date: str, _user: str = Depends(_require_auth)):
    """Render task heat map visual."""
    brief_data = load_brief_snapshot(date)
    template = jinja_env.get_template("brief_task_heatmap.html")
    html = template.render(brief_data=brief_data)
    return HTMLResponse(html)


@app.get("/briefs/{date}/risk-matrix/")
async def brief_risk_matrix(date: str, _user: str = Depends(_require_auth)):
    """Render risk matrix visual."""
    brief_data = load_brief_snapshot(date)
    template = jinja_env.get_template("brief_risk_matrix.html")
    html = template.render(brief_data=brief_data)
    return HTMLResponse(html)


app.mount("/training", StaticFiles(directory=str(ROOT / "Bryana"), html=True), name="training")
app.mount("/intel", StaticFiles(directory=str(ROOT / "intel_web"), html=True), name="intel")
app.mount("/cruises", StaticFiles(directory=str(ROOT / "cruises_web"), html=True), name="cruises")
app.mount("/buddy", StaticFiles(directory="/srv/www/htdocs/buddy", html=True), name="buddy")
# American Spirit — Commander's family piece (2026-07-04). Public by design: the
# claude.ai artifact link in the sent family email is login-walled; this is the
# open replacement his family can actually reach.
app.mount("/american-spirit", StaticFiles(directory=str(ROOT / "american_spirit_web"), html=True), name="american_spirit")
app.mount("/meetroom", StaticFiles(directory=str(ROOT / "OpsCenter" / "meetroom"), html=True), name="meetroom")


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8901,
        log_level="info"
    )

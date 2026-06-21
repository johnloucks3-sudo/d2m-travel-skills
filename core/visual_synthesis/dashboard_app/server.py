#!/usr/bin/env python3
"""
D2M Operational Dashboard + Hale Visual Briefs — FastAPI Server
Serves dynamic dashboard at http://localhost:8901
Routes live data from phase1_data.json + phase2_data.json via JSON API
Client-side filtering, real-time polling, exports
Hale Visual Briefs available at /briefs/{date}/ endpoints
"""

import json
import secrets
from pathlib import Path
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
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

MT = timezone(timedelta(hours=-6))

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


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8901,
        log_level="info"
    )

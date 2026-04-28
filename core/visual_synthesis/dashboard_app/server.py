#!/usr/bin/env python3
"""
D2M Operational Dashboard — FastAPI Server
Serves dynamic dashboard at http://localhost:8901
Routes live data from phase1_data.json + phase2_data.json via JSON API
Client-side filtering, real-time polling, exports
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI(title="D2M Dashboard", version="1.0")

# Paths
ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES = Path(__file__).resolve().parent / "templates"
OUTPUT_VISUALS = ROOT / "output" / "visuals"
PHASE1_DATA = OUTPUT_VISUALS / "phase1_data.json"
PHASE2_DATA = OUTPUT_VISUALS / "phase2" / "phase2_data.json"

MT = timezone(timedelta(hours=-6))


@app.get("/")
async def dashboard():
    """Serve the dashboard HTML."""
    dashboard_file = TEMPLATES / "dashboard.html"
    if not dashboard_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return FileResponse(dashboard_file, media_type="text/html")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({
        "status": "ok",
        "timestamp": datetime.now(MT).isoformat(),
        "phase1_exists": PHASE1_DATA.exists(),
        "phase2_exists": PHASE2_DATA.exists(),
    })


@app.get("/api/data/phase1")
async def get_phase1_data():
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
async def get_phase2_data():
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


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="127.0.0.1",
        port=8901,
        log_level="info"
    )

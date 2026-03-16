"""
Dreams2Memories Client Portal — Server
Minimal FastAPI server for portal.d2mluxury.quest
Port: 8780
"""

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

PORTAL_DIR = Path(__file__).parent

app = FastAPI(
    title="D2M Client Portal",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
)

# CORS — allow portal to be embedded or accessed from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok", "service": "d2m-client-portal"})


@app.get("/")
async def index():
    return FileResponse(PORTAL_DIR / "index.html", media_type="text/html")


# Serve static files (CSS, images, future JS)
app.mount("/static", StaticFiles(directory=str(PORTAL_DIR)), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8780,
        log_level="info",
    )

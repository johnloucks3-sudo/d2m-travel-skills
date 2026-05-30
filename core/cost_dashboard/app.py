"""AI Infrastructure Cost Dashboard — FastAPI app."""
import sqlite3, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uvicorn

DB = Path.home() / "Thunderbird" / "storage" / "ai_costs.db"
ROUTER_DB = Path.home() / "Thunderbird" / "core" / "ai_infra" / "data" / "router_cost.db"
TEMPLATES = Path(__file__).parent / "templates"

app = FastAPI(title="D2M AI Cost Dashboard")
templates = Jinja2Templates(directory=str(TEMPLATES))


def _ensure_tables():
    conn = sqlite3.connect(str(DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plan_snapshots (
          id INTEGER PRIMARY KEY,
          ts TEXT NOT NULL,
          plan_name TEXT DEFAULT 'Max',
          monthly_spent REAL,
          monthly_limit REAL,
          monthly_pct REAL,
          session_pct REAL,
          weekly_all_pct REAL,
          weekly_sonnet_pct REAL,
          balance REAL,
          auto_reload BOOLEAN DEFAULT 0,
          month_resets TEXT,
          UNIQUE(ts)
        )
    """)
    conn.commit()
    conn.close()


_ensure_tables()

def _query(sql, params=()):
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def _query_router(sql, params=()):
    if not ROUTER_DB.exists():
        return []
    conn = sqlite3.connect(str(ROUTER_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def _compute_claude_windows():
    CAP = 200_000
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT ts_start, effective_tokens FROM claude_events ORDER BY ts_start"
    ).fetchall()
    windows = {}
    for r in rows:
        raw = r["ts_start"].replace("Z", "+00:00")
        try:
            ts = datetime.fromisoformat(raw)
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        bucket = ts.hour - (ts.hour % 5)
        win_start = ts.replace(hour=bucket, minute=0, second=0, microsecond=0)
        key = win_start.isoformat()
        windows.setdefault(key, {"start": key, "toks": 0})
        windows[key]["toks"] += (r["effective_tokens"] or 0)
    for key, w in windows.items():
        pct = min(100.0, w["toks"] / CAP * 100)
        ws = w["start"]
        we = (datetime.fromisoformat(ws) + timedelta(hours=5)).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO claude_windows"
            " (window_start, window_end, effective_tokens, pct_consumed, closed)"
            " VALUES (?, ?, ?, ?, ?)",
            (ws, we, w["toks"], pct, False),
        )
    conn.commit()
    conn.close()


@app.get("/api/summary")
def api_summary():
    _compute_claude_windows()
    win = _query("SELECT * FROM claude_windows ORDER BY window_start DESC LIMIT 1")
    plan = _query("SELECT * FROM plan_snapshots ORDER BY ts DESC LIMIT 1")
    pools = _query_router("SELECT * FROM pools")
    w = win[0] if win else {}
    p = plan[0] if plan else {}
    oc_pool = next((r for r in pools if r["name"] == "opencode_native"), {})
    return JSONResponse({
        "claude_pct": round(w.get("pct_consumed", 0), 1),
        "claude_tokens": w.get("effective_tokens", 0),
        "window_start": w.get("window_start"),
        "opencode_consumed": round(oc_pool.get("consumed") or 0, 4),
        "plan_monthly_pct": round(p.get("monthly_pct") or 0, 1),
        "plan_balance": round(p.get("balance") or 0, 2),
        "updated": datetime.now(timezone.utc).isoformat(),
    })


@app.get("/api/claude/current")
def claude_current():
    _compute_claude_windows()
    rows = _query("SELECT * FROM claude_windows WHERE closed=0 ORDER BY window_start DESC LIMIT 1")
    return rows[0] if rows else {"window_start": None, "pct_consumed": 0}

@app.get("/api/opencode/pools")
def opencode_pools():
    return _query_router("SELECT * FROM pools ORDER BY name")

@app.get("/api/rollups")
def rollups(days: int = 30):
    return _query("SELECT * FROM daily_rollups ORDER BY date DESC LIMIT ?", (days,))

@app.get("/api/plan")
def plan_snapshot():
    rows = _query("SELECT * FROM plan_snapshots ORDER BY ts DESC LIMIT 1")
    return rows[0] if rows else {"plan_name": "unknown", "monthly_pct": 0}

@app.get("/api/zen/limits")
def zen_limits():
    return _query("SELECT model, requests_per_hour, requests_per_day, tokens_per_hour FROM zen_limits")

@app.get("/api/zen/usage")
def zen_usage():
    return _query("SELECT ts, calls_per_hour, tokens_per_hour, calls_per_day, tokens_per_day FROM zen_usage ORDER BY ts DESC LIMIT 1")

@app.get("/api/claude/models")
def claude_models():
    return _query("""
        SELECT model, COUNT(*) as events, SUM(input_tokens) as inp,
               SUM(output_tokens) as out, SUM(effective_tokens) as eff
        FROM claude_events GROUP BY model ORDER BY events DESC
    """)

@app.get("/healthz")
def healthz():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    _compute_claude_windows()
    window = _query("SELECT * FROM claude_windows WHERE closed=0 ORDER BY window_start DESC LIMIT 1")
    rollup = _query("SELECT * FROM daily_rollups ORDER BY date DESC LIMIT 7")
    claude_summary = _query("""
        SELECT model, COUNT(*) as events, SUM(input_tokens) as inp, SUM(output_tokens) as out,
               SUM(effective_tokens) as eff
        FROM claude_events GROUP BY model ORDER BY events DESC
    """)
    totals = _query("""
        SELECT COUNT(*) as total_events, SUM(input_tokens) as total_inp,
               SUM(output_tokens) as total_out, SUM(effective_tokens) as total_eff
        FROM claude_events
    """)
    plan = _query("SELECT * FROM plan_snapshots ORDER BY ts DESC LIMIT 1")
    poe_data = _query("SELECT * FROM poe_snapshots ORDER BY ts DESC LIMIT 1")
    zen_limits = _query("SELECT model, requests_per_hour, requests_per_day, tokens_per_hour FROM zen_limits")
    zen_usage = _query("SELECT ts, calls_per_hour, tokens_per_hour, calls_per_day, tokens_per_day FROM zen_usage ORDER BY ts DESC LIMIT 1")
    oc_pools = _query_router("SELECT * FROM pools ORDER BY name")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "window": window[0] if window else None,
        "rollups": rollup,
        "claude_summary": claude_summary,
        "totals": totals[0] if totals else None,
        "plan": plan[0] if plan else None,
        "poe": poe_data[0] if poe_data else None,
        "zen_limits": zen_limits,
        "zen_usage": zen_usage[0] if zen_usage else None,
        "oc_pools": oc_pools,
    })

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8901)

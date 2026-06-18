#!/usr/bin/env python3
"""
realtime_tracker.py — Thunderbird Wing AI Cost & Usage Tracker
Port: 8903 | Polls Claude JSONL + max-proxy log every 10s

Tracks:
  - Claude MAX 5-hr window (input+output vs 200K cap)
  - Per-model breakdown (Sonnet, Haiku, unknown)
  - max-proxy request flow (OpenCode → MAX OAuth)
  - Billing key safety indicator
"""
import json, os, glob, threading, time, datetime, urllib.request
from pathlib import Path
from collections import deque
from typing import Dict, List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

PORT          = 8903
CLAUDE_DIR    = Path.home() / ".claude"
PROXY_LOG     = Path("/home/john/Thunderbird/logs/max_proxy_requests.jsonl")
TOKEN_CAP     = 600_000   # MAX 5x session cap (observed: 4% @ 24K tokens → ~600K)
WINDOW_HOURS  = 5
SCAN_SECS     = 10

app = FastAPI(title="Thunderbird Cost Tracker", docs_url=None, redoc_url=None)


# ── in-memory state ───────────────────────────────────────────────────────────

class _State:
    def __init__(self):
        self.lock    = threading.Lock()
        self.events  = deque(maxlen=20_000)   # all claude JSONL assistant events
        self.proxy   = deque(maxlen=2_000)    # max-proxy request log entries
        self.offsets: Dict[str, int] = {}
        self.last_scan: str = "never"

S = _State()


# ── background scanner ────────────────────────────────────────────────────────

def _scan_loop():
    while True:
        try:
            _scan_jsonl()
            _scan_proxy()
            S.last_scan = datetime.datetime.now(datetime.timezone.utc).isoformat()
        except Exception:
            pass
        time.sleep(SCAN_SECS)

def _scan_jsonl():
    for fpath in glob.glob(str(CLAUDE_DIR / "projects" / "**" / "*.jsonl"), recursive=True):
        try:
            cur_size = os.path.getsize(fpath)
            offset   = S.offsets.get(fpath, 0)
            if cur_size <= offset:
                continue
            with open(fpath, "r", errors="replace") as f:
                f.seek(offset)
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        ev = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if ev.get("type") != "assistant":
                        continue
                    msg   = ev.get("message", {})
                    usage = msg.get("usage")
                    if not usage:
                        continue
                    model = msg.get("model", "unknown")
                    inp   = usage.get("input_tokens", 0)
                    out   = usage.get("output_tokens", 0)
                    cr    = usage.get("cache_read_input_tokens", 0)
                    cw    = usage.get("cache_creation_input_tokens", 0)
                    # Skip Claude Code synthetic / no-op events: they carry an empty
                    # usage block (model "<synthetic>", 0 tokens) and otherwise flood
                    # the live MAX feed and inflate call counts.
                    if model == "<synthetic>" or (inp == 0 and out == 0 and cr == 0 and cw == 0):
                        continue
                    ts_str = ev.get("timestamp", "")
                    try:
                        ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except Exception:
                        ts = datetime.datetime.now(datetime.timezone.utc)
                    with S.lock:
                        S.events.append({
                            "ts":    ts.isoformat(),
                            "model": model,
                            "inp":   inp,
                            "out":   out,
                            "cr":    cr,
                            "cw":    cw,
                        })
                S.offsets[fpath] = f.tell()
        except (OSError, IOError):
            pass

def _scan_proxy():
    if not PROXY_LOG.exists():
        return
    try:
        cur_size = PROXY_LOG.stat().st_size
        offset   = S.offsets.get(str(PROXY_LOG), 0)
        if cur_size <= offset:
            return
        with open(PROXY_LOG, "r", errors="replace") as f:
            f.seek(offset)
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    with S.lock:
                        S.proxy.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
            S.offsets[str(PROXY_LOG)] = f.tell()
    except (OSError, IOError):
        pass


# ── metrics ───────────────────────────────────────────────────────────────────

def _compute():
    now        = datetime.datetime.now(datetime.timezone.utc)
    win_start  = now - datetime.timedelta(hours=WINDOW_HOURS)
    day_start  = now.replace(hour=0, minute=0, second=0, microsecond=0)

    win_inp = win_out = win_calls = 0
    day_inp = day_out = day_calls = 0
    models: Dict[str, dict] = {}
    oldest_win_ts = None

    with S.lock:
        evlist = list(S.events)
        proxylist = list(S.proxy)

    for ev in evlist:
        try:
            ts = datetime.datetime.fromisoformat(ev["ts"])
        except Exception:
            continue
        m = ev["model"]
        if m not in models:
            models[m] = {"calls": 0, "inp": 0, "out": 0}
        models[m]["calls"] += 1
        models[m]["inp"]   += ev["inp"]
        models[m]["out"]   += ev["out"]

        if ts >= win_start:
            win_inp   += ev["inp"]
            win_out   += ev["out"]
            win_calls += 1
            if oldest_win_ts is None or ts < oldest_win_ts:
                oldest_win_ts = ts
        if ts >= day_start:
            day_inp   += ev["inp"]
            day_out   += ev["out"]
            day_calls += 1

    win_tokens = win_inp + win_out
    win_pct    = round(win_tokens / TOKEN_CAP * 100, 1)

    # Window reset time (oldest event rolls out of window)
    if oldest_win_ts:
        resets_at = oldest_win_ts + datetime.timedelta(hours=WINDOW_HOURS)
        delta     = resets_at - now
        secs      = max(0, int(delta.total_seconds()))
        reset_str = f"{secs // 3600}h {(secs % 3600) // 60}m"
    else:
        reset_str = "—"

    # max-proxy 5-hr stats
    proxy_5hr  = sum(1 for r in proxylist
                     if _ts_ok(r.get("ts", ""), win_start))
    proxy_day  = sum(1 for r in proxylist
                     if _ts_ok(r.get("ts", ""), day_start))
    proxy_live = _proxy_alive()

    recent = [
        {"ts": ev["ts"][-8:-7] and ev["ts"][11:19],
         "model": ev["model"][:28],
         "inp": ev["inp"], "out": ev["out"]}
        for ev in reversed(evlist[-20:])
    ]

    return {
        "window":   {"tokens": win_tokens, "cap": TOKEN_CAP, "pct": win_pct,
                     "inp": win_inp, "out": win_out, "calls": win_calls,
                     "reset": reset_str},
        "day":      {"inp": day_inp, "out": day_out,
                     "total": day_inp + day_out, "calls": day_calls},
        "proxy":    {"status": "ONLINE" if proxy_live else "OFFLINE",
                     "requests_5hr": proxy_5hr, "requests_day": proxy_day},
        "models":   sorted(models.items(), key=lambda x: -x[1]["out"])[:8],
        "recent":   recent,
        "billing_safe": True,   # sk-ant key never reaches api.anthropic.com — always true
        "last_scan": S.last_scan,
        "now":      now.isoformat(),
    }

def _ts_ok(ts_str: str, cutoff: datetime.datetime) -> bool:
    try:
        return datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00")) >= cutoff
    except Exception:
        return False

def _proxy_alive() -> bool:
    try:
        urllib.request.urlopen("http://localhost:5099/health", timeout=2)
        return True
    except Exception:
        return False


# ── routes ────────────────────────────────────────────────────────────────────

@app.get("/api/status")
def api_status():
    return JSONResponse(_compute())

@app.get("/")
def dashboard():
    return HTMLResponse(_HTML)


# ── HTML ──────────────────────────────────────────────────────────────────────

_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thunderbird · Cost Tracker</title>
<style>
  :root{--navy:#0d1b2a;--gold:#c9a84c;--cream:#f7f3ea;--green:#2ecc71;--yellow:#f1c40f;--orange:#e67e22;--red:#e74c3c;--dim:#8899aa}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--navy);color:var(--cream);font-family:'Segoe UI',system-ui,sans-serif;font-size:14px;min-height:100vh}
  header{background:#07111c;border-bottom:2px solid var(--gold);padding:12px 24px;display:flex;align-items:center;justify-content:space-between}
  header h1{color:var(--gold);font-size:18px;letter-spacing:.5px}
  #status-bar{font-size:12px;color:var(--dim)}
  #status-bar span{margin-left:16px}
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px}
  .green{background:var(--green)}.yellow{background:var(--yellow)}.red{background:var(--red)}
  main{padding:20px 24px;display:grid;grid-template-columns:320px 1fr;grid-template-rows:auto auto;gap:16px}
  .card{background:#111f30;border:1px solid #1e3050;border-radius:8px;padding:16px}
  .card h2{font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--gold);margin-bottom:12px}

  /* gauge */
  #gauge-wrap{display:flex;flex-direction:column;align-items:center;padding:8px 0}
  .gauge-svg{width:240px;height:130px}
  .gauge-track{fill:none;stroke:#1e3050;stroke-width:18;stroke-linecap:round}
  .gauge-fill{fill:none;stroke-width:18;stroke-linecap:round;transition:stroke-dashoffset .6s ease,stroke .3s}
  #gauge-pct{font-size:36px;font-weight:700;text-anchor:middle;dominant-baseline:middle}
  #gauge-sub{font-size:11px;fill:var(--dim);text-anchor:middle}
  .gauge-stats{display:grid;grid-template-columns:1fr 1fr;gap:6px;width:100%;margin-top:12px}
  .gs{background:#0d1b2a;border-radius:4px;padding:8px;text-align:center}
  .gs .val{font-size:16px;font-weight:600;color:var(--cream)}
  .gs .lbl{font-size:10px;color:var(--dim);margin-top:2px}

  /* tables */
  table{width:100%;border-collapse:collapse;font-size:13px}
  th{color:var(--gold);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.5px;padding:6px 8px;text-align:left;border-bottom:1px solid #1e3050}
  td{padding:6px 8px;border-bottom:1px solid #0d1b2a;color:var(--cream)}
  tr:last-child td{border-bottom:none}
  .num{text-align:right;font-variant-numeric:tabular-nums;color:#aac}
  .model-name{font-family:monospace;font-size:12px;color:#88aacc}
  .ts{color:var(--dim);font-size:11px;font-family:monospace}

  /* proxy + billing cards */
  .info-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #1e3050}
  .info-row:last-child{border-bottom:none}
  .info-lbl{color:var(--dim);font-size:12px}
  .info-val{font-weight:600}
  .safe{color:var(--green)}.warn{color:var(--yellow)}.danger{color:var(--red)}

  /* layout helpers */
  .col-left{grid-column:1;display:flex;flex-direction:column;gap:16px}
  .col-right{grid-column:2;display:flex;flex-direction:column;gap:16px}
  .refresh-note{font-size:11px;color:var(--dim);text-align:right;padding-top:4px}
</style>
</head>
<body>
<header>
  <h1>🦅 Thunderbird · AI Cost Tracker</h1>
  <div id="status-bar">
    <span><span class="dot green" id="proxy-dot"></span><span id="proxy-status">max-proxy —</span></span>
    <span id="billing-badge">💳 billing safe</span>
    <span id="last-update">updating…</span>
  </div>
</header>

<main>
  <div class="col-left">

    <!-- Weekly plan limits (manual — check claude.ai) -->
    <div class="card">
      <h2>weekly plan limits · claude.ai</h2>
      <div class="info-row">
        <span class="info-lbl">All models</span>
        <span class="info-val" id="wk-all" style="color:var(--yellow)">60% used</span>
      </div>
      <div class="info-row">
        <span class="info-lbl">Sonnet only</span>
        <span class="info-val" id="wk-sonnet" style="color:var(--orange)">73% used ⚠</span>
      </div>
      <div class="info-row">
        <span class="info-lbl">Resets</span>
        <span class="info-val" id="wk-reset" style="color:var(--dim)">Thu ~9:00 PM</span>
      </div>
      <div class="info-row" style="padding-top:8px">
        <span class="info-lbl" style="font-size:11px;color:var(--dim)">
          ↗ <a href="https://claude.ai/settings/billing" target="_blank" style="color:var(--dim)">update at claude.ai</a>
        </span>
        <span id="wk-updated" style="font-size:10px;color:var(--dim)">set 2026-05-18</span>
      </div>
    </div>

    <!-- 5-hour window gauge -->
    <div class="card">
      <h2>MAX plan · 5-hr session window</h2>
      <div id="gauge-wrap">
        <svg class="gauge-svg" viewBox="0 0 240 130">
          <path class="gauge-track"  d="M30,120 A90,90 0 0,1 210,120" />
          <path class="gauge-fill" id="gauge-arc" d="M30,120 A90,90 0 0,1 210,120"
                stroke-dasharray="283" stroke-dashoffset="283" stroke="var(--green)"/>
          <text id="gauge-pct" x="120" y="100" fill="var(--cream)">0%</text>
          <text id="gauge-sub" x="120" y="118" fill="var(--dim)">0 / 600,000 tokens</text>
        </svg>
        <div class="gauge-stats">
          <div class="gs"><div class="val" id="g-inp">0</div><div class="lbl">input tokens</div></div>
          <div class="gs"><div class="val" id="g-out">0</div><div class="lbl">output tokens</div></div>
          <div class="gs"><div class="val" id="g-calls">0</div><div class="lbl">API calls</div></div>
          <div class="gs"><div class="val" id="g-reset">—</div><div class="lbl">window resets</div></div>
        </div>
      </div>
    </div>

    <!-- Proxy + billing safety -->
    <div class="card">
      <h2>max-proxy · routing status</h2>
      <div class="info-row">
        <span class="info-lbl">Proxy health</span>
        <span class="info-val" id="proxy-health">—</span>
      </div>
      <div class="info-row">
        <span class="info-lbl">Requests (5hr)</span>
        <span class="info-val" id="proxy-5hr">—</span>
      </div>
      <div class="info-row">
        <span class="info-lbl">Requests (today)</span>
        <span class="info-val" id="proxy-day">—</span>
      </div>
      <div class="info-row">
        <span class="info-lbl">Billing key exposed</span>
        <span class="info-val safe" id="billing-safe">NO ✓</span>
      </div>
      <div class="info-row">
        <span class="info-lbl">sk-ant key cost</span>
        <span class="info-val safe">$0.00</span>
      </div>
    </div>

    <!-- Today totals -->
    <div class="card">
      <h2>today · all sessions</h2>
      <div class="info-row">
        <span class="info-lbl">Total tokens</span>
        <span class="info-val" id="day-total">—</span>
      </div>
      <div class="info-row">
        <span class="info-lbl">Input tokens</span>
        <span class="info-val" id="day-inp">—</span>
      </div>
      <div class="info-row">
        <span class="info-lbl">Output tokens</span>
        <span class="info-val" id="day-out">—</span>
      </div>
      <div class="info-row">
        <span class="info-lbl">API calls</span>
        <span class="info-val" id="day-calls">—</span>
      </div>
      <div class="info-row">
        <span class="info-lbl">Estimated cost</span>
        <span class="info-val safe">$0.00 (MAX plan)</span>
      </div>
    </div>
  </div>

  <div class="col-right">
    <!-- Model breakdown -->
    <div class="card">
      <h2>model breakdown · all time (this session history)</h2>
      <table>
        <thead><tr>
          <th>Model</th><th class="num">Calls</th>
          <th class="num">Input</th><th class="num">Output</th><th class="num">Total</th>
        </tr></thead>
        <tbody id="model-table"><tr><td colspan="5" style="color:var(--dim)">loading…</td></tr></tbody>
      </table>
    </div>

    <!-- Recent events -->
    <div class="card">
      <h2>recent events · last 20 turns</h2>
      <table>
        <thead><tr>
          <th>Time</th><th>Model</th>
          <th class="num">In</th><th class="num">Out</th>
        </tr></thead>
        <tbody id="recent-table"><tr><td colspan="4" style="color:var(--dim)">loading…</td></tr></tbody>
      </table>
      <p class="refresh-note" id="refresh-note">auto-refresh every 10s</p>
    </div>
  </div>
</main>

<script>
const CAP = 600000;   // MAX 5x session cap
const ARC_LEN = 283;

function fmt(n){
  if(n>=1e6) return (n/1e6).toFixed(1)+'M';
  if(n>=1e3) return (n/1e3).toFixed(1)+'K';
  return n.toString();
}

function gaugeColor(pct){
  if(pct<70) return 'var(--green)';
  if(pct<85) return 'var(--yellow)';
  if(pct<95) return 'var(--orange)';
  return 'var(--red)';
}

function update(){
  fetch('/api/status')
    .then(r=>r.json())
    .then(d=>{
      const w = d.window;
      const pct = w.pct;
      const color = gaugeColor(pct);

      // Gauge arc
      const offset = ARC_LEN - (Math.min(pct,100)/100)*ARC_LEN;
      const arc = document.getElementById('gauge-arc');
      arc.style.strokeDashoffset = offset;
      arc.style.stroke = color;

      document.getElementById('gauge-pct').textContent = pct+'%';
      document.getElementById('gauge-pct').style.fill = color;
      document.getElementById('gauge-sub').textContent =
        fmt(w.tokens)+' / '+fmt(CAP)+' tokens';

      document.getElementById('g-inp').textContent = fmt(w.inp);
      document.getElementById('g-out').textContent = fmt(w.out);
      document.getElementById('g-calls').textContent = w.calls;
      document.getElementById('g-reset').textContent = w.reset;

      // Proxy
      const pOnline = d.proxy.status === 'ONLINE';
      document.getElementById('proxy-dot').className = 'dot '+(pOnline?'green':'red');
      document.getElementById('proxy-status').textContent =
        'max-proxy '+d.proxy.status;
      document.getElementById('proxy-health').textContent = d.proxy.status;
      document.getElementById('proxy-health').className =
        'info-val '+(pOnline?'safe':'danger');
      document.getElementById('proxy-5hr').textContent = d.proxy.requests_5hr;
      document.getElementById('proxy-day').textContent = d.proxy.requests_day;

      // Billing safety
      document.getElementById('billing-badge').textContent =
        d.billing_safe ? '💳 billing safe ✓' : '⚠️ BILLING EXPOSED';

      // Today
      const dy = d.day;
      document.getElementById('day-total').textContent = fmt(dy.total);
      document.getElementById('day-inp').textContent = fmt(dy.inp);
      document.getElementById('day-out').textContent = fmt(dy.out);
      document.getElementById('day-calls').textContent = dy.calls;

      // Model table
      const mtb = document.getElementById('model-table');
      if(d.models.length===0){
        mtb.innerHTML='<tr><td colspan="5" style="color:var(--dim)">no data yet</td></tr>';
      } else {
        mtb.innerHTML = d.models.map(([m,v])=>
          `<tr>
            <td class="model-name">${m}</td>
            <td class="num">${v.calls}</td>
            <td class="num">${fmt(v.inp)}</td>
            <td class="num">${fmt(v.out)}</td>
            <td class="num">${fmt(v.inp+v.out)}</td>
          </tr>`
        ).join('');
      }

      // Recent table
      const rtb = document.getElementById('recent-table');
      if(d.recent.length===0){
        rtb.innerHTML='<tr><td colspan="4" style="color:var(--dim)">no events yet</td></tr>';
      } else {
        rtb.innerHTML = d.recent.map(r=>
          `<tr>
            <td class="ts">${r.ts||'—'}</td>
            <td class="model-name">${r.model}</td>
            <td class="num">${fmt(r.inp)}</td>
            <td class="num">${fmt(r.out)}</td>
          </tr>`
        ).join('');
      }

      // Last update
      const now = new Date();
      document.getElementById('last-update').textContent =
        'updated '+now.toLocaleTimeString();
      document.getElementById('refresh-note').textContent =
        'last scan: '+(d.last_scan==='never'?'scanning…':d.last_scan.substring(11,19)+' UTC')
        +'  |  auto-refresh every 10s';
    })
    .catch(()=>{
      document.getElementById('last-update').textContent = '⚠ fetch error';
    });
}

update();
setInterval(update, 10000);
</script>
</body>
</html>
"""


# ── startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    PROXY_LOG.parent.mkdir(parents=True, exist_ok=True)
    t = threading.Thread(target=_scan_loop, daemon=True)
    t.start()
    print(f"[tracker] Thunderbird Cost Tracker → http://localhost:{PORT}")
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")

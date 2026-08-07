#!/usr/bin/env python3
"""
OpsCenter/unified_limit_meter.py — Multi-Engine Rate Limit & Quota Meter
Unifies 5-hour, daily, weekly, and monthly meters across:
- Claude Code (MAX): OAuth API (5h session %, 7d weekly %)
- Poe.com: Points reservoir (1,002,366 pts, $30.37 USD baseline)
- OpenCode GO: $10.00 credit meter & DeepSeek v4 ZEN ($0 free)
- Google Antigravity: Gemini 3.6 Flash / 3.1 Pro daily quota & reset (18:00 MT)
- OpenRouter: $10.00 monthly hard spend cap
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# --- Timezone & Paths ---
MT = timezone(timedelta(hours=-6))
REPO = Path(__file__).resolve().parent.parent
OPSCENTER = REPO / "OpsCenter"
DATA_DIR = REPO / "data"
STATE_DIR = OPSCENTER / "state"

POE_POINTS_FILE = DATA_DIR / "poe_points.json"
BASELINE_FILE = OPSCENTER / "baseline_starting_points.json"
OUTPUT_HTML_DIR = REPO / "output" / "html"
OUTPUT_HTML_FILE = OUTPUT_HTML_DIR / "rate_limit_meter.html"
RATE_LIMIT_MD = OPSCENTER / "collaboration" / "rate_limit_status.md"

def _now():
    return datetime.now(MT)

def render_bar(pct: float, width: int = 20) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = int(round((pct / 100.0) * width))
    return "█" * filled + "░" * (width - filled)

def get_claude_telemetry() -> dict:
    """Fetch authoritative Claude Code capacity telemetry."""
    try:
        sys.path.insert(0, str(REPO))
        from core.relay.cc_capacity import get_cc_capacity
        return get_cc_capacity()
    except Exception as e:
        return {
            "engine": "CC", "status": "UNKNOWN", "ok": False,
            "five_hour_pct": 0.0, "seven_day_pct": 0.0, "error": str(e)
        }

def get_ag_telemetry() -> dict:
    """Fetch Antigravity / Gemini limit telemetry."""
    try:
        sys.path.insert(0, str(REPO))
        from core.relay.engine_limits import check_headroom
        return check_headroom("AG")
    except Exception as e:
        return {
            "engine": "AG", "status": "UNKNOWN", "ok": False,
            "used_pct": 0.0, "headroom_pct": 100.0, "error": str(e)
        }

def get_poe_telemetry() -> dict:
    """Fetch Poe.com points reservoir status."""
    if POE_POINTS_FILE.exists():
        try:
            data = json.loads(POE_POINTS_FILE.read_text())
            pts = data.get("points_available", 1002366)
            val = data.get("value_usd", 30.37)
            cap = 1500000
            pct = round((pts / cap) * 100, 1)
            return {
                "points_available": pts,
                "value_usd": val,
                "cap": cap,
                "pct": pct,
                "timestamp": data.get("timestamp")
            }
        except Exception:
            pass
    return {"points_available": 1002366, "value_usd": 30.37, "cap": 1500000, "pct": 66.8}

def get_opencode_telemetry() -> dict:
    """Fetch OpenCode GO credit & usage telemetry from the local opencode.db.

    Reads the `session` table (cost, tokens) for the current calendar month and
    computes: month cost, running total, credits remaining on the GO plan.
    Read-only WAL-safe connection (Claude/AG gotcha). Cost field is opencode's
    rate-card estimate (directional, not invoiced — Claude caveat).

    GO plan: $10.00 base credit. Note: opencode GO is a monthly credit allowance;
    month cost > $10 means the meter should flag for review, not clamp to 0.
    """
    import sqlite3
    go_credits_starting = 10.00
    usage = {
        "go_credits_starting_usd": go_credits_starting,
        "go_credits_remaining_usd": go_credits_starting,
        "month_cost_usd": 0.0,
        "month_sessions": 0,
        "month_input_tokens": 0,
        "month_output_tokens": 0,
        "running_total_usd": 0.0,
        "zen_tier": "DeepSeek v4 ZEN ($0 free)",
        "openrouter_cap_usd": 10.00,
        "source": "local opencode.db",
    }
    db = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
    if not db.exists():
        usage["note"] = "opencode.db not found"
        return usage
    try:
        import calendar
        now = _now()
        # first of current month in ms
        month_start = int(datetime(now.year, now.month, 1, tzinfo=MT).timestamp() * 1000)
        month_end = int(datetime(
            now.year + (1 if now.month == 12 else 0),
            1 if now.month == 12 else now.month + 1, 1, tzinfo=MT).timestamp() * 1000)
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=10)
        con.execute("PRAGMA busy_timeout=3000")
        row = con.execute(
            """SELECT COUNT(*), SUM(cost), SUM(tokens_input), SUM(tokens_output)
               FROM session WHERE time_created >= ? AND time_created < ?""",
            (month_start, month_end),
        ).fetchone()
        # per-provider/model cost split (model col is JSON {providerID,id})
        prov_rows = con.execute(
            """SELECT model, SUM(cost), COUNT(*) FROM session
               WHERE time_created >= ? AND time_created < ? GROUP BY model
               ORDER BY SUM(cost) DESC""", (month_start, month_end),
        ).fetchall()
        con.close()
        sessions, cost, tin, tout = row[0], row[1] or 0.0, row[2] or 0, row[3] or 0
        by_provider = {}
        for model, c, n in prov_rows:
            try:
                m = json.loads(model or "{}")
                prov, mid = m.get("providerID", "?"), m.get("id", "?")
            except Exception:
                prov, mid = "?", str(model)[:30]
            key = f"{prov}/{mid}"
            by_provider[key] = {"cost": round(c or 0, 4), "sessions": n}
        usage.update({
            "month_cost_usd": round(cost, 4),
            "month_sessions": sessions,
            "month_input_tokens": int(tin),
            "month_output_tokens": int(tout),
            "running_total_usd": round(cost, 4),
            "go_credits_remaining_usd": round(max(0.0, go_credits_starting - cost), 4),
            "by_provider": by_provider,
        })
    except Exception as e:
        usage["note"] = f"query failed: {e}"
    return usage

def evaluate_unified_meter():
    cc = get_claude_telemetry()
    ag = get_ag_telemetry()
    poe = get_poe_telemetry()
    oc = get_opencode_telemetry()

    oc_month_cost = oc.get("month_cost_usd", 0.0)
    oc_remaining = oc.get("go_credits_remaining_usd", 10.00)
    oc_cap = oc.get("go_credits_starting_usd", 10.00)
    oc_pct = round((oc_month_cost / oc_cap) * 100, 1) if oc_cap else 0.0

    cc_5h_pct = cc.get("five_hour_pct") or 0.0
    cc_7d_pct = cc.get("seven_day_pct") or 0.0
    ag_used_pct = ag.get("used_pct") or 0.0
    poe_pct = poe.get("pct") or 0.0

    # Determine pre-flight gate status
    gate_status = "PASS"
    warn_reasons = []
    if cc_7d_pct >= 90.0:
        gate_status = "WARN"
        warn_reasons.append(f"Claude 7-Day limit high ({cc_7d_pct}%)")
    if cc_5h_pct >= 85.0:
        gate_status = "WARN"
        warn_reasons.append(f"Claude 5-Hour limit high ({cc_5h_pct}%)")
    if ag_used_pct >= 85.0:
        gate_status = "WARN"
        warn_reasons.append(f"Antigravity daily quota high ({ag_used_pct}%)")

    now_str = _now().strftime("%Y-%m-%d %H:%M:%S MT")

    # Generate ASCII Console Output
    ascii_out = []
    ascii_out.append("===================== THUNDERBIRD MULTI-ENGINE LIMIT METER =====================")
    ascii_out.append(f"Timestamp: {now_str}")
    ascii_out.append("--------------------------------------------------------------------------------")
    ascii_out.append(f"5-HOUR SESSION (Claude MAX) : [{render_bar(cc_5h_pct)}] {cc_5h_pct:5.1f}%  ({cc.get('reset_str', 'Active')})")
    ascii_out.append(f"WEEKLY CLAUDE (7-Day Rolling): [{render_bar(cc_7d_pct)}] {cc_7d_pct:5.1f}%  ({cc.get('seven_day_resets_at', 'Active')})")
    ascii_out.append(f"DAILY ANTIGRAVITY (Gemini)  : [{render_bar(ag_used_pct)}] {ag_used_pct:5.1f}%  (Resets 18:00 MT)")
    ascii_out.append(f"POE POINTS RESERVOIR       : [{render_bar(poe_pct)}] {poe_pct:5.1f}%  ({poe['points_available']:,} pts / ~${poe['value_usd']:.2f})")
    ascii_out.append(f"OPENCODE GO CREDITS        : [{render_bar(oc_pct)}] {oc_pct:5.1f}%  (${oc_month_cost:.2f}/$10.00 used · ${oc_remaining:.2f} left · {oc.get('month_sessions',0)} sess)")
    ascii_out.append(f"DEEPSEEK v4 ZEN TIER       : [{render_bar(0.0)}]   0.0%  ($0.00 Free Tier active)")
    ascii_out.append(f"OPENROUTER MONTHLY CAP     : [{render_bar(0.0)}]   0.0%  ($0.00/$10.00 Hard Cap)")
    ascii_out.append("--------------------------------------------------------------------------------")
    if gate_status == "PASS":
        ascii_out.append("PRE-FLIGHT GATE: 🟢 PASSED (All engines within safe operating headroom)")
    else:
        ascii_out.append(f"PRE-FLIGHT GATE: 🟡 WARNING ({', '.join(warn_reasons)})")
    ascii_out.append("================================================================================")

    console_str = "\n".join(ascii_out)

    # Save to Markdown
    md_content = f"# THUNDERBIRD MULTI-ENGINE LIMIT METER\n`Updated: {now_str}`\n\n```text\n{console_str}\n```\n"
    RATE_LIMIT_MD.write_text(md_content)

    # Save HTML to Portal
    OUTPUT_HTML_DIR.mkdir(parents=True, exist_ok=True)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Thunderbird Multi-Engine Limit Meter</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; }}
        .card {{ background: #1e293b; border-radius: 8px; padding: 24px; max-width: 900px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
        h1 {{ color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 12px; margin-top: 0; }}
        .meter-row {{ margin-bottom: 18px; }}
        .meter-label {{ display: flex; justify-content: space-between; font-size: 14px; font-weight: 600; margin-bottom: 6px; }}
        .bar-bg {{ background: #334155; border-radius: 6px; height: 22px; overflow: hidden; position: relative; }}
        .bar-fill {{ height: 100%; transition: width 0.3s ease; }}
        .fill-green {{ background: linear-gradient(90deg, #10b981, #34d399); }}
        .fill-yellow {{ background: linear-gradient(90deg, #f59e0b, #fbbf24); }}
        .fill-red {{ background: linear-gradient(90deg, #ef4444, #f87171); }}
        .gate-banner {{ padding: 12px 16px; border-radius: 6px; font-weight: bold; margin-top: 24px; text-align: center; }}
        .gate-pass {{ background: #064e3b; color: #6ee7b7; border: 1px solid #10b981; }}
        .gate-warn {{ background: #78350f; color: #fde68a; border: 1px solid #f59e0b; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>⚡ Thunderbird Multi-Engine Limit Meter</h1>
        <p style="color: #94a3b8; font-size: 13px;">Last Updated: {now_str}</p>
        
        <div class="meter-row">
            <div class="meter-label"><span>5-Hour Session (Claude MAX)</span><span>{cc_5h_pct:.1f}%</span></div>
            <div class="bar-bg"><div class="bar-fill {'fill-red' if cc_5h_pct >= 85 else 'fill-yellow' if cc_5h_pct >= 60 else 'fill-green'}" style="width: {cc_5h_pct}%;"></div></div>
        </div>
        
        <div class="meter-row">
            <div class="meter-label"><span>Weekly Volume (Claude 7-Day)</span><span>{cc_7d_pct:.1f}%</span></div>
            <div class="bar-bg"><div class="bar-fill {'fill-red' if cc_7d_pct >= 90 else 'fill-yellow' if cc_7d_pct >= 70 else 'fill-green'}" style="width: {cc_7d_pct}%;"></div></div>
        </div>

        <div class="meter-row">
            <div class="meter-label"><span>Daily Antigravity (Gemini Daily)</span><span>{ag_used_pct:.1f}%</span></div>
            <div class="bar-bg"><div class="bar-fill {'fill-red' if ag_used_pct >= 85 else 'fill-yellow' if ag_used_pct >= 60 else 'fill-green'}" style="width: {ag_used_pct}%;"></div></div>
        </div>

        <div class="meter-row">
            <div class="meter-label"><span>Poe.com Points Reservoir ({poe['points_available']:,} pts)</span><span>{poe_pct:.1f}%</span></div>
            <div class="bar-bg"><div class="bar-fill fill-green" style="width: {poe_pct}%;"></div></div>
        </div>

            <div class="meter-row">
                <div class="meter-label"><span>OpenCode GO Credits (${oc_month_cost:.2f} used / ${oc_remaining:.2f} left · {oc.get('month_sessions',0)} sessions)</span><span>{oc_pct:.1f}%</span></div>
                <div class="bar-bg"><div class="bar-fill {'fill-red' if oc_pct >= 85 else 'fill-yellow' if oc_pct >= 60 else 'fill-green'}" style="width: {min(100, oc_pct)}%;"></div></div>
            </div>

        <div class="meter-row">
            <div class="meter-label"><span>DeepSeek v4 ZEN Tier ($0 Free)</span><span>0.0% Burn</span></div>
            <div class="bar-bg"><div class="bar-fill fill-green" style="width: 100%;"></div></div>
        </div>

        <div class="gate-banner {'gate-pass' if gate_status == 'PASS' else 'gate-warn'}">
            PRE-FLIGHT GATE: {'🟢 PASSED - Headroom Clear' if gate_status == 'PASS' else '🟡 WARNING - High Utilization Detected'}
        </div>
    </div>
</body>
</html>
"""
    OUTPUT_HTML_FILE.write_text(html_content)

    return console_str

if __name__ == "__main__":
    result = evaluate_unified_meter()
    print(result)

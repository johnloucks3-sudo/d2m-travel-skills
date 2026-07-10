#!/usr/bin/env python3
"""Morning Brief Dashboard — local server. Serves the dashboard HTML at / and
live JSON at /api/data, sourced from hale_state.json, mission_board.json, and
system health (free, systemctl)."""
import json
import re
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
DASHBOARD_HTML = ROOT / "output" / "morning_brief_dashboard.html"
HALE_STATE = ROOT / "hale_state.json"
MISSION_BOARD = ROOT / "OpsCenter" / "mission_board.json"
PORT = 8926

MISSION_SERVICES = [
    "agentmail-listener.service", "cloudflared.service", "cost-tracker.service",
    "d2m-litellm-gateway.service", "thunderbird-ai-metrics.service",
    "thunderbird-api.service", "thunderbird-ccr.service",
    "thunderbird-continuity.service", "thunderbird-mcp-tailscale.service",
    "thunderbird-mcp.service", "thunderbird-overwatch.service",
    "thunderbird-scheduler.service", "thunderbird-sla-monitor.service",
    "thunderbird-telegram-gw.service", "thunderbird-tunnel.service",
    "thunderbird-whatsapp-webhook.service",
]


def get_pipeline():
    state = json.loads(HALE_STATE.read_text())
    fp = state.get("financial_pulse", {})
    total = fp.get("total_d2m_pipeline", 0.0)
    clients = 16
    pct_of_target = 68
    target = round(total / (pct_of_target / 100), 2) if pct_of_target else None
    return {
        "total": total,
        "clients": clients,
        "pct_of_target": pct_of_target,
        "target_estimate": target,
        "note": "target_estimate is derived from the 68% figure (no hard YTD target on file)",
    }


def get_fpd_alerts():
    state = json.loads(HALE_STATE.read_text())
    alerts = []
    now = datetime.now(timezone.utc)
    for a in state.get("deferred_alerts", []):
        fpd = a.get("fpd")
        if not fpd:
            continue
        try:
            fpd_dt = datetime.fromisoformat(fpd).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        days_out = (fpd_dt - now).days
        severity = "critical" if days_out <= 14 else ("warning" if days_out <= 30 else "good")
        alerts.append({
            "client": a.get("client", "Unknown"),
            "booking": a.get("booking"),
            "fpd_date": fpd,
            "amount": a.get("amount"),
            "days_out": days_out,
            "severity": severity,
            "priority": a.get("priority", "P1"),
        })
    alerts.sort(key=lambda x: x["days_out"])
    return alerts


def get_system_health():
    free_out = subprocess.run(["free", "-m"], capture_output=True, text=True).stdout
    # Mem: total used free shared buff/cache available — "available" is the
    # metric that matters (raw "free" undercounts reclaimable disk cache).
    mem_line = re.search(r"Mem:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", free_out)
    swap_line = re.search(r"Swap:\s+(\d+)\s+(\d+)\s+(\d+)", free_out)
    mem = {"total_mb": 0, "used_mb": 0, "free_mb": 0, "pct_used": 0}
    swap = {"total_mb": 0, "used_mb": 0, "free_mb": 0, "pct_used": 0}
    if mem_line:
        total, used, _free, _shared, _buffcache, available = (int(x) for x in mem_line.groups())
        mem = {"total_mb": total, "used_mb": used, "free_mb": available,
               "pct_used": round((total - available) / total * 100, 1) if total else 0}
    if swap_line:
        total, used, free_mb = (int(x) for x in swap_line.groups())
        swap = {"total_mb": total, "used_mb": used, "free_mb": free_mb,
                "pct_used": round(used / total * 100, 1) if total else 0}

    active = 0
    down = []
    for svc in MISSION_SERVICES:
        r = subprocess.run(["systemctl", "--user", "is-active", svc], capture_output=True, text=True)
        if r.stdout.strip() == "active":
            active += 1
        else:
            down.append(svc)

    return {
        "memory": mem,
        "swap": swap,
        "services": {"active": active, "total": len(MISSION_SERVICES), "down": down},
    }


def get_missions():
    board = json.loads(MISSION_BOARD.read_text())
    missions = board.get("missions", [])
    buckets = {"active": [], "review": [], "backlog": [], "done": []}
    active_statuses = {"active", "in_progress", "monitoring"}
    review_statuses = {"pending_review", "pending_commander", "resolved_new_finding"}
    backlog_statuses = {"deferred", "parked", "suspended"}
    done_statuses = {"completed", "archived", "closed", "closed_duplicate", "killed"}
    for m in missions:
        status = m.get("status", "")
        if status in active_statuses:
            buckets["active"].append(m)
        elif status in review_statuses:
            buckets["review"].append(m)
        elif status in backlog_statuses:
            buckets["backlog"].append(m)
        elif status in done_statuses:
            buckets["done"].append(m)

    def sample(items, n=5):
        return [{"id": m.get("id"), "title": m.get("title"), "priority": m.get("priority")}
                for m in items[:n]]

    return {
        "active": {"count": len(buckets["active"]), "samples": sample(buckets["active"])},
        "review": {"count": len(buckets["review"]), "samples": sample(buckets["review"])},
        "backlog": {"count": len(buckets["backlog"]), "samples": sample(buckets["backlog"])},
        "done": {"count": len(buckets["done"]), "samples": sample(buckets["done"])},
    }


def build_payload():
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": get_pipeline(),
        "fpd_alerts": get_fpd_alerts(),
        "system_health": get_system_health(),
        "missions": get_missions(),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/api/data"):
            try:
                payload = build_payload()
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        if self.path in ("/", "/dashboard", "/index.html"):
            body = DASHBOARD_HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Dashboard server on http://127.0.0.1:{PORT}/  (data: /api/data)")
    server.serve_forever()

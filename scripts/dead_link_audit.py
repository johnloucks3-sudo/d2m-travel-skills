#!/usr/bin/env python3
"""Dead Link Audit — checks all D2M URLs for HTTP status. Part of M-177."""
import json, subprocess, sys, time, os
from datetime import datetime
from pathlib import Path

URLS = [
    # Root + www
    ("https://d2mluxury.quest", "Homepage root"),
    ("https://www.d2mluxury.quest", "Homepage www"),
    ("https://www.d2mluxury.quest/destinations/mediterranean", "Bulletin CTA — Med"),
    ("https://www.d2mluxury.quest/destinations/alaska", "Bulletin CTA — Alaska"),
    ("https://www.d2mluxury.quest/contact", "Bulletin CTA — Contact"),
    # Itinerary subdomain
    ("https://itinerary.d2mluxury.quest", "Itinerary root"),
    ("https://itinerary.d2mluxury.quest/flight_plan.html", "Flight plan"),
    ("https://itinerary.d2mluxury.quest/hale_dashboard.html", "Hale dashboard"),
    ("https://itinerary.d2mluxury.quest/executive_gantt_all_clients.html", "Executive gantt"),
    # API / MCP
    ("https://api.d2mluxury.quest", "API root"),
    ("https://api.d2mluxury.quest/docs", "API docs"),
    ("https://mcp.d2mluxury.quest", "MCP root"),
    ("https://mcp.d2mluxury.quest/sse", "MCP SSE"),
    ("https://mcp.d2mluxury.quest/mcp", "MCP endpoint"),
    # Infrastructure
    ("https://n8n.d2mluxury.quest", "n8n webhook root"),
    ("https://tg.d2mluxury.quest", "Telegram webhook root"),
    ("https://allm.d2mluxury.quest", "AllM chat"),
    ("https://portal.d2mluxury.quest", "Client portal"),
    ("https://app.d2mluxury.quest", "App portal"),
    ("https://code.d2mluxury.quest", "Code subdomain"),
    ("https://thunderbird.d2mluxury.quest", "Thunderbird subdomain"),
]

def check_url(url, label="", timeout=15):
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--connect-timeout", str(timeout), url],
            capture_output=True, text=True, timeout=timeout+5
        )
        code = r.stdout.strip()
        notes = ""
        if code in ("000", ""):
            code = "000"
            notes = "Connection failed / DNS / timeout"
        elif code.startswith("2"):
            notes = "OK"
        elif code == "401":
            notes = "Auth required (may be OK)"
        elif code == "403":
            notes = "Forbidden"
        elif code == "404":
            notes = "NOT FOUND"
        elif code.startswith("5"):
            notes = "Server error"
        elif code == "525":
            notes = "SSL handshake (Cloudflare)"
        return {"url": url, "label": label, "status": code, "notes": notes, "ok": code.startswith(("2", "3")) or code == "401"}
    except subprocess.TimeoutExpired:
        return {"url": url, "label": label, "status": "TIMEOUT", "notes": f"Timed out after {timeout}s", "ok": False}
    except Exception as e:
        return {"url": url, "label": label, "status": "ERROR", "notes": str(e), "ok": False}

def check_portal(portal_name):
    """Check portal accessibility via OA status."""
    try:
        r = subprocess.run(
            ["python3", "/home/john/Thunderbird/OpsCenter/mission_board_sync.py", "add", f"DIAG-{portal_name}-{int(time.time())}", f"Portal connectivity test for {portal_name}. Delete after reading.", "P3"],
            capture_output=True, text=True, timeout=30
        )
        return {"portal": portal_name, "diag_mission": r.stdout.strip(), "notes": "Diagnostic mission created to test portal"}
    except Exception as e:
        return {"portal": portal_name, "error": str(e)}

if __name__ == "__main__":
    print(f"D2M Dead Link Audit — {datetime.now().isoformat()}")
    print(f"{'='*70}")
    results = []
    failed = []
    for url, label in URLS:
        result = check_url(url, label)
        results.append(result)
        icon = "✅" if result["ok"] else "❌"
        print(f"  {icon} [{result['status']:>4}] {label:.<35} {url}")
        if not result["ok"]:
            failed.append(result)

    print(f"\n{'='*70}")
    print(f"Total: {len(results)} URLs")
    print(f"OK:    {sum(1 for r in results if r['ok'])}")
    print(f"FAIL:  {len(failed)}")
    if failed:
        print(f"\nFailed URLs:")
        for f in failed:
            print(f"  ❌ [{f['status']}] {f['label']} — {f['notes']}")
            print(f"     {f['url']}")

    report_path = Path("/home/john/Thunderbird/output/dead_link_audit_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "mission": "M-177",
        "total": len(results),
        "ok": sum(1 for r in results if r['ok']),
        "failed": len(failed),
        "results": results
    }, indent=2))
    print(f"\nReport saved: {report_path}")
    sys.exit(1 if failed else 0)

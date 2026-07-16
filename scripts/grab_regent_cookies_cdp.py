#!/usr/bin/env python3
"""Grab Regent ASPXAUTH from live Chrome via CDP Network.getAllCookies."""
import requests, json, websocket
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
TARGETS = [ROOT/"creds"/"regent_cookies_oa.json", ROOT/"creds"/"regent_cookies.json"]

tabs = requests.get("http://localhost:9222/json", timeout=5).json()
# Prefer the real rssc.com PAGE tab; fall back to first debuggable page.
# BUG FIX 2026-07-16: a substring check on the raw URL false-matches ad-tracker
# iframes whose URL embeds "ref=https%3A%2F%2Fwww.rssc.com..." as a referrer
# query param (rssc.com's own ad pixels do this constantly) -- must also
# require type=="page" so we don't hand a websocket to a tracking iframe.
def _is_rssc_page(t):
    url = t.get("url", "")
    return t.get("type") == "page" and ("://www.rssc.com" in url or "://rssc.com" in url)

tab = next((t for t in tabs if _is_rssc_page(t) and t.get("webSocketDebuggerUrl")), None)
if not tab:
    tab = next((t for t in tabs if t.get("type") == "page" and t.get("webSocketDebuggerUrl")), None)
if not tab:
    print("No debuggable Chrome tab found"); exit(1)

print(f"Tab: {tab.get('url','')[:80]}")
ws = websocket.create_connection(
    tab["webSocketDebuggerUrl"], timeout=5,
    header=["Origin: http://localhost:9222"]
)
ws.send(json.dumps({"id":1,"method":"Network.getAllCookies","params":{}}))
result = json.loads(ws.recv())
ws.close()

all_cookies = result.get("result",{}).get("cookies",[])
rssc = [c for c in all_cookies if "rssc.com" in c.get("domain","")]
auth = [c for c in rssc if "ASPXAUTH" in c.get("name","") or "ASP.NET_SessionId" in c.get("name","")]

print(f"rssc.com cookies: {len(rssc)}  |  auth cookies: {len(auth)}")
for c in auth:
    import datetime
    exp = c.get("expires",-1)
    exp_str = datetime.datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M") if exp > 0 else "session"
    print(f"  ✅ {c['name']}  domain={c['domain']}  expires={exp_str}")

if not auth:
    print("No ASPXAUTH found — Commander may not be logged into rssc.com in Chrome"); exit(2)

# Save in Playwright format
out = []
for c in rssc:
    pc = {k: c[k] for k in ("name","value","domain","path") if k in c}
    pc["secure"] = c.get("secure", False)
    pc["httpOnly"] = c.get("httpOnly", False)
    if c.get("expires",-1) > 0:
        pc["expires"] = float(c["expires"])
    ss = c.get("sameSite","")
    if ss and ss != "Unspecified":
        pc["sameSite"] = ss
    out.append(pc)

for tgt in TARGETS:
    tgt.parent.mkdir(parents=True, exist_ok=True)
    tgt.write_text(json.dumps(out, indent=2))
    print(f"  Wrote {len(out)} cookies → {tgt.name}")

print("Done — Regent portal cookies captured.")

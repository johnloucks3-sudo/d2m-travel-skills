#!/usr/bin/env python3
"""
push_claude_usage.py — read the REAL Claude MAX usage from an already-open
claude.ai/settings/usage tab in the Commander's authenticated Chrome (CDP :9222)
and POST it to the cost dashboard. Reading an existing human-loaded tab avoids the
Cloudflare bot wall that blocks any automated *navigation*.

Hands-off: Commander just keeps the usage tab parked; a systemd timer runs this.
Built 2026-06-17 by Hale.
"""
import json
import sys
import urllib.request

CDP = "http://localhost:9222"
INGEST = "http://127.0.0.1:8903/api/plan?token=yoda-grandeur"

EXTRACT_JS = r"""
() => {
  const L = document.body.innerText.split('\n').map(s=>s.trim()).filter(Boolean);
  const f = a => { const i = L.findIndex(s=>s.toLowerCase().startsWith(a)); return i<0?[]:L.slice(i+1,i+5); };
  const pct = A => { for (const s of A){ const m=s.match(/(\d+)%\s*used/i); if(m) return +m[1]; } return null; };
  const rs  = A => { for (const s of A){ if(/^resets\b/i.test(s)) return s; } return null; };
  const tier = (L.find(s=>/max\s*\(\d+x\)/i.test(s)) || 'Max');
  const se=f('current session'), al=f('all models'), so=f('sonnet only');
  return { plan_tier:tier,
           session_pct:pct(se), session_reset:rs(se),
           weekly_all_pct:pct(al), weekly_all_reset:rs(al),
           weekly_sonnet_pct:pct(so), weekly_sonnet_reset:rs(so) };
}
"""


def main():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            b = p.chromium.connect_over_cdp(CDP)
        except Exception as e:
            print(f"[push_usage] CDP not reachable: {e}", file=sys.stderr)
            return 2
        page = None
        for ctx in b.contexts:
            for pg in ctx.pages:
                if "claude.ai/settings/usage" in (pg.url or ""):
                    page = pg
                    break
            if page:
                break
        if not page:
            print("[push_usage] no open claude.ai/settings/usage tab — open one and park it.", file=sys.stderr)
            return 3
        try:
            data = page.evaluate(EXTRACT_JS)
        except Exception as e:
            print(f"[push_usage] evaluate failed: {e}", file=sys.stderr)
            return 4

    if data.get("session_pct") is None and data.get("weekly_all_pct") is None:
        print("[push_usage] usage tab not rendered yet (no %); skipping.", file=sys.stderr)
        return 5

    body = json.dumps(data).encode()
    req = urllib.request.Request(INGEST, data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f"[push_usage] pushed: session={data.get('session_pct')}% "
              f"weekly_all={data.get('weekly_all_pct')}% sonnet={data.get('weekly_sonnet_pct')}%")
        return 0
    except Exception as e:
        print(f"[push_usage] POST failed: {e}", file=sys.stderr)
        return 6


if __name__ == "__main__":
    sys.exit(main())

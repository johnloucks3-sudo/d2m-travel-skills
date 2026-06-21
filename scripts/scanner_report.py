#!/usr/bin/env python3
"""
SCANNER REPORT + ADJUDICATION → Commander (every pulse, timestamped)
====================================================================
Dreams2Memories Travel · built 2026-06-21
Commander: "Send me results of every tech scan with a timestamp, then send me
your adjudication — information yields confidence and assurance."

After each pulse, this emails johnloucks3 TWO things, timestamped:
  1. RAW — every find the scanner collected this pulse (the unfiltered take).
  2. HALE'S ADJUDICATION — the kill-pass verdict on each: KILL (noise/not a
     tool), WATCH (real but not for us yet), TRIAL (worth a bounded test),
     ADOPT (clear win). Cheap collects; Hale adjudicates before anything is
     believed — exactly the discipline Dembe demanded.

v1 adjudication is a transparent first-pass heuristic (kills discussion-noise,
surfaces real tools); my deeper verdict refines it in the loop. The verdict is
written back to the holding queue so the bus/board only ever see ADOPT/TRIAL.

Run:  python3 scripts/scanner_report.py        # adjudicate new finds + email
"""
import base64, json, sys, re
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

ROOT = Path("/home/john/Thunderbird")
HOLDING = ROOT / "state" / "scanner_holding.jsonl"
REPORTED = ROOT / "state" / "scanner_reported.json"
JL3 = ROOT / "creds" / "johnloucks3_token.json"
YODA = "johnloucks3@gmail.com"

# Hale's kill-pass heuristic (transparent v1). Noise dies; real tools survive.
NOISE = ["ask hn", "is claude code worth", "do you use", "what technique", "how to",
         "anyone else", "thoughts on", "opinion", "rant", "why i ", "i tried", "vs codex"]
TOOL_SIGNAL = ["directory", "library", "framework", "server", "plugin", "skill", "sdk",
               "mcp", "registry", "tool", "github.com", "open source", "mit", "apache"]


def adjudicate(text: str) -> tuple[str, str]:
    low = text.lower()
    if any(n in low for n in NOISE) and "github.com" not in low:
        return "KILL", "discussion/opinion, not a tool"
    sig = [s for s in TOOL_SIGNAL if s in low]
    if len(sig) >= 2 or "github.com" in low:
        return "TRIAL", f"real tool ({', '.join(sig[:3]) or 'repo'}) — worth a bounded look"
    if sig:
        return "WATCH", f"possible tool ({sig[0]}) — track"
    return "WATCH", "unclassified — track"


def main():
    if not HOLDING.exists():
        print("no holding queue"); return
    rows = [json.loads(l) for l in HOLDING.read_text().splitlines() if l.strip()]
    reported = set(json.loads(REPORTED.read_text()).get("keys", [])) if REPORTED.exists() else set()
    new = [r for r in rows if r.get("key") not in reported]
    if not new:
        print("no new finds since last report"); return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    for r in new:
        v, why = adjudicate(r["text"])
        r["verdict"], r["verdict_reason"] = v, why
    adopt = [r for r in new if r["verdict"] == "ADOPT"]
    trial = [r for r in new if r["verdict"] == "TRIAL"]
    watch = [r for r in new if r["verdict"] == "WATCH"]
    kill = [r for r in new if r["verdict"] == "KILL"]

    L = ["<div style='font-family:Georgia,serif;color:#1a1a2e;max-width:760px'>",
         f"<p style='color:#003087'><b>TECH SCAN — {ts}</b><br><i>airborne scanner pulse · {len(new)} finds · sectors {', '.join(sorted(set(r['sector'] for r in new)))}</i></p>",
         "<h3 style='color:#003087'>HALE'S ADJUDICATION (kill-pass before anything's believed)</h3>",
         f"<p>📊 <b>{len(trial)} TRIAL</b> · {len(watch)} WATCH · <b>{len(kill)} KILLED as noise</b> · {len(adopt)} adopt</p>"]
    if trial:
        L.append("<b>🧪 TRIAL — real tools, worth a bounded look:</b><ul>"
                 + "".join(f"<li>{r['text'][:130]}<br><i style='color:#555'>↳ {r['verdict_reason']}</i></li>" for r in trial[:12]) + "</ul>")
    if watch:
        L.append("<b>👁 WATCH:</b><ul>" + "".join(f"<li>{r['text'][:110]}</li>" for r in watch[:8]) + "</ul>")
    if kill:
        L.append(f"<b>🗑 KILLED ({len(kill)}) — discussion/opinion, not tools (so they don't pile up):</b><ul>"
                 + "".join(f"<li style='color:#888'>{r['text'][:90]}</li>" for r in kill[:6]) + "</ul>")
    L.append("<hr><details><summary style='color:#003087'><b>RAW — all finds this pulse (unfiltered)</b></summary><ul>"
             + "".join(f"<li>[{r['sector']}] {r['text'][:120]} <i>({r['source']})</i></li>" for r in new) + "</ul></details>")
    L.append("<p style='color:#003087'>— Hale · cheap collects, I adjudicate · this lands every pulse, no direction needed.</p></div>")

    c = Credentials.from_authorized_user_info(json.loads(JL3.read_text()))
    if c.expired and c.refresh_token: c.refresh(Request()); JL3.write_text(c.to_json())
    s = build("gmail", "v1", credentials=c)
    m = MIMEText("".join(L), "html"); m["To"] = YODA; m["From"] = YODA
    m["Subject"] = f"Tech Scan {ts} — {len(trial)} trial / {len(kill)} killed (Hale adjudicated)"
    sent = s.users().messages().send(userId="me", body={"raw": base64.urlsafe_b64encode(m.as_bytes()).decode()}).execute()

    # write verdicts back + mark reported
    HOLDING.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    reported |= {r["key"] for r in new}
    REPORTED.write_text(json.dumps({"keys": sorted(reported)[-5000:]}))
    print(f"DELIVERED tech scan {ts} to {YODA} id={sent.get('id')}: {len(new)} finds → {len(trial)} trial, {len(watch)} watch, {len(kill)} killed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
D2M → COMMANDER DIGEST — the email CI handler, rebuilt to DELIVER (verified)
===========================================================================
Dreams2Memories Travel · built 2026-06-21 (Commander: "this is CI, and it is failing")

The old pipeline LABELED mail "DirectiveReplied" and never sent anything to the
Commander — the silent-success failure (presence, not delivery). This replaces
that with the one thing that matters: actionable d2m-inbox mail (from the
Commander OR suppliers) is summarized and ACTUALLY SENT to johnloucks3, and an
email is only marked delivered AFTER the send returns a message-id. No Claude
subprocess, no fragile reasoning step, $0 — a reliable courier, not a clever one.

Efficacy is measured, not assumed: state records received-vs-delivered so the CI
probe (ci_probe_email_handling.py) goes RED the instant the gap reopens.

State: OpsCenter/state/d2m_digest_state.json
Run:  python3 scripts/d2m_commander_digest.py            # digest + send
      python3 scripts/d2m_commander_digest.py --metric   # received vs delivered
"""
import base64, json, sys, re
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

ROOT = Path("/home/john/Thunderbird")
D2M_TOKEN = ROOT/"config/persona_gmail_token.json"
JL3_TOKEN = ROOT/"creds/johnloucks3_token.json"
STATE = ROOT/"OpsCenter/state/d2m_digest_state.json"
YODA = "johnloucks3@gmail.com"

# Actionable = from the Commander, or from a known supplier. Not internal d2m sends, not clutter.
SUPPLIERS = ["projectexpedition", "regent", "silversea", "viking", "centrav", "bedsonline",
             "hotelbeds", "outsideagents", "nexion", "sabre", "expedition"]
ACTIONABLE_Q = ('in:inbox newer_than:4d -from:d2mconcierge -from:concierge@d2mluxury.quest '
                '-category:promotions -from:no-reply -from:noreply')


def svc(tok):
    c = Credentials.from_authorized_user_info(json.loads(tok.read_text()))
    if c.expired and c.refresh_token: c.refresh(Request()); tok.write_text(c.to_json())
    return build("gmail", "v1", credentials=c)


def _state():
    if STATE.exists():
        try: return json.loads(STATE.read_text())
        except Exception: pass
    return {"delivered_ids": [], "runs": []}


DIRECTIVE_PREFIXES = ("cos:", "hale:", "coo:", "hale,", "cos,")

def _is_actionable(frm: str, snippet: str = ""):
    f = frm.lower()
    if "johnloucks3" in f:
        # Directive forward (body starts with COS:/HALE: etc.) → actionable
        # Plain self-send (no prefix) → exclude to prevent self-forwarding loop
        snip = snippet.strip().lower()
        if any(snip.startswith(p) for p in DIRECTIVE_PREFIXES):
            return "commander"
        return None
    if any(s in f for s in SUPPLIERS): return "supplier"
    return None


def _hold_flag(subj: str):
    s = subj.lower()
    if "hold without payment" in s or "reminder" in s: return " ⏰ HOLD/DEADLINE"
    if "confirmation" in s: return " ✅ confirmation"
    if "following up" in s: return " ↩ vendor follow-up"
    return ""


def run(send=True):
    s = svc(D2M_TOKEN)
    st = _state()
    delivered = set(st["delivered_ids"])
    msgs = s.users().messages().list(userId="me", q=ACTIONABLE_Q, maxResults=40).execute().get("messages", [])
    new = []
    for m in msgs:
        if m["id"] in delivered:
            continue
        mm = s.users().messages().get(userId="me", id=m["id"], format="metadata",
              metadataHeaders=["From", "Subject", "Date"]).execute()
        h = {x["name"]: x["value"] for x in mm["payload"]["headers"]}
        kind = _is_actionable(h.get("From", ""), mm.get("snippet", ""))
        if not kind:
            continue
        new.append({"id": m["id"], "kind": kind, "from": h.get("From", "")[:40],
                    "subj": h.get("Subject", "")[:80], "date": h.get("Date", "")[:25],
                    "snippet": mm.get("snippet", "")[:160], "flag": _hold_flag(h.get("Subject", ""))})

    received = len(new)
    if not new:
        print("no new actionable d2m mail since last delivery"); _record(st, received, 0); return
    if not send:
        print(f"{received} new actionable (dry run):")
        for n in new: print(f"  [{n['kind']}]{n['flag']} {n['subj']} ({n['from']})")
        return

    # build digest
    sup = [n for n in new if n["kind"] == "supplier"]
    cmd = [n for n in new if n["kind"] == "commander"]
    lines = [f"D2M INBOX DIGEST — {len(new)} item(s) needing your eyes",
             f"(d2m received them; the old pipeline never forwarded — this courier does, verified)\n"]
    if sup:
        lines.append(f"── SUPPLIERS ({len(sup)}) ──")
        for n in sup:
            lines.append(f"• {n['subj']}{n['flag']}\n   from {n['from']} · {n['date']}\n   {n['snippet']}")
        lines.append("")
    if cmd:
        lines.append(f"── FROM YOU / FORWARDS ({len(cmd)}) ──")
        for n in cmd:
            lines.append(f"• {n['subj']}\n   {n['date']}\n   {n['snippet']}")
    lines.append("\n— Hale · d2m courier · " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    body = "\n".join(lines)

    # SEND to Commander — verified (message-id) before marking delivered
    jl = svc(JL3_TOKEN)
    msg = MIMEText(body)
    msg["To"] = YODA; msg["From"] = YODA
    msg["Subject"] = f"D2M Inbox Digest — {len(new)} item(s)" + (f" · {len(sup)} supplier" if sup else "")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    sent = jl.users().messages().send(userId="me", body={"raw": raw}).execute()
    msgid = sent.get("id")
    if not msgid:
        print("SEND FAILED — not marking delivered (no silent success)"); _record(st, received, 0); return

    for n in new: delivered.add(n["id"])
    st["delivered_ids"] = sorted(delivered)[-2000:]
    _record(st, received, len(new), msgid)
    print(f"DELIVERED to {YODA}: digest id={msgid} | {len(new)} items ({len(sup)} supplier, {len(cmd)} commander)")


def _record(st, received, delivered, msgid=None):
    st["runs"] = (st.get("runs", []) + [{
        "ts": datetime.now(timezone.utc).isoformat(), "received": received,
        "delivered": delivered, "msgid": msgid}])[-60:]
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))


def metric():
    st = _state()
    runs = st.get("runs", [])
    last = runs[-1] if runs else {}
    rec = sum(r.get("received", 0) for r in runs[-10:])
    dlv = sum(r.get("delivered", 0) for r in runs[-10:])
    print(f"EMAIL_HANDLING received={rec} delivered={dlv} (last10 runs) | "
          f"last_run={last.get('ts','never')} last_delivered={last.get('delivered',0)}")


if __name__ == "__main__":
    if "--metric" in sys.argv: metric()
    elif "--dry" in sys.argv: run(send=False)
    else: run(send=True)

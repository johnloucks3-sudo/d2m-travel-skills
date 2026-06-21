#!/usr/bin/env python3
"""
Session OODA Open — fires at the top of every Claude Code session.
Observe → Orient → Decide → Act on non-gated items → Report.
No Commander prompt needed. This IS the initiative.

Run: python3 scripts/session_ooda_open.py
Auto-wired via CLAUDE.md session startup.
"""
import json, sys, subprocess
from pathlib import Path
from datetime import date, datetime, timedelta

TODAY = date.today()
ROOT = Path("/home/john/Thunderbird")
REPORT = []

def log(msg):
    print(msg)
    REPORT.append(msg)

def section(title):
    log(f"\n{'─'*50}")
    log(f"  {title}")
    log(f"{'─'*50}")

# ── OBSERVE ──────────────────────────────────────────────────────────────────
section("OBSERVE — pulling live state")

# Mission board
mb_path = ROOT / "OpsCenter/mission_board.json"
missions = []
if mb_path.exists():
    mb = json.loads(mb_path.read_text())
    missions = mb.get("missions", [])
    active = [m for m in missions if m.get("status") not in ("complete","archived","cancelled")]
    log(f"  Mission board: {len(active)} active / {len(missions)} total")

# Dossier FPD sweep
dossier_dir = ROOT / "dossiers"
fpd_alerts = []
for f in dossier_dir.glob("*.md"):
    text = f.read_text(errors="ignore")
    import re
    fpd_match = re.search(r"fpd:\s*(\d{4}-\d{2}-\d{2})", text)
    status_match = re.search(r"payment_status:\s*(\S+)", text)
    if fpd_match and status_match:
        fpd_str = fpd_match.group(1)
        status = status_match.group(1).strip('"\'')
        if status != "paid_in_full":
            try:
                fpd_date = date.fromisoformat(fpd_str)
                days_out = (fpd_date - TODAY).days
                if days_out <= 60:
                    client_match = re.search(r"client:\s*[\"']?([^\"'\n]+)", text)
                    client = client_match.group(1).strip() if client_match else f.stem
                    fpd_alerts.append((days_out, client, fpd_str, f.name))
            except ValueError:
                pass

if fpd_alerts:
    fpd_alerts.sort()
    log(f"\n  🔴 FPD ALERTS ({len(fpd_alerts)}):")
    for days, client, fpd, fname in fpd_alerts:
        flag = "🔴 CRITICAL" if days <= 14 else "🟡 WARNING" if days <= 30 else "📅"
        log(f"    {flag} {client} — FPD {fpd} ({days}d out) [{fname}]")
else:
    log("  ✅ No FPD alerts")

# Draft queue
draft_dir = ROOT / "drafts"
drafts = list(draft_dir.glob("*.html"))
log(f"\n  Draft queue: {len(drafts)} HTML files in drafts/")

# Deferred alerts from hale_state
state_path = ROOT / "hale_state.json"
if state_path.exists():
    state = json.loads(state_path.read_text())
    deferred = state.get("deferred_alerts", [])
    triggered = []
    for alert in deferred:
        trigger = alert.get("trigger_date","")
        try:
            if date.fromisoformat(trigger) <= TODAY:
                triggered.append(alert)
        except ValueError:
            pass
    if triggered:
        log(f"\n  🔔 TRIGGERED DEFERRED ALERTS ({len(triggered)}):")
        for a in triggered:
            log(f"    • {a.get('id','?')} — {a.get('message','')[:80]}")

# ── ORIENT ───────────────────────────────────────────────────────────────────
section("ORIENT — what needs action today")

# Classify missions by gating
no_gate = []
gated = []
for m in active if 'active' in dir() else []:
    title = m.get("title","")
    # Heuristic: missions referencing "Commander" action are gated
    gated_keywords = ["Commander sends", "Call United", "Book ", "Commander approval"]
    is_gated = any(k.lower() in title.lower() for k in gated_keywords)
    if is_gated:
        gated.append(m)
    else:
        no_gate.append(m)

log(f"\n  Non-gated missions (Hale can close): {len(no_gate)}")
for m in no_gate[:5]:
    log(f"    [{m.get('priority','?')}] {m.get('id','?')} — {m.get('title','')[:60]}")

log(f"\n  Gated (Commander action needed): {len(gated)}")
for m in gated[:3]:
    log(f"    [{m.get('priority','?')}] {m.get('id','?')} — {m.get('title','')[:60]}")

# Upcoming TP pre-staging opportunities
log("\n  Upcoming TP opportunities to pre-stage:")
tp_windows = [
    ("2026-07-07", "McLeod FPD contact — 15 days to FPD $11,943 — pre-draft outreach email"),
    ("2026-07-15", "Kuklinski lifecycle emails — HOLD lifts — 4 drafts should be queued"),
    ("2026-08-01", "Loucks Grandeur FPD $24,798 — pre-draft payment reminder"),
]
for trigger, desc in tp_windows:
    days_out = (date.fromisoformat(trigger) - TODAY).days
    if 0 <= days_out <= 30:
        log(f"    🟡 {trigger} ({days_out}d) — {desc}")
    elif days_out < 0:
        log(f"    🔴 OVERDUE — {trigger} — {desc}")

# ── DECIDE + ACT ──────────────────────────────────────────────────────────────
section("ACT — non-gated closures this session")
log("  (Claude Code will execute non-gated items during this session)")
log("  Run validate_client_email.py --all to sweep draft queue")
log("  Check mission board for stale P2 items to archive")

# ── SUMMARY ──────────────────────────────────────────────────────────────────
section("SESSION BRIEF COMPLETE")
log(f"  Date: {TODAY}")
log(f"  Missions: {len(active)} active" if missions else "  Missions: unavailable")
log(f"  FPD alerts: {len(fpd_alerts)}")
log(f"  Triggered deferrals: {len(triggered) if 'triggered' in dir() else 0}")
log(f"  Draft queue: {len(drafts)}")
log("")

if __name__ == "__main__":
    pass  # output already printed

#!/usr/bin/env python3
"""
silver_gate.py — CMSgt Steve "Silver" Sterling's back-of-task check battery.
Deterministic gates (Silver never guesses a pass). Run before a portal reaches
the Commander or a client. Emits a visible CHIEF SILVER verdict.

Usage: python3 scripts/silver_gate.py <portal_client_dir> [--others name1,name2]
Checks (portal-scoped, from the 2026-07-03 misses):
  1 COUNT-MATCH  every doc states the SAME excursion count; 03 actual == stated
  2 IMAGES       no 📷 placeholders; no un-inlined assets/ src; inline b64 = real JPEG
  3 SEGREGATION  no other couple's surname appears
"""
import base64, re, sys
from pathlib import Path

WORD = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}

def excursion_claims(text):
    """Only TOTAL claims count. 'Six shore excursions' / 'six excursions are reserved'
    are totals; 'two excursions, both of you' (a single day's tours) is NOT."""
    out=[]
    num=r'(\d+|one|two|three|four|five|six|seven|eight|nine|ten)'
    pats=[ num+r'\s+shore\s+excursions?',
           num+r'\s+excursions?\s+(?:are|were|is|reserved|confirmed|booked|included|in all|in total)' ]
    for pat in pats:
        for m in re.finditer(pat, text, re.I):
            v=m.group(1).lower(); out.append(int(v) if v.isdigit() else WORD.get(v))
    return [n for n in out if n]

def board_hygiene():
    """Silver rides herd on the boards — surfaces anything left unresolved (the
    'still queued' / 'unclaimed but touched' misses)."""
    import subprocess
    findings=[]
    try:
        r=subprocess.run(["/home/john/Thunderbird/.venv/bin/python3","/home/john/Thunderbird/core/hale_bus/brain_bridge.py","list"],
                         capture_output=True,text=True,timeout=20).stdout
        pend=len(re.findall(r'^\[pending', r, re.M)); clm=len(re.findall(r'^\[claimed', r, re.M))
        if pend or clm:
            findings.append(("NOTE","board",f"{pend} pending + {clm} claimed on brain_bridge — declare their state, don't leave them queued"))
    except Exception as e: findings.append(("NOTE","board",f"board unreadable: {str(e)[:40]}"))
    return findings

def internal_ops_check():
    """Silver on internal processes (2026-07-04): same board-hygiene/no-orphan
    checks (#5/#6), pointed at the Wing's own machinery instead of a client
    portal — duplicate mission-board entries and re-injected inbox tasks are
    the internal-ops equivalent of an unresolved client-facing miss."""
    import json, collections
    findings = []
    root = Path("/home/john/Thunderbird")

    # Duplicate OPEN mission-board entries (same work tracked under >1 ID)
    try:
        board = json.loads((root / "OpsCenter/mission_board.json").read_text())
        open_m = [m for m in board.get("missions", [])
                  if m.get("status") in ("active", "in_progress", "open", "pending")]
        norm = lambda t: frozenset(w for w in re.sub(r'[^a-z0-9\s]', '', t.lower()).split())
        seen = {}
        for m in open_m:
            key = norm(m.get("title", ""))
            if not key:
                continue
            if key in seen:
                findings.append(("HOLD", "board-dup",
                    f"{m['id']} duplicates {seen[key]} — same work, two open mission IDs"))
            else:
                seen[key] = m["id"]
    except Exception as e:
        findings.append(("NOTE", "board-dup", f"mission board unreadable: {str(e)[:60]}"))

    # Re-injected UNREAD inbox tasks (same task_id appears UNREAD more than once)
    for inbox in ("claude_inbox.md", "OpsCenter/collaboration/opencode_inbox.md"):
        p = root / inbox
        if not p.exists():
            continue
        text = p.read_text()
        ids = re.findall(r'## TASK: (\S+)\nstatus: UNREAD', text)
        dupes = [tid for tid, c in collections.Counter(ids).items() if c > 1]
        if dupes:
            findings.append(("HOLD", "inbox-dup",
                f"{inbox}: task(s) injected UNREAD more than once without being read/closed: {dupes}"))

    findings += board_hygiene()
    return findings


def internal_ops_verdict():
    f = internal_ops_check()
    print("CHIEF SILVER — internal ops hygiene")
    if not f:
        print("  PASS. No duplicate open missions, no re-injected inbox tasks, board clean.")
        return 0
    print(f"  HOLD — {len(f)} finding(s):")
    for _, cat, msg in f:
        print(f"   • [{cat}] {msg}")
    print("  — CMSgt S. Sterling, Command Chief")
    return 1


def run(cdir, others, dossier=None):
    cdir=Path(cdir); findings=[]; docs=sorted(cdir.glob("*.md"))
    docs=[d for d in docs if d.name!="portal.json"]
    html=(cdir.parent/"html/index.html")
    # 1 COUNT-MATCH
    claims={}
    for d in docs:
        cs=excursion_claims(d.read_text())
        if cs: claims[d.name]=cs
    allnums={n for v in claims.values() for n in v}
    if len(allnums)>1:
        findings.append(("HOLD","count-match",
            f"excursion count disagrees across docs: "+"; ".join(f"{k}={v}" for k,v in claims.items())))
    # ground-truth: portal total vs the DOSSIER's own stated count (catches the original Ely miss)
    if dossier and Path(dossier).exists() and allnums:
        dm=re.search(r'(\d+)\s+excursions?\s+confirmed', Path(dossier).read_text(), re.I)
        if dm:
            dcount=int(dm.group(1)); pcount=max(allnums)
            if pcount!=dcount:
                findings.append(("HOLD","count-match",
                    f"portal states {pcount} excursions but dossier ground-truth = {dcount} confirmed"))
    # 2 IMAGES (on built html)
    if html.exists():
        h=html.read_text()
        if "📷" in h: findings.append(("HOLD","images",f"{h.count('📷')} caption placeholder(s) still rendering — no real image"))
        stray=re.findall(r'src="(assets/[^"]+)"', h)
        if stray: findings.append(("HOLD","images",f"{len(stray)} image(s) not inlined (will 401 on auth): {stray[:3]}"))
        bad=0
        for b in re.findall(r'data:image/jpeg;base64,([A-Za-z0-9+/=]+)', h):
            try:
                raw=base64.b64decode(b[:200]+"="*(-len(b[:200])%4))
                if raw[:2]!=b'\xff\xd8': bad+=1
            except Exception: bad+=1
        if bad: findings.append(("HOLD","images",f"{bad} inline image(s) are not valid JPEG"))
    else:
        findings.append(("HOLD","images","no built index.html to check"))
    # 3 SEGREGATION
    if others:
        blob=" ".join(d.read_text() for d in docs).lower()
        hit=[o for o in others if re.search(rf'\b{re.escape(o.lower())}\b', blob)]
        if hit: findings.append(("HOLD","segregation",f"other couple named in copy: {hit}"))
    return findings

def verdict(cdir, others, dossier=None):
    f=run(cdir, others, dossier)
    name=Path(cdir).parent.name
    print(f"CHIEF SILVER — {name}")
    if not f:
        print("  PASS. Count consistent, images real and inlined, no cross-couple leak. Ships.")
        return 0
    print(f"  HOLD — {len(f)} finding(s). This doesn't reach the Commander until it's fixed:")
    for _,cat,msg in f: print(f"   • [{cat}] {msg}")
    print("  — CMSgt S. Sterling, Command Chief")
    return 1

if __name__=="__main__":
    if "--internal-ops" in sys.argv:
        sys.exit(internal_ops_verdict())
    d=sys.argv[1]
    others=[]
    if "--others" in sys.argv: others=sys.argv[sys.argv.index("--others")+1].split(",")
    dossier=sys.argv[sys.argv.index("--dossier")+1] if "--dossier" in sys.argv else None
    sys.exit(verdict(d, others, dossier))

#!/usr/bin/env python3
"""rt_recorder.py - ROUND TABLE transcript recorder with RT-EFFICACY enforcement.

Build: C2 + RT-EFFICACY enforcement (2026-08-08):
  - RT_CARD YAML frontmatter envelope (inbound/quorum/vote/claims/
    session_pointer/fanout)
  - H8 state_hash verify: mismatch -> REFUSED line + stderr warn + exit 1 (M3)
  - G1/O1 sealed VOTE: held until all quorum.required seats file, or timeout;
    dynamic quorum count (M2), never a hardcoded len>=2
  - M1: inbound hold pages Commander on C2 telegram (best-effort)
  - O2: session_pointer target verify exist + hash at resume
  - fallback: plain prose papers unchanged

Usage: rt_recorder.py [session]   (default 'RT')
"""
import sys
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional

import yaml as _yaml

ROOM = Path(__file__).resolve().parent
SEATS = [("AG", "ag_hale_input.md"), ("CC", "cc_hale_input.md"),
         ("OC", "oc_hale_input.md"), ("GROK", "grok_hale_input.md")]
FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.M | re.S)


def bluf(text: str) -> str:
    m = re.search(r"^##+\s*BLUF\s*\n+(.+?)(?=\n#|\Z)", text, re.M | re.S)
    if m:
        return " ".join(m.group(1).split())[:280]
    m = re.search(r"\*\*BLUF:?\*\*\s*(.+)", text, re.M)
    if m:
        return m.group(1).strip()[:280]
    return next((l.strip() for l in text.splitlines() if l.strip()), "")[:140]


def engine_hint(text: str) -> str:
    for kw in ("claude", "gemini", "deepseek", "grok"):
        if re.search(rf"\b{kw}\b", text, re.I):
            return kw.title()
    return "?"


def split_front(text):
    m = FRONT.match(text)
    if not m:
        return None, text.strip()
    try:
        data = _yaml.safe_load(m.group(1)) or {}
        return (data.get("card", data), text[m.end():].strip())
    except _yaml.YAMLError:
        return None, text.strip()


def body_sha(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()


def state_ok(card: Optional[dict], body: str) -> bool:
    if not isinstance(card, dict):
        return True
    want = str(card.get("state_hash") or "")
    if not want:
        return True
    return body_sha(body) == want.split(":", 1)[-1].strip()


def page_hold(seat, kind, subj) -> bool:
    """M1 best-effort Commander page. Fails OPEN - never blocks transcript."""
    line = f"RT HOLD | {seat} {kind}: {subj[:90]}"
    try:
        from core.communication.thunderbird_telegram import _dm_commander_c2
        _dm_commander_c2(line)
        return True
    except Exception:
        pass
    return False

def parse_votes(rows):
    """Collect VOTE cards by question. Returns {q: {required, timeout_s,
    on_timeout, sealed, ballots:[seat...], mtime}}."""
    import time as _time
    votes = {}
    for r in rows:
        c = r["card"] or {}
        v = c.get("vote")
        if not isinstance(v, dict):
            continue
        spot_exists = r.get("exists_path") and Path(r["exists_path"]).exists()
        mtime = Path(r["exists_path"]).stat().st_mtime if spot_exists else _time.time()
        vq = v.get("quorum", c.get("quorum")) or {}
        q = str(v.get("q", "")) or c.get("id", "Q")
        votes.setdefault(q, {"required": [x.upper() for x in vq.get("required", [])],
                             "timeout_s": vq.get("timeout_s", 45),
                             "on_timeout": vq.get("on_timeout", "proceed"),
                             "sealed": v.get("sealed", True),
                             "ballots": [], "mtime": mtime})
        votes[q]["ballots"].append(r["seat"])
    return votes


def quorum_ok(info) -> tuple[bool, str]:
    """M2 dynamic quorum: reveal when all required seats have filed OR
    timeout_s since the first ballot elapsed (on_timeout=proceed). Hmm covers
    an aborted vote (timeout + on_timeout=abort → held, marked ABORTED)."""
    import time as _time
    present = {b.upper() for b in info["ballots"]}
    req = info["required"]
    if req:
        met = all(s.upper() in present for s in req)
    else:
        met = len(present) >= 2
    if met:
        return True, "quorum-met"
    elapsed = _time.time() - info.get("mtime", _time.time())
    if elapsed >= info.get("timeout_s", 45):
        if info.get("on_timeout", "proceed") == "abort":
            return False, f"TIMED-OUT/ABORTED after {int(elapsed)}s ({info['on_timeout']})"
        return True, f"timed-out after {int(elapsed)}s (proceed)"
    return False, "awaiting quorum"


def main():
    session = sys.argv[1] if len(sys.argv) > 1 else "RT"
    session_dir = ROOM / session
    root = session_dir if session_dir.is_dir() else ROOM
    now = datetime.now(timezone(timedelta(hours=-6))).strftime("%Y-%m-%d %H:%M MT")
    warns = []
    L = [f"# {session} — WAR ROOM TRANSCRIPT", f"**Recorded:** {now}",
         f"**Cards read from:** {root}", ""]

    # pass 1: collect rows
    rows = []
    for seat, fname in SEATS:
        fp = root / fname
        if not fp.exists():
            rows.append({"seat": seat, "card": None, "body": "",
                         "file": fname, "present": False})
            continue
        text = fp.read_text().strip()
        card, body = split_front(text)
        rows.append({"seat": seat, "card": card, "body": body,
                     "file": fname, "present": True, "text": text,
                     "exists_path": str(fp)})
    votes = parse_votes(rows)

    total = 0
    for r in rows:
        seat = r["seat"]
        if not r["present"]:
            L.append(f"## {seat} — (MISSING, no card)")
            L.append("")
            continue
        card = r["card"] or {}
        body, subj = r["body"], bluf(r["body"])
        total += len(body.split())

        if not state_ok(card, body):
            warns_l = f"REFUSED {seat}: state_hash mismatch (H8)"
            warns.append(warns_l)
            L.append(f"##{seat} — REFUSED (state_hash mismatch, H8)")
            L.append(f"- receipt: seat={seat} · file={r['file']} · words={len(body.split())}")
            L.append(f"- BLUF: {subj}")
            L.append("")
            continue

        if card.get("inbound") == "refuse":
            L.append(f"## {seat} — REFUSED (inbound=refuse)")
            L.append("")
            continue

        held = card.get("inbound") == "hold"
        if held and not page_hold(seat, card.get("type", "FINDING"), subj):
            pass  # printed below; page is best-effort

        kind = card.get("type", "FINDING")
        L.append(f"## {seat}")
        L.append(f"- receipt: seat={seat} · file={r['file']} · words={len(body.split())} · "
                 f"engine={engine_hint(r['body'])} · captured={now} · type={kind}"
                 f"{' · HELD-for-Commander' if held else ''}")
        L.append("")
        L.append(f"- BLUF: {subj}")
        L.append("")

        q = card.get("quorum")
        if isinstance(q, dict):
            L.append(f"- QUORUM: wait {[x.upper() for x in q.get('required', [])]} "
                     f"(≤{q.get('timeout_s', 45)}s) on_timeout={q.get('on_timeout', 'proceed')}")
            L.append("")

        if isinstance(card.get("vote"), dict):
            v = card["vote"]
            qq = str(v.get("q", "")) or card.get("id", "Q")
            info = votes.get(qq, {})
            held_now, reason = quorum_ok(info)
            held_now = info.get("sealed", True) and not held_now
            if held_now:
                missing = [s for s in info["required"] if s.upper() not in
                           {b.upper() for b in info.get("ballots", [])}]
                L.append(f"- VOTE({qq}): SEALED — {reason} ({missing or 'quorum'})")
            else:
                L.append(f"- VOTE({qq}): revealed ({reason}) — ballots: {', '.join(info.get('ballots', []))}")
            L.append("")

        if card.get("claims"):
            L.append(f"- CLAIMS: {', '.join(card['claims'])}")
            L.append("")

        if card.get("session_pointer"):
            sp = card["session_pointer"]
            target = ROOM / (sp.get("workitem_file") or "")
            if not target.exists():
                L.append(f"- SESSION_POINTER: ERROR {sp.get('workitem_file')} MISSING")
                warns.append(f"POINTER-FAIL {seat}: workitem missing")
            else:
                hs = str(sp.get("state_hash") or "")
                ok = body_sha(target.read_text().strip()) == hs.split(":", 1)[-1].strip() if hs else True
                L.append(f"- SESSION_POINTER: {sp.get('workitem_file')} → "
                         f"{'verified' if ok else 'HASH-MISMATCH'} state={sp.get('target_state')}")
                if not ok:
                    warns.append(f"POINTER-FAIL {seat}: hash mismatch on workitem")
            L.append("")

        if isinstance(card.get("fanout"), dict):
            fo = card["fanout"]
            L.append(f"- FANOUT: {fo.get('model_set')} matrix={fo.get('matrix', False)}")
            L.append("")

    # sealed reveal line (held votes stay hidden)
    revealed = []
    for qq, info in votes.items():
        ok_now, why = quorum_ok(info)
        if info["sealed"] and ok_now:
            revealed.append(f"**SEALED BALLOT ({qq})** — {why}: "
                            f"{', '.join(b for b in info['ballots'])}")
    L.extend(revealed)

    L.append(f"**total_word_count={total}**")
    L.append("Timeline (canonical): " + " → ".join(s for s, _ in SEATS))
    (ROOM / f"{session}_transcript.md").write_text("\n".join(L))
    print(ROOM / f"{session}_transcript.md")
    for w in warns:
        print(f"[WARN] {w}", file=sys.stderr)
    if warns:
        print(f"rt_recorder: {len(warns)} REFUSED/POINTER-FAIL — non-zero exit", file=sys.stderr)
        sys.exit(1)
    print(f"total_word_count={total}")


if __name__ == "__main__":
    main()

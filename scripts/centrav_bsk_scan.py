#!/usr/bin/env python3
"""
centrav_bsk_scan.py — Centrav B2B scan RIDING the live authenticated bsk tab.

WHY: Centrav's reCAPTCHA + email-OTP gate blocks fresh headless login, and its
cookies are v11/app-bound (no clean export). The ONLY reliable path is to ride
a human-authenticated browser tab via bsk (browser-skill CLI). The Commander
keeps the tab pinned; this driver navigates it to each fare and reads prices.

Used by: daily_airfare_scan.py --source centrav (or centrav_bsk) for the mover
routes, and by the Skybird-vs-Centrav 4-hour head-to-head.

Usage:
  python3 scripts/centrav_bsk_scan.py --from DEN --to VCE --date 2027-05-01 \
      --cabin Business --adults 2 [--return 2027-05-30] [--session lcbs]
  python3 scripts/centrav_bsk_scan.py --multi "DEN|2027-05-01|VCE;ATH|2027-05-30|DEN" ...

Exit codes: 0 = fares returned, 1 = no fares/no session, 2 = session dead/login wall.
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

BSK = "/home/john/.local/bin/bsk"
DEFAULT_SESSION = ""  # empty = auto-create a fresh session per run (sessions are ephemeral; auth rides the BROWSER)


def scan_fetch(session: str, frm: str, to: str, date: str,
               cabin: str = "Business", adults: int = 2, ret: str = "") -> dict:
    """Centrav fare read — ride an INITIALIZED tab, complete native fill, submit.

    Ground-truth contract (verified 2026-08-06, Grok + OC):
    - The search form's real field names have NO 'Fare' prefix:
      cabinClass, tripType, flyingFrom, flyingTo, departureDate, returnDate,
      fare_numDestinations + hidden: persist, autostart, ShowStandardFareRouting,
      AdvancedState.
    - Must run on an ALREADY-INITIALIZED tab (fresh sessions hit 'error report id').
    - fill via native setters + form.submit() (full-page POST → native script exec
      → fares render). Read body.innerText for $ amounts.
    """
    # 1) ensure initialized: the SPA form only renders after JS init. If no
    # form inputs exist, FAIL SOFT — never reload (a reload returns the shell).
    try:
        probe = run_bsk("evaluate",
                        "document.querySelectorAll('form input,form select').length",
                        "--session", session, timeout=15).strip()
        if probe == "0":
            return {"status": "not_initialized",
                    "error": "tab has no rendered form — use an initialized Centrav tab"}
    except Exception as e:
        return {"status": "error", "error": f"probe: {e}"}

    # 2) native-setter fill with VERIFIED field names
    trip = "One Way" if not ret else "Round Trip"
    fields = {
        "cabinClass": cabin, "tripType": trip,
        "flyingFrom": frm, "flyingTo": to,
        "departureDate": _to_mdy(date),
        "returnDate": _to_mdy(ret) if ret else "",
        "fare_numDestinations": "1",
        "persist": "1", "autostart": "1", "ShowStandardFareRouting": "1",
    }
    setter_js = ("(()=>{var s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
                 "var map=" + json.dumps(fields) + ";"
                 "var filled=[];"
                 "for(var name in map){var el=document.querySelector('[name='+name+']');"
                 "if(el){s.call(el,map[name]);el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));filled.push(name);}}"
                 "var as=document.querySelector('select[name=adults]');"
                 "if(as){as.value='" + str(adults) + "';as.dispatchEvent(new Event('change',{bubbles:true}));}"
                 "return 'filled:'+filled.join(',')})()")
    filled = run_bsk("evaluate", setter_js, "--session", session, timeout=20).strip()
    if "filled:0" in filled or filled == "0":
        return {"status": "no_form", "detail": filled}
    time.sleep(1)

    # 3) full-page POST submit (native script exec → fares render)
    run_bsk("evaluate",
            "(()=>{var f=document.querySelector('form');if(!f)return 'no-form';f.action='https://www.centrav.com/fares';f.method='POST';HTMLFormElement.prototype.submit.call(f);return 'submitted'})()",
            "--session", session, timeout=20)
    time.sleep(10)

    # 4) read rendered fares
    try:
        body = run_bsk("evaluate",
                       "(()=>{var t=document.body.innerText;var px=(t.match(/\\$[\\s]?[0-9][0-9,]+/g)||[]).map(function(x){return parseFloat(x.replace(/[^0-9.]/g,''))}).filter(function(v){return v>=50});return JSON.stringify({prices:px.sort(function(a,b){return a-b}).slice(0,15),err:t.indexOf('error report')>-1,has_500:t.indexOf('500 fares')>-1,url:location.href})})()",
                       "--session", session, timeout=20).strip()
        data = json.loads(body)
    except Exception as e:
        return {"status": "error", "error": f"read: {e}"}
    if data.get("err"):
        return {"status": "error_page", "url": data.get("url")}
    if not data.get("prices"):
        return {"status": "no_fares", "url": data.get("url"), "has_500": data.get("has_500")}
    return {"status": "ok", "best_price_pp": data["prices"][0],
            "price_list": data["prices"], "has_500": data.get("has_500")}


def run_bsk(*args, timeout=60) -> str:
    r = subprocess.run([BSK, *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"bsk {' '.join(args)} failed: {r.stderr.strip()[:200]}")
    return r.stdout


def snapshot(session: str) -> str:
    return run_bsk("snapshot", "--session", session)


def find_ref(snap: str, text: str) -> str | None:
    for line in snap.splitlines():
        if text.lower() in line.lower():
            m = re.search(r"@e\d+", line)
            if m:
                return m.group(0)
    return None


def dead_check(session: str) -> bool:
    """True if we got bounced to the login wall."""
    snap = snapshot(session)
    if "Login | Centrav" in snap or "Login to your Account" in snap:
        return True
    url = run_bsk("evaluate", "window.location.href", "--session", session).strip().lower()
    return "login" in url or "trust" in url


def _commit_airport(session: str, ref: str) -> None:
    """Type + Enter to commit an airport autocomplete chip."""
    run_bsk("press", "Enter", "--ref", ref, "--session", session, timeout=45)


def _to_mdy(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{m}/{d}/{y}"


def _read_fares(snap: str) -> list[dict]:
    """Parse fare cards from the results snapshot (Consolidator/NDC/Published)."""
    fares = []
    # prices appear as "$8,104" beside buttons; capture all $ amounts
    prices = re.findall(r"\$\s?([\d,]+(?:\.\d{2})?)", snap)
    # pairs: {airline_logo button} {price}. We can't reliably get airline names
    # from aria here, so return price list + the top-line "N fares from $X".
    best = None
    for p in prices:
        v = float(p.replace(",", ""))
        if best is None or v < best:
            best = v
    return [{"price_pp": best, "raw": prices[:20]}] if best else []


def scan_route(session: str, frm: str, to: str, date: str,
               cabin: str = "Business", adults: int = 2, ret: str = "") -> dict:
    if dead_check(session):
        return {"status": "dead", "error": "login wall"}

    # Go to the search form — auth redirects to results; click "Change Search" if needed
    try:
        run_bsk("navigate", "--session", session, "https://www.centrav.com/fares", timeout=45)
        time.sleep(3)
        snap = snapshot(session)
        cs = find_ref(snap, "Change Search")
        if cs:
            run_bsk("click", "--session", session, cs, timeout=30)
            time.sleep(2)
    except Exception as e:
        return {"status": "error", "error": str(e)[:120]}

    snap = snapshot(session)
    # Choose One Way / Round Trip
    mode = "One Way" if not ret else "Round Trip"
    mref = find_ref(snap, mode)
    if mref:
        run_bsk("click", "--session", session, mref, timeout=30)
        time.sleep(1)

    snap = snapshot(session)
    ff = find_ref(snap, "Flying From")
    ft = find_ref(snap, "Flying To")
    dd = find_ref(snap, "Departure Date")
    if not ff or not ft or not dd:
        return {"status": "error", "error": "search form not found"}

    run_bsk("fill", ff, "--value", frm, "--session", session, timeout=30)
    _commit_airport(session, ff)
    time.sleep(1)
    try:
        run_bsk("fill", ft, "--value", to, "--session", session, timeout=30)
    except RuntimeError:
        time.sleep(2)  # autocomplete re-render — retry once
        run_bsk("fill", ft, "--value", to, "--session", session, timeout=30)
    _commit_airport(session, ft)
    time.sleep(1)
    run_bsk("fill", dd, "--value", _to_mdy(date), "--session", session, timeout=30)

    if ret:
        snap = snapshot(session)
        rref = find_ref(snap, "Return Date")
        if rref:
            run_bsk("fill", rref, "--value", _to_mdy(ret), "--session", session, timeout=30)

    # Cabin
    snap = snapshot(session)
    cref = find_ref(snap, cabin)
    if cref:
        run_bsk("click", "--session", session, cref, timeout=30)
        time.sleep(1)

    # Adults
    snap = snapshot(session)
    aref = find_ref(snap, "Number of Adults")
    if aref:
        run_bsk("select", aref, "--value", str(adults), "--session", session, timeout=30)

    # Submit
    snap = snapshot(session)
    sref = find_ref(snap, "SEARCH FOR FARES")
    if sref:
        run_bsk("click", "--session", session, sref, timeout=45)
        time.sleep(6)

    snap = snapshot(session)
    fares = _read_fares(snap)
    if not fares:
        return {"status": "no_fares", "raw_snap": snap[:500]}
    return {"status": "ok", "best_price_pp": fares[0]["price_pp"], "fares": fares}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to", dest="to")
    ap.add_argument("--date", dest="date")
    ap.add_argument("--return", dest="ret", default="")
    ap.add_argument("--cabin", default="Business")
    ap.add_argument("--adults", type=int, default=2)
    ap.add_argument("--multi", default="", help="legs: ORIG|DATE|DEST;ORIG2|DATE2|DEST2")
    ap.add_argument("--session", default=DEFAULT_SESSION)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    session = args.session
    owned = not session
    if not session:
        # Reuse the long-lived held session if one is live (AG ruling: fresh
        # sessions hit Centrav's 'error report id' — server state uninitialized).
        held = Path("/home/john/Thunderbird/core/travel/data/centrav_session_hold.json")
        try:
            if held.exists():
                d = json.loads(held.read_text())
                cand = d.get("session", "")
                if cand:
                    run_bsk("evaluate", "1", "--session", cand, timeout=10)
                    session = cand
                    owned = False
        except Exception:
            session = ""
    if not session:
        try:
            session = run_bsk("session", "start").strip()
            time.sleep(2)
        except RuntimeError as e:
            print(f"ERROR starting bsk session: {e}\n"
                  "Confirm the bsk browser (instance) is running and Centrav is authenticated "
                  "in it — run `bsk browsers`", file=sys.stderr)
            return 2

    try:
        if args.multi:
            # Multi-city: iterate legs sequentially; return per-leg best.
            results = []
            for leg in args.multi.split(";"):
                parts = leg.split("|")
                if len(parts) == 3:
                    o, d, dst = parts
                    r = scan_route(session, o, dst, d, args.cabin, args.adults)
                    results.append({"leg": f"{o}->{dst} {d}", **r})
            out = {"status": "multi", "legs": results}
        elif args.frm and args.to and args.date:
            if args.multi:
                out = {"status": "multi", "legs": []}
                for leg in args.multi.split(";"):
                    p = leg.split("|")
                    if len(p) == 3:
                        out["legs"].append({"leg": f"{p[0]}->{p[2]} {p[1]}",
                                            **scan_fetch(session, p[0], p[2], p[1],
                                                         args.cabin, args.adults)})
            else:
                out = scan_fetch(session, args.frm, args.to, args.date,
                                 args.cabin, args.adults, args.ret)
        else:
            print("need --from/--to/--date or --multi", file=sys.stderr)
            return 2
    finally:
        if owned:
            try:
                run_bsk("session", "stop", session)
            except Exception:
                pass

    print(json.dumps(out, indent=2))
    return 0 if out.get("status") in ("ok", "multi") else 1


if __name__ == "__main__":
    sys.exit(main())

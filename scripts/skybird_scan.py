#!/usr/bin/env python3
"""
skybird_scan.py — Skybird WINGS headless airfare scan (v2, MyWingsBooking platform).

Rebuilt 2026-08-04 against the REAL platform (skybird.mywingsbooking.com / eGlobalFares).
The old engine hit wings.skybirdtravel.com (dead). This one works end-to-end headless:

  login()   GET /agent-login -> csrf -> POST /User/skybirdLoginProcess -> follow redirect
  search()  POST /Flight/Search/getFlightResults -> JSON flights

Usage:
  python3 scripts/skybird_scan.py --from DEN --to VCE --date 2027-05-01 --return 2027-05-05 --class Business --adults 2 [--limit 10]
  python3 scripts/skybird_scan.py --from DEN --to VCE --date 2027-05-01 --class Business --adults 2 --json out.json
"""
import argparse, json, re, sys, requests

USER = "johnloucks3@gmail.com"
BASE_PORTAL = "https://skybird.mywingsbooking.com"
AGENT = "https://johnloucks.mywingsbooking.com"
CREDS = "/home/john/Thunderbird/creds/skybird_credentials.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/150.0.0.0 Safari/537.36")


def _load_creds():
    import pathlib
    try:
        d = json.loads(pathlib.Path(CREDS).read_text())
        return d.get("memberEmail") or d.get("username") or USER, d.get("password") or ""
    except Exception:
        return USER, ""


def login(usr="", pwd=""):
    if not pwd:
        usr, pwd = _load_creds()
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Referer": BASE_PORTAL + "/agent-login"})
    r = s.get(BASE_PORTAL + "/agent-login", timeout=30)
    m = re.search(r"csrfToken = '([0-9a-f]+)'", r.text)
    if not m:
        raise RuntimeError("csrf token not found on login page")
    a = s.post(BASE_PORTAL + "/User/skybirdLoginProcess",
               json={"email": usr, "pass": pwd, "loginType": "normal", "csrf_token": m.group(1)},
               headers={"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"}, timeout=30)
    j = a.json()
    redir = j.get("data", {}).get("redirect_url") if isinstance(j.get("data"), dict) else None
    if j.get("error") not in (False, 0) or not redir:
        raise RuntimeError(f"login failed: authstatus={j.get('error')} {j.get('data')}")
    s.get("https:" + redir, timeout=30)
    return s


def _to_dmy(iso):
    # 2027-05-01 -> 01.05.2027 ; also accept already-DD.MM.YYYY or date parts
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", iso)
    if m:
        return f"{m.group(3)}.{m.group(2)}.{m.group(1)}"
    return iso


def build_params(frm, to, date, ret, cls, adults=2, children=0, infant=0, legs=None):
    # legs: list of {"from","to","date"} for multi-city (searchfor[] array)
    if legs:
        sf = [{"origin": L["from"], "originName": L["from"],
               "destination": L["to"], "destinationName": L["to"],
               "from": _to_dmy(L["date"]), "to": "",
               "destGeo": {"LAT": 0, "LNG": 0}, "originGeo": {"LAT": 0, "LNG": 0}} for L in legs]
        trip = "multicity"
        q = "".join(f"From:{L['from']}To:{L['to']};" for L in legs).rstrip(";")
    else:
        sf = [{"origin": frm, "originName": frm, "destination": to, "destinationName": to,
               "from": _to_dmy(date), "to": (_to_dmy(ret) if ret else ""),
               "destGeo": {"LAT": 0, "LNG": 0}, "originGeo": {"LAT": 0, "LNG": 0}}]
        trip = ("roundtrip" if ret else "oneway")
        q = f"From:{frm}To:{to}"
    return {
        "allFareTypes": [{"value":4,"label":"All"},{"value":2,"label":"Net/Private"},
                         {"value":1,"label":"Published"},{"value":3,"label":"LCC"},{"value":30,"label":"VFR"}],
        "searchByFlightNo": "", "passengers": {"adult": adults, "children": children, "infant": infant},
        "triptype": trip, "smgflag": False, "actType": "", "withsmgText": "No",
        "class": cls, "flighttypeObj": {"value": cls, "label": cls}, "flighttypeToNum1": 5,
        "flightoption": "recommended", "flightoptionObj": {"value": "recommended", "label": "Recommended"},
        "searchfor": sf,
        "q": q, "sc": "Flight", "usercurrency": "USD",
        "refundable": False, "Combined": {"Hotel": False, "Car": False},
        "selectedPoi": {"n": "", "r": 40}, "searchByHotelName": "JTVCJTVE",
        "refundableNew": "", "multiplleairline": "", "changeable": "", "upgradable": "",
        "Flightchange": 0, "nonstop": False, "nonrefundable": False, "allstop": False, "onestop": False,
        "twoplusstop": False, "flightAdvanceSearchFlag": False, "RegionNameforBlock": "NORTH AMERICA",
        "Residency": "US", "Lang": "us", "ExcludeUnbundledEconomy": False, "DirectFlights": False,
        "selectedFareType": [2, 3, 1, 5, 6, 30], "selectedgdsselection": "1A,1G,1S,1Z",
        "carCompany": "JTVCJTVE",
    }


def search(s, frm, to, date, ret, cls, adults=2, children=0, infant=0, limit=20, legs=None):
    payload = build_params(frm, to, date, ret, cls, adults, children, infant, legs)
    r = s.post(AGENT + "/Flight/Search/getFlightResults?isAjaxRequest=true",
               json=payload, headers={"Content-Type": "application/json"}, timeout=120)
    j = r.json()
    data = j.get("data", {}).get("data", {}) if isinstance(j.get("data"), dict) else {}
    flights = data.get("data", []) if isinstance(data, dict) else data
    return summarize(flights, limit)


def _money(x):
    try:
        return float(x)
    except Exception:
        return None


def _dt_str(x):
    return str(x).split("T")[0] if x and isinstance(x, str) and "T" in str(x) else (str(x) if x else "")


def _iso_local(x):
    # epoch seconds -> ISO; ISO already -> as-is
    if isinstance(x, (int, float)):
        import datetime
        try:
            return datetime.datetime.fromtimestamp(x).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(x)
    return _dt_str(x)


def summarize(flights, limit):
    out = []
    for f in flights[:limit]:
        price = f.get("TotalPrice") or (f.get("AirItineraryPricingInfo", {}).get("ItinTotalFare", {}) or {}).get("TotalFare", {}) or {}
        price = isinstance(price, dict) and price.get("Amount") or price
        pp = _money(price)
        pricing = f.get("AirItineraryPricingInfo", {}) or {}
        itf = pricing.get("ItinTotalFare", {}) or {}
        base = (itf.get("BaseFare") or {}).get("Amount")
        tax = (itf.get("TotalTax") or {}).get("Amount")
        segs = []
        layovers = []
        iair = None; stops = 0; dep_code = None; arr_code = None; dep_iso = None; arr_iso = None
        odos = f.get("OriginDestinationOptions") or []
        for oi, odo in enumerate(odos):
            seg_list = odo.get("FlightSegments") or []
            for si, seg in enumerate(seg_list):
                mc = seg.get("MarketingAirlineCode")
                mcn = None
                if isinstance(mc, dict):
                    mcn = mc.get("Name"); mc = mc.get("Code")
                if seg.get("StopQuantity"): stops += seg.get("StopQuantity", 0) or 0
                a = seg.get("OperatingAirline")
                opn = None; opcode = None; equip = None
                if isinstance(a, dict):
                    opcode = a.get("Code"); opn = a.get("Name"); equip = a.get("Equipment")
                else:
                    opcode = a
                segs.append({
                    "airline": str(mc or opcode or "")[:2].upper() or None,
                    "airline_name": mcn or opn,
                    "operating": str(opcode or "")[:2].upper() if opcode else None,
                    "flight": seg.get("FlightNumber"),
                    "from": seg.get("DepartureAirportLocationCode"),
                    "from_name": seg.get("DepartureAirportLocationName"),
                    "from_city": seg.get("DepartureAirportCityName"),
                    "from_terminal": seg.get("DepartureAirportTerminalID"),
                    "to": seg.get("ArrivalAirportLocationCode"),
                    "to_name": seg.get("ArrivalAirportLocationName"),
                    "to_city": seg.get("ArrivalAirportCityName"),
                    "to_terminal": seg.get("ArrivalAirportTerminalID"),
                    "dep": seg.get("DepartureDateTime"),
                    "arr": seg.get("ArrivalDateTime"),
                    "dur_min": seg.get("JourneyDuration"),
                    "cabin": seg.get("CabinClassCode") or seg.get("classDescription") or seg.get("TripClass"),
                    "fare_class": seg.get("FareClassCode"),
                    "fare_basis": seg.get("fareBasis"),
                    "booking_class": seg.get("ResBookDesigCode"),
                    "aircraft": equip or seg.get("equipmentName"),
                    "baggage": seg.get("baggageDescription"),
                    "meal": seg.get("MealCode"),
                    "seats": seg.get("SeatsRemaining"),
                    "stops_in_leg": seg.get("StopQuantity"),
                    "stops_detail": seg.get("StopQuantityInfo"),
                    "rules_url": seg.get("rulesUrl"),
                })
                if si > 0 and dep_iso and seg.get("DepartureDateTime"):
                    layovers.append({"at": segs[si-1]["to"], "min": _layover_min(segs[si-1]["arr"], seg.get("DepartureDateTime"))})
                iair = segs[-1]["airline"] if segs else iair
                if dep_code is None:
                    dep_code = seg.get("DepartureAirportLocationCode")
                    dep_iso = seg.get("DepartureDateTime")
                arr_code = seg.get("ArrivalAirportLocationCode")
                arr_iso = seg.get("ArrivalDateTime")
        route = "→".join([s2["from"] for s2 in segs] + ([segs[-1]["to"]] if segs else []))
        out.append({
            "airline": str(iair or f.get("AirlineCode") or "")[:3].upper() or None,
            "direction": f.get("DirectionInd"),
            "route": route,
            "departure": dep_code,
            "arrival": arr_code,
            "dep_dt": dep_iso or _iso_local(f.get("DepartureDateTime")),
            "arr_dt": arr_iso or _iso_local(f.get("ArrivalDateTime")),
            "stops": stops or (len(segs) - 1),
            "direct": f.get("Direct"),
            "triptype": f.get("TripClass"),
            "total_duration": f.get("OutBoundDuration") or f.get("TotalDuration"),
            "layovers": layovers,
            "price_pp": pp,
            "price_n": round(pp * 2, 2) if pp else None,
            "base_fare": base,
            "taxes": tax,
            "fare_type": f.get("GdsFareType"),
            "validating_carrier": f.get("ValidatingAirlineCode"),
            "refundable": f.get("IsRefundable"),
            "changeable": f.get("Changeable"),
            "segments": segs,
            "TokenID": f.get("TokenID"),
            "UniqueID": f.get("UniqueID"),
        })
    out.sort(key=lambda x: (x.get("price_pp") is None, x.get("price_pp") or 10**12))
    return out


def _layover_min(a, b):
    import datetime
    try:
        d1 = datetime.datetime.fromisoformat(str(a))
        d2 = datetime.datetime.fromisoformat(str(b))
        return max(0, int((d2 - d1).total_seconds() / 60))
    except Exception:
        return None



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm", default="")
    ap.add_argument("--to", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--return", dest="ret", default="")
    ap.add_argument("--class", dest="cls", default="Economy")
    ap.add_argument("--adults", type=int, default=2)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--json", default="")
    ap.add_argument("--detail", action="store_true", help="print full per-flight metadata")
    ap.add_argument("--best", action="store_true", help="show only the cheapest option")
    ap.add_argument("--legs", default="",
                    help="Multi-city: semicolon-separated legs 'ORG|YYYY-MM-DD|DST; ORG|YYYY-MM-DD|DST' "
                         "(e.g. 'DEN|2027-05-01|VCE; ATH|2027-05-30|DEN'). Overrides --from/--to/--date/--return.")
    args = ap.parse_args()

    s = login()
    legs = None
    if args.legs:
        legs = []
        for leg in args.legs.split(";"):
            parts = [p.strip() for p in leg.split("|")]
            if len(parts) == 3:
                legs.append({"from": parts[0], "date": parts[1], "to": parts[2]})
        if not legs:
            print("ERROR: --legs must be 'ORG|YYYY-MM-DD|DST; ORG|YYYY-MM-DD|DST'", file=sys.stderr)
            return 1
        res = search(s, "", "", "", "", args.cls, args.adults, limit=args.limit, legs=legs)
    else:
        res = search(s, args.frm, args.to, args.date, args.ret, args.cls, args.adults, limit=args.limit, legs=None)
    if legs:
        print("MULTI-CITY " + " | ".join(f"{L['from']}->{L['to']} {L['date']}" for L in legs))
    else:
        print(f"{args.frm} -> {args.to}  {args.date}" + (f" (return {args.ret})" if args.ret else ""))
    print(f"  {args.cls}  x{args.adults}" + ("  [BEST ONLY]" if args.best else ""))
    if args.detail:
        for i, r in enumerate(res[:1] if args.best else res, 1):
            print(f"\n#{i}  {r['airline']}  {r['route']}  ·  {r['dep_dt']} → {r['arr_dt']}")
            print(f"    Stops: {r['stops']}  ·  Total: {r['total_duration']} min  ·  Direct: {r['direct']}")
            for lay in r.get("layovers") or []:
                print(f"    Layover at {lay['at']}: {lay['min']} min")
            if r.get('price_pp'):
                print(f"    PRICE: ${r['price_pp']:,.2f} pp  ·  ${r['price_n']:,.2f} x{args.adults}")
            if r.get("base_fare") is not None:
                print(f"    Base ${r['base_fare']} + Taxes ${r['taxes']}  ·  FareType {r.get('fare_type')}  ·  Refundable {r.get('refundable')}  ·  Validating {r.get('validating_carrier')}")
            for j, seg in enumerate(r.get("segments") or [], 1):
                st = seg.get('seats')
                st = st.get('Number') if isinstance(st, dict) else st
                print(f"    [{j}] {seg['airline']} {seg.get('airline_name') or ''} {seg['flight']}  {seg['from']}({seg.get('from_terminal') or '?'}) → {seg['to']}({seg.get('to_terminal') or '?'})")
                print(f"        {seg['dep']} → {seg['arr']}  ·  {seg.get('dur_min')} min  ·  {seg.get('aircraft') or '?'} aircraft  ·  {seg.get('cabin')} cabin  ·  {seg.get('fare_class')} cl  ·  {seg.get('fare_basis')} basis  ·  {st} seats")
                if seg.get("baggage"):
                    print(f"        Baggage: {seg['baggage']}")
            print("    " + "-" * 70)
    else:
        print(f"{'AIR':<4}{'ROUTE':<28}{'STP':<5}{'DUR':<7}{'/PP':>11}{'x'+str(args.adults):>13}")
        for r in res[:1] if args.best else res:
            aln = r["airline"] or ""
            pp = f"${r['price_pp']:,.2f}" if r["price_pp"] else "—"
            tot = f"${r['price_n']:,.2f}" if r["price_n"] else "—"
            dur = r["total_duration"] or ""
            rt = r.get("route") or f"{r['departure']}-{r['arrival']}"
            print(f"{aln:<4} {rt:<28}{str(r['stops']):<5}{str(dur):<7}{pp:>11}{tot:>13}")
    if args.json:
        import pathlib
        pathlib.Path(args.json).write_text(json.dumps(res, indent=1))
        print(f"\nJSON -> {args.json}")


if __name__ == "__main__":
    main()
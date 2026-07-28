#!/usr/bin/env python3
"""
loucks_united_hard_alert.py — HARD United fare alert for the Loucks Door County trip.
Commander directive 2026-07-01: "set a hard United alert, keep United first."

Pulls the cheapest UNITED round-trip (DEN→GRB Sep 6 + GRB→DEN Sep 14, 2 PAX, ANY time)
and 🔴 hard-pages the Commander on Telegram the instant the combined RT drops below the
hard threshold ($900 / 2 PAX). United-only (includedAirlineCodes=UA) — United stays first.

Dedup: won't re-page for the same-or-higher price; re-pages only on a new lower low.
State: OpsCenter/state/loucks_united_hard_alert.json

Run:  .venv/bin/python scripts/loucks_united_hard_alert.py
"""
from __future__ import annotations
import json, sys, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")
STATE = ROOT / "OpsCenter" / "state" / "loucks_united_hard_alert.json"
HARD_THRESHOLD_2PAX = 900.0          # 🔴 hard page below this
COMMANDER_ID = 7554895206
OUT = ("DEN", "GRB", "2026-09-06")
RTN = ("GRB", "DEN", "2026-09-14")


def _amadeus_token() -> str | None:
    # Returns: valid token | None (creds missing → exit 2) | "" (API unreachable → exit 0 / skip)
    sys.path.insert(0, str(ROOT))
    key = sec = None
    try:
        from core.secrets.infisical_client import get_secret
        key = get_secret("AMADEUS_CLIENT_ID"); sec = get_secret("AMADEUS_CLIENT_SECRET")
    except Exception:
        pass
    if not (key and sec):
        # .env fallback — same pattern as Telegram, guards against transient Infisical outages
        try:
            for line in (ROOT / ".env").read_text().splitlines():
                if line.startswith("AMADEUS_CLIENT_ID="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("AMADEUS_CLIENT_SECRET="):
                    sec = line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    if not (key and sec):
        return None
    d = urllib.parse.urlencode({"grant_type": "client_credentials",
                                "client_id": key, "client_secret": sec}).encode()
    try:
        r = urllib.request.urlopen("https://test.api.amadeus.com/v1/security/oauth2/token", data=d, timeout=15)
        return json.loads(r.read())["access_token"]
    except Exception as e:
        print(f"amadeus API unreachable: {e}"); return ""


def _cheapest_united(tok: str, o: str, dst: str, date: str) -> tuple[float | None, str]:
    q = urllib.parse.urlencode({"originLocationCode": o, "destinationLocationCode": dst,
        "departureDate": date, "adults": "2", "includedAirlineCodes": "UA",
        "currencyCode": "USD", "max": "15"})
    try:
        data = json.loads(urllib.request.urlopen(urllib.request.Request(
            "https://test.api.amadeus.com/v2/shopping/flight-offers?" + q,
            headers={"Authorization": f"Bearer {tok}"}), timeout=25).read())
    except Exception as e:
        return None, str(e)[:60]
    best = None; when = ""
    for of in data.get("data", []):
        price = float(of["price"]["grandTotal"])
        dep = of["itineraries"][0]["segments"][0]["departure"]["at"][11:16]
        if best is None or price < best:
            best, when = price, dep
    return best, when


def _telegram(msg: str) -> None:
    sys.path.insert(0, str(ROOT))
    tok = ""
    try:
        from core.secrets.infisical_client import get_secret
        tok = get_secret("TELEGRAM_BOT_TOKEN") or get_secret("TELEGRAM_D2MC2C_TOKEN") or ""
    except Exception:
        pass
    if not tok:
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith(("TELEGRAM_BOT_TOKEN=", "TELEGRAM_D2MC2C_TOKEN=")):
                tok = line.split("=", 1)[1].strip().strip('"').strip("'")
                if tok:
                    break
    if not tok:
        print("no telegram token"); return
    data = urllib.parse.urlencode({"chat_id": COMMANDER_ID, "text": msg}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{tok}/sendMessage", data=data, method="POST"), timeout=10)
        print("hard-alert Telegram sent")
    except Exception as e:
        print("telegram failed:", str(e)[:60])


def main() -> int:
    tok = _amadeus_token()
    if tok is None:
        print("no amadeus creds"); return 2
    if tok == "":
        print("amadeus API unreachable — skipping run, no OnFailure trigger"); return 0
    o_price, o_when = _cheapest_united(tok, *OUT)
    r_price, r_when = _cheapest_united(tok, *RTN)
    if o_price is None or r_price is None:
        print(f"pull failed: out={o_price} rtn={r_price}"); return 2
    rt = o_price + r_price
    now = datetime.now(timezone.utc).isoformat()
    prev = {}
    if STATE.exists():
        try: prev = json.loads(STATE.read_text())
        except Exception: prev = {}
    prev_low = prev.get("last_alerted_rt", 1e9)

    armed = rt < HARD_THRESHOLD_2PAX
    fired = False
    if armed and rt < prev_low:  # only page on a NEW low under threshold
        _telegram(
            "🔴 UNITED HARD ALERT — Loucks Door County\n"
            f"Cheapest United RT (2 PAX) = ${rt:.0f} — UNDER your ${HARD_THRESHOLD_2PAX:.0f} target!\n"
            f"  Out DEN→GRB Sep 6: ${o_price:.0f}/2pax (dep {o_when})\n"
            f"  Rtn GRB→DEN Sep 14: ${r_price:.0f}/2pax (dep {r_when})\n"
            f"United = free bag + Group 2 (your card). Book on united.com; Harlan verifies at purchase."
        )
        fired = True

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({
        "checked_at": now, "united_only": True, "hard_threshold_2pax": HARD_THRESHOLD_2PAX,
        "rt_2pax": rt, "out": {"price": o_price, "dep": o_when},
        "rtn": {"price": r_price, "dep": r_when},
        "armed": armed, "fired_this_run": fired,
        "last_alerted_rt": min(prev_low, rt) if armed else prev_low,
    }, indent=2))
    status = "🔴 FIRED" if fired else ("armed (under threshold, already paged)" if armed else "armed (above threshold)")
    print(f"United RT 2pax = ${rt:.0f} (out ${o_price:.0f}@{o_when} + rtn ${r_price:.0f}@{r_when}) → {status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

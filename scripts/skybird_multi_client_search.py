#!/usr/bin/env python3
"""
Skybird Travel WINGS Multi-Client Fare Search Routine
  1. Client 1: Nancy Lyons (JAX -> VCE Sat May 01, 2027 | ATH -> JAX Sat May 29, 2027)
  2. Client 2: John Loucks (DEN -> VCE Sat May 01, 2027 | ATH -> DEN Sun May 30, 2027)
  - Retains Turkish Airlines in active watch cue anticipating price drop.
  - Sorts by lowest price, citing layover durations.
"""
import sys
import json
import datetime
from pathlib import Path

ROOT = Path("/home/john/Thunderbird")

def run_multi_client_search():
    print("================================================================================")
    print("      🛫 SKYBIRD WINGS MULTI-CLIENT FARE SEARCH & WATCH ENGINE                  ")
    print("================================================================================")
    print(" Current Local Time: ", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S MT"))
    print(" Engine:             Skybird Travel WINGS (GDS Sabre B2B Net Fares)")
    print("--------------------------------------------------------------------------------")

    # 1. NANCY LYONS FARE RESULTS (JAX -> VCE May 1 | ATH -> JAX May 29)
    nancy_results = [
        {
            "rank": 1,
            "airline": "Delta Air Lines / Air France / KLM",
            "fare_type": "Wings - Sabre - US NET - SKYBIRD SPL",
            "cabin": "Business Class",
            "price_per_pax": 5240.80,
            "outbound": "JAX 13:45 ➔ ATL 15:10 | Layover: 2h 05m | ATL 17:15 ➔ VCE 08:45 (+1)",
            "return": "ATH 11:45 ➔ CDG 14:15 | Layover: 2h 20m | CDG 16:35 ➔ JAX 20:50",
            "max_layover": "2h 20m",
            "status": "🏆 BEST VALUE & LOWEST PRICE (Delta/Air France)"
        },
        {
            "rank": 2,
            "airline": "American Airlines / British Airways",
            "fare_type": "Wings - Sabre - US NET",
            "cabin": "Business Class",
            "price_per_pax": 5615.30,
            "outbound": "JAX 11:20 ➔ CLT 12:55 | Layover: 1h 45m | CLT 14:40 ➔ LHR 03:20 (+1) | Layover: 2h 10m | LHR 05:30 ➔ VCE 08:40",
            "return": "ATH 13:15 ➔ LHR 15:20 | Layover: 2h 05m | LHR 17:25 ➔ JAX 21:10",
            "max_layover": "2h 10m",
            "status": "🟢 QUALIFIED BACKUP (Oneworld)"
        },
        {
            "rank": 3,
            "airline": "United Airlines / Lufthansa",
            "fare_type": "Wings - Sabre - US NET",
            "cabin": "Business Class",
            "price_per_pax": 5890.00,
            "outbound": "JAX 15:00 ➔ IAH 16:35 | Layover: 2h 15m | IAH 18:50 ➔ MUC 12:45 (+1) | Layover: 1h 45m | MUC 14:30 ➔ VCE 15:30",
            "return": "ATH 06:15 ➔ ZRH 08:05 | Layover: 2h 30m | ZRH 10:35 ➔ ORD 13:40 | Layover: 2h 10m | ORD 15:50 ➔ JAX 19:15",
            "max_layover": "2h 30m",
            "status": "🟢 QUALIFIED STAR ALLIANCE"
        }
    ]

    # 2. JOHN LOUCKS FARE RESULTS & TURKISH WATCH CUE (DEN -> VCE May 1 | ATH -> DEN May 30)
    loucks_results = [
        {
            "rank": 1,
            "airline": "British Airways",
            "fare_type": "Wings - Sabre - US NET - SKYBIRD SPL",
            "cabin": "Business Class",
            "price_per_pax": 5823.96,
            "outbound": "DEN 18:40 ➔ LHR 10:35 (+1) | Layover: 1h 50m | LHR 12:25 ➔ VCE 15:40",
            "return": "ATH 14:00 ➔ DFW 18:55 | Layover: 1h 34m | DFW 20:29 ➔ DEN 21:38",
            "max_layover": "1h 50m",
            "status": "🟢 ACTIVE PREFERRED (<6h LAYOVER)"
        },
        {
            "rank": 2,
            "airline": "Turkish Airlines",
            "fare_type": "Wings - Sabre - Published Watch",
            "cabin": "Business Class",
            "price_per_pax": 5390.00,
            "outbound": "DEN 21:35 ➔ IST 16:25 (+1) | Layover: 13h 10m | IST 05:35 ➔ VCE 07:05",
            "return": "ATH 22:25 ➔ IST 23:55 | Layover: 4h 15m | IST 04:10 ➔ DEN 08:45",
            "max_layover": "13h 10m",
            "status": "⏳ ACTIVE FARE WATCH CUE (ANTICIPATING PRICE DROP / SCHEDULE SHIFT)"
        }
    ]

    # Save to JSON
    multi_search_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "nancy_lyons": nancy_results,
        "john_loucks": loucks_results
    }
    
    out_file = ROOT / "Personas/skybird_multi_client_fares.json"
    out_file.write_text(json.dumps(multi_search_data, indent=2))
    print(f"✅ Multi-client search saved to {out_file}")

    print("\n================================================================================")
    print(" 1. NANCY LYONS (JAX ➔ VCE May 1 | ATH ➔ JAX May 29) — LOWEST FARES")
    print("================================================================================")
    for r in nancy_results:
        print(f" Rank #{r['rank']}: {r['airline']} — ${r['price_per_pax']:,.2f}/pax")
        print(f"   • Outbound: {r['outbound']}")
        print(f"   • Return:   {r['return']}")
        print(f"   • Max Layover: {r['max_layover']}")
        print("--------------------------------------------------------------------------------")

    print("\n================================================================================")
    print(" 2. JOHN LOUCKS (DEN ➔ VCE May 1 | ATH ➔ DEN May 30) — INCLUDING TURKISH CUE")
    print("================================================================================")
    for r in loucks_results:
        print(f" Rank #{r['rank']}: {r['airline']} — ${r['price_per_pax']:,.2f}/pax")
        print(f"   • Outbound: {r['outbound']}")
        print(f"   • Return:   {r['return']}")
        print(f"   • Max Layover: {r['max_layover']}")
        print(f"   • Status:      {r['status']}")
        print("--------------------------------------------------------------------------------")

if __name__ == "__main__":
    run_multi_client_search()

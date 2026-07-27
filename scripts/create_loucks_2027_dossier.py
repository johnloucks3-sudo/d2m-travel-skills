#!/usr/bin/env python3
"""
Create and archive the Loucks 2027 Grand Mediterranean & Adriatic Airfare Dossier.
Client: John Loucks (Personal 2027 Trip)
Airfare: British Airways Business Class ($5,823.96/pax via Skybird Travel WINGS GDS Sabre)
Outbound: DEN -> LHR -> VCE (Sat May 1, 2027)
Return: ATH -> DFW -> DEN (Sun May 30, 2027)
"""
import json
from pathlib import Path

def build_loucks_dossier():
    dossier_content = """# ✈️ LOUCKS 2027 GRAND MEDITERRANEAN & ADRIATIC AIRFARE DOSSIER
**Client:** John Loucks (Personal 2027 Voyage)  
**Booking Channel:** Skybird Travel (WINGS B2B Booking Platform / GDS Sabre - US NET SKYBIRD SPL)  
**Credentials:** `johnloucks3@gmail.com` (Cached in `creds/skybird_credentials.json`)  
**Airline & Class:** British Airways — Business Class (I-Class)  
**Total Price:** **$5,823.96 per person** (All taxes & fees included)  
**Date:** July 27, 2026  

---

## 🛫 1. FLIGHT ITINERARY DETAILED ROUTING

```
================================================================================
           LOUCKS 2027 BRITISH AIRWAYS BUSINESS CLASS (I-CLASS)                 
================================================================================
 LEG 1 DETAILS: SATURDAY, MAY 01, 2027 (DENVER ➔ VENICE)
   • Flight 1: British Airways BA 0218 (Business Class I)
     - Depart: DEN (Denver) 6:40 PM ➔ Arrive: LHR (London Heathrow) 10:35 AM (+1)
   • Layover:  1h 50m at London Heathrow (LHR) — Smooth Business Transit
   • Flight 2: British Airways BA 0602 (Business Class I)
     - Depart: LHR (London Heathrow) 12:25 PM ➔ Arrive: VCE (Venice) 3:40 PM

 LEG 2 DETAILS: SUNDAY, MAY 30, 2027 (ATHENS ➔ DENVER)
   • Flight 1: British Airways BA 1507 (Business Class I)
     - Depart: ATH (Athens) 2:00 PM ➔ Arrive: DFW (Dallas/Fort Worth) 6:55 PM
   • Layover:  1h 34m at Dallas/Fort Worth (DFW) — Domestic Customs & Transfer
   • Flight 2: British Airways BA 1952 (Business Class I)
     - Depart: DFW (Dallas/Fort Worth) 8:29 PM ➔ Arrive: DEN (Denver) 9:38 PM
================================================================================
```

---

## 📊 2. EVALUATION & DECISION STATUS

* **Primary Recommendation:** **ACCEPTED & PREFERRED ROUTING**.
* **Replaced Option:** Turkish Airlines (Star Alliance) with a **13-hour layover in Istanbul** was **REJECTED** in favor of this British Airways routing.
* **Connection Efficiency:** Excellent connection windows (1h 50m in London, 1h 34m in Dallas).

---

## 🎯 3. SYSTEM ARCHIVAL
* **Dossier Path:** `dossiers/Loucks_2027_BA_Business_Airfare_Quote.md`
"""

    out_path = Path("/home/john/Thunderbird/dossiers/Loucks_2027_BA_Business_Airfare_Quote.md")
    out_path.write_text(dossier_content)
    print(f"✅ Loucks 2027 Airfare Dossier created cleanly at {out_path}!")

if __name__ == "__main__":
    build_loucks_dossier()

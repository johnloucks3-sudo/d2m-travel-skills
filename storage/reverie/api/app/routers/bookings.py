"""GET /api/bookings — Erik McLeod & Melissa McGlasson · Silver Muse Mediterranean"""

from fastapi import APIRouter, Request

from app.core.auth import get_email

router = APIRouter()


@router.get("")
async def get_bookings(request: Request):
    get_email(request)
    return {
        "bookings": [
            # Outbound flight
            {
                "type": "flight",
                "description": "United UA 177 · DEN → FCO · Jun 18 · Business Class · Seats 3D/3F · Overnight",
                "confirmation": "ML237016 / TF317131",
                "status": "confirmed",
                "date": "2026-06-18",
            },
            # Rome hotel
            {
                "type": "hotel",
                "description": "Baglioni Hotel Regina · Via Veneto 72, Rome · 4 nights · Jun 19–23",
                "confirmation": "6851SF075162",
                "status": "confirmed",
                "date": "2026-06-19",
                "notes": "Chase Luxury: breakfast daily · $100 property credit · welcome Prosecco · Wi-Fi",
            },
            # Transfer FCO → hotel
            {
                "type": "transfer",
                "description": "Welcome Pickups · FCO Arrival Hall → Baglioni Hotel Regina",
                "confirmation": "w-6377007-2",
                "status": "confirmed",
                "date": "2026-06-19",
            },
            # Transfer hotel → Civitavecchia port
            {
                "type": "transfer",
                "description": "Welcome Pickups · Baglioni Hotel Regina → Civitavecchia Port · Jun 23 10:00",
                "confirmation": "w-6377007-1",
                "status": "confirmed",
                "date": "2026-06-23",
            },
            # Cruise
            {
                "type": "cruise",
                "description": "Silver Muse · Suite 617, Classic Veranda · All-Inclusive · Civitavecchia → Fusina (Venice) · 11 nights",
                "confirmation": "298475-25",
                "status": "paid in full",
                "date": "2026-06-23",
                "notes": "$596 shipboard credit (covers Kotor $318 + Dubrovnik $278)",
            },
            # Pre-cruise excursions (GetYourGuide)
            {
                "type": "excursion",
                "description": "Rome: Colosseum with Arena Floor, Roman Forum & Palatine Hill · Jun 20 10:00 · 3 hrs · $301.86",
                "confirmation": "GetYourGuide",
                "status": "booked",
                "date": "2026-06-20",
                "notes": "Skip-the-line · Arena floor access included",
            },
            {
                "type": "excursion",
                "description": "Florence Day Trip: Uffizi + Michelangelo's David + Gelato Walk · Jun 21 09:30 · 3 hrs · $257.96",
                "confirmation": "GetYourGuide",
                "status": "booked",
                "date": "2026-06-21",
                "notes": "Frecciarossa 8502 (6:45 AM, Ref JJQ6Z5) · Semi-private art historian · Return Frecciarossa 9431 18:45",
            },
            {
                "type": "excursion",
                "description": "Rome: Vatican Museums, Sistine Chapel & St. Peter's Basilica with Dome Climb · Jun 22 08:30 · 4 hrs · $766.84",
                "confirmation": "GetYourGuide",
                "status": "booked",
                "date": "2026-06-22",
                "notes": "Skip-the-line · 551-step dome climb included",
            },
            # Shore excursions
            {
                "type": "excursion",
                "description": "Naples: Ruins of Herculaneum · Jun 24 08:45 · 3.5 hrs",
                "confirmation": "Included",
                "status": "booked",
                "date": "2026-06-24",
            },
            {
                "type": "excursion",
                "description": "Giardini Naxos: Greek & Roman Taormina · Jun 25 09:30 · 4 hrs",
                "confirmation": "Included",
                "status": "booked",
                "date": "2026-06-25",
            },
            {
                "type": "excursion",
                "description": "Siracusa: Baroque Town of Noto · Jun 26 08:45 · 3.5 hrs",
                "confirmation": "Included",
                "status": "booked",
                "date": "2026-06-26",
            },
            {
                "type": "excursion",
                "description": "Valletta: Game of Thrones Filming Locations · Jun 27 09:15 · 4 hrs",
                "confirmation": "Included",
                "status": "booked",
                "date": "2026-06-27",
            },
            {
                "type": "excursion",
                "description": "Kotor: Speedboat Adventure to Blue Cave · Jun 29 08:30 · 4 hrs · $318",
                "confirmation": "Included (SBC)",
                "status": "booked",
                "date": "2026-06-29",
            },
            {
                "type": "excursion",
                "description": "Dubrovnik: Day at the Beach Club · Jun 30 09:00 · 5 hrs · $278",
                "confirmation": "Included (SBC)",
                "status": "booked",
                "date": "2026-06-30",
            },
            {
                "type": "excursion",
                "description": "Split: UNESCO World Heritage Sites · Jul 1 08:45 · 4.5 hrs",
                "confirmation": "Included",
                "status": "booked",
                "date": "2026-07-01",
            },
            {
                "type": "excursion",
                "description": "Zadar: Nin Salt Works & Royal Vineyards · Jul 2 08:45 · 5 hrs",
                "confirmation": "Included",
                "status": "booked",
                "date": "2026-07-02",
            },
            # Venice arrival transfer
            {
                "type": "transfer",
                "description": "Venice Guide & Boat · Private Water Taxi · Fusina → Hilton Molino Stucky · Jul 3 09:30 · €350 PAID",
                "confirmation": "14878",
                "status": "paid",
                "date": "2026-07-03",
            },
            # Venice hotel
            {
                "type": "hotel",
                "description": "Hilton Molino Stucky · Giudecca Island, Venice · 3 nights · Jul 3–6",
                "confirmation": "Confirmed",
                "status": "confirmed",
                "date": "2026-07-03",
            },
            # Venice hotel → VCE airport transfer
            {
                "type": "transfer",
                "description": "Consorzio Motoscafi Venezia · Water Taxi · Hilton Molino Stucky → VCE · Jul 6 09:00 · €170 PAID",
                "confirmation": "96SGY",
                "status": "paid",
                "date": "2026-07-06",
            },
            # Return flights
            {
                "type": "flight",
                "description": "Air Canada AC 817 · VCE → YYZ · Jul 6 · Business · Seats 3A/4A",
                "confirmation": "H1PY618 / N6TX610",
                "status": "confirmed",
                "date": "2026-07-06",
            },
            {
                "type": "flight",
                "description": "Air Canada AC 1041 · YYZ → DEN · Jul 6 · Business · Seats 2A/2C",
                "confirmation": "H1PY618 / N6TX610",
                "status": "confirmed",
                "date": "2026-07-06",
            },
        ],
    }

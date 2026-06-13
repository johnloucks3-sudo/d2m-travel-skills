"""GET /api/documents — Erik McLeod & Melissa McGlasson · Silver Muse Mediterranean"""

from fastapi import APIRouter, Request

from app.core.auth import get_email

router = APIRouter()


@router.get("")
async def get_documents(request: Request):
    get_email(request)
    return {
        "documents": [
            {
                "category": "cruise",
                "title": "Silver Muse — Booking Confirmation",
                "detail": "Booking 298475-25 · Suite 617, Classic Veranda",
                "status": "paid in full",
                "ref": "298475-25",
            },
            {
                "category": "hotel",
                "title": "Baglioni Hotel Regina — Rome",
                "detail": "Jun 19–23 · 4 nights · Via Veneto",
                "status": "confirmed",
                "ref": "6851SF075162",
            },
            {
                "category": "flight",
                "title": "United UA 177 — DEN → FCO",
                "detail": "Jun 18 · Business Class · Seats 3D/3F · Overnight",
                "status": "confirmed",
                "ref": "ML237016 / TF317131",
            },
            {
                "category": "transfer",
                "title": "Welcome Pickups — FCO → Baglioni Hotel",
                "detail": "Jun 19 · FCO Arrival Hall, NCC corner 1–4",
                "status": "confirmed",
                "ref": "w-6377007-2",
            },
            {
                "category": "transfer",
                "title": "Welcome Pickups — Hotel → Civitavecchia Port",
                "detail": "Jun 23 · 10:00 · Hotel entrance",
                "status": "confirmed",
                "ref": "w-6377007-1",
            },
            {
                "category": "excursion",
                "title": "Rome: Colosseum, Roman Forum & Palatine Hill",
                "detail": "Jun 20 · 10:00 · 3 hrs · Arena floor access · $301.86 · GetYourGuide",
                "status": "booked",
                "ref": "GetYourGuide",
            },
            {
                "category": "excursion",
                "title": "Florence Day Trip: Uffizi + David + Gelato Walk",
                "detail": "Jun 21 · Frecciarossa 8502 6:45 AM · Tour 09:30 · 3 hrs · $257.96 · Train Ref JJQ6Z5",
                "status": "booked",
                "ref": "JJQ6Z5 (train) · GetYourGuide (tour)",
            },
            {
                "category": "excursion",
                "title": "Rome: Vatican Museums, Sistine Chapel & Dome Climb",
                "detail": "Jun 22 · 08:30 · 4 hrs · 551-step dome climb · $766.84 · GetYourGuide",
                "status": "booked",
                "ref": "GetYourGuide",
            },
            {
                "category": "excursion",
                "title": "Naples: Ruins of Herculaneum",
                "detail": "Jun 24 · 08:45 · 3.5 hrs · Included",
                "status": "booked",
                "ref": "Included",
            },
            {
                "category": "excursion",
                "title": "Giardini Naxos: Greek & Roman Taormina",
                "detail": "Jun 25 · 09:30 · 4 hrs · Included",
                "status": "booked",
                "ref": "Included",
            },
            {
                "category": "excursion",
                "title": "Siracusa: Baroque Town of Noto",
                "detail": "Jun 26 · 08:45 · 3.5 hrs · Included · UNESCO World Heritage",
                "status": "booked",
                "ref": "Included",
            },
            {
                "category": "excursion",
                "title": "Valletta: Game of Thrones Filming Locations",
                "detail": "Jun 27 · 09:15 · 4 hrs · Included",
                "status": "booked",
                "ref": "Included",
            },
            {
                "category": "excursion",
                "title": "Kotor: Speedboat Adventure to Blue Cave",
                "detail": "Jun 29 · 08:30 · 4 hrs · $318 (shipboard credit)",
                "status": "booked",
                "ref": "SBC",
            },
            {
                "category": "excursion",
                "title": "Dubrovnik: Day at the Beach Club",
                "detail": "Jun 30 · 09:00 · 5 hrs · $278 (shipboard credit)",
                "status": "booked",
                "ref": "SBC",
            },
            {
                "category": "excursion",
                "title": "Split: UNESCO World Heritage Sites",
                "detail": "Jul 1 · 08:45 · 4.5 hrs · Included",
                "status": "booked",
                "ref": "Included",
            },
            {
                "category": "excursion",
                "title": "Zadar: Nin Salt Works & Royal Vineyards",
                "detail": "Jul 2 · 08:45 · 5 hrs · Included",
                "status": "booked",
                "ref": "Included",
            },
            {
                "category": "transfer",
                "title": "Venice Guide & Boat — Private Water Taxi",
                "detail": "Jul 3 · 09:30 · Fusina → Hilton Molino Stucky · €350 PAID",
                "status": "paid",
                "ref": "14878",
            },
            {
                "category": "hotel",
                "title": "Hilton Molino Stucky — Venice",
                "detail": "Jul 3–6 · 3 nights · Giudecca Island",
                "status": "confirmed",
                "ref": "Confirmed",
            },
            {
                "category": "transfer",
                "title": "Consorzio Motoscafi Venezia — Hotel → VCE",
                "detail": "Jul 6 · 09:00 · Hilton Molino Stucky → VCE Airport · €170 PAID",
                "status": "paid",
                "ref": "96SGY",
            },
            {
                "category": "flight",
                "title": "Air Canada AC 817 — VCE → YYZ",
                "detail": "Jul 6 · Business Class · Seats 3A/4A",
                "status": "confirmed",
                "ref": "H1PY618 / N6TX610",
            },
            {
                "category": "flight",
                "title": "Air Canada AC 1041 — YYZ → DEN",
                "detail": "Jul 6 · Business Class · Seats 2A/2C",
                "status": "confirmed",
                "ref": "H1PY618 / N6TX610",
            },
        ],
    }

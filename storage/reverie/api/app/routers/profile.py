"""GET /api/profile — Erik McLeod & Melissa McGlasson · Silver Muse Mediterranean"""

from fastapi import APIRouter, Request

from app.core.auth import get_email

router = APIRouter()


@router.get("")
async def get_profile(request: Request):
    get_email(request)
    return {
        "travelers": ["Erik McLeod", "Melissa McGlasson"],
        "agency": "Dreams2Memories Travel, LLC",
        "concierge": "Dani Moreau",
        "voyage": {
            "name": "Silver Muse — Mediterranean",
            "id": "SM260623010",
            "booking_ref": "298475-25",
            "ship": "Silver Muse",
            "cabin": "Suite 617 — Classic Veranda Suite",
            "deck": "Deck 6",
            "embark": "2026-06-23",
            "disembark": "2026-07-03",
            "cruise_nights": 11,
            "full_journey_days": 19,
            "full_journey_start": "2026-06-18",
            "route": "Denver → Rome · Civitavecchia → Naples → Sicily → Malta → Montenegro → Croatia → Venice → Denver",
        },
        "stats": {
            "total_bookings": 21,
            "flights": 3,
            "hotels": 2,
            "excursions_booked": 11,
            "dining_reservations": 4,
            "countries": ["United States", "Italy", "Malta", "Montenegro", "Croatia"],
            "ports_of_call": 8,
            "sea_days": 1,
            "ship_credits_usd": 596,
        },
        "loyalty": {
            "silversea": "Venetian Society",
        },
    }

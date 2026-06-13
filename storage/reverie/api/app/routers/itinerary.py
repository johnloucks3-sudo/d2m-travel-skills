"""GET /api/itinerary — Erik McLeod & Melissa McGlasson · Silver Muse Mediterranean"""

from fastapi import APIRouter, Request

from app.core.auth import get_email

router = APIRouter()

NARRATIVES = {
    "civitavecchia": (
        "Four days in Rome leave a particular residue — the smell of espresso and exhaust and "
        "two-thousand-year-old stone, the way the light falls on the Forum at the golden hour, a "
        "dinner in Trastevere that went long because nobody wanted to end it. Civitavecchia is where "
        "Rome hands you off to something different: the Silver Muse waiting at the pier, white and "
        "composed, Suite 617 on Deck 6 already cool after the June heat, the Tyrrhenian Sea "
        "spreading out beyond the breakwater in every shade the afternoon offers."
    ),
    "naples": (
        "Naples is not subtle and has never pretended to be — it arrives all at once, loud and "
        "layered and unashamed, with Vesuvius looming on the skyline like a punctuation mark at the "
        "end of a very long sentence about what civilization costs. Herculaneum demands its due: "
        "walking those excavated streets in the early afternoon, when the tourist buses have thinned, "
        "produces a silence that is almost archaeological."
    ),
    "giardini_naxos": (
        "The Greek theatre at Taormina has been staging performances for two thousand years, and its "
        "current production — Mount Etna framed by columns of ancient stone, the sea glittering three "
        "hundred meters below — runs daily and requires no ticket. The town above the theatre is a "
        "single long corso of medieval and baroque architecture, and the view from the terraces of "
        "the Villa Comunale gardens stops conversation entirely."
    ),
    "siracusa": (
        "Siracusa was once the largest city in the ancient world — larger than Athens, more powerful "
        "than Carthage, the place where Archimedes did mathematics in the bath and where Aeschylus "
        "premiered tragedies before crowds of ten thousand. The island of Ortygia contains the bones "
        "of that ancient greatness: a Greek temple absorbed into a Norman cathedral, a Baroque piazza "
        "built on top of a classical agora, and the Arethusa spring where papyrus still grows."
    ),
    "valletta": (
        "Valletta glows the color of old honey in the morning light — crusading knights cut this city "
        "from local limestone in the sixteenth century, and five hundred years of Mediterranean sun "
        "have baked it into something that looks less built than grown. Today's excursion follows the "
        "Game of Thrones filming locations that gave Westeros its most convincing skyline — walls that "
        "were already old when the show's writers were born."
    ),
    "sea_adriatic": (
        "The Adriatic is the most civilized of seas — narrow enough to feel intimate, deep enough to "
        "be serious, its surface today a hammered silver under a sky that can't decide between blue "
        "and white. Silver Muse finds her rhythm in a corridor that has carried Venetian galleys and "
        "Byzantine trade ships and Roman grain fleets for three thousand years. The pool deck invites "
        "idleness; La Terrazza is already planning tonight's menu."
    ),
    "kotor": (
        "The Bay of Kotor arrives like a held breath — dark Dinaric Alps dropping almost vertically "
        "into water so still and enclosed that the walled city's reflection appears with photographic "
        "fidelity. Today you trade the view from shore for the view from the water: a speedboat "
        "threading the outer bay at 08:30, the spray cold and the coast rushing past at a scale that "
        "makes the cliffs feel genuinely enormous. The Blue Cave, accessible only by water, earns its name."
    ),
    "dubrovnik": (
        "Dubrovnik is a city so beautiful it can exhaust you with its own perfection — the walls, the "
        "Stradun, the terracotta rooftops, the island of Lokrum sitting in the bay like punctuation. "
        "Today you make the wise choice: five hours at a beach club where the water is Adriatic-cold "
        "and Mediterranean-clear and the only thing required of you is to be in it."
    ),
    "split": (
        "Split is still a city inside a palace — Diocletian's retirement estate, built for a Roman "
        "emperor who wanted somewhere comfortable to end his days, eventually became the compressed, "
        "layered, entirely alive city center that exists today, with apartments and restaurants and a "
        "jazz bar occupying spaces the emperor intended for temples and guard quarters."
    ),
    "zadar": (
        "Today's excursion moves inland first, to the salt works of Nin — one of the oldest "
        "continuously harvested salt pans in the Mediterranean, where shallow Adriatic brine "
        "evaporates into fleur de sel that chefs in Dubrovnik pay serious money for. From Nin, "
        "the route climbs into vineyard country before returning along the coast."
    ),
    "venice": (
        "The water taxi from Fusina threads the lagoon as dawn firms up behind the campaniles and "
        "the pink marble of the Doge's Palace emerges from morning mist — Venice arriving not like "
        "a city but like a revelation that has been waiting patiently. Your three nights at the "
        "Hilton Molino Stucky on Giudecca put you across the channel from San Marco: close enough "
        "to walk the sestieri easily, far enough to return each evening to a neighborhood that moves "
        "at a different, quieter tempo."
    ),
}


@router.get("")
async def get_itinerary(request: Request):
    get_email(request)
    return {
        "client_name": "Erik McLeod & Melissa McGlasson",
        "voyage_name": "Silver Muse — Mediterranean",
        "voyage_subtitle": "Rome · The Mediterranean · The Adriatic · Venice",
        "voyage_id": "SM260623010",
        "booking_ref": "298475-25",
        "ship": "Silver Muse",
        "cabin": "Suite 617 — Classic Veranda Suite · All-Suite, All-Inclusive",
        "embark_date": "2026-06-23",
        "disembark_date": "2026-07-03",
        "duration_nights": 11,
        "full_journey_days": 19,
        "full_journey_start": "2026-06-18",
        "route": "Civitavecchia → Naples → Sicily → Malta → Montenegro → Croatia → Venice",
        "welcome_narrative": (
            "Rome doesn't ease you in — it arrives all at once, every century simultaneously. "
            "You have four days here, entirely your own. You planned them, booked them, and know "
            "exactly how to spend them. What the Baglioni will do is hold you beautifully while you "
            "do it. When June 23 arrives and the driver pulls away from the hotel, you'll feel the "
            "city releasing you, unhurried, into something else entirely — the Silver Muse at "
            "Civitavecchia, and it has been worth every day of anticipation."
        ),
        "ship_credits": "$596 remaining (covers Kotor $318 + Dubrovnik $278)",
        "ports": [
            {
                "name": "Denver → Rome (FCO)",
                "date": "2026-06-18",
                "type": "pre-cruise",
                "subtitle": "Overnight flight",
                "notes": "United UA 177 · Erik: PNR ML237016 · Melissa: PNR TF317131 · Business Class · Seats 3D/3F · Overnight",
            },
            {
                "name": "Rome — Baglioni Hotel Regina",
                "date": "2026-06-19",
                "type": "pre-cruise",
                "subtitle": "Arrive FCO · Transfer to Via Veneto",
                "notes": "Welcome Pickups Order #w-6377007-2 · FCO Arrival Hall, NCC corner 1–4 · Baglioni Hotel Regina, Via V. Veneto 72 · Conf #6851SF075162 · Chase Luxury: breakfast daily, $100 property credit, welcome Prosecco, Wi-Fi",
                "narrative": (
                    "The Baglioni Regina is exactly the right place to shake off an overnight flight: "
                    "high ceilings, marble, the smell of lilies in the lobby. Via Veneto outside your "
                    "window is quieter than it was in Fellini's day, which is to say it is exactly as "
                    "it should be."
                ),
            },
            {
                "name": "Rome",
                "date": "2026-06-20",
                "type": "pre-cruise",
                "subtitle": "Colosseum, Roman Forum & Palatine Hill",
                "notes": "COLOSSEUM WITH ARENA FLOOR, ROMAN FORUM & PALATINE HILL · GetYourGuide · 10:00 AM · 3 hrs · $301.86 · Skip-the-line · Arena floor access included",
                "narrative": (
                    "The Arena Floor is what most tourists never see — you stand where the gladiators stood, "
                    "looking up at fifty thousand stone tiers. Then the Forum, then the Palatine, all in a "
                    "single morning that turns the rest of Rome into context rather than scenery."
                ),
            },
            {
                "name": "Florence (day trip from Rome)",
                "date": "2026-06-21",
                "type": "pre-cruise",
                "subtitle": "Frecciarossa to Florence — Uffizi, David & Gelato Walk",
                "notes": (
                    "TRENITALIA FRECCIAROSSA 8502 (Business Class) · 6:45 AM · Roma Termini → Firenze S.M.N. · 1h 45m · Train Ref JJQ6Z5 · "
                    "UFFIZI + MICHELANGELO'S DAVID + GELATO WALK WITH ART HISTORIAN · 9:30 AM · 3 hrs · GetYourGuide · Semi-private (max 9) · $257.96 · "
                    "TRENITALIA FRECCIAROSSA 9431 (Executive Class) · 6:45 PM return · Firenze S.M.N. → Roma Termini"
                ),
                "narrative": (
                    "A 6:45 AM Frecciarossa puts you in Florence before 9:00 — early enough to reach the "
                    "Uffizi before the heat and the crowds thicken. An art historian leads a semi-private "
                    "group of nine through both the Uffizi and the Accademia (Michelangelo's David), then "
                    "the gelato walk through the streets Brunelleschi built. The 6:45 PM Executive-class "
                    "train returns you to Rome in time for a late dinner."
                ),
            },
            {
                "name": "Rome",
                "date": "2026-06-22",
                "type": "pre-cruise",
                "subtitle": "Vatican Museums, Sistine Chapel & St. Peter's Dome Climb",
                "notes": (
                    "VATICAN MUSEUMS, SISTINE CHAPEL & ST. PETER'S BASILICA WITH DOME CLIMB · GetYourGuide · "
                    "8:30 AM · 4 hrs · $766.84 · Skip-the-line · 551-step dome climb included · "
                    "Transfer to Civitavecchia departs Jun 23 at 10:00 · Order #w-6377007-1 · Driver at hotel entrance"
                ),
                "narrative": (
                    "The Dome Climb is the move: 551 steps, no elevator, and a view of Rome from the top "
                    "of St. Peter's that makes everything worthwhile. The Vatican Museums first — the Sistine "
                    "Chapel, the spiral staircase, the Gallery of Maps — then the Basilica, then the dome "
                    "while your legs are still willing. Last evening in Rome; driver at the hotel entrance "
                    "tomorrow at 10:00 for Civitavecchia."
                ),
            },
            {
                "name": "Civitavecchia (Rome) — Embarkation",
                "date": "2026-06-23",
                "type": "embark",
                "subtitle": "Rome releases you to the sea",
                "excursion": None,
                "notes": "Welcome Pickups Order #w-6377007-1 · Hotel → Civitavecchia Port · Embarkation Day · Booking 298475-25",
                "narrative": NARRATIVES["civitavecchia"],
            },
            {
                "name": "Naples, Italy",
                "date": "2026-06-24",
                "type": "port",
                "subtitle": "Naples & Herculaneum",
                "excursion": {
                    "name": "Ruins of Herculaneum",
                    "depart": "08:45",
                    "duration": "3.5 hrs",
                    "cost": "Included",
                    "booked": True,
                },
                "notes": "RUINS OF HERCULANEUM · Depart 08:45 · 3.5 hrs · Included\nLA DAME · 19:30 · $120 (2 pax) · Birthday Dinner for Erik",
                "narrative": NARRATIVES["naples"],
            },
            {
                "name": "Giardini Naxos, Sicily",
                "date": "2026-06-25",
                "type": "port",
                "subtitle": "Taormina & Mount Etna",
                "excursion": {
                    "name": "Greek & Roman Taormina",
                    "depart": "09:30",
                    "duration": "4 hrs",
                    "cost": "Included",
                    "booked": True,
                },
                "notes": "GREEK & ROMAN TAORMINA · Depart 09:30 · 4 hrs · Included",
                "narrative": NARRATIVES["giardini_naxos"],
            },
            {
                "name": "Siracusa (Syracuse), Sicily",
                "date": "2026-06-26",
                "type": "port",
                "subtitle": "Baroque Noto & the Greek City of the West",
                "excursion": {
                    "name": "Baroque Town of Noto",
                    "depart": "08:45",
                    "duration": "3.5 hrs",
                    "cost": "Included",
                    "booked": True,
                },
                "notes": "BAROQUE TOWN OF NOTO · Depart 08:45 · 3.5 hrs · Included · UNESCO World Heritage",
                "narrative": NARRATIVES["siracusa"],
            },
            {
                "name": "Valletta, Malta",
                "date": "2026-06-27",
                "type": "port",
                "subtitle": "Honey limestone, Game of Thrones, and the Grand Harbour",
                "excursion": {
                    "name": "Game of Thrones Filming Locations",
                    "depart": "09:15",
                    "duration": "4 hrs",
                    "cost": "Included",
                    "booked": True,
                },
                "notes": "GAME OF THRONES FILMING LOCATIONS · Depart 09:15 · 4 hrs · Included",
                "narrative": NARRATIVES["valletta"],
            },
            {
                "name": "Day at Sea — Adriatic Crossing",
                "date": "2026-06-28",
                "type": "sea",
                "subtitle": "The Adriatic at Midpassage",
                "excursion": None,
                "notes": "Crossing toward Montenegro",
                "narrative": NARRATIVES["sea_adriatic"],
            },
            {
                "name": "Kotor, Montenegro",
                "date": "2026-06-29",
                "type": "port",
                "subtitle": "Blue Cave Speedboat Adventure",
                "excursion": {
                    "name": "Speedboat Adventure to Blue Cave",
                    "depart": "08:30",
                    "duration": "4 hrs",
                    "cost": "$318 booked",
                    "booked": True,
                },
                "notes": "SPEEDBOAT ADVENTURE TO BLUE CAVE · Depart 08:30 · 4 hrs · $318 booked",
                "narrative": NARRATIVES["kotor"],
            },
            {
                "name": "Dubrovnik, Croatia",
                "date": "2026-06-30",
                "type": "port",
                "subtitle": "A Day at the Beach Club",
                "excursion": {
                    "name": "Day at the Beach Club",
                    "depart": "09:00",
                    "duration": "5 hrs",
                    "cost": "$278 booked",
                    "booked": True,
                },
                "notes": "DAY AT THE BEACH CLUB · Depart 09:00 · 5 hrs · $278 booked",
                "narrative": NARRATIVES["dubrovnik"],
            },
            {
                "name": "Split, Croatia",
                "date": "2026-07-01",
                "type": "port",
                "subtitle": "Diocletian's Living Palace",
                "excursion": {
                    "name": "UNESCO World Heritage Sites",
                    "depart": "08:45",
                    "duration": "4.5 hrs",
                    "cost": "Included",
                    "booked": True,
                },
                "notes": "UNESCO WORLD HERITAGE SITES · Depart 08:45 · 4.5 hrs · Included",
                "narrative": NARRATIVES["split"],
            },
            {
                "name": "Zadar, Croatia",
                "date": "2026-07-02",
                "type": "port",
                "subtitle": "Salt works, royal vineyards, and a sea that plays music",
                "excursion": {
                    "name": "Zadar, Nin Salt Works & Royal Vineyards",
                    "depart": "08:45",
                    "duration": "5 hrs",
                    "cost": "Included",
                    "booked": True,
                },
                "notes": "ZADAR, NIN SALT WORKS & ROYAL VINEYARDS · Depart 08:45 · 5 hrs · Included",
                "narrative": NARRATIVES["zadar"],
            },
            {
                "name": "Fusina (Venice) — Disembarkation",
                "date": "2026-07-03",
                "type": "disembark",
                "subtitle": "Arriving in Venice",
                "excursion": None,
                "notes": "Venice Guide & Boat — Private Water Taxi & Guide · Order #14878 · 09:30 · €350 PAID · Fusina → Hilton Molino Stucky, Giudecca Island",
                "narrative": NARRATIVES["venice"],
            },
            {
                "name": "Venice — Hilton Molino Stucky",
                "date": "2026-07-03",
                "type": "post-cruise",
                "subtitle": "Giudecca Island · 3 nights",
                "notes": "3 nights · Skyline Rooftop Bar · Trattoria Altanella for dinner (Giudecca, cash only, legendary fritto misto)",
                "narrative": (
                    "Giudecca puts you across the channel from San Marco — close enough to walk the "
                    "sestieri easily, far enough to return each evening to a neighborhood that moves "
                    "at a different, quieter tempo. Dinner at Trattoria Altanella tonight: old-school "
                    "Venetian, cash only, legendary fritto misto."
                ),
            },
            {
                "name": "Venice",
                "date": "2026-07-04",
                "type": "post-cruise",
                "subtitle": "Cannaregio, the Frari, aperitivo hour",
                "notes": "Bacaro crawl through Cannaregio · Campo Santa Margherita at aperitivo hour · The Frari church and the Accademia · A gondola if the mood takes you",
            },
            {
                "name": "Venice",
                "date": "2026-07-05",
                "type": "post-cruise",
                "subtitle": "Final evening in La Serenissima",
                "notes": (
                    "Your last evening in Venice — make it count. "
                    "Seafood dining options: Osteria Alle Testiere (Castello, 22 seats, try walk-in at 6 PM) · "
                    "Trattoria Altanella (Giudecca, 5 min walk from hotel, cash only) · "
                    "Zanze XVI (Cannaregio, local neighborhood gem, same-day reservation)"
                ),
            },
            {
                "name": "Venice (VCE) → Denver (DEN)",
                "date": "2026-07-06",
                "type": "post-cruise",
                "subtitle": "Homeward",
                "notes": "Air Canada AC 817 (VCE→YYZ · seats 3A/4A) + AC 1041 (YYZ→DEN · seats 2A/2C) · Business Class · PNRs: H1PY618 (Erik) / N6TX610 (Melissa)",
            },
        ],
    }

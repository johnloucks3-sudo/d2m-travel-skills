"""
D2M Dani Proposal — Data Schema + PDF Renderer
===============================================
Dataclasses that feed dani_proposal.html.j2, plus one-call render functions.

All currency must be pre-formatted as strings via fmt_usd() — NEVER format
inside templates. Photos as base64 data URIs.

Usage:
    from d2m_proposal_schema import ProposalContext, render_to_pdf

    ctx = ProposalContext(
        meta=ProposalMeta(
            client_name="Nancy & Ken Lyons",
            destination="Athens, Greece",
            travel_dates="August 8–12, 2026",
            nights=4,
            guests=2,
        ),
        summary=(
            "Athens is one of those rare cities that rewards the unhurried traveler — "
            "and Nancy, I have a feeling you and Ken are exactly that. I've built this "
            "proposal around the rhythms of the city: mornings at the Acropolis before "
            "the crowds arrive, afternoons lost in the Plaka, and evenings on a rooftop "
            "with a view that will stay with you long after you're home."
        ),
        destination=DestinationOverview(
            description="Athens...",
            highlights=["The Acropolis at sunrise", "Plaka neighborhood dining"],
            best_season="April – June / September – October",
            weather_note="August is warm (84°F avg) and sunny — arrive early to beat the heat.",
        ),
        accommodations=[AccommodationOption(name="Hotel Grande Bretagne", ...)],
        excursions=[ExcursionHighlight(name="Private Acropolis at Dawn", ...)],
        itinerary=[ItineraryDay(day_number=1, title="Arrive & Settle In", ...)],
        pricing=PricingSummary(
            per_person="$4,250",
            total="$8,500",
            included=["4 nights accommodation", "Daily breakfast", "Private airport transfer"],
            not_included=["International airfare", "Personal spending", "Travel insurance"],
        ),
    )
    render_to_pdf(ctx, "output/Lyons_Athens_Aug2026_Proposal.pdf")
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class ProposalMeta:
    """Cover page metadata — client identity and trip vitals."""
    client_name: str                    # e.g., "Nancy & Ken Lyons"
    destination: str                    # e.g., "Athens, Greece"
    travel_dates: str = ""              # e.g., "August 8–12, 2026"
    nights: int = 0                     # e.g., 4
    guests: int = 0                     # e.g., 2
    hero_image: str = ""                # base64 data URI — destination hero photo
    tagline: str = ""                   # e.g., "Your journey awaits." (blank = default)
    prepared_date: str = ""             # Auto-filled if blank


@dataclass
class DestinationOverview:
    """Destination context — why here, why now."""
    description: str                    # 2-4 sentences, warm and evocative
    highlights: list[str] = field(default_factory=list)   # "Why you'll love it" bullets
    best_season: str = ""               # e.g., "April – June / September – October"
    weather_note: str = ""              # Brief weather context with numbers


@dataclass
class PriceBox:
    """Compact price display for accommodation cards."""
    label: str = "From"                 # e.g., "From", "Our Rate", "Starting at"
    amount: str = ""                    # Pre-formatted via fmt_usd(): "$1,800"
    per_night: str = ""                 # e.g., "$450/night · 4 nights"
    prestige: bool = False              # Purple tier for over-budget / ultra-luxury


@dataclass
class AccommodationOption:
    """One hotel/resort option in the accommodations section."""
    name: str
    description: str = ""              # 2-3 sentences — atmosphere, standout features
    photos: list[str] = field(default_factory=list)  # base64 data URIs; index 0 = main
    price_box: Optional[PriceBox] = None
    recommendation_note: str = ""      # Dani's personal note — shows "Our Pick" ribbon


@dataclass
class ExcursionHighlight:
    """One curated experience in the excursions section."""
    name: str
    description: str = ""              # 1-2 sentences — what makes it special
    photo: str = ""                    # base64 data URI
    duration: str = ""                 # e.g., "Half Day", "3 hours", "Full Day"
    price: str = ""                    # Pre-formatted via fmt_usd(): "$175/person"
    category: str = ""                 # e.g., "Culinary", "History", "Adventure", "Wellness"
    category_icon: str = "✦"           # Emoji fallback when no photo


@dataclass
class ItineraryDay:
    """One day in the day-by-day itinerary preview."""
    day_number: int
    title: str                         # e.g., "Arrive & Settle In", "Morning at the Acropolis"
    description: str = ""             # 1-2 sentences on the day's feel and flow
    highlights: list[str] = field(default_factory=list)  # Activity pills: ["Breakfast", "Cooking Class"]


@dataclass
class PricingSummary:
    """Investment summary — per-person, total, included/excluded."""
    per_person: str                    # Pre-formatted via fmt_usd(): "$4,250"
    total: str = ""                    # Pre-formatted via fmt_usd(): "$8,500"
    included: list[str] = field(default_factory=list)
    not_included: list[str] = field(default_factory=list)


@dataclass
class ProposalContext:
    """Top-level context object — everything the template needs."""
    meta: ProposalMeta
    summary: str = ""                  # Dani's executive narrative, 3-4 sentences
    destination: Optional[DestinationOverview] = None
    accommodations: list[AccommodationOption] = field(default_factory=list)
    excursions: list[ExcursionHighlight] = field(default_factory=list)
    itinerary: list[ItineraryDay] = field(default_factory=list)
    pricing: Optional[PricingSummary] = None


# ── Rendering ────────────────────────────────────────────────────────────────

TEMPLATE_DIR = Path(__file__).parent


def render_to_html(ctx: ProposalContext) -> str:
    """Render proposal context to an HTML string."""
    from jinja2 import Environment, FileSystemLoader

    if not ctx.meta.prepared_date:
        ctx.meta.prepared_date = date.today().strftime("%B %d, %Y")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
    )
    template = env.get_template("dani_proposal.html.j2")

    return template.render(
        meta=ctx.meta,
        summary=ctx.summary,
        destination=ctx.destination,
        accommodations=ctx.accommodations,
        excursions=ctx.excursions,
        itinerary=ctx.itinerary,
        pricing=ctx.pricing,
    )


def render_to_pdf(ctx: ProposalContext, output_path: str | Path) -> Path:
    """Render proposal context to PDF via WeasyPrint.

    Args:
        ctx: Fully populated ProposalContext.
        output_path: Destination path, e.g. "output/Lyons_Athens_Aug2026_Proposal.pdf"

    Returns:
        Path to the written PDF file.
    """
    from weasyprint import HTML

    html_content = render_to_html(ctx)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(str(output))
    return output

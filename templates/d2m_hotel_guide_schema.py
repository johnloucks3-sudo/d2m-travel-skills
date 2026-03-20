"""
D2M Hotel Guide — Data Schema + PDF Renderer
=============================================
Dataclasses that feed hotel_guide.html.j2, plus a one-call render_to_pdf().

Usage:
    from d2m_hotel_guide_schema import HotelGuideContext, render_to_pdf

    ctx = HotelGuideContext(
        doc=DocMeta(client_name="Nancy & Ken Lyons", destination="Athens", ...),
        hotels=[HotelCard(name="Hotel Grande Bretagne", ...)],
        comparison=[CompRow(feature="Location", values=["Syntagma", "Plaka"])],
        recommendations=[Recommendation(label="Best Value", hotel_name="...", reason="...")],
        logistics=Logistics(transport=[Transport(icon="🚕", mode="Taxi", detail="25 min from ATH")]),
    )
    render_to_pdf(ctx, "output/Lyons_Athens_Aug2026.pdf")
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class DocMeta:
    """Cover page metadata."""
    client_name: str
    destination: str
    travel_dates: str           # e.g., "August 8–12, 2026"
    nights: int
    guests: int
    budget: str = ""            # e.g., "$3,500" — pre-formatted via fmt_usd()
    prepared_date: str = ""     # Auto-filled if blank


@dataclass
class Badge:
    label: str                  # e.g., "Value", "Luxury"
    css_class: str = "experience"  # value | location | experience | luxury | local


@dataclass
class Landmark:
    name: str
    distance: str               # e.g., "0.2 mi", "5 min walk"
    nearest: bool = False       # Gold NEAREST badge


@dataclass
class RoomRate:
    room_type: str              # e.g., "Deluxe King"
    nightly: str                # Pre-formatted: "$450"
    total: str                  # Pre-formatted: "$1,800"
    includes: str = ""          # e.g., "Breakfast, WiFi"
    is_pick: bool = False       # Gold highlight row


@dataclass
class PriceBox:
    label: str = "From"         # e.g., "From", "Our Rate"
    amount: str = ""            # Pre-formatted: "$1,800"
    per_night: str = ""         # e.g., "$450/night for 4 nights"
    prestige: bool = False      # Purple tier for over-budget / 5-star


@dataclass
class Cancellation:
    text: str                   # e.g., "Free cancellation until July 1"
    cancel_class: str = "ok"    # ok (green) | no (red) | tbd (muted)


@dataclass
class HotelCard:
    name: str
    stars: int = 5
    neighborhood: str = ""
    description: str = ""
    photos: list[str] = field(default_factory=list)  # base64 data URIs
    badges: list[Badge] = field(default_factory=list)
    price_box: PriceBox = field(default_factory=PriceBox)
    rates: list[RoomRate] = field(default_factory=list)
    landmarks: list[Landmark] = field(default_factory=list)
    cancellation: Optional[Cancellation] = None


@dataclass
class CompRow:
    """One row in the comparison table."""
    feature: str                # e.g., "Location", "Price", "Cancellation"
    values: list[str] = field(default_factory=list)  # One per hotel
    cancel_class: str = ""      # ok | no | tbd — applies to all cells in row


@dataclass
class Recommendation:
    label: str                  # e.g., "Best Value", "Best Location"
    hotel_name: str
    reason: str


@dataclass
class Transport:
    icon: str                   # Emoji: "🚕", "🚇", "🚌"
    mode: str                   # "Taxi", "Metro", "Bus"
    detail: str                 # "25 min from ATH airport"
    cost: str = ""              # Pre-formatted: "$35"


@dataclass
class Logistics:
    transport: list[Transport] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    footnotes: list[str] = field(default_factory=list)


@dataclass
class HotelGuideContext:
    """Top-level context object for the hotel guide template."""
    doc: DocMeta
    hotels: list[HotelCard] = field(default_factory=list)
    comparison: list[CompRow] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    logistics: Optional[Logistics] = None


# ── Rendering ────────────────────────────────────────────────────────────────

TEMPLATE_DIR = Path(__file__).parent


def render_to_html(ctx: HotelGuideContext) -> str:
    """Render hotel guide context to HTML string."""
    from jinja2 import Environment, FileSystemLoader

    if not ctx.doc.prepared_date:
        ctx.doc.prepared_date = date.today().strftime("%B %d, %Y")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
    )
    template = env.get_template("hotel_guide.html.j2")

    return template.render(
        doc=ctx.doc,
        hotels=ctx.hotels,
        comparison=ctx.comparison,
        recommendations=ctx.recommendations,
        logistics=ctx.logistics,
    )


def render_to_pdf(ctx: HotelGuideContext, output_path: str | Path) -> Path:
    """Render hotel guide context to PDF via WeasyPrint."""
    from weasyprint import HTML

    html_content = render_to_html(ctx)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(str(output))
    return output

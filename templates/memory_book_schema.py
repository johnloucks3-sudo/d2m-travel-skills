"""
D2M Post-Voyage Memory Book — Data Schema + PDF/HTML Renderer
================================================================
Dataclasses that feed memory_book.html.j2, plus render_to_pdf() / render_to_html().

Mirrors the pattern in templates/d2m_hotel_guide_schema.py.

Usage:
    from templates.memory_book_schema import MemoryBookContext, CoverMeta, PhotoPage, render_to_pdf

    ctx = MemoryBookContext(
        cover=CoverMeta(client_name="Erik McLeod & Melissa McGlasson", ship_name="Silver Muse",
                        voyage_name="Mediterranean", voyage_dates="June 23 - July 6, 2026"),
        pages=[PhotoPage(section_title="Departure", photos=[...])],
    )
    render_to_pdf(ctx, "output/memory_book_3096289.pdf")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class CoverMeta:
    """Cover page metadata."""
    client_name: str
    ship_name: str
    voyage_name: str
    voyage_dates: str            # e.g., "June 23 - July 6, 2026"
    booking_id: str = ""
    prepared_date: str = ""      # Auto-filled if blank


@dataclass
class PhotoCaption:
    """One curated photo, ready to embed."""
    data_uri: str                # base64 data URI (image bytes already fetched)
    caption: str = ""            # e.g., "Santorini — June 27"
    category: str = ""           # scenic | group | dining | other


@dataclass
class PhotoPage:
    """One section of the book — a port day, an event, a theme."""
    section_title: str           # e.g., "Santorini, Greece — Day 4"
    photos: list[PhotoCaption] = field(default_factory=list)
    note: str = ""               # optional short narrative line under the title


@dataclass
class MemoryBookContext:
    """Top-level context object for the memory book template."""
    cover: CoverMeta
    pages: list[PhotoPage] = field(default_factory=list)
    closing_note: str = "Thank you for letting us plan this voyage. — Dreams2Memories Travel"


# ── Rendering ────────────────────────────────────────────────────────────────

TEMPLATE_DIR = Path(__file__).parent


def render_to_html(ctx: MemoryBookContext) -> str:
    """Render memory book context to HTML string (also used as the interactive digital copy)."""
    from jinja2 import Environment, FileSystemLoader

    if not ctx.cover.prepared_date:
        ctx.cover.prepared_date = date.today().strftime("%B %d, %Y")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
    )
    template = env.get_template("memory_book.html.j2")

    return template.render(
        cover=ctx.cover,
        pages=ctx.pages,
        closing_note=ctx.closing_note,
    )


def render_to_interactive_html(ctx: MemoryBookContext, output_path: str | Path) -> Path:
    """Render the client-facing digital copy (CSS-only lightbox, no JS) and write to disk."""
    from jinja2 import Environment, FileSystemLoader

    if not ctx.cover.prepared_date:
        ctx.cover.prepared_date = date.today().strftime("%B %d, %Y")

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    template = env.get_template("memory_book_interactive.html.j2")
    html_content = template.render(cover=ctx.cover, pages=ctx.pages, closing_note=ctx.closing_note)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_content, encoding="utf-8")
    return output


def render_to_pdf(ctx: MemoryBookContext, output_path: str | Path) -> Path:
    """Render memory book context to PDF via WeasyPrint."""
    from weasyprint import HTML

    html_content = render_to_html(ctx)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    HTML(string=html_content, base_url=str(TEMPLATE_DIR)).write_pdf(str(output))
    return output

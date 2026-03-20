"""
Thunderbird Dining Curation Module
====================================

Curates restaurant and dining experience proposals for D2M clients.

Pipeline:
  1. Research — Web search for top restaurants at a destination
  2. Curate — Filter by cuisine, price, Michelin status, proximity
  3. Cache — Save images to ~/Thunderbird/restaurant_images/
  4. Render — HTML -> PDF with D2M branding
  5. Deliver — Gmail draft with logo signature -> Drive archive

Usage:
  MCP tools: dining_research, dining_render_proposal
  CLI: python3 thunderbird_dining.py --research "Stockholm" --cuisine "Nordic,Seafood"
"""

import base64
import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
from jinja2 import Template

logger = logging.getLogger(__name__)

THUNDERBIRD_DIR = Path.home() / "Thunderbird"
IMAGE_CACHE = THUNDERBIRD_DIR / "restaurant_images"
OUTPUT_DIR = THUNDERBIRD_DIR / "output"
LOGO_PATH = THUNDERBIRD_DIR / "Agency_Logo.png"
HEADSHOT_PATH = THUNDERBIRD_DIR / "John_Headshot.jpg"

# LLM calls — routed through Claude Opus ($0 on Max plan)
# Groq eliminated per standing order 2026-03-17

IMAGE_CACHE.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _groq_call(system: str, user: str, max_tokens: int = 2000) -> str:
    """Call Claude Opus via Anthropic SDK. Name kept for backward compat."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


def _img_to_base64(path: Path) -> str:
    """Convert image file to base64 data URI."""
    if not path.exists():
        return ""
    suffix = path.suffix.lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(suffix, "image/jpeg")
    data = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def _cache_image(url: str, dest_name: str) -> Optional[Path]:
    """Download and cache an image. Returns cached path or None."""
    safe_name = re.sub(r'[^\w\-.]', '_', dest_name)
    cached = IMAGE_CACHE / safe_name
    if cached.exists():
        return cached

    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"
        })
        if resp.status_code == 200 and len(resp.content) > 1000:
            cached.write_bytes(resp.content)
            logger.info(f"Cached image: {safe_name}")
            return cached
    except Exception as e:
        logger.warning(f"Image cache failed for {url}: {e}")
    return None


def research_restaurants(
    destination: str,
    cuisine_types: Optional[List[str]] = None,
    price_range: str = "moderate to upscale",
    count: int = 6,
    context: str = "",
) -> Dict[str, Any]:
    """Research top restaurants for a destination using Groq.

    Returns structured restaurant data ready for rendering.
    """
    cuisine_str = ", ".join(cuisine_types) if cuisine_types else "local specialties, fine dining"

    system_prompt = """You are a luxury travel dining curator for Dreams2Memories Travel, LLC.
Your job is to recommend real, currently-operating restaurants for travelers.

RULES:
- Only recommend REAL restaurants that actually exist. Never fabricate.
- Include Michelin-starred options if available at the destination.
- Mix price ranges: 1-2 splurge, 2-3 mid-range gems, 1-2 casual/local favorites.
- For each restaurant, provide the Google Maps-searchable name and address.
- Note any reservation requirements or dress codes.

Respond in JSON format ONLY. No markdown, no explanation."""

    user_prompt = f"""Recommend {count} restaurants in {destination}.

Cuisine preferences: {cuisine_str}
Price range: {price_range}
{f"Additional context: {context}" if context else ""}

Return a JSON array where each item has:
{{
  "name": "Restaurant Name",
  "cuisine": "Italian, Seafood",
  "price_level": "$$$",
  "michelin": "1 star" or null,
  "address": "Full address",
  "neighborhood": "Area name",
  "why": "One sentence on why this is special",
  "signature_dish": "Their most famous dish",
  "reservation": "Required" or "Recommended" or "Walk-in OK",
  "dress_code": "Smart casual" or null,
  "hours_note": "Closed Sundays" or null,
  "website": "URL if known" or null
}}"""

    try:
        raw = _groq_call(system_prompt, user_prompt)
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', raw, re.DOTALL)
        if json_match:
            restaurants = json.loads(json_match.group())
        else:
            restaurants = json.loads(raw)

        return {
            "status": "success",
            "destination": destination,
            "cuisine_filter": cuisine_str,
            "count": len(restaurants),
            "restaurants": restaurants,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse restaurant JSON: {e}")
        return {"status": "error", "message": f"JSON parse error: {e}", "raw": raw[:500]}
    except Exception as e:
        logger.error(f"Restaurant research failed: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# PDF TEMPLATE
# ============================================================================

DINING_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page { size: letter; margin: 0.6in; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Georgia', 'Times New Roman', serif;
    color: #1a1a2e;
    background: #fff;
    line-height: 1.5;
  }

  .cover {
    text-align: center;
    padding: 60px 40px;
    background: linear-gradient(135deg, #0d1b2e 0%, #1e3358 100%);
    color: #fff;
    border-radius: 8px;
    margin-bottom: 30px;
  }
  .cover img.logo {
    width: 120px;
    margin-bottom: 20px;
  }
  .cover h1 {
    font-size: 28px;
    color: #c9a84c;
    margin-bottom: 8px;
    letter-spacing: 1px;
  }
  .cover h2 {
    font-size: 18px;
    font-weight: 400;
    color: #e8c97a;
    margin-bottom: 6px;
  }
  .cover .meta {
    font-size: 13px;
    color: #8a9ab5;
    margin-top: 15px;
  }

  .restaurant-card {
    border: 1px solid #e0d8c8;
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 20px;
    page-break-inside: avoid;
    background: #fdfcfa;
  }
  .restaurant-card h3 {
    font-size: 18px;
    color: #0d1b2e;
    margin-bottom: 4px;
  }
  .restaurant-card .cuisine-tag {
    display: inline-block;
    background: #c9a84c;
    color: #0d1b2e;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 3px;
    font-weight: 600;
    margin-right: 6px;
    margin-bottom: 8px;
  }
  .restaurant-card .michelin {
    display: inline-block;
    background: #b91c1c;
    color: #fff;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 3px;
    font-weight: 600;
    margin-bottom: 8px;
  }
  .restaurant-card .price {
    display: inline-block;
    color: #c9a84c;
    font-size: 14px;
    font-weight: 700;
    margin-left: 8px;
  }
  .restaurant-card .why {
    font-style: italic;
    color: #4a5568;
    margin: 8px 0;
    font-size: 14px;
  }
  .restaurant-card .details {
    font-size: 13px;
    color: #555;
    margin-top: 8px;
  }
  .restaurant-card .details span {
    display: inline-block;
    margin-right: 16px;
  }
  .restaurant-card .signature {
    margin-top: 6px;
    font-size: 13px;
    color: #0d1b2e;
  }
  .restaurant-card .signature strong {
    color: #c9a84c;
  }

  .footer {
    text-align: center;
    padding: 20px;
    font-size: 12px;
    color: #8a9ab5;
    border-top: 1px solid #e0d8c8;
    margin-top: 30px;
  }
  .footer img {
    width: 40px;
    border-radius: 50%;
    vertical-align: middle;
    margin-right: 8px;
  }
</style>
</head>
<body>

<div class="cover">
  {% if logo_b64 %}<img class="logo" src="{{ logo_b64 }}" alt="D2M Logo">{% endif %}
  <h1>Dining Guide</h1>
  <h2>{{ destination }}</h2>
  {% if client_name %}<h2>Curated for {{ client_name }}</h2>{% endif %}
  <div class="meta">{{ date }} &bull; Dreams2Memories Travel, LLC</div>
</div>

{% for r in restaurants %}
<div class="restaurant-card">
  <h3>{{ r.name }} <span class="price">{{ r.price_level }}</span></h3>
  <span class="cuisine-tag">{{ r.cuisine }}</span>
  {% if r.michelin %}<span class="michelin">{{ r.michelin }}</span>{% endif %}
  <div class="why">"{{ r.why }}"</div>
  {% if r.signature_dish %}
  <div class="signature"><strong>Must-try:</strong> {{ r.signature_dish }}</div>
  {% endif %}
  <div class="details">
    <span>{{ r.neighborhood }}</span>
    <span>{{ r.reservation }}</span>
    {% if r.dress_code %}<span>{{ r.dress_code }}</span>{% endif %}
    {% if r.hours_note %}<span>{{ r.hours_note }}</span>{% endif %}
  </div>
  {% if r.address %}
  <div class="details" style="margin-top: 4px; font-size: 12px; color: #888;">{{ r.address }}</div>
  {% endif %}
</div>
{% endfor %}

<div class="footer">
  {% if headshot_b64 %}<img src="{{ headshot_b64 }}" alt="John">{% endif %}
  John A Loucks III &bull; Dreams2Memories Travel, LLC &bull; 719-291-0742 &bull; johnloucks3@gmail.com
</div>

</body>
</html>"""


def render_dining_pdf(
    destination: str,
    restaurants: List[Dict],
    client_name: str = "",
    output_filename: str = "",
) -> Dict[str, Any]:
    """Render a dining guide PDF from restaurant data.

    Returns path to generated PDF.
    """
    from weasyprint import HTML

    if not output_filename:
        safe_dest = re.sub(r'[^\w]', '_', destination)
        safe_client = re.sub(r'[^\w]', '_', client_name) if client_name else "General"
        output_filename = f"{safe_client}_{safe_dest}_Dining_{datetime.now().strftime('%b%Y')}.pdf"

    output_path = OUTPUT_DIR / output_filename

    # Load branding
    logo_b64 = _img_to_base64(LOGO_PATH) if LOGO_PATH.exists() else ""
    headshot_b64 = _img_to_base64(HEADSHOT_PATH) if HEADSHOT_PATH.exists() else ""

    template = Template(DINING_TEMPLATE)
    html_str = template.render(
        destination=destination,
        client_name=client_name,
        restaurants=restaurants,
        date=datetime.now().strftime("%B %d, %Y"),
        logo_b64=logo_b64,
        headshot_b64=headshot_b64,
    )

    HTML(string=html_str).write_pdf(str(output_path))
    logger.info(f"Dining PDF rendered: {output_path}")

    return {
        "status": "success",
        "pdf_path": str(output_path),
        "filename": output_filename,
        "restaurant_count": len(restaurants),
        "destination": destination,
        "client": client_name,
    }


# ============================================================================
# MCP TOOL REGISTRATION
# ============================================================================

def register_dining_tools(mcp_server):
    """Register dining curation MCP tools."""
    from pydantic import Field

    @mcp_server.tool(
        name="dining_research",
        annotations={"title": "Research Restaurants for Destination", "readOnlyHint": True},
    )
    async def dining_research_tool(
        destination: str = Field(..., description="City or port name (e.g., 'Stockholm', 'Venice', 'Tokyo')"),
        cuisine_types: str = Field("", description="Comma-separated cuisine preferences (e.g., 'Nordic,Seafood,Fine Dining')"),
        price_range: str = Field("moderate to upscale", description="Price range preference"),
        count: int = Field(6, description="Number of restaurants to recommend (3-10)"),
        context: str = Field("", description="Additional context (e.g., 'anniversary dinner', 'family with kids', 'near cruise port')"),
    ) -> str:
        """Research and curate top restaurants for a travel destination.

        Returns structured restaurant data with Michelin status, signature dishes,
        reservation requirements, and neighborhood info.
        """
        cuisines = [c.strip() for c in cuisine_types.split(",")] if cuisine_types else None
        count = max(3, min(count, 10))
        result = research_restaurants(destination, cuisines, price_range, count, context)
        return json.dumps(result, indent=2)

    @mcp_server.tool(
        name="dining_render_proposal",
        annotations={"title": "Render Dining Guide PDF", "readOnlyHint": False},
    )
    async def dining_render_proposal_tool(
        destination: str = Field(..., description="Destination city"),
        restaurants_json: str = Field(..., description="JSON array of restaurant objects (from dining_research)"),
        client_name: str = Field("", description="Client name for personalization"),
        output_filename: str = Field("", description="Custom filename (default: auto-generated)"),
    ) -> str:
        """Render a branded D2M Dining Guide PDF from restaurant data.

        Use dining_research first to get restaurant data, then pass it here to render.
        Output goes to ~/Thunderbird/output/.
        """
        try:
            restaurants = json.loads(restaurants_json)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON in restaurants_json"})

        result = render_dining_pdf(destination, restaurants, client_name, output_filename)
        return json.dumps(result, indent=2)

    logger.info("Dining curation tools registered (dining_research, dining_render_proposal)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if "--research" in sys.argv:
        idx = sys.argv.index("--research")
        dest = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "Stockholm"
        cuisines = None
        if "--cuisine" in sys.argv:
            cidx = sys.argv.index("--cuisine")
            cuisines = [c.strip() for c in sys.argv[cidx + 1].split(",")]

        print(f"Researching restaurants in {dest}...", file=sys.stderr)
        result = research_restaurants(dest, cuisines)
        print(json.dumps(result, indent=2))

    elif "--render" in sys.argv:
        # Expects JSON on stdin
        import sys as _sys
        data = json.load(_sys.stdin)
        result = render_dining_pdf(
            data["destination"],
            data["restaurants"],
            data.get("client_name", ""),
        )
        print(json.dumps(result, indent=2))

    else:
        print("Usage:", file=sys.stderr)
        print("  python3 thunderbird_dining.py --research 'Stockholm' --cuisine 'Nordic,Seafood'", file=sys.stderr)
        print("  echo '{...}' | python3 thunderbird_dining.py --render", file=sys.stderr)

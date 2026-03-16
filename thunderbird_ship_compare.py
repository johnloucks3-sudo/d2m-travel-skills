"""
Dreams2Memories Ship Comparison MCP Module
===========================================

Generates professional head-to-head luxury cruise ship comparison reports:
- Side-by-side specifications (space ratios, amenities, suites)
- Pricing analysis
- Upcoming voyage comparisons
- Client reviews and testimonials
- Executive summary with recommendations

Output formats: DOCX + PDF
Integrates with: travel_mcp_server.py
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from jinja2 import Template
import weasyprint

# ============================================================================
# CONFIGURATION
# ============================================================================

class ComparisonConfig:
    """Configuration for ship comparison reports"""
    
    # Output paths
    OUTPUT_DIR = Path.home() / "Documents" / "Luxury_Itineraries" / "Ship_Comparisons"
    SHIP_DATABASE_PATH = Path(__file__).parent / "ship_database.json"
    
    # Branding
    COMPANY_NAME = "Dreams2Memories Travel"
    COMPANY_WEBSITE = "www.d2mtravel.luxury"
    COMPANY_EMAIL = "johnloucks3@gmail.com"
    COMPANY_PHONE = "(719) 291-0742"
    AGENT_NAME = "John Loucks"
    
    # Brand Colors (Dreams2Memories/Love Group Travel)
    PRIMARY_COLOR = RGBColor(31, 71, 136)  # #1f4788 (Navy Blue)
    SECONDARY_COLOR = RGBColor(102, 102, 102)  # #666666 (Gray)
    ACCENT_COLOR = RGBColor(53, 92, 157)  # #355c9d (Lighter Blue)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# SHIP DATABASE (EMBEDDED)
# ============================================================================

SHIP_DATABASE = {
    "Silver Nova": {
        "line": "Silversea",
        "launched": 2023,
        "specs": {
            "gross_tonnage": 40700,
            "max_guests": 728,
            "suites": 364,
            "avg_suite_size": 29,
            "all_suites_balcony": True
        },
        "ratios": {
            "space_to_guest": 10.7,
            "crew_to_guest": "1:1.1",
            "crew_count": 656
        },
        "amenities": {
            "restaurants": 7,
            "bars": 6,
            "pools": 3,
            "spa_sq_ft": 5500,
            "design_feature": "Asymmetrical hull design maximizes cabin views"
        },
        "pricing": {
            "base_suite": 28500,
            "veranda": 32000,
            "owners_suite": 45000,
            "all_inclusive": True
        },
        "advantages": [
            "Highest space-to-guest ratio (10.7:1) among small luxury ships",
            "All-suite vessel—no inside cabins",
            "Asymmetrical hull design maximizes cabin views",
            "True all-inclusive pricing (spirits, wines, excursions)",
            "Butler service in all suites",
            "Newest ship in Silversea fleet (launched 2023)"
        ],
        "considerations": [
            "Premium pricing (starting $28,500 per person)",
            "Pool deck can feel crowded during sea days",
            "Smaller onboard entertainment options vs. mega-ships"
        ],
        "best_for": [
            "Guests seeking maximum space and privacy",
            "All-inclusive cruise experience seekers",
            "Explorers of remote destinations"
        ]
    },
    
    "Seven Seas Grandeur": {
        "line": "Regent Seven Seas Cruises",
        "launched": 2024,
        "specs": {
            "gross_tonnage": 54000,
            "max_guests": 750,
            "suites": 375,
            "avg_suite_size": 36,
            "all_suites_balcony": True
        },
        "ratios": {
            "space_to_guest": 12.7,
            "crew_to_guest": "1:1",
            "crew_count": 750
        },
        "amenities": {
            "restaurants": 8,
            "bars": 7,
            "pools": 2,
            "spa_sq_ft": 6500,
            "design_feature": "Fabergé partnership with exclusive Medallion Suite collection"
        },
        "pricing": {
            "base_suite": 42000,
            "veranda": 48000,
            "regent_suite": 85000,
            "all_inclusive": True
        },
        "advantages": [
            "Industry-leading space-to-guest ratio (12.7:1)",
            "Perfect 1:1 crew-to-guest ratio",
            "Fabergé Medallion Suite exclusivity",
            "Largest standard suites in luxury cruising (36 sq m minimum)",
            "Unlimited shore excursions included",
            "Free unlimited WiFi"
        ],
        "considerations": [
            "Ultra-premium pricing (starting $42,000 per person)",
            "Limited expedition capabilities vs. smaller ships",
            "Regent Suite availability extremely limited"
        ],
        "best_for": [
            "Guests prioritizing maximum space and luxury",
            "All-inclusive luxury with no hidden costs",
            "Medallion Suite collectors and Fabergé enthusiasts"
        ]
    },
    
    "World Navigator": {
        "line": "Atlas Ocean Voyages",
        "launched": 2021,
        "specs": {
            "gross_tonnage": 9300,
            "max_guests": 200,
            "suites": 100,
            "avg_suite_size": 22,
            "all_suites_balcony": True
        },
        "ratios": {
            "space_to_guest": "Polar Class",
            "crew_to_guest": "1:1.25",
            "crew_count": 160
        },
        "amenities": {
            "restaurants": 3,
            "bars": 2,
            "pools": 1,
            "expedition_features": ["Zodiac fleet", "Mudroom", "Polar expedition staff"]
        },
        "pricing": {
            "base_suite": 32000,
            "veranda": 36000,
            "owners_suite": 48000,
            "all_inclusive": True
        },
        "advantages": [
            "Polar Class expedition vessel",
            "Intimate size (200 guests) enables remote landings",
            "Complimentary cultural immersion excursions",
            "Expedition staff and naturalists included",
            "Zodiac operations for Arctic/Antarctic access"
        ],
        "considerations": [
            "Smaller suite sizes vs. ocean cruisers",
            "Limited onboard amenities (expedition focus)",
            "Weather-dependent itineraries"
        ],
        "best_for": [
            "Adventure travelers seeking remote destinations",
            "Guests prioritizing expedition experiences",
            "Arctic and Antarctic explorers"
        ]
    }
}

# ============================================================================
# DOCX GENERATION
# ============================================================================

def create_comparison_docx(ship1_name: str, ship2_name: str, output_path: Path) -> bool:
    """
    Generate professional DOCX comparison report
    
    Args:
        ship1_name: First ship to compare
        ship2_name: Second ship to compare
        output_path: Where to save the DOCX file
    
    Returns:
        True if successful, False otherwise
    """
    
    ship1 = SHIP_DATABASE.get(ship1_name)
    ship2 = SHIP_DATABASE.get(ship2_name)
    
    if not ship1 or not ship2:
        logger.error(f"Ship(s) not found in database: {ship1_name}, {ship2_name}")
        return False
    
    logger.info(f"📄 Generating comparison: {ship1_name} vs {ship2_name}")
    
    # Create document
    doc = Document()
    
    # Title
    title = doc.add_paragraph()
    title_run = title.add_run(f"{ship1_name} vs {ship2_name}")
    title_run.font.size = Pt(28)
    title_run.font.bold = True
    title_run.font.color.rgb = ComparisonConfig.PRIMARY_COLOR
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    
    # Subtitle
    subtitle = doc.add_paragraph()
    subtitle_run = subtitle.add_run("Comprehensive Luxury Cruise Ship Comparison Report")
    subtitle_run.font.size = Pt(14)
    subtitle_run.font.color.rgb = ComparisonConfig.SECONDARY_COLOR
    subtitle.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    
    doc.add_paragraph()  # Spacing
    
    # Executive Summary
    doc.add_heading("EXECUTIVE SUMMARY", level=1)
    summary = doc.add_paragraph()
    summary.add_run(
        f"{ship1_name} emphasizes {ship1['amenities']['design_feature'].lower()}, "
        f"while {ship2_name} focuses on {ship2['amenities']['design_feature'].lower()}. "
        f"{ship1_name} offers a {ship1['ratios']['space_to_guest']}:1 space-to-guest ratio with "
        f"{ship1['specs']['max_guests']} guests, compared to {ship2_name}'s "
        f"{ship2['ratios']['space_to_guest']}:1 ratio serving {ship2['specs']['max_guests']} guests."
    )
    
    doc.add_paragraph()
    
    # Comparison Table
    doc.add_heading("QUICK COMPARISON", level=1)
    
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Light Grid Accent 1'
    
    # Header row
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Metric'
    hdr_cells[1].text = ship1_name
    hdr_cells[2].text = ship2_name
    
    # Make header bold with brand color
    for cell in hdr_cells:
        cell.paragraphs[0].runs[0].font.bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        cell._element.get_or_add_tcPr().append(
            parse_xml(f'<w:shd w:fill="{ComparisonConfig.PRIMARY_COLOR.rgb}" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')
        )
    
    # Data rows
    metrics = [
        ("Max Guests", ship1['specs']['max_guests'], ship2['specs']['max_guests']),
        ("Space-to-Guest Ratio", f"{ship1['ratios']['space_to_guest']}:1", f"{ship2['ratios']['space_to_guest']}:1"),
        ("Average Suite Size", f"{ship1['specs']['avg_suite_size']} sq m", f"{ship2['specs']['avg_suite_size']} sq m"),
        ("Starting Price", f"${ship1['pricing']['base_suite']:,}", f"${ship2['pricing']['base_suite']:,}"),
        ("Crew-to-Guest Ratio", ship1['ratios']['crew_to_guest'], ship2['ratios']['crew_to_guest']),
        ("Number of Suites", ship1['specs']['suites'], ship2['specs']['suites'])
    ]
    
    for metric_name, val1, val2 in metrics:
        row = table.add_row().cells
        row[0].text = metric_name
        row[1].text = str(val1)
        row[2].text = str(val2)
    
    doc.add_paragraph()
    
    # Key Advantages Section
    doc.add_heading(f"{ship1_name.upper()} - KEY ADVANTAGES", level=1)
    for advantage in ship1['advantages']:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(advantage)
    
    doc.add_paragraph()
    
    doc.add_heading(f"{ship2_name.upper()} - KEY ADVANTAGES", level=1)
    for advantage in ship2['advantages']:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(advantage)
    
    doc.add_paragraph()
    
    # Considerations
    doc.add_heading(f"{ship1_name.upper()} - IMPORTANT CONSIDERATIONS", level=1)
    for consideration in ship1['considerations']:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(consideration)
    
    doc.add_paragraph()
    
    doc.add_heading(f"{ship2_name.upper()} - IMPORTANT CONSIDERATIONS", level=1)
    for consideration in ship2['considerations']:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(consideration)
    
    doc.add_paragraph()
    
    # Best For
    doc.add_heading("IDEAL PASSENGERS", level=1)
    
    doc.add_heading(ship1_name, level=2)
    for item in ship1['best_for']:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(item)
    
    doc.add_paragraph()
    
    doc.add_heading(ship2_name, level=2)
    for item in ship2['best_for']:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(item)
    
    doc.add_paragraph()
    
    # Conclusion
    doc.add_heading("CONCLUSION", level=1)
    conclusion = doc.add_paragraph()
    conclusion.add_run(
        f"Both {ship1_name} and {ship2_name} represent the pinnacle of luxury cruising, "
        f"each with distinct advantages. {ship1_name} excels in {ship1['amenities']['design_feature'].lower()}, "
        f"while {ship2_name} offers {ship2['amenities']['design_feature'].lower()}. "
        f"The choice ultimately depends on whether you prioritize {ship1_name}'s strengths or {ship2_name}'s offerings."
    )
    
    doc.add_paragraph()
    doc.add_paragraph()
    
    # Footer
    footer = doc.add_paragraph()
    footer_run = footer.add_run(
        f"Report generated by {ComparisonConfig.COMPANY_NAME}\n"
        f"For personalized recommendations: {ComparisonConfig.COMPANY_EMAIL} | {ComparisonConfig.COMPANY_PHONE}"
    )
    footer_run.font.size = Pt(10)
    footer_run.font.italic = True
    footer_run.font.color.rgb = ComparisonConfig.SECONDARY_COLOR
    footer.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    
    # Save document
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    logger.info(f"✅ DOCX saved: {output_path}")
    
    return True

def parse_xml(xml_str):
    """Helper to parse XML for table styling"""
    from lxml import etree
    return etree.fromstring(xml_str)

# ============================================================================
# PDF GENERATION (via WeasyPrint)
# ============================================================================

def generate_comparison_pdf(ship1_name: str, ship2_name: str, output_path: Path) -> bool:
    """
    Generate PDF comparison report using HTML + WeasyPrint
    
    Args:
        ship1_name: First ship to compare
        ship2_name: Second ship to compare
        output_path: Where to save the PDF
    
    Returns:
        True if successful
    """
    
    ship1 = SHIP_DATABASE.get(ship1_name)
    ship2 = SHIP_DATABASE.get(ship2_name)
    
    if not ship1 or not ship2:
        logger.error(f"Ship(s) not found: {ship1_name}, {ship2_name}")
        return False
    
    # HTML Template
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page { size: A4; margin: 1.5cm; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #333;
                line-height: 1.6;
            }
            h1 { 
                color: #1f4788;
                border-bottom: 3px solid #1f4788;
                padding-bottom: 10px;
            }
            h2 {
                color: #355c9d;
                margin-top: 30px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th {
                background-color: #1f4788;
                color: white;
                padding: 12px;
                text-align: left;
            }
            td {
                border: 1px solid #ddd;
                padding: 10px;
            }
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            ul {
                list-style-type: none;
                padding-left: 0;
            }
            li:before {
                content: "✓ ";
                color: #1f4788;
                font-weight: bold;
                margin-right: 8px;
            }
            .footer {
                text-align: center;
                font-size: 10pt;
                color: #666;
                margin-top: 50px;
                font-style: italic;
            }
        </style>
    </head>
    <body>
        <h1 style="text-align: center;">{{ ship1_name }} vs {{ ship2_name }}</h1>
        <p style="text-align: center; color: #666;">Comprehensive Luxury Cruise Ship Comparison</p>
        
        <h2>Quick Comparison</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>{{ ship1_name }}</th>
                <th>{{ ship2_name }}</th>
            </tr>
            <tr>
                <td>Max Guests</td>
                <td>{{ ship1.specs.max_guests }}</td>
                <td>{{ ship2.specs.max_guests }}</td>
            </tr>
            <tr>
                <td>Space-to-Guest Ratio</td>
                <td>{{ ship1.ratios.space_to_guest }}:1</td>
                <td>{{ ship2.ratios.space_to_guest }}:1</td>
            </tr>
            <tr>
                <td>Starting Price</td>
                <td>${{ "{:,}".format(ship1.pricing.base_suite) }}</td>
                <td>${{ "{:,}".format(ship2.pricing.base_suite) }}</td>
            </tr>
        </table>
        
        <h2>{{ ship1_name }} - Key Advantages</h2>
        <ul>
        {% for adv in ship1.advantages %}
            <li>{{ adv }}</li>
        {% endfor %}
        </ul>
        
        <h2>{{ ship2_name }} - Key Advantages</h2>
        <ul>
        {% for adv in ship2.advantages %}
            <li>{{ adv }}</li>
        {% endfor %}
        </ul>
        
        <div class="footer">
            Report generated by {{ company_name }}<br>
            {{ company_email }} | {{ company_phone }}
        </div>
    </body>
    </html>
    """
    
    # Render template
    template = Template(html_template)
    html_content = template.render(
        ship1_name=ship1_name,
        ship2_name=ship2_name,
        ship1=ship1,
        ship2=ship2,
        company_name=ComparisonConfig.COMPANY_NAME,
        company_email=ComparisonConfig.COMPANY_EMAIL,
        company_phone=ComparisonConfig.COMPANY_PHONE
    )
    
    # Generate PDF
    output_path.parent.mkdir(parents=True, exist_ok=True)
    weasyprint.HTML(string=html_content).write_pdf(output_path)
    logger.info(f"✅ PDF saved: {output_path}")
    
    return True

# ============================================================================
# MCP INTEGRATION
# ============================================================================

def register_comparison_tools(mcp_server: FastMCP):
    """Register ship comparison tools with MCP server"""
    
    @mcp_server.tool(
        name="generate_ship_comparison_docx",
        annotations={"title": "Generate Ship Comparison (DOCX)", "readOnlyHint": False}
    )
    async def tool_generate_comparison_docx(
        ship1: str = Field(..., description="First ship name (e.g., 'Silver Nova')"),
        ship2: str = Field(..., description="Second ship name (e.g., 'Seven Seas Grandeur')")
    ) -> str:
        """Generate professional DOCX comparison report"""
        
        output_filename = f"{ship1.replace(' ', '_')}_vs_{ship2.replace(' ', '_')}.docx"
        output_path = ComparisonConfig.OUTPUT_DIR / output_filename
        
        success = create_comparison_docx(ship1, ship2, output_path)
        
        if success:
            return json.dumps({
                "status": "success",
                "output_file": str(output_path),
                "format": "DOCX",
                "ships_compared": [ship1, ship2]
            }, indent=2)
        else:
            return json.dumps({"error": "Failed to generate comparison"})
    
    @mcp_server.tool(
        name="generate_ship_comparison_pdf",
        annotations={"title": "Generate Ship Comparison (PDF)", "readOnlyHint": False}
    )
    async def tool_generate_comparison_pdf(
        ship1: str = Field(..., description="First ship name"),
        ship2: str = Field(..., description="Second ship name")
    ) -> str:
        """Generate PDF comparison report"""
        
        output_filename = f"{ship1.replace(' ', '_')}_vs_{ship2.replace(' ', '_')}.pdf"
        output_path = ComparisonConfig.OUTPUT_DIR / output_filename
        
        success = generate_comparison_pdf(ship1, ship2, output_path)
        
        if success:
            return json.dumps({
                "status": "success",
                "output_file": str(output_path),
                "format": "PDF",
                "ships_compared": [ship1, ship2]
            }, indent=2)
        else:
            return json.dumps({"error": "Failed to generate PDF"})
    
    @mcp_server.tool(
        name="list_available_ships",
        annotations={"title": "List Available Ships for Comparison", "readOnlyHint": True}
    )
    async def tool_list_ships() -> str:
        """List all ships available in the comparison database"""
        ships = []
        for name, data in SHIP_DATABASE.items():
            ships.append({
                "name": name,
                "line": data['line'],
                "launched": data['launched'],
                "max_guests": data['specs']['max_guests'],
                "space_ratio": data['ratios']['space_to_guest']
            })
        return json.dumps({"available_ships": ships}, indent=2)
    
    logger.info("✅ Ship Comparison tools registered with MCP server")

# ============================================================================
# STANDALONE EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("DREAMS2MEMORIES SHIP COMPARISON MODULE")
    print("Standalone Test Mode")
    print("="*70)
    
    # Test comparison
    ComparisonConfig.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n📄 Generating DOCX: Silver Nova vs Seven Seas Grandeur...")
    docx_path = ComparisonConfig.OUTPUT_DIR / "Silver_Nova_vs_Seven_Seas_Grandeur.docx"
    create_comparison_docx("Silver Nova", "Seven Seas Grandeur", docx_path)
    
    print("\n📕 Generating PDF: Silver Nova vs Seven Seas Grandeur...")
    pdf_path = ComparisonConfig.OUTPUT_DIR / "Silver_Nova_vs_Seven_Seas_Grandeur.pdf"
    generate_comparison_pdf("Silver Nova", "Seven Seas Grandeur", pdf_path)
    
    print("\n✅ Test complete! Check output directory:")
    print(f"   {ComparisonConfig.OUTPUT_DIR}")

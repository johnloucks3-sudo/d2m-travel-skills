#!/usr/bin/env python3
"""
Visual Synthesis Data Layer — Generate data files for Canva + HTML dashboards
No external dependencies. JSON + HTML output.
"""

import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/home/john/Thunderbird/output/visuals")
OUTPUT_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────
# PHASE 1 DATA (from hale_brief.md + hale_state.json)
# ─────────────────────────────────────────────────────────────────────

PHASE1_DATA = {
    "timestamp": datetime.now().isoformat(),
    "clients": [
        {"name": "Lyons", "phase": "Pre-booking", "fpd_days": 13, "commission": 8500, "urgency": "red", "fpd_date": "May 11"},
        {"name": "Furlow", "phase": "TP2 (Final Payment)", "fpd_days": 0, "commission": 15486, "urgency": "red", "fpd_date": "OVERDUE (Apr 1)"},
        {"name": "Kuklinski", "phase": "TP1 (Validation)", "fpd_days": 45, "commission": 12000, "urgency": "yellow", "fpd_date": "TBD"},
        {"name": "McLeod", "phase": "TP0.5/0.6", "fpd_days": 30, "commission": 18500, "urgency": "green", "fpd_date": "TBD"},
        {"name": "Nichols", "phase": "Booked (Grandeur)", "fpd_days": 120, "commission": 14200, "urgency": "green", "fpd_date": "Aug 29"},
        {"name": "Ely", "phase": "Booked (Grandeur)", "fpd_days": 120, "commission": 13800, "urgency": "green", "fpd_date": "Aug 29"},
        {"name": "Westbrook", "phase": "Prospect", "fpd_days": 60, "commission": 16000, "urgency": "yellow", "fpd_date": "TBD"},
    ],
    "financial": {
        "prospect_pool": 120000,
        "qualified": 95000,
        "booked": 73000,
        "delivered": 45000,
        "allianz_pending": 11280,
        "furlow_overdue": 15486,
        "conversion_rate": 0.73,
    },
    "tasks": [
        {"client": "Lyons", "task": "Booking", "urgency": "red", "days_remaining": 13, "effort": "high"},
        {"client": "Furlow", "task": "Payment", "urgency": "red", "days_remaining": 0, "effort": "low"},
        {"client": "Kuklinski", "task": "Validation", "urgency": "yellow", "days_remaining": 5, "effort": "medium"},
        {"client": "McLeod", "task": "Excursions", "urgency": "yellow", "days_remaining": 10, "effort": "low"},
        {"client": "Westbrook", "task": "Proposals", "urgency": "yellow", "days_remaining": 7, "effort": "medium"},
        {"client": "Furlow", "task": "Excursions", "urgency": "green", "days_remaining": 3, "effort": "low"},
        {"client": "Nichols", "task": "Excursions", "urgency": "green", "days_remaining": 3, "effort": "low"},
    ],
    "risks": [
        {"name": "Furlow Payment Overdue", "likelihood": 0.95, "impact": 0.95, "value": 15486, "quadrant": "escalate"},
        {"name": "Lyons FPD Slip", "likelihood": 0.6, "impact": 0.85, "value": 8500, "quadrant": "mitigate"},
        {"name": "Allianz Claim Denied", "likelihood": 0.4, "impact": 0.7, "value": 11280, "quadrant": "monitor"},
        {"name": "TESS Auth Failure", "likelihood": 0.3, "impact": 0.5, "value": 5000, "quadrant": "monitor"},
    ],
}


def generate_data_json():
    """Export phase 1 data as JSON"""
    path = OUTPUT_DIR / "phase1_data.json"
    path.write_text(json.dumps(PHASE1_DATA, indent=2))
    return str(path)


def generate_html_dashboard():
    """Generate interactive HTML dashboard with Financial Waterfall + Heat Map"""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HALE Dashboard — Operational Snapshot</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; background: #f8f9fa; color: #2c3e50; }}
        .header {{ background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; padding: 2rem; text-align: center; }}
        .header h1 {{ font-size: 2em; margin-bottom: 0.5rem; }}
        .header p {{ font-size: 0.9em; opacity: 0.9; }}
        .container {{ max-width: 1400px; margin: 2rem auto; padding: 0 1rem; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 2rem; }}
        .chart-box {{ background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 1.5rem; }}
        .chart-box h2 {{ font-size: 1.3em; margin-bottom: 1rem; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; }}
        .chart {{ width: 100%; height: 400px; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }}
        .stat-card {{ background: white; border-radius: 8px; padding: 1.5rem; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .stat-card .value {{ font-size: 2em; font-weight: bold; margin: 0.5rem 0; }}
        .stat-card .label {{ font-size: 0.9em; color: #7f8c8d; }}
        .stat-card.red {{ border-left: 4px solid #ef553b; }}
        .stat-card.yellow {{ border-left: 4px solid #ffa500; }}
        .stat-card.green {{ border-left: 4px solid #00cc96; }}
        .timestamp {{ text-align: center; color: #95a5a6; font-size: 0.85em; margin-top: 2rem; }}
        @media (max-width: 900px) {{
            .grid {{ grid-template-columns: 1fr; }}
            .stats {{ grid-template-columns: repeat(2, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>⚙️ HALE OPERATIONAL DASHBOARD</h1>
        <p>Real-time financial + task overview | Generated {datetime.now().strftime('%Y-%m-%d %H:%M MT')}</p>
    </div>

    <div class="container">
        <!-- KEY METRICS -->
        <div class="stats">
            <div class="stat-card red">
                <div class="label">🔴 URGENT</div>
                <div class="value">2</div>
                <div class="label">Action Required</div>
            </div>
            <div class="stat-card yellow">
                <div class="label">🟡 AT RISK</div>
                <div class="value">3</div>
                <div class="label">Monitor Closely</div>
            </div>
            <div class="stat-card green">
                <div class="label">🟢 ON TRACK</div>
                <div class="value">2</div>
                <div class="label">Clients</div>
            </div>
            <div class="stat-card">
                <div class="label">💰 PIPELINE</div>
                <div class="value">$73K</div>
                <div class="label">Booked Commission</div>
            </div>
        </div>

        <!-- CHARTS GRID -->
        <div class="grid">
            <div class="chart-box">
                <h2>Financial Waterfall</h2>
                <div id="waterfall" class="chart"></div>
            </div>
            <div class="chart-box">
                <h2>Operational Heat Map</h2>
                <div id="heatmap" class="chart"></div>
            </div>
        </div>
    </div>

    <div class="timestamp">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S MT')} | Next update: 18:00 MT</div>

    <script>
        // FINANCIAL WATERFALL
        const waterfall = {{
            x: ['Prospect Pool', 'Qualified', 'Booked', 'Delivered', 'Allianz Pending', 'Furlow Overdue'],
            y: [120000, -25000, -22000, -28000, -11280, -15486],
            type: 'waterfall',
            orientation: 'v',
            connector: {{line: {{color: '#636EFA', width: 2}}}},
            decreasing: {{marker: {{color: '#636EFA'}}}},
            increasing: {{marker: {{color: '#00cc96'}}}},
            totals: {{marker: {{color: '#2c3e50'}}}},
            text: ['$120K', '-$25K', '-$22K', '-$28K', '-$11.3K', '-$15.5K'],
            textposition: 'outside',
            hovertemplate: '<b>%{{x}}</b><br>$%{{y:,.0f}}<extra></extra>'
        }};
        Plotly.newPlot('waterfall', [waterfall], {{
            margin: {{l: 50, r: 50, t: 30, b: 50}},
            paper_bgcolor: '#f8f9fa',
            plot_bgcolor: '#f8f9fa',
            xaxis: {{title: 'Stage'}},
            yaxis: {{title: 'Amount ($)'}},
            hovermode: 'closest'
        }}, {{responsive: true}});

        // OPERATIONAL HEAT MAP
        const heatmapData = {{
            z: [
                [5, 1, 1],  // Lyons: red booking, green excursions, green payment
                [5, 1, 1],  // Furlow: red payment, green excursions
                [3, 1, 1],  // Kuklinski: yellow validation
                [1, 3, 1],  // McLeod: green booking, yellow excursions
                [1, 1, 1],  // Nichols: green all
                [1, 1, 1],  // Ely: green all
                [1, 3, 3]   // Westbrook: green booking, yellow proposals
            ],
            x: ['Booking', 'Excursions', 'Payment'],
            y: ['Lyons', 'Furlow', 'Kuklinski', 'McLeod', 'Nichols', 'Ely', 'Westbrook'],
            type: 'heatmap',
            colorscale: [
                [0, '#00cc96'],     // green
                [0.5, '#ffa500'],   // yellow
                [1, '#ef553b']      // red
            ],
            hovertemplate: '<b>%{{y}}</b><br>%{{x}}<br>Urgency: %{{z:.0f}}<extra></extra>',
            colorbar: {{title: 'Urgency'}}
        }};
        Plotly.newPlot('heatmap', [heatmapData], {{
            margin: {{l: 120, r: 50, t: 30, b: 50}},
            paper_bgcolor: '#f8f9fa',
            plot_bgcolor: '#f8f9fa',
            hovermode: 'closest'
        }}, {{responsive: true}});
    </script>
</body>
</html>"""

    path = OUTPUT_DIR / "dashboard.html"
    path.write_text(html)
    return str(path)


def generate_canva_prompts():
    """Generate prompts for Canva visual generation (Lifecycle Wheel + Risk Matrix)"""
    prompts = {
        "lifecycle_wheel": {
            "design_type": "infographic",
            "query": """Create a professional circular client lifecycle wheel infographic showing 7 active clients.

LAYOUT:
- Center: "CLIENT LIFECYCLE" title
- Outer ring: 7 segments representing clients (Lyons, Furlow, Kuklinski, McLeod, Nichols, Ely, Westbrook)
- Color coding:
  - RED segment: Lyons (Pre-booking, FPD May 11) - 13 days
  - RED segment: Furlow (Final Payment) - OVERDUE
  - YELLOW segment: Kuklinski (Validation) - 45 days
  - YELLOW segment: Westbrook (Prospect) - 60 days
  - GREEN segments: McLeod, Nichols, Ely (On track)
- Inner ring: Progress bars showing FPD countdown for each client
- Segment size proportional to commission value
- Icons for each phase (pre-booking, validation, booked, travel)

STYLE: Clean, professional, corporate color scheme (dark blue, white, accent colors). Minimalist design. Clear typography. High contrast for readability.""",
            "style": "corporate, minimalist, data-driven"
        },
        "risk_matrix": {
            "design_type": "infographic",
            "query": """Create a professional 2x2 risk matrix infographic.

LAYOUT:
- Title: "RISK ASSESSMENT MATRIX"
- 2x2 grid with axes labeled:
  - X-axis (left to right): "Likelihood" (Low → High)
  - Y-axis (bottom to top): "Impact" (Low → High)
- Quadrant labels:
  - Bottom-left (green): "ACCEPT"
  - Bottom-right (orange): "MITIGATE"
  - Top-left (yellow): "MONITOR"
  - Top-right (red): "ESCALATE"
- Risk bubbles positioned in quadrants:
  1. "Furlow Payment Overdue" ($15.5K) - RED zone, top-right
  2. "Lyons FPD Slip" ($8.5K) - ORANGE zone, right-center
  3. "Allianz Claim Denied" ($11.3K) - YELLOW zone, top-center
  4. "TESS Auth Failure" ($5K) - YELLOW zone, center
- Bubble size represents financial impact
- Legend showing color coding

STYLE: Professional risk dashboard. Dark blue background or white. Red/orange/yellow/green risk indicators. Clear typography. Executive summary style.""",
            "style": "professional, risk-management, executive"
        }
    }

    path = OUTPUT_DIR / "canva_prompts.json"
    path.write_text(json.dumps(prompts, indent=2))
    return str(path)


if __name__ == "__main__":
    print("📊 Generating Phase 1 data layers...")

    data_path = generate_data_json()
    print(f"✅ Data JSON: {data_path}")

    dashboard_path = generate_html_dashboard()
    print(f"✅ HTML Dashboard: {dashboard_path}")

    prompts_path = generate_canva_prompts()
    print(f"✅ Canva Prompts: {prompts_path}")

    print("\n✨ All data layers generated! Ready for Canva + HTML rendering.")
    print(f"\n📍 Dashboard accessible at: file://{dashboard_path}")

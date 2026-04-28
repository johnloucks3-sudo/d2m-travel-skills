#!/usr/bin/env python3
"""
Phase 2: Weekly Strategic Visuals — Opportunity Map, Revenue Timeline, Capability Roadmap
========================================================================================

Generates three executive-level strategic infographics:
1. Opportunity Map — market opportunities by cruise line + destination
2. Revenue Timeline — multi-year commission forecast by client + phase
3. Capability Roadmap — Thunderbird Wing evolution (3/6/12 month targets)

Deployed: Weekly on Sundays at 18:00 MT via systemd timer
Author: Col Victoria "Iron Vic" Hale, COS — 2026-04-28
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

OUTPUT_DIR = Path("/home/john/Thunderbird/output/visuals/phase2")
OUTPUT_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────
# PHASE 2 DATA: Strategic Intelligence
# ─────────────────────────────────────────────────────────────────────

PHASE2_DATA = {
    "timestamp": datetime.now().isoformat(),
    "week_of": datetime.now().strftime("%Y-%m-%d"),

    # Opportunity Map: Market opportunities by cruise line + destination
    "opportunity_map": {
        "title": "Market Opportunity Map — Cruise Lines × Destinations",
        "cruise_lines": [
            {
                "name": "Seven Seas Grandeur",
                "line": "Regent",
                "destinations": [
                    {"name": "Scandinavia", "value": 73000, "clients": 3, "season": "Aug 2026", "urgency": "high"},
                    {"name": "Caribbean", "value": 45000, "clients": 1, "season": "Dec 2026", "urgency": "medium"},
                ],
                "total_pipeline": 118000,
            },
            {
                "name": "Silver Muse",
                "line": "Silversea",
                "destinations": [
                    {"name": "Med/Spain", "value": 18500, "clients": 1, "season": "Dec 2026", "urgency": "medium"},
                ],
                "total_pipeline": 18500,
            },
            {
                "name": "Silver Nova",
                "line": "Silversea",
                "destinations": [
                    {"name": "Hawaii", "value": 0, "clients": 0, "season": "Apr 2026", "urgency": "low"},
                ],
                "total_pipeline": 0,
            },
            {
                "name": "Viking Mars",
                "line": "Viking",
                "destinations": [
                    {"name": "Panama Canal", "value": 12000, "clients": 1, "season": "Dec 2026", "urgency": "medium"},
                ],
                "total_pipeline": 12000,
            },
        ],
        "total_market_value": 148500,
        "top_opportunity": "Grandeur Caribbean (Dec 2026) — 1 booked + 2 prospects",
    },

    # Revenue Timeline: Multi-year commission forecast
    "revenue_timeline": {
        "title": "Revenue Timeline — Commission Forecast by Client + Phase",
        "forecast_periods": [
            {
                "period": "Apr 2026 (Now)",
                "month": 4,
                "year": 2026,
                "status": "delivery window",
                "committed": 0,
                "at_risk": 26766,  # Furlow overdue + Allianz pending
                "booked": 73000,
                "forecast": 46234,  # Committed - at-risk
                "clients_active": 7,
            },
            {
                "period": "May 2026",
                "month": 5,
                "year": 2026,
                "status": "lyons fpd target",
                "committed": 0,
                "at_risk": 26766,
                "booked": 73000,
                "forecast": 46234,
                "clients_active": 7,
            },
            {
                "period": "Aug 2026",
                "month": 8,
                "year": 2026,
                "status": "grandeur departure",
                "committed": 48686,  # Furlow + Nichols + Ely excursions
                "at_risk": 11280,    # Allianz pending
                "booked": 73000,
                "forecast": 61720,
                "clients_active": 3,
            },
            {
                "period": "Dec 2026",
                "month": 12,
                "year": 2026,
                "status": "multi-ship departures",
                "committed": 73000,  # All booked ships depart
                "at_risk": 0,
                "booked": 73000,
                "forecast": 73000,
                "clients_active": 4,
            },
            {
                "period": "Q1 2027",
                "month": 1,
                "year": 2027,
                "status": "post-delivery",
                "committed": 0,
                "at_risk": 0,
                "booked": 0,
                "forecast": 0,
                "clients_active": 0,
            },
        ],
        "total_pipeline_12m": 148500,
        "realized_commission": 45000,
        "pending_delivery": 73000,
    },

    # Capability Roadmap: Thunderbird Wing evolution
    "capability_roadmap": {
        "title": "Thunderbird Wing Capability Evolution",
        "baseline": {
            "period": "Now (Apr 2026)",
            "clients_active": 7,
            "ships_active": 4,
            "destinations": 5,
            "pipeline_value": 148500,
            "staff_count": 9,
            "automation_level": "60%",
            "capabilities": [
                "Email-first booking workflow",
                "Real-time dossier management",
                "Commission tracking + reconciliation",
                "Voice-matched client emails",
                "Daily operational briefs",
                "Visual synthesis (dashboards + infographics)",
                "Telegram command center",
                "MCP-native integrations",
                "DeepSeek + Claude hybrid reasoning",
            ],
        },
        "roadmap_3m": {
            "period": "Jul 2026 (3-month outlook)",
            "focus": "Scale client touchpoints + capability redundancy",
            "new_capabilities": [
                "Weekly strategic visuals (opportunity map, revenue timeline)",
                "Automated excursion recommendations (A8 Reyes integration)",
                "Real-time payment tracking dashboard",
                "Smart follow-up reminders (by client + urgency)",
                "Supplier portal integration (TESS, MAGOA)",
            ],
            "targets": {
                "clients_active": "8-10",
                "automation_level": "75%",
                "response_time_avg": "< 2 hours",
            },
        },
        "roadmap_6m": {
            "period": "Oct 2026 (6-month outlook)",
            "focus": "Autonomous operations + predictive analytics",
            "new_capabilities": [
                "Predictive booking close rates (by client archetype)",
                "Automated upsell detection (excursions, dining, upgrades)",
                "Monthly board-level visuals (strategic + financial)",
                "Supplier rate comparison + negotiation (flight, hotel, transfers)",
                "Client lifetime value forecasting",
            ],
            "targets": {
                "clients_active": "12-15",
                "automation_level": "85%",
                "ceo_time_freed": "15 hours/week",
            },
        },
        "roadmap_12m": {
            "period": "Apr 2027 (12-month outlook)",
            "focus": "Agency-scale operations (9-12 person equivalent)",
            "new_capabilities": [
                "Outside agent portal (commission tracking, booking rules)",
                "AI-powered proposal generation (client-specific itineraries)",
                "Dynamic pricing engine (margin optimization)",
                "Consultant integrations (specialized expertise on-demand)",
                "Public-facing chatbot (FAQ + booking inquiry triage)",
            ],
            "targets": {
                "clients_active": "25-30",
                "annual_commission": "$250K+",
                "automation_level": "90%",
                "team_size": "12 (9 operational, 3 strategic)",
            },
        },
    },
}


def generate_phase2_data_json():
    """Export Phase 2 data as JSON."""
    path = OUTPUT_DIR / "phase2_data.json"
    path.write_text(json.dumps(PHASE2_DATA, indent=2))
    return str(path)


def generate_opportunity_map_prompt():
    """Generate Canva prompt for Opportunity Map infographic."""
    prompt = {
        "design_type": "infographic",
        "query": """Create a professional market opportunity map infographic.

LAYOUT:
- Title: "MARKET OPPORTUNITY MAP — Cruise Lines × Destinations"
- Matrix view: Vertical axis = Cruise Lines (Regent, Silversea, Viking, Ponant)
  Horizontal axis = Destinations (Scandinavia, Caribbean, Med, Panama, Hawaii)
- Heat map cells showing:
  - Color intensity = market value ($73K red, $18K orange, $0 gray)
  - Client count per cell (3 clients, 1 client, 0 prospects)
  - Season/timing (Aug 2026, Dec 2026, etc)
- Bubble overlays for active opportunities:
  - "Grandeur Scandinavia: 3 clients, $73K" (largest, top-left)
  - "Grandeur Caribbean: 1 booked + prospects" (right side)
  - "Silver Muse Med: 1 client, $18.5K" (medium)
  - "Viking Panama: 1 client, $12K" (small)
- Legend showing color coding (pipeline value scale)
- Bottom banner: "Total pipeline: $148.5K across 4 ships, 5 destinations"

STYLE: Executive dashboard. Professional color scheme. Clean typography. Data-driven layout.""",
        "style": "professional, data-driven, executive"
    }
    return prompt


def generate_revenue_timeline_prompt():
    """Generate Canva prompt for Revenue Timeline infographic."""
    prompt = {
        "design_type": "infographic",
        "query": """Create a professional revenue timeline infographic.

LAYOUT:
- Title: "REVENUE TIMELINE — Commission Forecast by Client + Phase"
- Timeline: Horizontal axis spanning Apr 2026 → Q1 2027
- Stacked bar chart showing:
  - Green (Committed): Delivered commission
  - Blue (Booked): Ships booked, in lifecycle
  - Red (At-Risk): Overdue payments, pending claims
- Key milestone markers:
  - Apr 2026: Now ($46K forecast)
  - May 2026: Lyons FPD target (13 days away)
  - Aug 2026: Grandeur departure (+3 clients depart)
  - Dec 2026: Multi-ship departures (+$73K committed)
  - Q1 2027: Post-delivery wind-down
- Data labels on each bar showing:
  - Total value, committed/booked/at-risk split
  - Active clients count
- Impact annotations:
  - Furlow overdue ($15.5K)
  - Allianz pending ($11.3K)
  - Lyons decision point (13 days)

STYLE: Executive financial dashboard. Green/blue/red color coding. Clear milestone markers.""",
        "style": "professional, financial, timeline"
    }
    return prompt


def generate_capability_roadmap_prompt():
    """Generate Canva prompt for Capability Roadmap infographic."""
    prompt = {
        "design_type": "infographic",
        "query": """Create a professional capability roadmap infographic.

LAYOUT:
- Title: "THUNDERBIRD WING CAPABILITY EVOLUTION"
- Vertical timeline: Now → 3M → 6M → 12M
- For each milestone, show:
  - Period & focus area
  - 5-6 new capabilities (bullet list)
  - Key metrics (clients, automation %, response time, etc)
- Current baseline (Apr 2026):
  - 7 active clients, 4 ships, $148.5K pipeline
  - 60% automation, email-first workflow
  - Daily briefs, visual synthesis, Telegram command center
- 3-month (Jul 2026):
  - 8-10 clients target, 75% automation
  - Weekly strategic visuals, smart follow-ups, payment dashboard
- 6-month (Oct 2026):
  - 12-15 clients, 85% automation, 15 hrs/week CEO freed
  - Predictive analytics, upsell detection, supplier integration
- 12-month (Apr 2027):
  - 25-30 clients, $250K+ annual commission
  - 90% automation, 12-person equivalent team
  - AI proposals, dynamic pricing, consultant integrations
- Design as cascading or timeline flow
- Color gradient (blue → green → gold) showing progression
- Icons for each capability type (envelope, dashboard, chart, etc)

STYLE: Strategic roadmap. Professional, forward-looking. Clear progression.""",
        "style": "professional, strategic, roadmap"
    }
    return prompt


def generate_canva_prompts_phase2():
    """Generate all Canva prompts for Phase 2 infographics."""
    prompts = {
        "opportunity_map": generate_opportunity_map_prompt(),
        "revenue_timeline": generate_revenue_timeline_prompt(),
        "capability_roadmap": generate_capability_roadmap_prompt(),
    }
    path = OUTPUT_DIR / "phase2_canva_prompts.json"
    path.write_text(json.dumps(prompts, indent=2))
    return str(path)


if __name__ == "__main__":
    print("📊 Generating Phase 2 Strategic Visuals data...")

    data_path = generate_phase2_data_json()
    print(f"✅ Phase 2 data: {data_path}")

    prompts_path = generate_canva_prompts_phase2()
    print(f"✅ Canva prompts: {prompts_path}")

    print("\n✨ Phase 2 data layers ready for Canva generation.")
    print(f"Next: Generate 3 infographics using prompts from {prompts_path}")

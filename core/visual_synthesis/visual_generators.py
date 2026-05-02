#!/usr/bin/env python3
"""
Hale Visual Synthesis Engine — Generate operational dashboards
Deployed: 2026-04-28 | Integration: hale_dispatcher.py → visual_synthesis()
"""

import json
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

OUTPUT_DIR = Path("/home/john/Thunderbird/output/visuals")
OUTPUT_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────
# 1. CLIENT LIFECYCLE WHEEL
# ─────────────────────────────────────────────────────────────────────

def generate_lifecycle_wheel(client_data: List[Dict]) -> str:
    """
    Generate donut/sunburst chart showing client phases + FPD countdown + urgency

    Args:
        client_data: [
            {"name": "Lyons", "phase": "Pre-booking", "fpd_days": 13, "commission": 8500, "urgency": "red"},
            ...
        ]

    Returns: Path to PNG file
    """
    names = [c["name"] for c in client_data]
    values = [c["commission"] for c in client_data]
    colors = [c["urgency"] for c in client_data]

    # Map urgency to color
    color_map = {
        "red": "#ef553b",      # urgent/action needed
        "yellow": "#ffa500",   # at-risk
        "green": "#00cc96"     # on-track
    }
    mapped_colors = [color_map.get(c["urgency"], "#636EFA") for c in client_data]

    fig = go.Figure(data=[
        go.Sunburst(
            labels=names,
            values=values,
            marker=dict(
                colors=mapped_colors,
                line=dict(color="white", width=3)
            ),
            hovertemplate="<b>%{label}</b><br>Commission: $%{value:,.0f}<extra></extra>",
            textinfo="label+percent entry",
            textposition="inside"
        )
    ])

    fig.update_layout(
        title={
            "text": "CLIENT LIFECYCLE WHEEL<br><sub>Phase Status + FPD Countdown + Commission Value</sub>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18, "color": "#2c3e50"}
        },
        width=900,
        height=700,
        margin=dict(l=50, r=50, t=120, b=50),
        paper_bgcolor="#f8f9fa",
        plot_bgcolor="#f8f9fa",
        font=dict(size=12, family="Arial, sans-serif")
    )

    filepath = OUTPUT_DIR / f"01_lifecycle_wheel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    fig.write_image(str(filepath), width=900, height=700, scale=2)
    return str(filepath)


# ─────────────────────────────────────────────────────────────────────
# 2. FINANCIAL WATERFALL
# ─────────────────────────────────────────────────────────────────────

def generate_financial_waterfall(pipeline_data: Dict) -> str:
    """
    Generate waterfall chart: prospect pool → qualified → booked → delivered
    Plus off-flows: pending claims, overdue payments

    Args:
        pipeline_data: {
            "prospect": 120000,
            "qualified": 85000,
            "booked": 65000,
            "delivered": 45000,
            "allianz_pending": 11280,
            "furlow_overdue": 15486
        }
    """
    stages = ["Prospect Pool", "Qualified", "Booked", "Delivered", "Allianz Pending", "Furlow Overdue"]
    values = [
        pipeline_data["prospect"],
        -(pipeline_data["prospect"] - pipeline_data["qualified"]),
        -(pipeline_data["qualified"] - pipeline_data["booked"]),
        -(pipeline_data["booked"] - pipeline_data["delivered"]),
        -pipeline_data["allianz_pending"],
        -pipeline_data["furlow_overdue"]
    ]
    colors = ["#00cc96", "#636EFA", "#636EFA", "#636EFA", "#ffa500", "#ef553b"]

    fig = go.Figure(go.Waterfall(
        name="Commission Pipeline",
        orientation="v",
        x=stages,
        textposition="outside",
        y=values,
        connector={"line": {"color": "#636EFA", "width": 2}},
        decreasing={"marker": {"color": "#636EFA"}},
        increasing={"marker": {"color": "#00cc96"}},
        totals={"marker": {"color": "#2c3e50"}},
        marker={"color": colors},
        text=[f"${v:,.0f}" if v > 0 else f"-${abs(v):,.0f}" for v in values],
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}<extra></extra>"
    ))

    fig.update_layout(
        title={
            "text": "FINANCIAL WATERFALL<br><sub>Commission Pipeline Flow + At-Risk Items</sub>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18, "color": "#2c3e50"}
        },
        xaxis=dict(title="Stage", showgrid=True, gridwidth=1, gridcolor="#e0e0e0"),
        yaxis=dict(title="Amount ($)", showgrid=True, gridwidth=1, gridcolor="#e0e0e0"),
        width=1000,
        height=600,
        margin=dict(l=80, r=50, t=120, b=80),
        paper_bgcolor="#f8f9fa",
        plot_bgcolor="#f8f9fa",
        hovermode="x unified",
        font=dict(size=11, family="Arial, sans-serif")
    )

    filepath = OUTPUT_DIR / f"02_financial_waterfall_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    fig.write_image(str(filepath), width=1000, height=600, scale=2)
    return str(filepath)


# ─────────────────────────────────────────────────────────────────────
# 3. OPERATIONAL HEAT MAP
# ─────────────────────────────────────────────────────────────────────

def generate_heat_map(task_data: List[Dict]) -> str:
    """
    Generate heatmap: rows=clients, columns=task type, values=urgency + effort

    Args:
        task_data: [
            {"client": "Lyons", "task": "Booking", "urgency": "red", "days_remaining": 13, "effort": "high"},
            ...
        ]
    """
    # Pivot: create matrix
    clients = sorted(set(t["client"] for t in task_data))
    tasks = sorted(set(t["task"] for t in task_data))

    # Build heatmap values (0-5 scale: 0=green, 5=red)
    urgency_scale = {"green": 1, "yellow": 3, "red": 5}
    z_values = []
    hover_text = []

    for client in clients:
        row = []
        row_hover = []
        for task in tasks:
            task_item = next((t for t in task_data if t["client"] == client and t["task"] == task), None)
            if task_item:
                z_val = urgency_scale.get(task_item["urgency"], 1)
                row.append(z_val)
                row_hover.append(f"{client}<br>{task}<br>Days: {task_item['days_remaining']}<br>Effort: {task_item['effort']}")
            else:
                row.append(0)
                row_hover.append(f"{client}<br>{task}<br>—")
        z_values.append(row)
        hover_text.append(row_hover)

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=tasks,
        y=clients,
        colorscale=[[0, "#00cc96"], [0.5, "#ffa500"], [1, "#ef553b"]],
        hoverongaps=False,
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover_text,
        colorbar=dict(title="Urgency", tickvals=[1, 3, 5], ticktext=["Green", "Yellow", "Red"])
    ))

    fig.update_layout(
        title={
            "text": "OPERATIONAL HEAT MAP<br><sub>Client Tasks by Urgency + Effort</sub>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18, "color": "#2c3e50"}
        },
        xaxis=dict(title="Task Category", side="bottom"),
        yaxis=dict(title="Client"),
        width=800,
        height=500,
        margin=dict(l=150, r=100, t=120, b=100),
        paper_bgcolor="#f8f9fa",
        font=dict(size=12, family="Arial, sans-serif")
    )

    filepath = OUTPUT_DIR / f"03_heat_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    fig.write_image(str(filepath), width=800, height=500, scale=2)
    return str(filepath)


# ─────────────────────────────────────────────────────────────────────
# 4. RISK MATRIX
# ─────────────────────────────────────────────────────────────────────

def generate_risk_matrix(risks: List[Dict]) -> str:
    """
    Generate 2D scatter: X=likelihood, Y=impact, bubble size=mitigation cost

    Args:
        risks: [
            {"name": "Furlow Payment", "likelihood": 0.9, "impact": 0.9, "value": 15486, "color": "red"},
            ...
        ]
    """
    names = [r["name"] for r in risks]
    likelihoods = [r["likelihood"] for r in risks]
    impacts = [r["impact"] for r in risks]
    values = [r["value"] for r in risks]
    colors_list = [r["color"] for r in risks]

    color_map = {"red": "#ef553b", "yellow": "#ffa500", "green": "#00cc96", "orange": "#ff7f0e"}
    mapped_colors = [color_map.get(c, "#636EFA") for c in colors_list]

    fig = go.Figure(data=[
        go.Scatter(
            x=likelihoods,
            y=impacts,
            mode="markers",
            marker=dict(
                size=[max(20, min(50, v/500)) for v in values],  # Scale bubble size
                color=mapped_colors,
                line=dict(width=2, color="white"),
                opacity=0.7
            ),
            text=names,
            hovertemplate="<b>%{text}</b><br>Likelihood: %{x:.0%}<br>Impact: %{y:.0%}<extra></extra>",
            showlegend=False
        )
    ])

    # Add quadrant lines
    fig.add_shape(type="line", x0=0.5, y0=0, x1=0.5, y1=1, line=dict(color="#ccc", width=2, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=0.5, x1=1, y1=0.5, line=dict(color="#ccc", width=2, dash="dash"))

    # Quadrant annotations
    fig.add_annotation(x=0.25, y=0.75, text="MONITOR", showarrow=False, font=dict(size=12, color="#999"))
    fig.add_annotation(x=0.75, y=0.75, text="ESCALATE", showarrow=False, font=dict(size=12, color="#ef553b", weight="bold"))
    fig.add_annotation(x=0.25, y=0.25, text="ACCEPT", showarrow=False, font=dict(size=12, color="#999"))
    fig.add_annotation(x=0.75, y=0.25, text="MITIGATE", showarrow=False, font=dict(size=12, color="#ffa500"))

    fig.update_layout(
        title={
            "text": "RISK MATRIX<br><sub>Likelihood vs Impact — Bubble Size = Value at Risk</sub>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18, "color": "#2c3e50"}
        },
        xaxis=dict(
            title="Likelihood →",
            range=[0, 1],
            showgrid=True,
            gridwidth=1,
            gridcolor="#e0e0e0",
            tickformat=".0%"
        ),
        yaxis=dict(
            title="Impact →",
            range=[0, 1],
            showgrid=True,
            gridwidth=1,
            gridcolor="#e0e0e0",
            tickformat=".0%"
        ),
        width=800,
        height=700,
        margin=dict(l=80, r=80, t=120, b=80),
        paper_bgcolor="#f8f9fa",
        plot_bgcolor="#f8f9fa",
        hovermode="closest",
        font=dict(size=11, family="Arial, sans-serif")
    )

    filepath = OUTPUT_DIR / f"04_risk_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    fig.write_image(str(filepath), width=800, height=700, scale=2)
    return str(filepath)


# ─────────────────────────────────────────────────────────────────────
# PHASE 1 TEST DATA (Real state from hale_brief.md + hale_state.json)
# ─────────────────────────────────────────────────────────────────────

def get_phase1_test_data() -> Tuple[List[Dict], Dict, List[Dict], List[Dict]]:
    """Return real test data for Phase 1 brief generation"""

    # Client Lifecycle data (from hale_brief.md)
    clients = [
        {"name": "Lyons", "phase": "Pre-booking", "fpd_days": 13, "commission": 8500, "urgency": "red"},
        {"name": "Furlow", "phase": "TP2 (Payment)", "fpd_days": 0, "commission": 15486, "urgency": "red"},
        {"name": "Kuklinski", "phase": "TP1 (Validation)", "fpd_days": 45, "commission": 12000, "urgency": "yellow"},
        {"name": "McLeod", "phase": "TP0.5/0.6", "fpd_days": 30, "commission": 18500, "urgency": "green"},
        {"name": "Nichols", "phase": "Booked", "fpd_days": 120, "commission": 14200, "urgency": "green"},
        {"name": "Ely", "phase": "Booked", "fpd_days": 120, "commission": 13800, "urgency": "green"},
        {"name": "Westbrook", "phase": "Prospect", "fpd_days": 60, "commission": 16000, "urgency": "yellow"},
    ]

    # Financial Waterfall data
    pipeline = {
        "prospect": 120000,
        "qualified": 95000,
        "booked": 73000,
        "delivered": 45000,
        "allianz_pending": 11280,
        "furlow_overdue": 15486
    }

    # Operational Heat Map data
    tasks = [
        {"client": "Lyons", "task": "Booking", "urgency": "red", "days_remaining": 13, "effort": "high"},
        {"client": "Furlow", "task": "Payment", "urgency": "red", "days_remaining": 0, "effort": "low"},
        {"client": "Kuklinski", "task": "Validation", "urgency": "yellow", "days_remaining": 5, "effort": "medium"},
        {"client": "McLeod", "task": "Excursions", "urgency": "yellow", "days_remaining": 10, "effort": "low"},
        {"client": "Westbrook", "task": "Proposals", "urgency": "yellow", "days_remaining": 7, "effort": "medium"},
        {"client": "Furlow", "task": "Excursions", "urgency": "green", "days_remaining": 3, "effort": "low"},
        {"client": "Nichols", "task": "Excursions", "urgency": "green", "days_remaining": 3, "effort": "low"},
    ]

    # Risk Matrix data
    risks = [
        {"name": "Furlow Payment Overdue", "likelihood": 0.95, "impact": 0.95, "value": 15486, "color": "red"},
        {"name": "Lyons FPD Slip", "likelihood": 0.6, "impact": 0.85, "value": 8500, "color": "yellow"},
        {"name": "Allianz Claim Denied", "likelihood": 0.4, "impact": 0.7, "value": 11280, "color": "yellow"},
        {"name": "TESS Auth Failure", "likelihood": 0.3, "impact": 0.5, "value": 5000, "color": "orange"},
        {"name": "Chrome Debug Offline", "likelihood": 0.1, "impact": 0.2, "value": 0, "color": "green"},
    ]

    return clients, pipeline, tasks, risks


if __name__ == "__main__":
    # Test generation
    clients, pipeline, tasks, risks = get_phase1_test_data()

    print("📊 Generating Phase 1 Test Visuals...")

    wheel_path = generate_lifecycle_wheel(clients)
    print(f"✅ Client Lifecycle Wheel: {wheel_path}")

    waterfall_path = generate_financial_waterfall(pipeline)
    print(f"✅ Financial Waterfall: {waterfall_path}")

    heatmap_path = generate_heat_map(tasks)
    print(f"✅ Operational Heat Map: {heatmap_path}")

    risk_path = generate_risk_matrix(risks)
    print(f"✅ Risk Matrix: {risk_path}")

    print("\n✨ All Phase 1 visuals generated successfully!")

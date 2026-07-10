"""
D2M brand tokens — extracted from storage/templates/d2m_canonical_darknavy.html.
Single source of truth for Tracks A/B/C visual integration. Import, don't redefine.
"""

NAVY_DARKEST = "#02021e"
NAVY_DARK = "#030338"
NAVY_BASE = "#07076b"     # primary brand navy
NAVY_MID = "#0a0a68"
NAVY_ACCENT = "#2428b0"
BLUE_INK = "#0000ff"      # Commander's pen color — email ink only, not dashboard chrome
SHIMMER = "#c8d8ff"
SHIMMER_ALT = "#7fb0ff"
TEXT_ON_NAVY = "#e8f1ff"
TEXT_ON_NAVY_MUTED = "#a8c4f0"
CREAM = "#f7f3ea"         # email paper — not used on dashboards

STATUS_GREEN = "#2ecc71"
STATUS_YELLOW = "#f1c40f"
STATUS_RED = "#e74c3c"
STATUS_GREY = "#8899bb"

FONT_SERIF = "Georgia, 'Times New Roman', serif"
FONT_MONO = "'SF Mono', Consolas, monospace"

# dataviz-skill categorical palette, swapped to brand hues (validate before reuse)
CATEGORICAL_PALETTE = [NAVY_BASE, SHIMMER_ALT, STATUS_YELLOW, TEXT_ON_NAVY_MUTED, NAVY_ACCENT]

# sequential palette (low -> high), for heatmaps / fare matrices
SEQUENTIAL_PALETTE = [NAVY_DARKEST, NAVY_DARK, NAVY_BASE, NAVY_ACCENT, SHIMMER_ALT, SHIMMER]

PAGE_SHELL_CSS = f"""
  body {{
    background: linear-gradient(160deg, {NAVY_DARKEST}, {NAVY_DARK} 60%, {NAVY_BASE});
    color: {TEXT_ON_NAVY};
    font-family: {FONT_SERIF};
    margin: 0;
    padding: 24px;
  }}
  .d2m-card {{
    background: rgba(10, 10, 104, 0.35);
    border: 1px solid {NAVY_ACCENT};
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 18px;
  }}
  .d2m-card h2 {{
    margin-top: 0;
    color: {SHIMMER};
    font-size: 1.05em;
    letter-spacing: 0.03em;
    text-transform: uppercase;
  }}
  table.d2m-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92em;
  }}
  table.d2m-table th {{
    text-align: left;
    color: {TEXT_ON_NAVY_MUTED};
    border-bottom: 1px solid {NAVY_ACCENT};
    padding: 6px 8px;
    font-weight: 600;
  }}
  table.d2m-table td {{
    padding: 6px 8px;
    border-bottom: 1px solid rgba(36, 40, 176, 0.35);
  }}
"""


def status_color(value: str) -> str:
    """Map a health/status string to a brand status color."""
    v = str(value).upper()
    if "ONLINE" in v or "LIVE" in v or "OK" in v or "RUNNING" in v or "PAID" in v:
        return STATUS_GREEN
    if "OFFLINE" in v or "🔴" in v or "EXPIRED" in v:
        return STATUS_RED
    if "🟡" in v or "PENDING" in v or "DUE" in v:
        return STATUS_YELLOW
    return STATUS_GREY

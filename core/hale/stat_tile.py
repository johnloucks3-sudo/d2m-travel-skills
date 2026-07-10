"""
Reusable stat-tile / status-badge HTML primitives.
Shared by Track A (financial pulse), Track B (fare-watch counts), Track C (payment-status badges).
"""

from core.hale.d2m_brand_tokens import (
    NAVY_MID, NAVY_ACCENT, SHIMMER, TEXT_ON_NAVY, TEXT_ON_NAVY_MUTED, status_color,
)


def stat_tile(label: str, value: str, sub: str = "", color: str | None = None) -> str:
    """A single KPI tile: big value, small label under it, optional sub-line."""
    c = color or SHIMMER
    sub_html = f"<div style='font-size:0.75em;color:{TEXT_ON_NAVY_MUTED};margin-top:2px'>{sub}</div>" if sub else ""
    return f"""
    <div style="background:{NAVY_MID};border:1px solid {NAVY_ACCENT};border-radius:8px;
                padding:14px 16px;min-width:140px;display:inline-block;margin:0 10px 10px 0;">
      <div style="font-size:1.6em;font-weight:700;color:{c};">{value}</div>
      <div style="font-size:0.78em;color:{TEXT_ON_NAVY_MUTED};text-transform:uppercase;letter-spacing:0.04em;">{label}</div>
      {sub_html}
    </div>"""


def status_badge(text: str) -> str:
    """Colored pill for a status string (ONLINE/OFFLINE/PAID/DUE/etc)."""
    c = status_color(text)
    return (
        f"<span style='display:inline-block;padding:2px 9px;border-radius:11px;"
        f"background:{c};color:#02021e;font-size:0.78em;font-weight:600;'>{text}</span>"
    )


def tile_row(tiles_html: list[str]) -> str:
    return f"<div style='display:flex;flex-wrap:wrap;'>{''.join(tiles_html)}</div>"

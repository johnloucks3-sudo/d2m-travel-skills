"""Great Circle Route Map — SVG generator.

Design (per docs/DATAVIZ_FLIGHT_CHARTS_SPEC_20260710.md, component 1):
  - Route line: D2M navy (#003087), 2px stroke — a brand-ink stroke, not a
    categorical identity mark, so it is exempt from the dataviz skill's
    8-hue categorical checks (same reasoning as an axis line or reference line).
  - Endpoint markers: gold (#d4af37), 8px circles — a single accent color.
    Gold-on-cream contrast is 1.9:1 (WARN band per validate_palette.js), so
    every marker carries its IATA code as a direct label (the skill's
    mandatory relief for a sub-3:1 mark) — never color alone.
  - Surface: cream (#f7f3ea), consistent with existing flight-option artifacts.

Pure stdlib. No network calls, no external map tiles — this is a stylized
route diagram (great-circle bearing + distance), not a navigational chart.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from core.dataviz.airports import lookup

NAVY = "#003087"
GOLD = "#d4af37"
CREAM = "#f7f3ea"
INK_MUTED = "#666666"

EARTH_RADIUS_NM = 3440.065  # nautical miles, for flight-distance framing


@dataclass
class RouteMapResult:
    svg: str
    distance_nm: float
    distance_mi: float
    origin_label: str
    dest_label: str


def _to_xyz(lat: float, lon: float) -> tuple[float, float, float]:
    lat_r, lon_r = math.radians(lat), math.radians(lon)
    return (
        math.cos(lat_r) * math.cos(lon_r),
        math.cos(lat_r) * math.sin(lon_r),
        math.sin(lat_r),
    )


def _to_latlon(x: float, y: float, z: float) -> tuple[float, float]:
    lat = math.degrees(math.asin(max(-1.0, min(1.0, z))))
    lon = math.degrees(math.atan2(y, x))
    return lat, lon


def _slerp_points(lat1, lon1, lat2, lon2, n: int = 48) -> list[tuple[float, float]]:
    """n interpolated (lat, lon) points along the great circle, endpoints included."""
    x1, y1, z1 = _to_xyz(lat1, lon1)
    x2, y2, z2 = _to_xyz(lat2, lon2)
    dot = max(-1.0, min(1.0, x1 * x2 + y1 * y2 + z1 * z2))
    omega = math.acos(dot)
    pts = []
    if omega < 1e-9:
        return [(lat1, lon1), (lat2, lon2)]
    for i in range(n + 1):
        t = i / n
        a = math.sin((1 - t) * omega) / math.sin(omega)
        b = math.sin(t * omega) / math.sin(omega)
        x = a * x1 + b * x2
        y = a * y1 + b * y2
        z = a * z1 + b * z2
        pts.append(_to_latlon(x, y, z))
    return pts


def _haversine_nm(lat1, lon1, lat2, lon2) -> float:
    r1, r2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(r1) * math.cos(r2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(a))


def render_route_map(
    origin_iata: str,
    dest_iata: str,
    width: int = 640,
    height: int = 340,
    title: str | None = None,
) -> RouteMapResult:
    """Render a Great Circle route SVG between two IATA airports.

    Falls back to a "no coordinate data" label card if either code is
    unknown — never raises, so a bad/rare IATA code degrades visibly
    instead of breaking the page that embeds it.
    """
    o = lookup(origin_iata)
    d = lookup(dest_iata)
    pad = 48

    if not o or not d:
        missing = origin_iata if not o else dest_iata
        svg = (
            f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Route map unavailable for {origin_iata}-{dest_iata}">'
            f'<rect width="{width}" height="{height}" fill="{CREAM}" rx="8"/>'
            f'<text x="{width/2}" y="{height/2}" text-anchor="middle" '
            f'font-family="Georgia,serif" font-size="14" fill="{INK_MUTED}">'
            f"No coordinate data for {missing} — add it to core/dataviz/airports.py"
            f"</text></svg>"
        )
        return RouteMapResult(svg, 0.0, 0.0, origin_iata, dest_iata)

    lat1, lon1, label1 = o
    lat2, lon2, label2 = d
    dist_nm = _haversine_nm(lat1, lon1, lat2, lon2)
    dist_mi = dist_nm * 1.15078

    pts = _slerp_points(lat1, lon1, lat2, lon2, n=48)
    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)
    # guard against a degenerate (near-zero span) bounding box
    lat_span = max(lat_max - lat_min, 1.0)
    lon_span = max(lon_max - lon_min, 1.0)

    plot_w, plot_h = width - 2 * pad, height - 2 * pad

    def project(lat: float, lon: float) -> tuple[float, float]:
        x = pad + (lon - lon_min) / lon_span * plot_w
        y = pad + (1 - (lat - lat_min) / lat_span) * plot_h
        return x, y

    path_pts = [project(lat, lon) for lat, lon in pts]
    path_d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in path_pts)
    x1, y1 = project(lat1, lon1)
    x2, y2 = project(lat2, lon2)

    title_text = title or f"{origin_iata} → {dest_iata}"

    svg = f'''<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Great circle route {origin_iata} to {dest_iata}, {dist_mi:.0f} statute miles">
<rect width="{width}" height="{height}" fill="{CREAM}" rx="8"/>
<text x="{pad}" y="24" font-family="Georgia,serif" font-size="14" font-weight="bold" fill="{NAVY}">{title_text}</text>
<text x="{pad}" y="40" font-family="Georgia,serif" font-size="11" fill="{INK_MUTED}">{dist_nm:,.0f} nm &middot; {dist_mi:,.0f} mi &middot; great circle</text>
<path d="{path_d}" fill="none" stroke="{NAVY}" stroke-width="2" stroke-linecap="round"/>
<circle cx="{x1:.1f}" cy="{y1:.1f}" r="6" fill="{GOLD}" stroke="{NAVY}" stroke-width="1.5"/>
<circle cx="{x2:.1f}" cy="{y2:.1f}" r="6" fill="{GOLD}" stroke="{NAVY}" stroke-width="1.5"/>
<text x="{x1:.1f}" y="{y1-12:.1f}" text-anchor="middle" font-family="Georgia,serif" font-size="12" font-weight="bold" fill="{NAVY}">{origin_iata}</text>
<text x="{x1:.1f}" y="{y1+22:.1f}" text-anchor="middle" font-family="Georgia,serif" font-size="9" fill="{INK_MUTED}">{label1}</text>
<text x="{x2:.1f}" y="{y2-12:.1f}" text-anchor="middle" font-family="Georgia,serif" font-size="12" font-weight="bold" fill="{NAVY}">{dest_iata}</text>
<text x="{x2:.1f}" y="{y2+22:.1f}" text-anchor="middle" font-family="Georgia,serif" font-size="9" fill="{INK_MUTED}">{label2}</text>
</svg>'''

    return RouteMapResult(svg, dist_nm, dist_mi, label1, label2)


if __name__ == "__main__":
    r = render_route_map("DEN", "VCE", title="DEN → VCE (via great circle)")
    print(f"distance: {r.distance_nm:.0f} nm / {r.distance_mi:.0f} mi")
    with open("/tmp/route_map_test.svg", "w") as f:
        f.write(r.svg)
    print("wrote /tmp/route_map_test.svg")

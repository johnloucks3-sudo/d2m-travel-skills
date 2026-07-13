"""
sections — Intel / Tech Scans / Next 7 Days collectors (Phase 3 data layer).

Each function returns a list of Item objects (same shape as the main Items
sheet) destined for its OWN Sheet tab — Looker Studio reads these tabs
directly for the read-only dashboard views. Local-only files (intel reports,
tech-scan outputs) get a REAL Drive link via drive_mirror, not a fuzzy
search, so every row is genuinely clickable (requirement #1) even without a
custom backend to serve them.

All three are pure-ish functions parameterized by root paths / an injectable
``mirror_fn`` so they unit-test offline (no Drive credentials needed to
verify the file-discovery and row-shaping logic).
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import _imports
from .drive_mirror import mirror_file
from .item_model import Item
from .permalink import derive_link, drive_search_link, first_nonempty

ROOT = _imports.ROOT
INTEL_DIR = ROOT / "intel"
SHIP_INTEL_DIR = ROOT / "data" / "ship_intel"
OPSCENTER_STATE = ROOT / "OpsCenter" / "state"
CI_REGISTRY = ROOT / "config" / "ci_registry.json"
DOSSIERS_DIR = ROOT / "dossiers"
FPD_STATE = OPSCENTER_STATE / "fpd_state.json"
SUSPENSE_CALENDAR = OPSCENTER_STATE / "SUSPENSE_CALENDAR.md"
MISSION_BOARD = ROOT / "OpsCenter" / "mission_board.json"

INTEL_DRIVE_FOLDER = "TCD Intel Archive"
TECHSCANS_DRIVE_FOLDER = "TCD Tech Scans Archive"
STALE_DAYS = 7


def _load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def _snip(text: str, n: int = 220) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:n] + ("…" if len(text) > n else "")


def _mtime_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return ""


def _is_stale(path: Path, days: int = STALE_DAYS) -> bool:
    try:
        age = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
        return age > days * 86400
    except OSError:
        return True


# --------------------------------------------------------------------- Intel
def _title_from_md(path: Path) -> str:
    try:
        text = path.read_text(errors="ignore")
        line = text.splitlines()[0].lstrip("# ").strip() if text else ""
        return line or path.stem
    except OSError:
        return path.stem


def collect_intel(days: int = 14, max_items: int = 40, *, mirror_fn=mirror_file,
                  now: datetime = None) -> list:
    """Recent intel reports (cruise/pricing/competitor/route) as Items.

    ``mirror_fn`` is injectable for offline testing (returns "" instead of
    hitting Drive). Bounded to the most-recently-modified ``max_items`` files
    across intel/*.md, intel/email_intel/*.md, and one latest JSON summary
    per subdirectory (cruise_intel, ship_intel, daily_search) — a report
    ARCHIVE dashboard, not a per-voyage-pricing-row explosion.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now.timestamp() - days * 86400
    candidates = []

    if INTEL_DIR.is_dir():
        candidates += sorted(INTEL_DIR.glob("*.md"))
        candidates += sorted((INTEL_DIR / "email_intel").glob("*.md")) \
            if (INTEL_DIR / "email_intel").is_dir() else []

    # One latest JSON summary per subdirectory — avoids row-explosion from
    # per-voyage pricing scrapes while still surfacing "what's fresh."
    for sub in ("cruise_intel", "daily_search"):
        d = INTEL_DIR / sub
        if d.is_dir():
            files = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            candidates += files[:1]
    if SHIP_INTEL_DIR.is_dir():
        files = sorted(SHIP_INTEL_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        candidates += files[:1]

    recent = [p for p in candidates if p.is_file() and p.stat().st_mtime >= cutoff]
    recent.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    recent = recent[:max_items]

    items = []
    for p in recent:
        is_md = p.suffix == ".md"
        title = _title_from_md(p) if is_md else p.stem.replace("_", " ")
        snippet = _snip(p.read_text(errors="ignore")[:400]) if is_md else f"Data file: {p.name}"
        link = mirror_fn(p, INTEL_DRIVE_FOLDER, "text/markdown" if is_md else "application/json")
        link = first_nonempty(link, drive_search_link(p.stem))
        items.append(Item(
            id=f"intel-{p.stem}", inbox="reference", type="paper", priority="routine",
            stage="REF", title=title, source="Intel Archive",
            date=_mtime_iso(p)[:10], snippet=snippet, body=snippet,
            link=link, sourcePath=str(p.relative_to(ROOT)),
            comments="", status="Reference",
        ))
    return items


# ------------------------------------------------------------------ TechScans
_TECHSCAN_FILES = [
    ("config/ci_registry.json", "CI/CD Tool Registry"),
    ("OpsCenter/state/STACK_FRESHNESS.md", "Stack Freshness Report"),
    ("OpsCenter/state/credentials_health.json", "Credentials Health"),
    ("OpsCenter/state/dead_code_report.txt", "Dead Code Report"),
    ("OpsCenter/state/heartbeat_scan_latest.json", "Heartbeat Scan"),
    ("OpsCenter/state/portal_live_health.json", "Portal Live Health"),
]


def _latest_glob(pattern: str) -> Path:
    matches = sorted(ROOT.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def collect_techscans(*, mirror_fn=mirror_file) -> list:
    """CI/CD, infra, and security scan outputs as Items — a linked VIEW,
    not ownership (TCD does not replace tech scans, per CLAUDE.md)."""
    items = []
    targets = [(ROOT / rel, label) for rel, label in _TECHSCAN_FILES]
    latest_home_health = _latest_glob("OpsCenter/state/home_dir_health_*.json")
    if latest_home_health and "baseline" not in latest_home_health.name:
        targets.append((latest_home_health, "Home Dir Health Audit"))

    for path, label in targets:
        if not path.is_file():
            continue
        stale = _is_stale(path)
        mime = "text/markdown" if path.suffix == ".md" else (
            "application/json" if path.suffix == ".json" else "text/plain")
        link = mirror_fn(path, TECHSCANS_DRIVE_FOLDER, mime)
        link = first_nonempty(link, drive_search_link(path.stem))
        snippet = _snip(path.read_text(errors="ignore")[:400])
        items.append(Item(
            id=f"techscan-{path.stem}", inbox="reference", type="brief",
            priority="p1" if stale else "routine", stage="REF",
            title=f"{'⚠ STALE — ' if stale else ''}{label}",
            source="Tech Scans", date=_mtime_iso(path)[:10],
            snippet=snippet, body=snippet, link=link,
            sourcePath=str(path.relative_to(ROOT)), comments="", status="Reference",
        ))
    return items


# -------------------------------------------------------------------- Next 7
def collect_next7(*, calendar_events_fn=None, now: datetime = None) -> list:
    """Forward 7-day view: Calendar events + FPD dates + suspense calendar +
    mission suspense dates, each item carrying a real link to its source.
    """
    now = now or datetime.now(timezone.utc)
    items = []

    # 1. Calendar events (real htmlLink from the API — no mirroring needed).
    if calendar_events_fn is None:
        try:
            gauth = _imports.load_google_auth()
            svc = gauth.get_calendar()
            from datetime import timedelta
            res = svc.events().list(
                calendarId="primary", timeMin=now.isoformat(),
                timeMax=(now + timedelta(days=7)).isoformat(),
                maxResults=25, singleEvents=True, orderBy="startTime",
            ).execute()
            calendar_events_fn = lambda: res.get("items", [])
        except Exception:
            calendar_events_fn = lambda: []
    for e in calendar_events_fn():
        s = e.get("start", {})
        items.append(Item(
            id=f"next7-cal-{e.get('id', '')}", inbox="reference", type="brief",
            priority="p2", stage="REF", title=e.get("summary", "(no title)"),
            source="Calendar", date=(s.get("dateTime", s.get("date", "")) or "")[:10],
            snippet=e.get("location", ""), body=e.get("location", ""),
            link=e.get("htmlLink", ""), sourcePath="Google Calendar",
            comments="", status="Reference",
        ))

    # 2. FPD dates within the window, linked to the dossier (reuses the
    # existing dossier-> Drive-search link logic, same as Reference items).
    fpd_state = _load_json(FPD_STATE, {})
    window_end = (now.timestamp() + 7 * 86400)
    fpd_entries = fpd_state if isinstance(fpd_state, list) else fpd_state.get("clients", [])
    for entry in fpd_entries:
        fpd_date = entry.get("fpd", "")
        if not fpd_date:
            continue
        try:
            fpd_ts = datetime.fromisoformat(fpd_date).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
        if not (now.timestamp() <= fpd_ts <= window_end):
            continue
        dossier_stem = entry.get("dossier", entry.get("client", ""))
        link = derive_link({"id": f"dossier-{dossier_stem}", "title": dossier_stem,
                            "tags": ["dossier", entry.get("client", "")]})
        items.append(Item(
            id=f"next7-fpd-{entry.get('client', dossier_stem)}", inbox="strategic",
            type="decision", priority="p1", stage="REF",
            title=f"FPD due: {entry.get('client', dossier_stem)}",
            source="FPD Tracker", date=fpd_date,
            snippet=f"{entry.get('payment_status', '')} — {entry.get('fpd_amount', '')}",
            body="", link=link, sourcePath="OpsCenter/state/fpd_state.json",
            comments="", status="Reference",
        ))

    # 3. Mission suspense dates (forward-compatible — currently all null
    # per the live mission_board.json, so this contributes 0 rows today).
    mission_board = _load_json(MISSION_BOARD, {})
    for m in mission_board.get("missions", []) + mission_board.get("active_missions", []):
        susp = m.get("suspense_date")
        if not susp:
            continue
        try:
            susp_ts = datetime.fromisoformat(susp).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
        if not (now.timestamp() <= susp_ts <= window_end):
            continue
        items.append(Item(
            id=f"next7-mission-{m.get('id', '')}", inbox="strategic", type="decision",
            priority="p1", stage="REF", title=f"Mission suspense: {m.get('id', '')}",
            source="Mission Board", date=susp, snippet=m.get("title", ""),
            body="", link=drive_search_link(m.get("id", "")),
            sourcePath="OpsCenter/mission_board.json", comments="", status="Reference",
        ))

    return items

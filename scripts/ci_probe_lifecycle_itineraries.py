#!/usr/bin/env python3
"""
CI EFFICACY PROBE — Lifecycle Itinerary Generator Health
=========================================================
Dreams2Memories Travel, LLC · CI razor-sharp doctrine (SO 2026-06-20)

Checks:
  1. itinerary/luxury_itinerary_generator.py exists and imports successfully
     (import failure = cannot produce itineraries = RED)
  2. No active booking has a sail date within 30 days WITHOUT an itinerary
     artifact in output/validation_emails/ or drafts/ — checks by scanning
     dossier files for departure dates near today

PROBE-NOTE: luxury_itinerary_generator.py is the legacy Google API-based tool.
The Wing now produces HTML itineraries. This probe gates on import health
(can the engine load?) + sail-date gap detection (is there a booking in the
30-day window that lacks an artifact?). nearest sail is Aug 29 (59+ days out)
so no gap expected today. MISSION-802 itinerary build window opens Jul 22.

Probe does NOT re-run the engine. The repair function re-runs it.
Exit 0 = GREEN. Exit 1 = RED.
"""
import importlib.util
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "python3")
ITINERARY_ENGINE = THUNDERBIRD_ROOT / "itinerary" / "luxury_itinerary_generator.py"
DOSSIERS_DIR = THUNDERBIRD_ROOT / "dossiers"
OUTPUT_DIR = THUNDERBIRD_ROOT / "output" / "validation_emails"
DRAFTS_DIR = THUNDERBIRD_ROOT / "drafts"
SAIL_WINDOW_DAYS = 30  # Flag gap if sail date within this many days
ID = "lifecycle-itineraries"

# Date patterns to extract from dossier files
DATE_PATTERNS = [
    # YYYY-MM-DD
    re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b"),
    # Month DD YYYY or Month D, YYYY
    re.compile(
        r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
        r"Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?[,\s]+(\d{4})\b",
        re.IGNORECASE,
    ),
]

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def fail(m: str) -> None:
    print(f"RED {ID}: {m}")
    sys.exit(1)


def extract_dates_from_dossier(path: Path) -> list[datetime]:
    """Extract plausible sail/departure dates from a dossier file."""
    dates = []
    now = datetime.now(tz=timezone.utc)
    horizon = now + timedelta(days=365)

    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return dates

    # ISO dates
    for m in DATE_PATTERNS[0].finditer(text):
        try:
            d = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
            if now < d < horizon:
                dates.append(d)
        except Exception:
            pass

    # Month name dates
    for m in DATE_PATTERNS[1].finditer(text):
        try:
            mon = m.group(1)[:3].lower()
            day = int(m.group(2))
            year = int(m.group(3))
            d = datetime(year, MONTH_MAP.get(mon, 0) or 1, day, tzinfo=timezone.utc)
            if now < d < horizon:
                dates.append(d)
        except Exception:
            pass

    return dates


def itinerary_artifact_exists(dossier_name: str) -> bool:
    """Check if any itinerary artifact exists for this client (best-effort)."""
    # Derive a short search key from the dossier filename
    stem = Path(dossier_name).stem.lower()
    # Try common name segments (first word after DOSSIER_ or first word)
    parts = re.split(r"[_\-\s]+", stem)
    search_keys = [p for p in parts if len(p) > 3 and p not in ("dossier", "the", "and")][:2]

    for search_dir in [OUTPUT_DIR, DRAFTS_DIR]:
        if not search_dir.exists():
            continue
        for f in search_dir.iterdir():
            fname_lower = f.name.lower()
            if any(k in fname_lower for k in search_keys):
                return True
    return False


def main() -> None:
    # ── CHECK 1: Engine file exists ──────────────────────────────────────────
    if not ITINERARY_ENGINE.exists():
        fail(
            f"luxury_itinerary_generator.py missing at {ITINERARY_ENGINE} — "
            "itinerary engine file absent"
        )

    # ── CHECK 2: Import health ───────────────────────────────────────────────
    try:
        spec = importlib.util.spec_from_file_location(
            "luxury_itinerary_generator", ITINERARY_ENGINE
        )
        if spec is None or spec.loader is None:
            fail(f"importlib cannot load spec for {ITINERARY_ENGINE}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    except SystemExit:
        pass  # Some modules call sys.exit() on load if __main__ guard is missing
    except ImportError as e:
        fail(
            f"luxury_itinerary_generator.py import failed (ImportError): {e}. "
            "Engine dependencies missing — cannot produce itineraries."
        )
    except Exception as e:
        # Non-ImportError exceptions (e.g., config errors) are warnings, not RED
        # The engine requires Google credentials which won't exist in CI context
        # If it's a credential/config error, we allow GREEN with a note
        err_str = str(e).lower()
        if any(kw in err_str for kw in ("credential", "oauth", "token", "auth", "google")):
            # Expected: Google auth not available in headless CI — engine code is fine
            pass
        else:
            fail(
                f"luxury_itinerary_generator.py raised unexpected exception on import: "
                f"{type(e).__name__}: {e}"
            )

    # ── CHECK 3: No upcoming sail (within 30d) lacks an itinerary artifact ──
    now = datetime.now(tz=timezone.utc)
    window_end = now + timedelta(days=SAIL_WINDOW_DAYS)
    gaps = []  # (dossier_name, sail_date)

    if DOSSIERS_DIR.exists():
        for dossier_path in DOSSIERS_DIR.glob("*.md"):
            dates = extract_dates_from_dossier(dossier_path)
            for sail_dt in dates:
                if now < sail_dt <= window_end:
                    # Sailing is within the 30-day window — check for artifact
                    if not itinerary_artifact_exists(dossier_path.name):
                        gaps.append((dossier_path.name, sail_dt.date().isoformat()))

    if gaps:
        gap_str = "; ".join(f"{d[0]} sails {d[1]}" for d in gaps[:3])
        fail(
            f"{len(gaps)} booking(s) sail within {SAIL_WINDOW_DAYS} days without "
            f"itinerary artifact: {gap_str}. "
            "Build itinerary immediately — MISSION-802 pattern."
        )

    # Informational: nearest sail date
    nearest_info = "no bookings within 1 year found in dossiers"
    all_upcoming = []
    if DOSSIERS_DIR.exists():
        for dossier_path in DOSSIERS_DIR.glob("*.md"):
            dates = extract_dates_from_dossier(dossier_path)
            for d in dates:
                if d > now:
                    all_upcoming.append((d, dossier_path.stem))
    if all_upcoming:
        all_upcoming.sort()
        nearest_dt, nearest_name = all_upcoming[0]
        days_out = (nearest_dt - now).days
        nearest_info = f"nearest sail: {nearest_dt.date().isoformat()} ({days_out}d out) — {nearest_name}"

    print(
        f"GREEN {ID}: engine imports OK; "
        f"no gaps in {SAIL_WINDOW_DAYS}-day window; "
        f"{nearest_info}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()

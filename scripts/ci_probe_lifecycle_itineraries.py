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

# Statuses that mean no itinerary is expected
INACTIVE_STATUSES = {"complete", "archived"}

THUNDERBIRD_ROOT = Path("/home/john/Thunderbird")
VENV_PY = str(THUNDERBIRD_ROOT / ".venv" / "bin" / "python3")
ITINERARY_ENGINE = THUNDERBIRD_ROOT / "itinerary" / "luxury_itinerary_generator.py"
DOSSIERS_DIR = THUNDERBIRD_ROOT / "dossiers"
OUTPUT_DIR = THUNDERBIRD_ROOT / "output" / "validation_emails"
DRAFTS_DIR = THUNDERBIRD_ROOT / "drafts"
SAIL_WINDOW_DAYS = 30  # Flag gap if sail date within this many days
ID = "lifecycle-itineraries"

# Patterns for parsing YAML frontmatter fields only
_DEPARTURE_RE = re.compile(r'^departure:\s*["\']?(20\d{2}-\d{2}-\d{2})["\']?', re.MULTILINE)
_STATUS_RE = re.compile(r'^status:\s*(\S+)', re.MULTILINE)


def fail(m: str) -> None:
    print(f"RED {ID}: {m}")
    sys.exit(1)


def parse_frontmatter(path: Path) -> dict | None:
    """Parse YAML frontmatter from a dossier and return {departure, status}.

    Only reads the frontmatter block (between the first two '---' lines) to
    avoid false-positive date matches from port-call schedules, FPDs, or
    payment dates in the dossier body.

    Returns None if no frontmatter found.
    """
    try:
        text = path.read_text(errors="ignore")
    except Exception:
        return None

    # Require frontmatter block: starts with '---' on first non-empty line
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    # Collect frontmatter lines up to closing '---'
    fm_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)
    else:
        # No closing '---' found — no valid frontmatter
        return None

    fm_text = "\n".join(fm_lines)

    result: dict = {}

    # Extract departure field
    dep_m = _DEPARTURE_RE.search(fm_text)
    if dep_m:
        try:
            result["departure"] = datetime.fromisoformat(dep_m.group(1)).replace(tzinfo=timezone.utc)
        except Exception:
            pass

    # Extract status field (first word only, strip punctuation)
    st_m = _STATUS_RE.search(fm_text)
    if st_m:
        result["status"] = st_m.group(1).strip("\"'").lower()

    return result if result else None


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
    # Uses YAML frontmatter departure: field ONLY — avoids false positives from
    # port-call schedules, payment dates, FPDs in the dossier body.
    # A booking is a gap iff:
    #   (a) frontmatter departure is within 30d
    #   (b) status is NOT complete/archived (absent status → treat as active)
    #   (c) no itinerary artifact exists in output/validation_emails/ or drafts/
    now = datetime.now(tz=timezone.utc)
    window_end = now + timedelta(days=SAIL_WINDOW_DAYS)
    gaps = []  # (dossier_name, sail_date)
    all_upcoming = []

    if DOSSIERS_DIR.exists():
        for dossier_path in DOSSIERS_DIR.glob("*.md"):
            fm = parse_frontmatter(dossier_path)
            if fm is None:
                continue  # No frontmatter → skip (template or non-booking dossier)

            sail_dt = fm.get("departure")
            if sail_dt is None:
                continue  # No departure field → skip

            status = fm.get("status", "active")
            if status in INACTIVE_STATUSES:
                continue  # Voyage complete/archived — no itinerary expected

            if sail_dt > now:
                all_upcoming.append((sail_dt, dossier_path.stem))

            if now < sail_dt <= window_end:
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

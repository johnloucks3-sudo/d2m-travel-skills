"""Regression test for the cruise selector region-filter bug (2026-07-16).

Root cause: scripts/fetch_perx_sailings.py (silversea_perx, atlas_perx sources)
carried its own REGION_MAP with labels that diverged from the canonical
labels in scripts/build_master_cruise_db.py (e.g. "Asia Pacific" vs
"Asia & Pacific", "Northern Europe" vs "Baltic / Northern Europe", "World"
vs "Other / World"). Both scripts write into the same cruises.region column,
so the divergence silently split what should be one region into two, and
the minority variant returned almost nothing when selected in the /cruises
region dropdown.
"""

import importlib.util
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_perx_region_labels_match_canonical_set():
    canonical = _load_module(ROOT / "scripts" / "build_master_cruise_db.py")
    perx = _load_module(ROOT / "scripts" / "fetch_perx_sailings.py")

    canonical_labels = {region for region, _ in canonical.REGION_MAP}
    canonical_labels.add("Other / World")  # canonical fallback

    perx_labels = {region for region, _ in perx.REGION_MAP}
    perx_labels.add(perx.infer_region("no keywords match anything here"))

    unknown = perx_labels - canonical_labels
    assert not unknown, (
        f"fetch_perx_sailings.py region labels diverge from canonical "
        f"build_master_cruise_db.py labels: {unknown}"
    )


def test_perx_fallback_is_canonical_other_world():
    perx = _load_module(ROOT / "scripts" / "fetch_perx_sailings.py")
    assert perx.infer_region("zzz no keyword matches zzz") == "Other / World"


def test_live_db_has_no_duplicate_region_labels():
    db_path = ROOT / "output" / "cruises.db"
    if not db_path.exists():
        return  # DB not built in this environment; nothing to check
    conn = sqlite3.connect(db_path)
    regions = {r[0] for r in conn.execute(
        "SELECT DISTINCT region FROM cruises WHERE region != ''"
    )}
    conn.close()

    known_near_duplicates = [
        {"Asia Pacific", "Asia & Pacific"},
        {"Northern Europe", "Baltic / N. Europe", "Baltic / Northern Europe"},
        {"World", "Other / World"},
    ]
    for group in known_near_duplicates:
        present = group & regions
        assert len(present) <= 1, (
            f"Duplicate region labels found in cruises.db: {present} "
            "(region-normalization regression)"
        )

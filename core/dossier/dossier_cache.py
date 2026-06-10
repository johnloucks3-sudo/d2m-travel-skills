"""
M-086 — Dossier Cache Layer
Dreams2Memories Travel, LLC

dict+pickle cache for dossier FPD and pricing data.
4-hour TTL. Invalidates per-file when mtime changes.

Usage:
    from core.dossier.dossier_cache import get_cache
    cache = get_cache()
    dossiers = cache.get_all()          # list of DossierRecord dicts
    record = cache.get("DOSSIER_SilverMuse_Mediterranean_Jun2026.md")
    cache.invalidate()                  # force full refresh
"""
import logging
import os
import pickle
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DOSSIER_DIR = Path(__file__).parents[2] / "dossiers"
CACHE_PATH  = Path(__file__).parent / ".dossier_cache.pkl"
CACHE_TTL   = timedelta(hours=4)

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}


@dataclass
class DossierRecord:
    filename: str
    client_label: str           # human-readable label derived from filename
    fpd: Optional[date]         # final payment deadline
    fpd_amount: Optional[float] # balance/amount due at FPD
    departure: Optional[date]   # embarkation date
    booking_refs: list          # booking reference numbers found
    raw_snippet: str            # first 400 chars for diagnostics
    parsed_at: datetime = field(default_factory=datetime.now)


def _parse_iso(s: str) -> Optional[date]:
    try:
        return date.fromisoformat(s.strip())
    except (ValueError, AttributeError):
        return None


def _parse_natural_date(s: str, ref_year: int = None) -> Optional[date]:
    """Parse 'June 23, 2026', 'Jun 18', 'December 17, 2026' etc."""
    if ref_year is None:
        ref_year = date.today().year
    s = s.strip()
    m = re.match(r'([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})', s)
    if m:
        mon = MONTHS.get(m.group(1).lower())
        if mon:
            try:
                return date(int(m.group(3)), mon, int(m.group(2)))
            except ValueError:
                pass
    m = re.match(r'([A-Za-z]+)\s+(\d{1,2})', s)
    if m:
        mon = MONTHS.get(m.group(1).lower())
        if mon:
            try:
                return date(ref_year, mon, int(m.group(2)))
            except ValueError:
                pass
    return None


def _extract_fpd_from_text(text: str) -> tuple[Optional[date], Optional[float]]:
    """Extract FPD date and amount from dossier markdown text."""
    # Pattern 1 — YAML frontmatter: fpd: 2026-04-01
    m = re.search(r'^fpd:\s*(\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
    if m:
        fpd = _parse_iso(m.group(1))
        # Try fpd_amount from YAML
        am = re.search(r'^fpd_amount:\s*([\d.]+)', text, re.MULTILINE)
        amount = float(am.group(1)) if am else None
        return fpd, amount

    # Pattern 2 — timeline row: YYYY-MM-DD ... FINAL PAYMENT DUE
    m = re.search(
        r'(\d{4}-\d{2}-\d{2})\s+\S+\s+\[payment\s*\]\s+FINAL PAYMENT DUE',
        text, re.IGNORECASE
    )
    if m:
        fpd = _parse_iso(m.group(1))
        # Look for dollar amount within 3 lines of the FPD line
        start = max(0, m.start() - 200)
        context = text[start:m.end() + 300]
        am = re.search(r'\$\s*([\d,]+(?:\.\d{2})?)', context)
        amount = float(am.group(1).replace(",", "")) if am else None
        return fpd, amount

    # Pattern 3 — inline: "FPD: April 1" or "Final Payment: Aug 1, 2026"
    m = re.search(
        r'(?:FPD|Final\s+Payment(?:\s+Due)?)\s*[:\-–]\s*([A-Za-z]+ \d{1,2}(?:,\s*\d{4})?)',
        text, re.IGNORECASE
    )
    if m:
        fpd = _parse_natural_date(m.group(1))
        am = re.search(r'\$\s*([\d,]+(?:\.\d{2})?)', text[m.start():m.end() + 200])
        amount = float(am.group(1).replace(",", "")) if am else None
        return fpd, amount

    return None, None


def _extract_departure(text: str) -> Optional[date]:
    """Extract embarkation/departure date from dossier."""
    # YAML frontmatter
    m = re.search(r'^departure:\s*(\d{4}-\d{2}-\d{2})', text, re.MULTILINE)
    if m:
        return _parse_iso(m.group(1))

    # Inline: Embarkation: June 23, 2026
    m = re.search(
        r'[Ee]mbarkation\s*[:\-–]\s*([A-Za-z]+ \d{1,2}(?:,\s*\d{4})?)',
        text
    )
    if m:
        return _parse_natural_date(m.group(1))

    # Departure date: YYYY-MM-DD line
    m = re.search(r'[Dd]eparture(?:\s+date)?\s*[:\-–]\s*(\d{4}-\d{2}-\d{2})', text)
    if m:
        return _parse_iso(m.group(1))

    return None


def _extract_booking_refs(text: str) -> list:
    """Extract booking reference numbers (7-digit TESS IDs or named refs)."""
    refs = re.findall(r'\b([A-Z]{2}\d{4,6}|\d{7})\b', text)
    return list(set(refs))[:6]


def _make_label(filename: str) -> str:
    """DOSSIER_SilverMuse_Mediterranean_Jun2026.md → SilverMuse Mediterranean Jun2026"""
    name = Path(filename).stem
    name = re.sub(r'^DOSSIER_', '', name)
    return name.replace('_', ' ')


def parse_dossier(path: Path) -> DossierRecord:
    """Parse a single dossier file into a DossierRecord."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning("Cannot read %s: %s", path.name, e)
        text = ""

    fpd, fpd_amount = _extract_fpd_from_text(text)
    departure = _extract_departure(text)
    booking_refs = _extract_booking_refs(text)
    raw_snippet = text[:400].replace("\n", " ")

    return DossierRecord(
        filename=path.name,
        client_label=_make_label(path.name),
        fpd=fpd,
        fpd_amount=fpd_amount,
        departure=departure,
        booking_refs=booking_refs,
        raw_snippet=raw_snippet,
    )


class DossierCache:
    """
    dict+pickle cache for parsed dossier records.
    Keyed by filename. Each entry: {mtime, record}.
    Full cache written to CACHE_PATH after every refresh.
    """

    def __init__(self, dossier_dir: Path = DOSSIER_DIR, cache_path: Path = CACHE_PATH):
        self._dir = dossier_dir
        self._path = cache_path
        self._store: dict[str, dict] = {}  # filename → {mtime, record, loaded_at}
        self._loaded_at: Optional[datetime] = None
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, "rb") as f:
                    data = pickle.load(f)
                self._store = data.get("store", {})
                self._loaded_at = data.get("loaded_at")
                logger.debug("Cache loaded from disk: %d entries", len(self._store))
            except Exception as e:
                logger.warning("Cache load failed, starting fresh: %s", e)
                self._store = {}
                self._loaded_at = None

    def _save_to_disk(self) -> None:
        try:
            with open(self._path, "wb") as f:
                pickle.dump({"store": self._store, "loaded_at": datetime.now()}, f)
        except Exception as e:
            logger.warning("Cache save failed: %s", e)

    def _is_stale(self) -> bool:
        if self._loaded_at is None:
            return True
        return datetime.now() - self._loaded_at > CACHE_TTL

    def _refresh_entry(self, path: Path) -> DossierRecord:
        mtime = path.stat().st_mtime
        entry = self._store.get(path.name)
        if entry and entry["mtime"] == mtime:
            return entry["record"]
        record = parse_dossier(path)
        self._store[path.name] = {"mtime": mtime, "record": record}
        logger.debug("Refreshed cache entry: %s", path.name)
        return record

    def get_all(self, skip_prospects: bool = True) -> list[DossierRecord]:
        """Return all dossier records, refreshing stale entries."""
        if not self._dir.exists():
            logger.error("Dossier directory not found: %s", self._dir)
            return []

        records = []
        for md_path in sorted(self._dir.glob("*.md")):
            if skip_prospects and md_path.parent.name == "prospects":
                continue
            if md_path.name == "CLAUDE.md":
                continue
            try:
                records.append(self._refresh_entry(md_path))
            except Exception as e:
                logger.warning("Skipped %s: %s", md_path.name, e)

        self._loaded_at = datetime.now()
        self._save_to_disk()
        return records

    def get(self, filename: str) -> Optional[DossierRecord]:
        """Get a single dossier record by filename, refreshing if stale."""
        path = self._dir / filename
        if not path.exists():
            return None
        return self._refresh_entry(path)

    def invalidate(self, filename: str = None) -> None:
        """Force refresh. Pass filename to invalidate one entry, or None for all."""
        if filename:
            self._store.pop(filename, None)
            logger.info("Invalidated cache entry: %s", filename)
        else:
            self._store.clear()
            self._loaded_at = None
            if self._path.exists():
                self._path.unlink()
            logger.info("Full cache invalidated")

    def stats(self) -> dict:
        return {
            "entries": len(self._store),
            "loaded_at": self._loaded_at.isoformat() if self._loaded_at else None,
            "ttl_hours": CACHE_TTL.total_seconds() / 3600,
            "cache_path": str(self._path),
        }


_cache_instance: Optional[DossierCache] = None


def get_cache() -> DossierCache:
    """Return the singleton DossierCache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DossierCache()
    return _cache_instance


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cache = DossierCache()
    records = cache.get_all()
    print(f"\n{'='*60}")
    print(f"Dossier Cache — {len(records)} records")
    print(f"{'='*60}")
    for r in records:
        fpd_str = r.fpd.isoformat() if r.fpd else "—"
        dep_str = r.departure.isoformat() if r.departure else "—"
        amt_str = f"${r.fpd_amount:,.0f}" if r.fpd_amount else "—"
        print(f"  {r.client_label:<40} FPD: {fpd_str:<12} Amt: {amt_str:<12} Dep: {dep_str}")
    print(f"\nCache stats: {json.dumps(cache.stats(), indent=2)}")

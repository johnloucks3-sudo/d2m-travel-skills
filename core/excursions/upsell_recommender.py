"""Shore excursion upsell recommendation engine.

Reads real client dossiers (`dossiers/*.md` frontmatter + body) and real
excursion catalog scrapes (`cache/pe_*.json`) already on disk. No synthetic
client data — every recommendation traces to a dossier path and, where a
catalog exists, a scraped listing.

Scoring is rule-based (see `_score`), not a trained model — there is no
acceptance-rate history anywhere in this repo yet to train against. See
`test_upsell_recommender.py` for the honest readiness metric this produces
in place of a fabricated acceptance rate.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

THUNDERBIRD_DIR = Path(__file__).resolve().parents[2]
DOSSIERS_DIR = THUNDERBIRD_DIR / "dossiers"
CACHE_DIR = THUNDERBIRD_DIR / "cache"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "excursion_upsells.json"

# Catalog cache files use scrape-run naming, not the dossier `client:` key,
# so the mapping is maintained here rather than derived. Both are real
# scraped catalogs already on disk (Project Expedition, port-keyed).
CATALOG_REGISTRY: dict[str, Path] = {
    "loucks silver nova may 2027": CACHE_DIR / "pe_excursions_loucks_may2027.json",
    "kuklinski": CACHE_DIR / "pe_kuklinski_panama_dec2026.json",
}

PREMIUM_SPEND_THRESHOLD_PP = 200.0

TIER_BASE_SCORE = {
    "PREMIUM": 70.0,
    "COMBO_SAVINGS": 55.0,
    "LIGHT_UPSELL": 35.0,
    "EXCLUDED_PRO_BONO": 0.0,
}

CONFIDENCE_BONUS = {
    "CONFIRMED": 10.0,
    "CONFIRMED_ZERO_ALL_INCLUSIVE": 5.0,
    "UNKNOWN": 0.0,
}


@dataclass
class CatalogEntry:
    port: str
    name: str
    price: float
    is_private: bool
    source_file: str


@dataclass
class ClientProfile:
    key: str
    dossier_path: str
    full_name: str
    cruise_line: Optional[str]
    voyage: Optional[str]
    relationship: Optional[str]
    payment_status: Optional[str]
    prior_spend_pp: Optional[float]
    prior_spend_confidence: str  # CONFIRMED | CONFIRMED_ZERO_ALL_INCLUSIVE | UNKNOWN
    is_repeat_client: bool


@dataclass
class UpsellRecommendation:
    excursion_id: str
    client: str
    port: str
    base_excursion: str
    upsell_option: str
    recommendation_score: float
    estimated_spend: Optional[float]
    tier: str
    confidence: str
    source: str

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- parsing --

def _parse_frontmatter(text: str) -> dict:
    """Minimal `key: value` frontmatter parser — no external YAML dep."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    fm: dict = {}
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"')
        if key and key not in fm:
            fm[key] = value
    return fm


_ALL_INCLUSIVE_RE = re.compile(r"(?:regent choice|included|complimentary)[^\n$]*\$\s*0(?:\.00)?", re.IGNORECASE)
_PAID_EXCURSION_RE = re.compile(r"excursion[^\n]{0,60}\$\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)


def _detect_prior_spend(body: str) -> tuple[Optional[float], str]:
    """Look for confirmed excursion spend evidence in the dossier body.

    Ordering matters: an explicit all-inclusive marker ($0, Regent Choice)
    is itself a confirmed data point, distinct from no data being present.
    """
    if _ALL_INCLUSIVE_RE.search(body):
        return 0.0, "CONFIRMED_ZERO_ALL_INCLUSIVE"
    amounts = [
        float(m.replace(",", ""))
        for m in _PAID_EXCURSION_RE.findall(body)
        if float(m.replace(",", "")) > 0
    ]
    if amounts:
        return sum(amounts) / len(amounts), "CONFIRMED"
    return None, "UNKNOWN"


def _load_all_dossiers() -> list[tuple[Path, dict, str]]:
    out = []
    for path in sorted(DOSSIERS_DIR.glob("*.md")):
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        fm = _parse_frontmatter(text)
        out.append((path, fm, text))
    return out


def _is_canonical_booking_dossier(fm: dict) -> bool:
    """A one-booking-per-dossier file (has a `booking` ref), OR an explicit
    friend/pro-bono relationship (kept even without a booking ref so the
    no-upsell exclusion path is exercised against real files, not skipped).
    Filters out rollup/group/logistics/timeline dossiers that duplicate a
    booking already represented by its own per-couple dossier."""
    if fm.get("status") == "prospect":
        return False
    if fm.get("relationship") == "friend":
        return True
    if not (fm.get("payment_status") or fm.get("status") in {"active", "pro_bono"}):
        return False
    return bool(fm.get("booking"))


def load_client_profiles() -> list[ClientProfile]:
    """Real, active/pro-bono client bookings only — prospects, test
    fixtures, and non-canonical rollup/logistics dossiers are excluded."""
    all_dossiers = _load_all_dossiers()

    # Repeat-client detection: count real bookings per full_name.
    name_counts: dict[str, int] = {}
    for _, fm, _ in all_dossiers:
        if not _is_canonical_booking_dossier(fm):
            continue
        name = fm.get("full_name") or fm.get("client")
        if not name:
            continue
        name_counts[name] = name_counts.get(name, 0) + 1

    profiles: list[ClientProfile] = []
    for path, fm, text in all_dossiers:
        if not _is_canonical_booking_dossier(fm):
            continue
        full_name = fm.get("full_name") or fm.get("client")
        if not full_name:
            continue
        prior_spend, confidence = _detect_prior_spend(text)
        profiles.append(
            ClientProfile(
                key=fm.get("client", full_name),
                dossier_path=str(path.relative_to(THUNDERBIRD_DIR)),
                full_name=full_name,
                cruise_line=fm.get("cruise_line"),
                voyage=fm.get("voyage"),
                relationship=fm.get("relationship"),
                payment_status=fm.get("payment_status"),
                prior_spend_pp=prior_spend,
                prior_spend_confidence=confidence,
                is_repeat_client=name_counts.get(full_name, 0) > 1,
            )
        )
    return profiles


# --------------------------------------------------------------- catalog --

def _normalize_catalog_file(path: Path) -> list[CatalogEntry]:
    """Normalizes the two real catalog schemas found in cache/pe_*.json.

    Schema A (e.g. pe_excursions_loucks_may2027.json): per-port dict with
    "top": [{"name","price","priv": bool}, ...].
    Schema B (e.g. pe_kuklinski_panama_dec2026.json): per-port list of
    {"name","price_pp", ...} with private tours identified by name.
    """
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    entries: list[CatalogEntry] = []
    for port, value in data.items():
        if isinstance(value, dict):
            if value.get("status") and "top" not in value:
                continue  # failed scrape (no_id, redir-loop, etc.)
            for item in value.get("top", []):
                entries.append(
                    CatalogEntry(
                        port=port,
                        name=item["name"],
                        price=float(item.get("price", 0)),
                        is_private=bool(item.get("priv")) or "private" in item["name"].lower(),
                        source_file=path.name,
                    )
                )
        elif isinstance(value, list):
            for item in value:
                price = item.get("price_pp") or item.get("price") or 0
                entries.append(
                    CatalogEntry(
                        port=port,
                        name=item["name"],
                        price=float(price),
                        is_private="private" in item["name"].lower(),
                        source_file=path.name,
                    )
                )
    return entries


def load_catalog_for_client(client_key: str) -> list[CatalogEntry]:
    key = client_key.strip().lower()
    for registry_key, path in CATALOG_REGISTRY.items():
        if registry_key in key or key in registry_key:
            return _normalize_catalog_file(path)
    return []


# ------------------------------------------------------------- scoring ---

def _score(tier: str, confidence: str, price_delta: float) -> float:
    score = TIER_BASE_SCORE[tier] + CONFIDENCE_BONUS[confidence]
    score += min(20.0, price_delta / 50.0)
    return round(min(100.0, max(0.0, score)), 1)


def recommend_for_client(profile: ClientProfile) -> list[UpsellRecommendation]:
    # Lyons-type: relationship recorded as "friend" with no payment_status
    # (D2M has zero booking involvement). Explicit no-upsell, no financial
    # pressure on a pro-bono relationship (see feedback_lyons_probono_no_fpd).
    is_pro_bono = profile.relationship == "friend" and profile.payment_status is None
    catalog = load_catalog_for_client(profile.key)

    if is_pro_bono:
        return [
            UpsellRecommendation(
                excursion_id=f"{profile.key}-PROBONO",
                client=profile.full_name,
                port="N/A",
                base_excursion="N/A",
                upsell_option="NONE — pro bono / friend relationship, no revenue upsell",
                recommendation_score=0.0,
                estimated_spend=None,
                tier="EXCLUDED_PRO_BONO",
                confidence=profile.prior_spend_confidence,
                source=profile.dossier_path,
            )
        ]

    if profile.prior_spend_pp is not None and profile.prior_spend_pp > PREMIUM_SPEND_THRESHOLD_PP:
        tier = "PREMIUM"
    elif not profile.is_repeat_client:
        tier = "COMBO_SAVINGS"
    else:
        tier = "LIGHT_UPSELL"

    if not catalog:
        base_spend = profile.prior_spend_pp or 0.0
        return [
            UpsellRecommendation(
                excursion_id=f"{profile.key}-NOCATALOG",
                client=profile.full_name,
                port="N/A",
                base_excursion="(no catalog scrape on file for this voyage)",
                upsell_option="Route to Reyes (A8) for live port-by-port quote — no scraped catalog available",
                recommendation_score=_score(tier, profile.prior_spend_confidence, 0.0),
                estimated_spend=None,
                tier=tier,
                confidence=profile.prior_spend_confidence,
                source=profile.dossier_path,
            )
        ]

    recs: list[UpsellRecommendation] = []
    by_port: dict[str, list[CatalogEntry]] = {}
    for entry in catalog:
        if entry.price <= 0:
            continue  # transfer/free listings scraped alongside tours — not sellable upsells
        by_port.setdefault(entry.port, []).append(entry)

    for port, entries in by_port.items():
        entries_sorted = sorted(entries, key=lambda e: e.price, reverse=True)
        if tier == "PREMIUM":
            candidates = [e for e in entries_sorted if e.is_private][:2]
        elif tier == "COMBO_SAVINGS":
            candidates = entries_sorted[-2:]  # lower-priced pair to bundle
        else:
            candidates = entries_sorted[:1]
        if not candidates:
            candidates = entries_sorted[:1]

        base_spend = profile.prior_spend_pp or 0.0
        for entry in candidates:
            if tier == "COMBO_SAVINGS" and len(candidates) == 2:
                combo_total = round(sum(c.price for c in candidates) * 0.90, 2)  # 10% bundle discount, labeled
                upsell_option = f"Combo bundle: {' + '.join(c.name for c in candidates)} (~10% bundle savings)"
                estimated_spend = combo_total
            else:
                upsell_option = entry.name + (" (private tour)" if entry.is_private else "")
                estimated_spend = entry.price

            price_delta = max(0.0, estimated_spend - base_spend)
            recs.append(
                UpsellRecommendation(
                    excursion_id=f"{profile.key}-{port}-{entry.name[:24]}".replace(" ", "_"),
                    client=profile.full_name,
                    port=port,
                    base_excursion=f"prior avg spend ${base_spend:.0f}/pp ({profile.prior_spend_confidence})",
                    upsell_option=upsell_option,
                    recommendation_score=_score(tier, profile.prior_spend_confidence, price_delta),
                    estimated_spend=estimated_spend,
                    tier=tier,
                    confidence=profile.prior_spend_confidence,
                    source=f"{profile.dossier_path} + {entry.source_file}",
                )
            )
            if tier == "COMBO_SAVINGS":
                break  # one combo record per port, not one per candidate
    return recs


def build_all_recommendations() -> list[UpsellRecommendation]:
    all_recs: list[UpsellRecommendation] = []
    for profile in load_client_profiles():
        all_recs.extend(recommend_for_client(profile))
    return all_recs


def write_output(records: list[UpsellRecommendation], path: Path = DEFAULT_OUTPUT) -> Path:
    path.write_text(json.dumps([r.to_dict() for r in records], indent=2))
    return path


# -------------------------------------------------- TP template hand-off --

def budget_guidance_facts(client_key: str) -> dict:
    """Structured facts for the `{{PAID_EXCURSION_BUDGET_GUIDANCE}}` slot in
    tp_2_1_excursion_planning.html. Returns DATA only — Reyes (A8)/Dani own
    turning this into client-facing prose (creative-chain rule, Failure A).
    """
    for profile in load_client_profiles():
        if profile.key.lower() == client_key.lower():
            recs = recommend_for_client(profile)
            top = max(recs, key=lambda r: r.recommendation_score, default=None)
            return {
                "tier": top.tier if top else None,
                "top_upsell_option": top.upsell_option if top else None,
                "estimated_spend": top.estimated_spend if top else None,
                "confidence": top.confidence if top else None,
                "source": top.source if top else None,
            }
    return {"tier": None, "top_upsell_option": None, "estimated_spend": None,
             "confidence": "UNKNOWN", "source": None}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Shore excursion upsell recommender")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    records = build_all_recommendations()
    out_path = write_output(records, args.out)
    print(f"Wrote {len(records)} recommendations for "
          f"{len({r.client for r in records})} clients -> {out_path}")


if __name__ == "__main__":
    main()

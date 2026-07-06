"""
core/ml/demand_predictor.py — RandomForest cruise demand forecasting.

DATA REALITY (recorded 2026-07-06, do not re-derive from scratch):
The only booking source in this repo (output/tess_map/booking_master_dump.json)
has 34 rows, all CONFIRMED bookings — no lost-inquiry ("did not book") records
and no multi-year history (earliest Created_Date is 2026). A booking-probability
classifier needs both classes to fit at all; a real demand-volume regressor
needs a monthly time series spanning years. Neither exists yet.

This module implements the full pipeline (feature engineering, RandomForest
train/predict, time-based holdout evaluation, JSON forecast output) so it runs
correctly the moment real volume exists. Every output carries a
`data_sufficiency` field — segments below MIN_SAMPLES_PER_SEGMENT are tagged
INSUFFICIENT_DATA rather than presented as a trustworthy number. Never remove
that tag to make output look more finished; that would be exactly the
fabricated-metric failure this doctrine (see CLAUDE.md persona health audit
rule) exists to prevent.

Training table granularity: one row per (destination, season, cruise_line,
departure_year_month) with target = booking count in that month for that
segment. A per-segment-only table (no time axis) can't be evaluated with a
real 6-month holdout, because held-out segments would be entirely unseen
combinations the model has no way to generalize to — the holdout would be
measuring interpolation across categories, not forecasting. Aggregating by
month lets the same segment recur across many periods, so a time-ordered
holdout (train on early months, forecast the last N) tests what the spec
actually asks for.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BOOKING_SOURCE = REPO_ROOT / "output" / "tess_map" / "booking_master_dump.json"
MODEL_DIR = REPO_ROOT / "core" / "ml" / "models"
MODEL_PATH = MODEL_DIR / "demand_predictor.joblib"
FORECAST_DIR = REPO_ROOT / "output" / "ml_forecasts"

# Below this many bookings in a destination/season/cruise_line segment, a
# prediction for that segment is statistically unreliable and gets flagged.
MIN_SAMPLES_PER_SEGMENT = 30

# Minimum distinct calendar months required before a time-based holdout is
# attempted at all. Below this, train() fits on everything and says so.
MIN_MONTHS_FOR_HOLDOUT = 8
DEFAULT_HOLDOUT_MONTHS = 6

SEASON_BY_MONTH = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "fall", 10: "fall", 11: "fall",
}

_DATE_FORMATS = ("%d-%b-%y", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%Y-%m-%d")


def _parse_date(value) -> Optional[date]:
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_money(value) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _month_ordinal(year: int, month: int) -> int:
    """Months since year 0 — a monotonic integer time axis a tree can split on."""
    return year * 12 + (month - 1)


@dataclass
class BookingRecord:
    destination: str
    cruise_line: str
    season: str
    start_date: date
    created_date: Optional[date]
    days_to_departure: Optional[int]
    amount_paid: Optional[float]


def load_booking_records(source: Path = DEFAULT_BOOKING_SOURCE) -> list[BookingRecord]:
    """Parse the booking master export into BookingRecords.

    Tolerant by design — the export's columns are inconsistently populated
    (see module docstring), so any row missing a usable Start_Date is skipped
    rather than raising.
    """
    payload = json.loads(Path(source).read_text())
    rows = payload.get("rows", payload if isinstance(payload, list) else [])

    records = []
    for row in rows:
        start = _parse_date(row.get("Start_Date"))
        if not start:
            continue
        created = _parse_date(row.get("Created_Date"))
        destination = (row.get("Destination") or row.get("Trip_Name") or "Unknown").strip() or "Unknown"
        cruise_line = (row.get("Supplier") or row.get("Ship_Name") or "Unknown").strip() or "Unknown"
        days_out = (start - created).days if created else None
        amount = _parse_money(row.get("Amount_Paid"))
        records.append(BookingRecord(
            destination=destination,
            cruise_line=cruise_line,
            season=SEASON_BY_MONTH[start.month],
            start_date=start,
            created_date=created,
            days_to_departure=days_out,
            amount_paid=amount,
        ))
    return records


class _CategoryEncoder:
    """Minimal label encoder that maps unseen categories to a fixed OOV index."""

    def __init__(self, values: list[str]):
        uniques = sorted(set(values)) or ["Unknown"]
        self.index = {v: i for i, v in enumerate(uniques)}
        self.oov = len(uniques)

    def transform(self, value: str) -> int:
        return self.index.get(value, self.oov)


def _monthly_aggregate(records: list[BookingRecord]) -> dict[tuple, dict]:
    """Group bookings into (destination, season, cruise_line, year, month) rows."""
    grouped: dict[tuple, dict] = {}
    for r in records:
        key = (r.destination, r.season, r.cruise_line, r.start_date.year, r.start_date.month)
        g = grouped.setdefault(key, {"count": 0, "amounts": [], "lead_times": []})
        g["count"] += 1
        if r.amount_paid is not None:
            g["amounts"].append(r.amount_paid)
        if r.days_to_departure is not None:
            g["lead_times"].append(r.days_to_departure)
    return grouped


def _segment_summary(records: list[BookingRecord]) -> dict[tuple, dict]:
    """Overall (all-time) stats per (destination, season, cruise_line) segment,
    used for observed-volume reporting and demand_score normalization."""
    summary: dict[tuple, dict] = {}
    for r in records:
        key = (r.destination, r.season, r.cruise_line)
        s = summary.setdefault(key, {"count": 0, "amounts": [], "lead_times": []})
        s["count"] += 1
        if r.amount_paid is not None:
            s["amounts"].append(r.amount_paid)
        if r.days_to_departure is not None:
            s["lead_times"].append(r.days_to_departure)
    return summary


class DemandPredictor:
    """RandomForest-backed monthly demand model.

    Target: booking count per (destination, season, cruise_line) for a given
    departure year-month — a defensible regression target given only
    won-booking data. A true booking-probability classifier requires labeled
    lost inquiries, which the Wing does not capture yet (see module
    docstring). `predict()` derives a 0-1 "demand_score" by normalizing the
    regressor's count prediction against the max observed segment-month
    count, and is explicit about that derivation rather than presenting it
    as a calibrated probability.
    """

    def __init__(self, model_dir: Path = MODEL_DIR):
        self.model_dir = Path(model_dir)
        self.model: Optional[RandomForestRegressor] = None
        self.dest_encoder: Optional[_CategoryEncoder] = None
        self.season_encoder: Optional[_CategoryEncoder] = None
        self.line_encoder: Optional[_CategoryEncoder] = None
        self.max_segment_month_count: int = 1
        self.segment_summary: dict = {}
        self.n_training_records: int = 0
        self.trained_at: Optional[str] = None

    # -- feature engineering -------------------------------------------------

    def _fit_encoders(self, records: list[BookingRecord]) -> None:
        self.dest_encoder = _CategoryEncoder([r.destination for r in records])
        self.season_encoder = _CategoryEncoder([r.season for r in records])
        self.line_encoder = _CategoryEncoder([r.cruise_line for r in records])

    def _feature_row(self, destination: str, season: str, cruise_line: str,
                      year: int, month: int, avg_lead_time: float, avg_amount: float) -> list[float]:
        return [
            self.dest_encoder.transform(destination),
            self.season_encoder.transform(season),
            self.line_encoder.transform(cruise_line),
            _month_ordinal(year, month),
            month,  # calendar month (1-12) captures seasonality independent of trend
            avg_lead_time,
            avg_amount,
        ]

    def build_training_table(self, records: list[BookingRecord]) -> tuple[np.ndarray, np.ndarray, list[int]]:
        """Returns (X, y, month_ordinals) — month_ordinals lines up 1:1 with
        rows so callers can build a time-based (not random) holdout split."""
        self._fit_encoders(records)
        monthly = _monthly_aggregate(records)
        self.segment_summary = _segment_summary(records)
        self.max_segment_month_count = max((g["count"] for g in monthly.values()), default=1)

        X, y, month_ords = [], [], []
        for (destination, season, cruise_line, year, month), stats in monthly.items():
            avg_lead = float(np.mean(stats["lead_times"])) if stats["lead_times"] else 0.0
            avg_amount = float(np.mean(stats["amounts"])) if stats["amounts"] else 0.0
            X.append(self._feature_row(destination, season, cruise_line, year, month, avg_lead, avg_amount))
            y.append(stats["count"])
            month_ords.append(_month_ordinal(year, month))
        return np.array(X, dtype=float), np.array(y, dtype=float), month_ords

    # -- train / evaluate -----------------------------------------------------

    def train(self, records: Optional[list[BookingRecord]] = None,
              source: Path = DEFAULT_BOOKING_SOURCE, n_estimators: int = 200,
              random_state: int = 42, holdout_months: int = DEFAULT_HOLDOUT_MONTHS) -> dict:
        if records is None:
            records = load_booking_records(source)
        self.n_training_records = len(records)

        X, y, month_ords = self.build_training_table(records)
        n_rows = len(X)
        distinct_months = sorted(set(month_ords))

        metrics = {
            "n_training_records": self.n_training_records,
            "n_segment_month_rows": n_rows,
            "n_distinct_months": len(distinct_months),
            "data_sufficiency": ("SUFFICIENT" if self.n_training_records >= MIN_SAMPLES_PER_SEGMENT * 3
                                  else "INSUFFICIENT_DATA"),
        }

        if len(distinct_months) < MIN_MONTHS_FOR_HOLDOUT:
            self.model = RandomForestRegressor(n_estimators=n_estimators, random_state=random_state)
            self.model.fit(X, y)
            metrics["rmse_holdout"] = None
            metrics["rmse_note"] = (
                f"only {len(distinct_months)} distinct months of history — "
                f"need >= {MIN_MONTHS_FOR_HOLDOUT} for a meaningful time-based holdout; "
                "trained on all data"
            )
        else:
            cutoff = distinct_months[-holdout_months]
            month_arr = np.array(month_ords)
            train_mask = month_arr < cutoff
            test_mask = ~train_mask

            self.model = RandomForestRegressor(n_estimators=n_estimators, random_state=random_state)
            self.model.fit(X[train_mask], y[train_mask])
            preds = self.model.predict(X[test_mask])
            rmse = float(np.sqrt(mean_squared_error(y[test_mask], preds)))
            metrics["holdout_months"] = holdout_months
            metrics["rmse_holdout"] = rmse
            metrics["rmse_pct_of_mean"] = float(rmse / max(np.mean(y[test_mask]), 1e-9) * 100)
            # Refit on full data for the deployed model.
            self.model.fit(X, y)

        self.trained_at = datetime.now(timezone.utc).isoformat()
        return metrics

    def save(self, path: Path = MODEL_PATH) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": self.model,
            "dest_encoder": self.dest_encoder,
            "season_encoder": self.season_encoder,
            "line_encoder": self.line_encoder,
            "max_segment_month_count": self.max_segment_month_count,
            "segment_summary": self.segment_summary,
            "n_training_records": self.n_training_records,
            "trained_at": self.trained_at,
        }, path)
        return path

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "DemandPredictor":
        # joblib.load deserializes via pickle — safe here because MODEL_PATH is
        # only ever written by this module's own save() (core/ml/models/, not
        # user- or network-supplied input). Never point this at an untrusted path.
        payload = joblib.load(Path(path))
        predictor = cls()
        predictor.model = payload["model"]
        predictor.dest_encoder = payload["dest_encoder"]
        predictor.season_encoder = payload["season_encoder"]
        predictor.line_encoder = payload["line_encoder"]
        predictor.max_segment_month_count = payload["max_segment_month_count"]
        predictor.segment_summary = payload["segment_summary"]
        predictor.n_training_records = payload["n_training_records"]
        predictor.trained_at = payload["trained_at"]
        return predictor

    # -- predict ---------------------------------------------------------------

    def predict(self, destination: str, season: str, cruise_line: str,
                target_year: int, target_month: int) -> dict:
        if self.model is None:
            raise RuntimeError("DemandPredictor.train() or .load() must run before predict()")

        seg_key = (destination, season, cruise_line)
        summary = self.segment_summary.get(seg_key, {"count": 0, "amounts": [], "lead_times": []})
        avg_lead = float(np.mean(summary["lead_times"])) if summary["lead_times"] else 0.0
        avg_amount = float(np.mean(summary["amounts"])) if summary["amounts"] else 0.0

        row = np.array([self._feature_row(destination, season, cruise_line,
                                           target_year, target_month, avg_lead, avg_amount)])
        predicted_count = float(self.model.predict(row)[0])
        demand_score = float(min(max(predicted_count / self.max_segment_month_count, 0.0), 1.0))

        n_observed = summary["count"]
        sufficiency = "SUFFICIENT" if n_observed >= MIN_SAMPLES_PER_SEGMENT else "INSUFFICIENT_DATA"

        # Simple, explainable pricing signal: high relative demand -> room to
        # raise price; low relative demand -> discount to move inventory.
        pricing_action = "hold"
        if sufficiency == "SUFFICIENT":
            if demand_score >= 0.7:
                pricing_action = "increase_15pct"
            elif demand_score <= 0.2:
                pricing_action = "decrease_10pct"

        return {
            "destination": destination,
            "season": season,
            "cruise_line": cruise_line,
            "target_year_month": f"{target_year:04d}-{target_month:02d}",
            "demand_score": round(demand_score, 4),
            "predicted_month_bookings": round(predicted_count, 2),
            "observed_segment_bookings_all_time": n_observed,
            "avg_days_to_departure_at_booking": round(avg_lead, 1),
            "recommended_pricing_action": pricing_action,
            "data_sufficiency": sufficiency,
        }

    # -- forecast output ---------------------------------------------------------

    def generate_forecast(self, out_dir: Path = FORECAST_DIR, as_of: Optional[date] = None) -> Path:
        """Forecast next month's demand for every segment seen in training."""
        as_of = as_of or date.today()
        target_year, target_month = as_of.year, as_of.month

        predictions = [
            self.predict(destination, season, cruise_line, target_year, target_month)
            for (destination, season, cruise_line) in self.segment_summary
        ]
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model_trained_at": self.trained_at,
            "n_training_records": self.n_training_records,
            "overall_data_sufficiency": (
                "SUFFICIENT" if self.n_training_records >= MIN_SAMPLES_PER_SEGMENT * 3
                else "INSUFFICIENT_DATA — treat all scores below as directional only"
            ),
            "predictions": predictions,
        }
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"demand_forecast_{as_of.strftime('%Y-%m')}.json"
        out_path.write_text(json.dumps(payload, indent=2))
        return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and/or forecast cruise demand.")
    parser.add_argument("--source", type=Path, default=DEFAULT_BOOKING_SOURCE,
                        help="Path to booking master JSON export")
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH)
    parser.add_argument("--train", action="store_true", help="Retrain the model")
    parser.add_argument("--forecast", action="store_true", help="Write demand_forecast_YYYY-MM.json")
    args = parser.parse_args()

    if not args.train and not args.forecast:
        args.train = args.forecast = True  # default: full monthly job

    if args.train:
        predictor = DemandPredictor()
        metrics = predictor.train(source=args.source)
        predictor.save(args.model_path)
        print(f"[demand_predictor] trained on {metrics['n_training_records']} records "
              f"({metrics['data_sufficiency']}); rmse_holdout={metrics.get('rmse_holdout')}")
    else:
        predictor = DemandPredictor.load(args.model_path)

    if args.forecast:
        path = predictor.generate_forecast()
        print(f"[demand_predictor] forecast written to {path}")


if __name__ == "__main__":
    main()

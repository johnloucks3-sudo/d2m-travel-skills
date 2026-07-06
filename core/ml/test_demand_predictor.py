"""
Tests for core/ml/demand_predictor.py.

The synthetic datasets built below exist purely to exercise the pipeline at a
time-series volume the real booking source doesn't have yet (see
demand_predictor.py's module docstring: 34 rows, no multi-year history). Any
RMSE or demand_score asserted here is a claim about the *mechanism*, not
about real D2M booking behavior — do not cite these numbers outside this file.

Run with: python3 -m pytest core/ml/test_demand_predictor.py --import-mode=importlib
The --import-mode flag works around a pre-existing repo bug: core/ has no
__init__.py, so pytest's default import mode inserts core/ itself onto
sys.path, and core/signal + core/email then shadow the stdlib modules of the
same name, breaking numpy/scipy at import time. Fixing that repo-wide (adding
core/__init__.py) changes sys.path insertion for every test under core/ and
breaks other pre-existing tests that rely on bare `from X import` sibling
imports (e.g. core/test_schemas.py) — out of scope for this module; flagged
to Sterling separately rather than patched here.
"""

from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

import pytest

from core.ml.demand_predictor import (
    DemandPredictor,
    BookingRecord,
    MIN_SAMPLES_PER_SEGMENT,
    MIN_MONTHS_FOR_HOLDOUT,
    load_booking_records,
    DEFAULT_BOOKING_SOURCE,
)


def _synthetic_records(seed: int = 7) -> list[BookingRecord]:
    """Two segments with a deliberate, known signal spanning 3 months:
    Nordic/summer/Viking books ~5x more than Caribbean/winter/Carnival, so a
    fitted model's predictions should preserve that ordering."""
    rng = random.Random(seed)
    segments = {
        ("Nordic", "summer", "Viking"): 40,
        ("Caribbean", "winter", "Carnival"): 8,
    }
    records = []
    for (destination, season, cruise_line), per_month in segments.items():
        for month_offset in range(3):
            start_month = date(2024, 1, 1) + timedelta(days=31 * month_offset)
            for _ in range(per_month):
                lead = rng.randint(60, 400)
                start = start_month + timedelta(days=rng.randint(0, 27))
                created = start - timedelta(days=lead)
                records.append(BookingRecord(
                    destination=destination,
                    cruise_line=cruise_line,
                    season=season,
                    start_date=start,
                    created_date=created,
                    days_to_departure=lead,
                    amount_paid=rng.uniform(4000, 25000),
                ))
    return records


def _monthly_time_series_records(seed: int = 11, n_segments: int = 4,
                                  n_months: int = 18) -> list[BookingRecord]:
    """n_segments recurring destination/season/cruise_line combos, each with
    its own stable monthly booking rate plus small noise, across n_months —
    enough history for a real time-based train/holdout split."""
    rng = random.Random(seed)
    destinations = ["Nordic", "Caribbean", "Mediterranean", "Alaska"][:n_segments]
    seasons = ["summer", "winter", "fall", "summer"][:n_segments]
    lines = ["Viking", "Carnival", "Regent", "Silversea"][:n_segments]
    base_rates = [40, 15, 25, 30][:n_segments]

    records = []
    for seg_idx in range(n_segments):
        destination, season, cruise_line = destinations[seg_idx], seasons[seg_idx], lines[seg_idx]
        rate = base_rates[seg_idx]
        for month_offset in range(n_months):
            year = 2023 + (month_offset // 12)
            month = (month_offset % 12) + 1
            start_month = date(year, month, 1)
            count = max(1, rate + rng.randint(-2, 2))
            for _ in range(count):
                lead = rng.randint(60, 400)
                start = start_month + timedelta(days=rng.randint(0, 27))
                records.append(BookingRecord(
                    destination=destination,
                    cruise_line=cruise_line,
                    season=season,
                    start_date=start,
                    created_date=start - timedelta(days=lead),
                    days_to_departure=lead,
                    amount_paid=rng.uniform(4000, 25000),
                ))
    return records


def test_build_training_table_shapes():
    predictor = DemandPredictor()
    records = _synthetic_records()
    X, y, month_ords = predictor.build_training_table(records)
    assert X.shape[0] == 6  # 2 segments x 3 months each
    assert X.shape[1] == 7  # dest, season, line, month_ordinal, calendar_month, avg_lead, avg_amount
    assert y.shape[0] == 6
    assert len(month_ords) == 6


def test_train_below_holdout_threshold_trains_on_everything():
    predictor = DemandPredictor()
    metrics = predictor.train(records=_synthetic_records())  # only 3 months of history
    assert metrics["n_distinct_months"] < MIN_MONTHS_FOR_HOLDOUT
    assert metrics["rmse_holdout"] is None
    assert "distinct months" in metrics["rmse_note"]


def test_train_rmse_within_10pct_on_synthetic_time_series():
    """Matches the task spec's acceptance bar (RMSE < 10% of actual) against
    a synthetic 18-month time series with a real per-segment monthly rate —
    the real booking source doesn't have this much history yet (see
    demand_predictor.py docstring), so this validates the mechanism only."""
    predictor = DemandPredictor()
    metrics = predictor.train(records=_monthly_time_series_records(), holdout_months=6)

    assert metrics["n_distinct_months"] == 18
    assert metrics["holdout_months"] == 6
    assert metrics["rmse_holdout"] is not None
    assert metrics["rmse_pct_of_mean"] < 10.0


def test_predict_preserves_relative_demand_ordering():
    predictor = DemandPredictor()
    predictor.train(records=_synthetic_records())

    high = predictor.predict("Nordic", "summer", "Viking", 2024, 2)
    low = predictor.predict("Caribbean", "winter", "Carnival", 2024, 2)

    assert high["demand_score"] > low["demand_score"]
    assert high["data_sufficiency"] == "SUFFICIENT"       # 120 total >= MIN_SAMPLES_PER_SEGMENT
    assert low["data_sufficiency"] == "INSUFFICIENT_DATA"  # 24 total < MIN_SAMPLES_PER_SEGMENT
    assert high["recommended_pricing_action"] == "increase_15pct"
    # Below-threshold segments never get a pricing recommendation, even if
    # the raw score would otherwise trigger one.
    assert low["recommended_pricing_action"] == "hold"


def test_predict_unseen_segment_does_not_crash():
    predictor = DemandPredictor()
    predictor.train(records=_synthetic_records())
    result = predictor.predict("Antarctica", "winter", "UnknownLine", 2024, 6)
    assert result["observed_segment_bookings_all_time"] == 0
    assert result["data_sufficiency"] == "INSUFFICIENT_DATA"


def test_save_and_load_roundtrip(tmp_path: Path):
    predictor = DemandPredictor()
    predictor.train(records=_synthetic_records())
    model_path = tmp_path / "demand_predictor.joblib"
    predictor.save(model_path)

    reloaded = DemandPredictor.load(model_path)
    original = predictor.predict("Nordic", "summer", "Viking", 2024, 2)
    restored = reloaded.predict("Nordic", "summer", "Viking", 2024, 2)
    assert original == restored


def test_generate_forecast_writes_expected_schema(tmp_path: Path):
    predictor = DemandPredictor()
    predictor.train(records=_synthetic_records())
    out_path = predictor.generate_forecast(out_dir=tmp_path, as_of=date(2026, 8, 1))

    assert out_path.name == "demand_forecast_2026-08.json"
    payload = json.loads(out_path.read_text())
    assert payload["n_training_records"] == 144
    assert len(payload["predictions"]) == 2
    for prediction in payload["predictions"]:
        assert "demand_score" in prediction
        assert "recommended_pricing_action" in prediction
        assert "data_sufficiency" in prediction
        assert prediction["target_year_month"] == "2026-08"


def test_load_real_booking_source_does_not_crash():
    """Guards against the loader breaking on the real, messily-populated
    export. Does not assert forecast quality — 34 records is below
    MIN_SAMPLES_PER_SEGMENT and any output from it is directional only."""
    if not DEFAULT_BOOKING_SOURCE.exists():
        pytest.skip("booking_master_dump.json not present in this environment")
    records = load_booking_records(DEFAULT_BOOKING_SOURCE)
    assert isinstance(records, list)
    if records:
        predictor = DemandPredictor()
        metrics = predictor.train(records=records)
        assert metrics["data_sufficiency"] == "INSUFFICIENT_DATA"

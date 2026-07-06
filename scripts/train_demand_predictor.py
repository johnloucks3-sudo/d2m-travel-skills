#!/usr/bin/env python3
"""
scripts/train_demand_predictor.py — monthly retrain entry point.

Called by the demand-predictor-retrain.timer (systemd user unit). Retrains
core/ml/demand_predictor.py's DemandPredictor on the current booking master
export, saves the model, and writes this month's demand_forecast_YYYY-MM.json.

See core/ml/demand_predictor.py's module docstring for the current real-data
limitation (34 booking rows, no multi-year history) — this script runs
correctly today and will produce SUFFICIENT-confidence output once booking
volume grows past MIN_SAMPLES_PER_SEGMENT.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.ml.demand_predictor import DemandPredictor, MODEL_PATH  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("train_demand_predictor")


def main() -> int:
    predictor = DemandPredictor()
    try:
        metrics = predictor.train()
    except FileNotFoundError as e:
        log.error("booking source not found: %s", e)
        return 1

    predictor.save(MODEL_PATH)
    log.info("trained on %s records (%s)", metrics["n_training_records"], metrics["data_sufficiency"])
    if metrics.get("rmse_holdout") is not None:
        log.info("holdout RMSE: %.2f (%.1f%% of mean)", metrics["rmse_holdout"], metrics["rmse_pct_of_mean"])
    else:
        log.info("no holdout: %s", metrics["rmse_note"])

    forecast_path = predictor.generate_forecast()
    log.info("forecast written to %s", forecast_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Tests for core/ai_infra/cost_attribution.py.

Builds 4 weeks of synthetic usage-log data across the three known sources
(narrative, gemini data-processing, gemini file-processing), then verifies
the aggregation totals match a hand-computed sum of the raw records.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.ai_infra.cost_attribution import (
    SOURCES,
    UNINSTRUMENTED_FUNCTIONS,
    aggregate_by_function,
    aggregate_by_model,
    load_records,
    monthly_report,
    summary_text,
)


@pytest.fixture
def four_weeks_of_data(tmp_path: Path):
    """Write 28 days of records across all three source files into tmp_path."""
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)

    narrative_path = tmp_path / "claude_narrative_usage.jsonl"
    gemini_path = tmp_path / "gemini_usage.jsonl"
    gemini_file_path = tmp_path / "gemini_file_usage.jsonl"

    narrative_lines = []
    gemini_lines = []
    gemini_file_lines = []

    expected_narrative_cost = 0.0
    expected_gemini_cost = 0.0
    expected_gemini_file_cost = 0.0
    expected_narrative_success = 0

    for day in range(28):
        ts = (start + timedelta(days=day)).isoformat()

        # 2 narrative calls/day, one fails (cost 0, like the real fallback-used pattern)
        success_cost = round(0.0021 + (day % 5) * 0.0001, 6)
        narrative_lines.append(json.dumps({
            "ts": ts, "port_name": f"Port {day}", "model": "claude-sonnet-4-6",
            "input_tokens": 1200, "output_tokens": 400,
            "cost_usd": success_cost, "success": True, "fallback_used": False,
        }))
        narrative_lines.append(json.dumps({
            "ts": ts, "port_name": f"Port {day} retry", "model": "claude-sonnet-4-6",
            "input_tokens": 0, "output_tokens": 0,
            "cost_usd": 0.0, "success": False, "fallback_used": True, "error": "credit low",
        }))
        expected_narrative_cost += success_cost
        expected_narrative_success += 1

        # 1 gemini data-processing call/day, free tier -> $0 but still a logged call
        gemini_lines.append(json.dumps({
            "ts": ts, "model": "gemini-2.5-flash-lite", "tier": "Haiku-equivalent",
            "caller": "test", "task_hint": "synthetic", "input_tokens_est": 500,
            "output_tokens_est": 50, "in_allowlist": True, "paid_tier_flag": "false",
            "success": True, "error": None,
        }))

        # 1 gemini file-processing call every other day, priced model this time
        if day % 2 == 0:
            gemini_file_lines.append(json.dumps({
                "ts": ts, "operation": "upload", "file": f"/tmp/doc_{day}.pdf",
                "model": "gemini-2.5-pro", "tokens_est": 2000, "success": True, "error": None,
            }))
            expected_gemini_file_cost += round((2000 / 1_000_000) * 1.25, 6)

    narrative_path.write_text("\n".join(narrative_lines) + "\n")
    gemini_path.write_text("\n".join(gemini_lines) + "\n")
    gemini_file_path.write_text("\n".join(gemini_file_lines) + "\n")

    return {
        "data_dir": tmp_path,
        "expected_narrative_cost": round(expected_narrative_cost, 4),
        "expected_narrative_success": expected_narrative_success,
        "expected_narrative_calls": 56,  # 28 days * 2 calls
        "expected_gemini_calls": 28,
        "expected_gemini_file_calls": 14,
        "expected_gemini_file_cost": round(expected_gemini_file_cost, 4),
    }


def test_load_records_reads_all_sources(four_weeks_of_data):
    records = load_records(data_dir=four_weeks_of_data["data_dir"])
    narrative_records = [r for r in records if r.source_file == "claude_narrative_usage.jsonl"]
    gemini_records = [r for r in records if r.source_file == "gemini_usage.jsonl"]
    gemini_file_records = [r for r in records if r.source_file == "gemini_file_usage.jsonl"]

    assert len(narrative_records) == four_weeks_of_data["expected_narrative_calls"]
    assert len(gemini_records) == four_weeks_of_data["expected_gemini_calls"]
    assert len(gemini_file_records) == four_weeks_of_data["expected_gemini_file_calls"]


def test_aggregate_by_function_matches_raw_totals(four_weeks_of_data):
    records = load_records(data_dir=four_weeks_of_data["data_dir"])
    by_function = aggregate_by_function(records)

    assert by_function["narrative_generation"]["calls"] == four_weeks_of_data["expected_narrative_calls"]
    assert by_function["narrative_generation"]["successful_calls"] == four_weeks_of_data["expected_narrative_success"]
    assert by_function["narrative_generation"]["cost_usd"] == pytest.approx(
        four_weeks_of_data["expected_narrative_cost"], abs=1e-4
    )

    # data_processing spans both gemini sources
    assert by_function["data_processing"]["calls"] == (
        four_weeks_of_data["expected_gemini_calls"] + four_weeks_of_data["expected_gemini_file_calls"]
    )
    assert by_function["data_processing"]["cost_usd"] == pytest.approx(
        four_weeks_of_data["expected_gemini_file_cost"], abs=1e-4
    )


def test_aggregate_by_model_matches_raw_totals(four_weeks_of_data):
    records = load_records(data_dir=four_weeks_of_data["data_dir"])
    by_model = aggregate_by_model(records)

    assert by_model["claude-sonnet-4-6"]["calls"] == four_weeks_of_data["expected_narrative_calls"]
    assert by_model["claude-sonnet-4-6"]["cost_usd"] == pytest.approx(
        four_weeks_of_data["expected_narrative_cost"], abs=1e-4
    )
    assert by_model["gemini-2.5-flash-lite"]["calls"] == four_weeks_of_data["expected_gemini_calls"]
    assert by_model["gemini-2.5-pro"]["calls"] == four_weeks_of_data["expected_gemini_file_calls"]


def test_monthly_report_totals_match_individual_logs(four_weeks_of_data):
    report = monthly_report(year_month="2026-06", data_dir=four_weeks_of_data["data_dir"])

    expected_total = round(
        four_weeks_of_data["expected_narrative_cost"] + four_weeks_of_data["expected_gemini_file_cost"], 4
    )
    assert report["total_spend_usd"] == pytest.approx(expected_total, abs=1e-4)
    assert report["total_calls"] == (
        four_weeks_of_data["expected_narrative_calls"]
        + four_weeks_of_data["expected_gemini_calls"]
        + four_weeks_of_data["expected_gemini_file_calls"]
    )
    # Every uninstrumented function is surfaced explicitly, never silently $0
    for fn in UNINSTRUMENTED_FUNCTIONS:
        assert fn in report["uninstrumented_functions"]
        assert fn not in report["spend_by_function"]


def test_monthly_report_period_filtering_excludes_other_months(four_weeks_of_data):
    # Data is all in June 2026 — a July query should see zero records, not an error.
    report = monthly_report(year_month="2026-07", data_dir=four_weeks_of_data["data_dir"])
    assert report["total_calls"] == 0
    assert report["total_spend_usd"] == 0.0
    assert report["spend_by_function"] == {}


def test_summary_text_renders_without_error(four_weeks_of_data):
    report = monthly_report(year_month="2026-06", data_dir=four_weeks_of_data["data_dir"])
    text = summary_text(report)
    assert "AI MODEL COST ATTRIBUTION" in text
    assert "NOT INSTRUMENTED" in text
    assert "narrative_generation" in text


def test_load_records_missing_file_is_not_an_error(tmp_path: Path):
    # No files written at all in tmp_path — should return empty, not raise.
    records = load_records(data_dir=tmp_path)
    assert records == []


def test_load_records_skips_malformed_lines(tmp_path: Path):
    path = tmp_path / "claude_narrative_usage.jsonl"
    path.write_text(
        '{"ts": "2026-06-01T00:00:00+00:00", "model": "claude-sonnet-4-6", '
        '"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.001, "success": true}\n'
        "not valid json\n"
        "\n"
    )
    records = load_records(data_dir=tmp_path)
    assert len(records) == 1
    assert records[0].cost_usd == pytest.approx(0.001)


def test_cost_estimated_flag_when_no_precomputed_cost(tmp_path: Path):
    path = tmp_path / "gemini_usage.jsonl"
    path.write_text(json.dumps({
        "ts": "2026-06-01T00:00:00+00:00", "model": "gemini-2.5-pro",
        "input_tokens_est": 1_000_000, "output_tokens_est": 1_000_000, "success": True,
    }) + "\n")
    records = load_records(data_dir=tmp_path)
    assert len(records) == 1
    assert records[0].cost_estimated is True
    assert records[0].cost_usd == pytest.approx(1.25 + 5.00)

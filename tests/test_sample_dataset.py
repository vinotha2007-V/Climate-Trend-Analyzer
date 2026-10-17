"""
Integration test verifying loading and analysis of the verified NOAA sample dataset.
"""
from pathlib import Path
import pytest

from app.analysis.anomalies import detect_anomalies
from app.analysis.seasonal import calculate_seasonal_patterns
from app.analysis.trends import calculate_trends
from app.core.quality_reporter import DataQualityReporter
from app.core.validator import ClimateDataValidator

SAMPLE_PATH = Path("data/sample/sample_climate_data.csv")
PROVENANCE_PATH = Path("data/sample/DATASET_SOURCE.md")


def test_sample_files_exist():
    """Verify sample CSV and provenance markdown files exist on disk."""
    assert SAMPLE_PATH.exists(), "Sample climate CSV must exist in data/sample/"
    assert SAMPLE_PATH.stat().st_size > 0
    assert PROVENANCE_PATH.exists(), "Provenance document must exist in data/sample/"
    assert PROVENANCE_PATH.stat().st_size > 0


def test_sample_dataset_validation():
    """Verify NOAA sample dataset passes schema validation with perfect health."""
    df, val = ClimateDataValidator.load_and_validate(SAMPLE_PATH)

    assert val.is_valid is True
    assert len(val.fatal_errors) == 0
    assert len(val.warnings) == 0
    assert val.total_rows == 2100
    assert val.date_column == "date"
    assert "temp_anomaly" in val.climate_columns
    assert df is not None
    assert len(df) == 2100


def test_sample_dataset_quality_score():
    """Verify sample dataset achieves an Excellent 100.0 quality score."""
    df, val = ClimateDataValidator.load_and_validate(SAMPLE_PATH)
    report = DataQualityReporter.evaluate(df, val)

    assert report.validation.is_valid is True
    assert report.quality_score.final_score == 100.0
    assert report.quality_score.grade == "Excellent"
    assert report.duplicate_date_count == 0
    assert report.date_range_start == "1850-01-01T00:00:00"
    assert report.date_range_end == "2024-12-01T00:00:00"


def test_sample_dataset_trend_analysis():
    """Verify trend analysis runs on sample dataset and identifies historical warming trend."""
    df, _ = ClimateDataValidator.load_and_validate(SAMPLE_PATH)
    trend_res = calculate_trends(
        df,
        date_col="date",
        value_col="temp_anomaly",
        aggregation_frequency="annual",
        rolling_window=5,
    )

    assert trend_res.valid_observations == 2100
    assert trend_res.linear_trend is not None
    # Historical NOAA warming trend is positive (~0.05 - 0.07 °C / decade over 1850-2024)
    assert trend_res.linear_trend.slope_per_decade > 0.0
    assert trend_res.linear_trend.is_statistically_significant is True
    assert trend_res.linear_trend.p_value < 0.001
    assert "°C per decade" in trend_res.linear_trend.unit_description
    assert len(trend_res.data_points) == 175  # 175 calendar years (1850-2024)


def test_sample_dataset_seasonal_analysis():
    """Verify seasonal climatology supports 175 years of monthly records."""
    df, _ = ClimateDataValidator.load_and_validate(SAMPLE_PATH)
    seasonal_res = calculate_seasonal_patterns(df, value_col="temp_anomaly")

    assert seasonal_res.is_seasonal_supported is True
    assert seasonal_res.total_years == 175
    assert len(seasonal_res.monthly_patterns) == 12
    assert len(seasonal_res.seasonal_summaries) == 4


def test_sample_dataset_anomaly_detection():
    """Verify anomaly detection flags extreme historical global temperature deviations."""
    df, _ = ClimateDataValidator.load_and_validate(SAMPLE_PATH)
    z_res = detect_anomalies(df, value_col="temp_anomaly", method="z_score", threshold=2.5)

    assert z_res.total_points == 2100
    assert z_res.valid_points == 2100
    assert z_res.anomaly_count > 0
    # Anomalies should represent a small percentage of extreme historical deviations
    assert 0.5 < z_res.anomaly_percentage < 5.0

"""
Tests for DataQualityReporter and quality scoring rules.
"""
import pytest
from app.core.validator import ClimateDataValidator
from app.core.quality_reporter import DataQualityReporter


CLEAN_CSV = """date,temperature,rainfall
2020-01-01,10.0,50.0
2020-02-01,11.5,45.0
2020-03-01,13.0,30.0
2020-04-01,16.2,20.0
2020-05-01,19.1,15.0
"""

DUPLICATES_CSV = """date,temperature
2020-01-01,10.0
2020-01-01,10.5
2020-01-01,11.0
2020-02-01,12.0
"""

MISSING_VALUES_CSV = """date,temperature,rainfall
2020-01-01,,50.0
2020-02-01,11.5,
2020-03-01,,
2020-04-01,16.2,20.0
"""

NON_NUMERIC_CSV = """date,temperature
2020-01-01,10.0
2020-02-01,INVALID_A
2020-03-01,INVALID_B
2020-04-01,15.0
"""


def test_clean_data_quality_report():
    """Verify perfect dataset achieves 100.0 score and 'Excellent' grade."""
    df, val = ClimateDataValidator.load_and_validate(CLEAN_CSV)
    report = DataQualityReporter.evaluate(df, val)

    assert report.validation.is_valid is True
    assert report.quality_score.final_score == 100.0
    assert report.quality_score.grade == "Excellent"
    assert report.quality_score.missing_data_penalty == 0.0
    assert report.quality_score.duplicate_date_penalty == 0.0
    assert report.quality_score.invalid_value_penalty == 0.0
    assert report.duplicate_date_count == 0
    assert report.date_range_start is not None
    assert report.date_range_end is not None
    assert len(report.column_metrics) == 3


def test_duplicate_date_penalty():
    """Verify duplicate dates incur proper deduction in quality score."""
    df, val = ClimateDataValidator.load_and_validate(DUPLICATES_CSV)
    report = DataQualityReporter.evaluate(df, val)

    assert report.duplicate_date_count == 2
    assert report.quality_score.duplicate_date_penalty > 0.0
    assert report.quality_score.final_score < 100.0


def test_missing_value_reporting_and_penalty():
    """Verify per-column missing statistics and missing penalty computation."""
    df, val = ClimateDataValidator.load_and_validate(MISSING_VALUES_CSV)
    report = DataQualityReporter.evaluate(df, val)

    # Check column breakdown
    temp_metrics = next(c for c in report.column_metrics if c.name == "temperature")
    rain_metrics = next(c for c in report.column_metrics if c.name == "rainfall")

    assert temp_metrics.missing_count == 2
    assert temp_metrics.missing_percentage == 50.0

    assert rain_metrics.missing_count == 2
    assert rain_metrics.missing_percentage == 50.0

    assert report.quality_score.missing_data_penalty > 0.0
    assert report.quality_score.final_score < 100.0


def test_non_numeric_invalid_penalty():
    """Verify invalid text values inside numeric columns are tracked and penalized."""
    df, val = ClimateDataValidator.load_and_validate(NON_NUMERIC_CSV)
    report = DataQualityReporter.evaluate(df, val)

    temp_metrics = next(c for c in report.column_metrics if c.name == "temperature")
    assert temp_metrics.invalid_count == 2
    assert report.quality_score.invalid_value_penalty > 0.0


def test_empty_dataset_quality_evaluation():
    """Verify empty dataset reports score 0.0 and grade 'Poor'."""
    df, val = ClimateDataValidator.load_and_validate("")
    report = DataQualityReporter.evaluate(df, val)

    assert report.validation.is_valid is False
    assert report.quality_score.final_score == 0.0
    assert report.quality_score.grade == "Poor"
    assert report.column_metrics == []


def test_quality_score_clamping():
    """Verify that score remains within [0.0, 100.0] even with extreme penalties."""
    # Compute score with large penalty values
    score = DataQualityReporter._calculate_quality_score(
        total_rows=10,
        total_cells=10,
        total_missing=10,
        total_invalid=10,
        duplicate_date_count=10,
        has_fatal_errors=True,
    )
    assert 0.0 <= score.final_score <= 100.0
    assert score.final_score == 0.0
    assert score.grade == "Poor"

"""
Unit tests for Seasonal Climatology Engine (app/analysis/seasonal.py).
"""
import pytest
import pandas as pd
from app.analysis.seasonal import calculate_seasonal_patterns


def test_multi_year_seasonal_patterns():
    """Verify standard 12-month pattern and 4 seasonal groupings on multi-year data."""
    dates = []
    temps = []
    # 3 years of monthly data (2018, 2019, 2020)
    for year in (2018, 2019, 2020):
        for m in range(1, 13):
            dates.append(f"{year}-{m:02d}-01")
            # Typical seasonal curve: lowest in Jan (~5°C), peak in Jul (~25°C)
            temps.append(15.0 + 10.0 * (m - 6) / 6.0)

    df = pd.DataFrame({"date": dates, "temperature": temps})
    result = calculate_seasonal_patterns(df, date_col="date", value_col="temperature")

    assert result.is_seasonal_supported is True
    assert result.reason_if_unsupported is None
    assert result.total_years == 3
    assert len(result.monthly_patterns) == 12
    # Verify each month has 3 observations
    for pat in result.monthly_patterns:
        assert pat.observation_count == 3
        assert pat.month_name != ""

    assert len(result.seasonal_summaries) == 4
    season_names = [s.season for s in result.seasonal_summaries]
    assert any("Winter" in s for s in season_names)
    assert any("Summer" in s for s in season_names)
    assert result.scientific_distinction_note != ""


def test_insufficient_years_flagged():
    """Verify single-year dataset is flagged as unsupported for multi-year climatology."""
    dates = [f"2020-{m:02d}-01" for m in range(1, 13)]
    temps = [10.0 + m for m in range(1, 13)]
    df = pd.DataFrame({"date": dates, "temperature": temps})

    result = calculate_seasonal_patterns(df, date_col="date", value_col="temperature")

    assert result.is_seasonal_supported is False
    assert result.total_years == 1
    assert "at least 2 calendar years" in result.reason_if_unsupported


def test_insufficient_distinct_months_flagged():
    """Verify annual frequency dataset (e.g. only January) is flagged."""
    dates = [f"{year}-01-01" for year in range(2010, 2020)]
    temps = [12.0 + (year - 2010) * 0.1 for year in range(2010, 2020)]
    df = pd.DataFrame({"date": dates, "temperature": temps})

    result = calculate_seasonal_patterns(df, date_col="date", value_col="temperature")

    assert result.is_seasonal_supported is False
    assert "distinct month" in result.reason_if_unsupported


def test_empty_dataframe_seasonal():
    """Verify empty DataFrame returns safe unsupported result."""
    df = pd.DataFrame()
    result = calculate_seasonal_patterns(df)

    assert result.is_seasonal_supported is False
    assert result.total_years == 0
    assert result.monthly_patterns == []

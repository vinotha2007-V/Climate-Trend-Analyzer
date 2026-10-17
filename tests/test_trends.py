"""
Unit tests for Climate Trend Analysis Engine (app/analysis/trends.py).
"""
import pytest
import numpy as np
import pandas as pd
from app.analysis.trends import calculate_trends


def test_known_linear_trend():
    """Verify linear trend regression on known slope (0.2 °C/year -> 2.0 °C/decade)."""
    # 10 years of annual data: 2010 to 2019
    dates = [f"{year}-01-01" for year in range(2010, 2020)]
    # y = 14.0 + 0.2 * (year - 2010)
    temps = [14.0 + 0.2 * (year - 2010) for year in range(2010, 2020)]
    df = pd.DataFrame({"date": dates, "temperature": temps})

    result = calculate_trends(
        df,
        date_col="date",
        value_col="temperature",
        aggregation_frequency="annual",
        rolling_window=3,
    )

    assert result.valid_observations == 10
    assert result.missing_observations == 0
    assert result.linear_trend is not None
    # Slope should be approximately 0.20 °C/year and 2.0 °C/decade
    assert pytest.approx(result.linear_trend.slope_per_year, rel=1e-2) == 0.20
    assert pytest.approx(result.linear_trend.slope_per_decade, rel=1e-2) == 2.0
    assert pytest.approx(result.linear_trend.r_squared, abs=0.01) == 1.0
    assert result.linear_trend.is_statistically_significant is True
    assert "°C per decade" in result.linear_trend.unit_description
    assert len(result.data_points) == 10
    assert result.scientific_disclaimer != ""


def test_constant_values_trend():
    """Verify constant values yield zero slope without crashing."""
    dates = [f"2020-{m:02d}-01" for m in range(1, 13)]
    temps = [18.0] * 12
    df = pd.DataFrame({"date": dates, "temperature": temps})

    result = calculate_trends(df, date_col="date", value_col="temperature")

    assert result.linear_trend is not None
    assert result.linear_trend.slope_per_year == 0.0
    assert result.linear_trend.slope_per_decade == 0.0
    assert result.linear_trend.r_squared == 0.0
    assert any("constant" in lim.lower() for lim in result.limitations)


def test_missing_and_corrupt_observations_handling():
    """Verify missing values and corrupt dates are handled and reported."""
    df = pd.DataFrame({
        "date": ["2020-01-01", "2020-02-01", "invalid_date", "2020-04-01", "2020-05-01"],
        "temperature": [10.0, np.nan, 12.0, 14.0, 16.0],
    })

    result = calculate_trends(df, date_col="date", value_col="temperature")

    # 5 total, only 3 valid pairs (2020-01, 2020-04, 2020-05)
    assert result.total_observations == 5
    assert result.valid_observations == 3
    assert result.missing_observations == 2
    assert result.missing_percentage == 40.0
    assert any("excluded" in lim.lower() for lim in result.limitations)
    assert result.linear_trend is not None


def test_insufficient_data_points():
    """Verify datasets with fewer than 3 valid observations do not fit regression."""
    df = pd.DataFrame({
        "date": ["2020-01-01", "2020-02-01"],
        "temperature": [10.0, 12.0],
    })

    result = calculate_trends(df, date_col="date", value_col="temperature")

    assert result.valid_observations == 2
    assert result.linear_trend is None
    assert any("insufficient" in lim.lower() for lim in result.limitations)


def test_precipitation_sum_aggregation():
    """Verify rainfall metric computes total summation in addition to means."""
    dates = ["2020-01-01", "2020-01-15", "2020-02-01", "2020-02-15"]
    rain = [20.0, 30.0, 15.0, 25.0]
    df = pd.DataFrame({"date": dates, "rainfall": rain})

    result = calculate_trends(
        df,
        date_col="date",
        value_col="rainfall",
        aggregation_frequency="monthly",
    )

    assert len(result.data_points) == 2
    jan_point = next(p for p in result.data_points if "2020-01" in p.period)
    feb_point = next(p for p in result.data_points if "2020-02" in p.period)
    assert jan_point.total == 50.0
    assert feb_point.total == 40.0


def test_rolling_average_calculation():
    """Verify moving average window operates as expected."""
    dates = [f"2020-{m:02d}-01" for m in range(1, 7)]
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
    df = pd.DataFrame({"date": dates, "temperature": values})

    result = calculate_trends(
        df,
        aggregation_frequency="monthly",
        rolling_window=3,
    )

    # 3-period rolling average on 3rd point (Jan, Feb, Mar): (10+20+30)/3 = 20.0
    assert result.data_points[2].rolling_avg == 20.0
    # 4th point: (20+30+40)/3 = 30.0
    assert result.data_points[3].rolling_avg == 30.0

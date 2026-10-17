"""
Unit tests for Climate Anomaly Detection Engine (app/analysis/anomalies.py).
"""
import pytest
import numpy as np
import pandas as pd
from app.analysis.anomalies import detect_anomalies


def test_zscore_known_outliers():
    """Verify Z-score correctly identifies an extreme outlier."""
    # 20 observations around 15.0 with small variance, and one extreme spike at 50.0
    dates = [f"2020-01-{d:02d}" for d in range(1, 22)]
    values = [15.0 + (i % 3) * 0.5 for i in range(20)] + [50.0]  # index 20 is outlier
    df = pd.DataFrame({"date": dates, "temperature": values})

    result = detect_anomalies(
        df,
        date_col="date",
        value_col="temperature",
        method="z_score",
        threshold=2.5,
    )

    assert result.method == "z_score"
    assert result.valid_points == 21
    assert result.anomaly_count == 1
    # Check that the 21st point (50.0) is flagged as anomaly
    outlier_point = result.anomalies[20]
    assert outlier_point.is_anomaly is True
    assert outlier_point.original_value == 50.0
    assert outlier_point.score > 2.5
    assert result.scientific_caveat != ""


def test_iqr_known_outliers():
    """Verify IQR method flags values breaching boxplot fences."""
    dates = [f"2020-01-{d:02d}" for d in range(1, 22)]
    # Values mostly between 10 and 20, with one low outlier (-15.0) and one high outlier (60.0)
    values = [15.0] * 19 + [-15.0, 60.0]
    df = pd.DataFrame({"date": dates, "temperature": values})

    result = detect_anomalies(
        df,
        date_col="date",
        value_col="temperature",
        method="iqr",
        threshold=1.5,
    )

    assert result.method == "iqr"
    assert result.valid_points == 21
    assert result.anomaly_count == 2
    anomalous_vals = [p.original_value for p in result.anomalies if p.is_anomaly]
    assert -15.0 in anomalous_vals
    assert 60.0 in anomalous_vals


def test_configurable_threshold_sensitivity():
    """Verify adjusting the threshold changes detection sensitivity."""
    dates = [f"2020-01-{d:02d}" for d in range(1, 16)]
    # A distribution where a value of 25.0 is around 2.2 std dev
    values = [10.0, 11.0, 10.5, 11.5, 12.0, 10.0, 11.0, 10.5, 11.5, 12.0, 10.0, 11.0, 10.5, 11.5, 25.0]
    df = pd.DataFrame({"date": dates, "temperature": values})

    # Strict threshold (threshold=2.0) should flag the 25.0 point
    strict_res = detect_anomalies(df, method="z_score", threshold=2.0)
    # Lenient threshold (threshold=4.0) should NOT flag it
    lenient_res = detect_anomalies(df, method="z_score", threshold=4.0)

    assert strict_res.anomaly_count > 0
    assert lenient_res.anomaly_count == 0


def test_constant_values_anomalies():
    """Verify zero variance does not produce false positives or zero-division crashes."""
    dates = [f"2020-01-{d:02d}" for d in range(1, 11)]
    values = [22.0] * 10
    df = pd.DataFrame({"date": dates, "temperature": values})

    z_res = detect_anomalies(df, method="z_score", threshold=2.5)
    assert z_res.anomaly_count == 0
    assert any("variance is zero" in lim.lower() for lim in z_res.limitations)

    iqr_res = detect_anomalies(df, method="iqr", threshold=1.5)
    assert iqr_res.anomaly_count == 0
    assert any("iqr) is zero" in lim.lower() for lim in iqr_res.limitations)


def test_missing_values_anomaly_exclusion():
    """Verify rows with NaN values are safely excluded from baseline computation."""
    dates = ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]
    values = [15.0, np.nan, 16.0, 15.5]
    df = pd.DataFrame({"date": dates, "temperature": values})

    res = detect_anomalies(df, method="z_score", threshold=2.0)
    assert res.total_points == 4
    assert res.valid_points == 3
    assert any("excluded" in lim.lower() for lim in res.limitations)


def test_unsupported_method_raises():
    """Verify invalid method string raises ValueError."""
    df = pd.DataFrame({"date": ["2020-01-01"], "temperature": [10.0]})
    with pytest.raises(ValueError):
        detect_anomalies(df, method="unsupported_algorithm")

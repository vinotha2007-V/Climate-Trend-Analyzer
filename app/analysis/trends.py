"""
Climate Trend Analysis Engine.

Calculates monthly and annual statistical summaries, configurable rolling averages,
and estimates linear trend slopes over time with documented physical units,
comprehensive limitation reporting, and scientific non-causation disclaimers.
"""
from __future__ import annotations

from typing import List, Optional
import numpy as np
import pandas as pd
from scipy import stats

from app.models.schemas import LinearTrend, TrendAnalysisResult, TrendPoint
from app.core.validator import parse_dates_safe


def calculate_trends(
    df: pd.DataFrame,
    date_col: str = "date",
    value_col: str = "temperature",
    aggregation_frequency: str = "annual",
    rolling_window: int = 5,
) -> TrendAnalysisResult:
    """
    Perform statistical time series trend calculation on climate data.
    
    Args:
        df: Input DataFrame with normalized columns.
        date_col: Name of datetime column.
        value_col: Target numeric climate column.
        aggregation_frequency: Cadence for summarization ('annual', 'monthly', or 'raw').
        rolling_window: Moving average window size in periods (default: 5).
        
    Returns:
        TrendAnalysisResult with summary points, regression metrics, and caveats.
    """
    limitations: List[str] = []

    if df is None or len(df) == 0 or date_col not in df.columns or value_col not in df.columns:
        return TrendAnalysisResult(
            column_name=value_col,
            aggregation_frequency=aggregation_frequency,
            total_observations=0,
            valid_observations=0,
            missing_observations=0,
            missing_percentage=0.0,
            rolling_window=rolling_window,
            linear_trend=None,
            data_points=[],
            limitations=["Dataset is empty or does not contain required columns."],
        )

    # Clean working copy
    work_df = pd.DataFrame()
    work_df["date_raw"] = df[date_col]
    work_df["date"] = parse_dates_safe(df[date_col])
    work_df["value"] = pd.to_numeric(df[value_col], errors="coerce")

    total_rows = len(work_df)
    valid_mask = work_df["date"].notna() & work_df["value"].notna()
    valid_df = work_df[valid_mask].sort_values("date").reset_index(drop=True)

    valid_count = len(valid_df)
    missing_count = total_rows - valid_count
    missing_pct = round((missing_count / total_rows * 100.0), 2) if total_rows > 0 else 0.0

    if missing_count > 0:
        limitations.append(
            f"{missing_count} observation(s) ({missing_pct}%) were excluded due to missing "
            f"or unparseable date/measurement values."
        )

    if valid_count == 0:
        return TrendAnalysisResult(
            column_name=value_col,
            aggregation_frequency=aggregation_frequency,
            total_observations=total_rows,
            valid_observations=0,
            missing_observations=missing_count,
            missing_percentage=missing_pct,
            rolling_window=rolling_window,
            linear_trend=None,
            data_points=[],
            limitations=limitations + ["No valid observations available for trend analysis."],
        )

    time_start = valid_df["date"].min().strftime("%Y-%m-%d")
    time_end = valid_df["date"].max().strftime("%Y-%m-%d")

    # 1. Aggregation (Annual, Monthly, or Raw)
    points: List[TrendPoint] = []
    agg_df: pd.DataFrame

    if aggregation_frequency == "annual":
        valid_df["period_key"] = valid_df["date"].dt.year
        grouped = valid_df.groupby("period_key")["value"]
        agg_df = pd.DataFrame({
            "period": [str(p) for p in grouped.groups.keys()],
            "mean": grouped.mean().round(3).values,
            "min": grouped.min().round(3).values,
            "max": grouped.max().round(3).values,
            "total": grouped.sum().round(3).values if "rain" in value_col.lower() else None,
            "count": grouped.count().values,
        })
    elif aggregation_frequency == "monthly":
        valid_df["period_key"] = valid_df["date"].dt.to_period("M")
        grouped = valid_df.groupby("period_key")["value"]
        agg_df = pd.DataFrame({
            "period": [str(p) for p in grouped.groups.keys()],
            "mean": grouped.mean().round(3).values,
            "min": grouped.min().round(3).values,
            "max": grouped.max().round(3).values,
            "total": grouped.sum().round(3).values if "rain" in value_col.lower() else None,
            "count": grouped.count().values,
        })
    else:  # 'raw'
        valid_df["period_key"] = valid_df["date"].dt.strftime("%Y-%m-%d")
        agg_df = pd.DataFrame({
            "period": valid_df["period_key"].values,
            "mean": valid_df["value"].round(3).values,
            "min": valid_df["value"].round(3).values,
            "max": valid_df["value"].round(3).values,
            "total": valid_df["value"].round(3).values if "rain" in value_col.lower() else None,
            "count": [1] * len(valid_df),
        })

    # 2. Configurable Rolling Average
    if len(agg_df) > 0:
        rolling_series = (
            pd.Series(agg_df["mean"])
            .rolling(window=max(1, rolling_window), min_periods=1, center=False)
            .mean()
            .round(3)
        )
        agg_df["rolling_avg"] = rolling_series

        for _, row in agg_df.iterrows():
            points.append(
                TrendPoint(
                    period=str(row["period"]),
                    mean=float(row["mean"]),
                    min=float(row["min"]),
                    max=float(row["max"]),
                    total=float(row["total"]) if pd.notna(row["total"]) else None,
                    count=int(row["count"]),
                    rolling_avg=float(row["rolling_avg"]) if pd.notna(row["rolling_avg"]) else None,
                )
            )

    # 3. Linear Trend Estimation (using decimal years)
    linear_trend: Optional[LinearTrend] = None
    if valid_count < 3:
        limitations.append(
            f"Insufficient observations (n={valid_count}) for linear trend regression. "
            "A minimum of 3 observations is required."
        )
    else:
        # Convert timestamps to decimal years for consistent slope units
        t_min = valid_df["date"].min()
        days_from_start = (valid_df["date"] - t_min).dt.total_seconds() / 86400.0
        x_years = days_from_start / 365.25
        y = valid_df["value"].values

        # Check for constant values
        y_std = np.std(y)
        if np.isclose(y_std, 0.0):
            limitations.append(
                "Observations are constant across the entire time period. "
                "Calculated slope is exactly 0.0."
            )
            unit_desc = _get_unit_description(value_col)
            linear_trend = LinearTrend(
                slope_per_year=0.0,
                slope_per_decade=0.0,
                intercept=float(y[0]),
                r_squared=0.0,
                p_value=1.0,
                std_err=0.0,
                unit_description=unit_desc,
                is_statistically_significant=False,
            )
        elif len(np.unique(x_years)) < 2:
            limitations.append(
                "All observations share the same timestamp or year. Linear trend cannot be determined."
            )
        else:
            reg = stats.linregress(x_years, y)
            slope_year = float(reg.slope)
            slope_decade = float(reg.slope * 10.0)
            r_sq = float(reg.rvalue ** 2) if pd.notna(reg.rvalue) else 0.0
            p_val = float(reg.pvalue) if pd.notna(reg.pvalue) else None
            s_err = float(reg.stderr) if pd.notna(reg.stderr) else None
            unit_desc = _get_unit_description(value_col)

            is_sig = (p_val is not None) and (p_val < 0.05)

            linear_trend = LinearTrend(
                slope_per_year=round(slope_year, 5),
                slope_per_decade=round(slope_decade, 4),
                intercept=round(float(reg.intercept), 4),
                r_squared=round(r_sq, 4),
                p_value=round(p_val, 6) if p_val is not None else None,
                std_err=round(s_err, 5) if s_err is not None else None,
                unit_description=unit_desc,
                is_statistically_significant=is_sig,
            )

    return TrendAnalysisResult(
        column_name=value_col,
        aggregation_frequency=aggregation_frequency,
        time_period_start=time_start,
        time_period_end=time_end,
        total_observations=total_rows,
        valid_observations=valid_count,
        missing_observations=missing_count,
        missing_percentage=missing_pct,
        rolling_window=rolling_window,
        linear_trend=linear_trend,
        data_points=points,
        limitations=limitations,
    )


def _get_unit_description(column_name: str) -> str:
    """Format physical units based on climate metric semantics."""
    col_lower = column_name.lower()
    if any(k in col_lower for k in ("temp", "tavg", "anomaly", "tmin", "tmax")):
        return "°C per decade (and °C per year)"
    elif any(k in col_lower for k in ("rain", "precip", "prcp")):
        return "mm per decade (and mm per year)"
    return "units per decade (and units per year)"

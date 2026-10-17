"""
Climate Seasonal Climatology & Monthly Patterns Engine.

Calculates multi-year monthly averages and meteorological seasonal summaries.
Distinguishes empirical monthly climatology from formal time-series decomposition
and flags datasets with insufficient coverage or unsuitable sampling frequency.
"""
from __future__ import annotations

import calendar
from typing import List, Optional
import numpy as np
import pandas as pd

from app.models.schemas import (
    MonthlyClimatology,
    SeasonalAnalysisResult,
    SeasonalSummary,
)
from app.core.validator import parse_dates_safe

METEOROLOGICAL_SEASONS = [
    {"name": "DJF (Winter)", "months": [12, 1, 2]},
    {"name": "MAM (Spring)", "months": [3, 4, 5]},
    {"name": "JJA (Summer)", "months": [6, 7, 8]},
    {"name": "SON (Autumn)", "months": [9, 10, 11]},
]


def calculate_seasonal_patterns(
    df: pd.DataFrame,
    date_col: str = "date",
    value_col: str = "temperature",
) -> SeasonalAnalysisResult:
    """
    Calculate multi-year monthly patterns and meteorological seasonal summaries.
    
    Args:
        df: DataFrame containing date and climate columns.
        date_col: Datetime column name.
        value_col: Target numeric climate column.
        
    Returns:
        SeasonalAnalysisResult with monthly patterns, seasonal summaries, and suitability flags.
    """
    if df is None or len(df) == 0 or date_col not in df.columns or value_col not in df.columns:
        return SeasonalAnalysisResult(
            column_name=value_col,
            total_years=0,
            is_seasonal_supported=False,
            reason_if_unsupported="Dataset is empty or required columns are missing.",
            monthly_patterns=[],
            seasonal_summaries=[],
        )

    # Clean working copy
    work_df = pd.DataFrame()
    work_df["date"] = parse_dates_safe(df[date_col])
    work_df["value"] = pd.to_numeric(df[value_col], errors="coerce")

    valid_mask = work_df["date"].notna() & work_df["value"].notna()
    valid_df = work_df[valid_mask].copy()

    if len(valid_df) == 0:
        return SeasonalAnalysisResult(
            column_name=value_col,
            total_years=0,
            is_seasonal_supported=False,
            reason_if_unsupported="Dataset contains no valid datetime and numeric values.",
            monthly_patterns=[],
            seasonal_summaries=[],
        )

    valid_df["year"] = valid_df["date"].dt.year
    valid_df["month"] = valid_df["date"].dt.month

    unique_years = sorted(valid_df["year"].unique())
    unique_months = sorted(valid_df["month"].unique())
    total_years = len(unique_years)

    # Suitability Checks
    # 1. Dataset needs at least 2 distinct years to represent a recurring annual cycle
    # 2. Dataset needs at least 3 distinct calendar months (cannot be single-month annual data)
    if len(unique_months) < 3:
        return SeasonalAnalysisResult(
            column_name=value_col,
            total_years=total_years,
            is_seasonal_supported=False,
            reason_if_unsupported=(
                f"Dataset only covers {len(unique_months)} distinct month(s). "
                "Seasonal analysis requires multi-month time series data."
            ),
            monthly_patterns=[],
            seasonal_summaries=[],
        )

    if total_years < 2:
        return SeasonalAnalysisResult(
            column_name=value_col,
            total_years=total_years,
            is_seasonal_supported=False,
            reason_if_unsupported=(
                f"Dataset spans only {total_years} year. Multi-year climatology "
                "requires at least 2 calendar years to evaluate seasonal recurrence."
            ),
            monthly_patterns=[],
            seasonal_summaries=[],
        )

    # Calculate Monthly Climatology Patterns
    monthly_patterns: List[MonthlyClimatology] = []
    month_grouped = valid_df.groupby("month")["value"]

    for m in range(1, 13):
        if m in month_grouped.groups:
            vals = month_grouped.get_group(m)
            std_val = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
            if pd.isna(std_val):
                std_val = 0.0

            monthly_patterns.append(
                MonthlyClimatology(
                    month=m,
                    month_name=calendar.month_name[m],
                    mean=round(float(vals.mean()), 3),
                    min=round(float(vals.min()), 3),
                    max=round(float(vals.max()), 3),
                    std=round(std_val, 3),
                    observation_count=len(vals),
                )
            )

    # Calculate Meteorological Seasonal Summaries
    seasonal_summaries: List[SeasonalSummary] = []
    for season in METEOROLOGICAL_SEASONS:
        season_mask = valid_df["month"].isin(season["months"])
        season_vals = valid_df.loc[season_mask, "value"]

        if not season_vals.empty:
            month_names = [calendar.month_abbr[m] for m in season["months"]]
            seasonal_summaries.append(
                SeasonalSummary(
                    season=season["name"],
                    months=month_names,
                    mean=round(float(season_vals.mean()), 3),
                    min=round(float(season_vals.min()), 3),
                    max=round(float(season_vals.max()), 3),
                )
            )

    return SeasonalAnalysisResult(
        column_name=value_col,
        total_years=total_years,
        is_seasonal_supported=True,
        reason_if_unsupported=None,
        monthly_patterns=monthly_patterns,
        seasonal_summaries=seasonal_summaries,
    )

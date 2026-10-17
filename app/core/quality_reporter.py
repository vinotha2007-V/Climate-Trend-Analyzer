"""
Climate Data Quality Reporter.

Computes comprehensive data-quality metrics, per-column missingness, duplicate
date detection, and calculates a transparent, bounded 0-100 quality health score.
"""
from __future__ import annotations

from typing import List, Optional, Tuple
import pandas as pd

from app.models.schemas import (
    ColumnQuality,
    DataQualityReport,
    QualityScoreBreakdown,
    ValidationResult,
)
from app.core.validator import parse_dates_safe


class DataQualityReporter:
    """Evaluates data quality metrics and produces structured audit reports."""

    @classmethod
    def evaluate(
        cls,
        df: Optional[pd.DataFrame],
        validation: ValidationResult,
    ) -> DataQualityReport:
        """
        Generate a comprehensive quality report and 0-100 score for a dataset.
        """
        if df is None or len(df) == 0:
            score_breakdown = QualityScoreBreakdown(
                base_score=100.0,
                missing_data_penalty=35.0,
                duplicate_date_penalty=0.0,
                invalid_value_penalty=0.0,
                empty_column_penalty=65.0,
                final_score=0.0,
                grade="Poor",
                methodology=(
                    "Dataset is completely empty or could not be loaded. "
                    "Maximal penalties applied."
                ),
            )
            return DataQualityReport(
                validation=validation,
                quality_score=score_breakdown,
                column_metrics=[],
                duplicate_date_count=0,
                date_range_start=None,
                date_range_end=None,
            )

        total_rows = len(df)
        column_metrics: List[ColumnQuality] = []
        duplicate_date_count = 0
        date_range_start: Optional[str] = None
        date_range_end: Optional[str] = None

        total_cells = 0
        total_missing = 0
        total_invalid = 0

        date_col = validation.date_column
        climate_cols = validation.climate_columns

        # Analyze Date column if present
        if date_col and date_col in df.columns:
            date_series = df[date_col]
            coerced_dates = parse_dates_safe(date_series)
            missing_dates = int(date_series.isna().sum())
            invalid_dates = int((coerced_dates.isna() & date_series.notna()).sum())
            valid_dates = coerced_dates.dropna()

            if not valid_dates.empty:
                duplicate_date_count = int(valid_dates.duplicated().sum())
                date_range_start = valid_dates.min().isoformat()
                date_range_end = valid_dates.max().isoformat()

            missing_pct = (missing_dates / total_rows * 100.0) if total_rows > 0 else 0.0

            column_metrics.append(
                ColumnQuality(
                    name=date_col,
                    normalized_name=date_col,
                    inferred_type="datetime",
                    total_records=total_rows,
                    missing_count=missing_dates,
                    missing_percentage=round(missing_pct, 2),
                    invalid_count=invalid_dates,
                )
            )
            total_cells += total_rows
            total_missing += missing_dates
            total_invalid += invalid_dates

        # Analyze Climate Numeric Columns
        for col in climate_cols:
            if col in df.columns:
                series = df[col]
                missing_count = int(series.isna().sum())
                coerced_num = pd.to_numeric(series, errors="coerce")
                invalid_count = int((coerced_num.isna() & series.notna()).sum())

                missing_pct = (missing_count / total_rows * 100.0) if total_rows > 0 else 0.0

                column_metrics.append(
                    ColumnQuality(
                        name=col,
                        normalized_name=col,
                        inferred_type="float",
                        total_records=total_rows,
                        missing_count=missing_count,
                        missing_percentage=round(missing_pct, 2),
                        invalid_count=invalid_count,
                    )
                )
                total_cells += total_rows
                total_missing += missing_count
                total_invalid += invalid_count

        # Compute Quality Score
        score_breakdown = cls._calculate_quality_score(
            total_rows=total_rows,
            total_cells=total_cells,
            total_missing=total_missing,
            total_invalid=total_invalid,
            duplicate_date_count=duplicate_date_count,
            has_fatal_errors=not validation.is_valid,
        )

        return DataQualityReport(
            validation=validation,
            quality_score=score_breakdown,
            column_metrics=column_metrics,
            duplicate_date_count=duplicate_date_count,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
        )

    @staticmethod
    def _calculate_quality_score(
        total_rows: int,
        total_cells: int,
        total_missing: int,
        total_invalid: int,
        duplicate_date_count: int,
        has_fatal_errors: bool,
    ) -> QualityScoreBreakdown:
        """
        Transparent 0–100 Data-Quality Score Algorithm:
        - Base: 100.0 points
        - Missing values penalty: up to 35.0 points (proportional to % missing across evaluated columns)
        - Duplicate date penalty: up to 25.0 points (proportional to % duplicate dates)
        - Invalid value penalty: up to 25.0 points (proportional to % unparseable dates or non-numeric entries)
        - Fatal schema/empty penalty: 15.0 points if validation has fatal errors
        - Final score is bounded strictly between 0.0 and 100.0
        """
        missing_ratio = (total_missing / total_cells) if total_cells > 0 else 1.0
        invalid_ratio = (total_invalid / total_cells) if total_cells > 0 else 0.0
        duplicate_ratio = (duplicate_date_count / total_rows) if total_rows > 0 else 0.0

        missing_penalty = round(min(35.0, missing_ratio * 35.0), 2)
        duplicate_penalty = round(min(25.0, duplicate_ratio * 25.0), 2)
        invalid_penalty = round(min(25.0, invalid_ratio * 25.0), 2)
        fatal_penalty = 15.0 if has_fatal_errors else 0.0

        raw_score = 100.0 - (missing_penalty + duplicate_penalty + invalid_penalty + fatal_penalty)
        final_score = round(max(0.0, min(100.0, raw_score)), 1)

        # Rating tiers
        if final_score >= 90.0:
            grade = "Excellent"
        elif final_score >= 75.0:
            grade = "Good"
        elif final_score >= 50.0:
            grade = "Fair"
        else:
            grade = "Poor"

        methodology = (
            f"Base: 100.0 pts | Missing penalty: -{missing_penalty:.1f} (max 35) | "
            f"Duplicate dates penalty: -{duplicate_penalty:.1f} (max 25) | "
            f"Invalid format penalty: -{invalid_penalty:.1f} (max 25) | "
            f"Fatal errors penalty: -{fatal_penalty:.1f} (15 if invalid schema). "
            f"Clamped to [0.0, 100.0]."
        )

        return QualityScoreBreakdown(
            base_score=100.0,
            missing_data_penalty=missing_penalty,
            duplicate_date_penalty=duplicate_penalty,
            invalid_value_penalty=invalid_penalty,
            empty_column_penalty=fatal_penalty,
            final_score=final_score,
            grade=grade,
            methodology=methodology,
        )

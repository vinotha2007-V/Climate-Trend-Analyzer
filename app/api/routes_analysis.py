"""
Analysis API Routes.

Exposes endpoints for calculating linear trends, moving averages, seasonal climatology,
anomaly detection, and data-quality evaluation for selected datasets.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.analysis.anomalies import detect_anomalies
from app.analysis.seasonal import calculate_seasonal_patterns
from app.analysis.trends import calculate_trends
from app.core.dataset_manager import load_dataset_or_404
from app.core.quality_reporter import DataQualityReporter
from app.models.schemas import (
    AnomalyDetectionResult,
    DataQualityReport,
    SeasonalAnalysisResult,
    TrendAnalysisResult,
)

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


def _resolve_target_column(val_climate_cols: list[str], requested_col: Optional[str]) -> str:
    """Resolve target climate column name or default to the first available."""
    if not val_climate_cols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected dataset contains no recognized numeric climate columns.",
        )
    if requested_col:
        norm_req = requested_col.strip().lower()
        if norm_req not in val_climate_cols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Requested column '{requested_col}' not recognized in dataset. "
                    f"Available climate columns: {val_climate_cols}"
                ),
            )
        return norm_req
    return val_climate_cols[0]


@router.get(
    "/trends",
    response_model=TrendAnalysisResult,
    summary="Compute time-series aggregations, rolling averages, and linear trend slopes",
)
def get_trends(
    dataset_id: str = Query("sample", description="Dataset identifier or 'sample'"),
    column: Optional[str] = Query(None, description="Climate measurement column"),
    frequency: str = Query("annual", pattern="^(annual|monthly|raw)$", description="Aggregation frequency"),
    window: int = Query(5, ge=1, le=50, description="Rolling average window size"),
):
    """Calculates linear trend statistics, rates of change per decade, and moving averages."""
    df, val = load_dataset_or_404(dataset_id)
    target_col = _resolve_target_column(val.climate_columns, column)
    date_col = val.date_column or "date"

    return calculate_trends(
        df=df,
        date_col=date_col,
        value_col=target_col,
        aggregation_frequency=frequency,
        rolling_window=window,
    )


@router.get(
    "/seasonal",
    response_model=SeasonalAnalysisResult,
    summary="Compute 12-month climatology cycle and seasonal patterns",
)
def get_seasonal(
    dataset_id: str = Query("sample", description="Dataset identifier or 'sample'"),
    column: Optional[str] = Query(None, description="Climate measurement column"),
):
    """Calculates multi-year average monthly patterns and standard meteorological seasons."""
    df, val = load_dataset_or_404(dataset_id)
    target_col = _resolve_target_column(val.climate_columns, column)
    date_col = val.date_column or "date"

    return calculate_seasonal_patterns(
        df=df,
        date_col=date_col,
        value_col=target_col,
    )


@router.get(
    "/anomalies",
    response_model=AnomalyDetectionResult,
    summary="Detect statistical anomalies using configurable Z-score or IQR thresholds",
)
def get_anomalies(
    dataset_id: str = Query("sample", description="Dataset identifier or 'sample'"),
    column: Optional[str] = Query(None, description="Climate measurement column"),
    method: str = Query("z_score", pattern="^(z_score|iqr)$", description="Detection algorithm"),
    threshold: float = Query(2.5, gt=0.0, description="Sensitivity threshold multiplier"),
):
    """Flags statistically unusual observations based on parametric or non-parametric fences."""
    df, val = load_dataset_or_404(dataset_id)
    target_col = _resolve_target_column(val.climate_columns, column)
    date_col = val.date_column or "date"

    return detect_anomalies(
        df=df,
        date_col=date_col,
        value_col=target_col,
        method=method,
        threshold=threshold,
    )


@router.get(
    "/quality",
    response_model=DataQualityReport,
    summary="Retrieve 0-100 data quality report for any active dataset",
)
def get_quality(
    dataset_id: str = Query("sample", description="Dataset identifier or 'sample'"),
):
    """Returns per-column missing statistics, duplicate date counts, and health score."""
    df, val = load_dataset_or_404(dataset_id)
    return DataQualityReporter.evaluate(df, val)

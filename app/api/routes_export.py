"""
Export API Routes.

Exposes endpoints for downloading processed climate datasets as CSV (with optional
anomaly flags and scores) and structured analytical summaries as downloadable JSON.
"""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
import pandas as pd

from app.analysis.anomalies import detect_anomalies
from app.analysis.trends import calculate_trends
from app.core.dataset_manager import get_dataset_metadata, load_dataset_or_404
from app.core.quality_reporter import DataQualityReporter

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get(
    "/csv",
    summary="Download processed climate dataset as CSV with optional anomaly flags",
)
def export_csv(
    dataset_id: str = Query("sample", description="Dataset identifier or 'sample'"),
    column: Optional[str] = Query(None, description="Climate measurement column"),
    include_anomalies: bool = Query(False, description="Whether to append anomaly detection flags"),
    method: str = Query("z_score", pattern="^(z_score|iqr)$", description="Anomaly detection algorithm"),
    threshold: float = Query(2.5, gt=0.0, description="Anomaly sensitivity threshold"),
):
    """
    Generates a downloadable CSV containing original observations, standardized dates,
    and optional anomaly detection flags and scores.
    """
    df, val = load_dataset_or_404(dataset_id)
    climate_cols = val.climate_columns
    if not climate_cols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset contains no recognized climate columns.",
        )

    target_col = column.strip().lower() if column else climate_cols[0]
    if target_col not in climate_cols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Column '{target_col}' not recognized in dataset. Options: {climate_cols}",
        )

    export_df = df.copy()

    if include_anomalies:
        date_col = val.date_column or "date"
        anomaly_res = detect_anomalies(
            df=df,
            date_col=date_col,
            value_col=target_col,
            method=method,
            threshold=threshold,
        )

        # Match flags and scores by date index
        anomaly_lookup = {
            p.date: (p.is_anomaly, p.score, p.lower_bound, p.upper_bound)
            for p in anomaly_res.anomalies
        }

        # Convert date to string format for matching
        d_series = pd.to_datetime(export_df[date_col], format="mixed", errors="coerce").dt.strftime("%Y-%m-%d")

        is_anom_list = []
        scores_list = []
        for d in d_series:
            if d in anomaly_lookup:
                flag, score, _, _ = anomaly_lookup[d]
                is_anom_list.append(flag)
                scores_list.append(score)
            else:
                is_anom_list.append(False)
                scores_list.append(None)

        export_df[f"{target_col}_is_anomaly"] = is_anom_list
        export_df[f"{target_col}_anomaly_score"] = scores_list
        export_df[f"{target_col}_anomaly_method"] = method
        export_df[f"{target_col}_anomaly_threshold"] = threshold

    csv_buffer = io.StringIO()
    export_df.to_csv(csv_buffer, index=False)
    csv_bytes = csv_buffer.getvalue().encode("utf-8")

    filename = f"climate_{dataset_id}_processed.csv"

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get(
    "/summary",
    summary="Download comprehensive analysis report as structured JSON",
)
def export_summary(
    dataset_id: str = Query("sample", description="Dataset identifier or 'sample'"),
    column: Optional[str] = Query(None, description="Climate measurement column"),
):
    """
    Generates a structured, machine-readable JSON summary report bundling dataset metadata,
    data health score, trend slopes, and scientific disclaimers.
    """
    df, val = load_dataset_or_404(dataset_id)
    metadata = get_dataset_metadata(dataset_id)
    quality_report = DataQualityReporter.evaluate(df, val)

    climate_cols = val.climate_columns
    if not climate_cols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dataset contains no climate columns for analysis.",
        )

    target_col = column.strip().lower() if column else climate_cols[0]
    if target_col not in climate_cols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Column '{target_col}' not recognized in dataset. Options: {climate_cols}",
        )

    date_col = val.date_column or "date"
    trend_res = calculate_trends(df=df, date_col=date_col, value_col=target_col)

    summary_payload = {
        "report_title": f"Climate Trend Analysis Summary - {metadata.name}",
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata.model_dump(),
        "data_quality_report": quality_report.model_dump(),
        "trend_analysis": trend_res.model_dump(),
        "scientific_disclaimer": (
            "This report is generated for academic and research trend analysis. "
            "Statistical trends and mathematical anomalies describe observed correlations "
            "and do not constitute definitive causal attribution without physical modeling."
        ),
    }

    json_str = json.dumps(summary_payload, indent=2)
    filename = f"climate_{dataset_id}_summary.json"

    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )

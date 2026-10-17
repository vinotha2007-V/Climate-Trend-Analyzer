"""
Climate Anomaly Detection Engine.

Implements configurable Z-score (standardized deviation) and Interquartile Range
(IQR boxplot fences) outlier detection with customizable sensitivity thresholds,
resilience against zero-variance/constant data, and explicit scientific caveats.
"""
from __future__ import annotations

from typing import List, Optional
import numpy as np
import pandas as pd

from app.models.schemas import AnomalyDetectionResult, AnomalyPoint
from app.core.validator import parse_dates_safe


def detect_anomalies(
    df: pd.DataFrame,
    date_col: str = "date",
    value_col: str = "temperature",
    method: str = "z_score",
    threshold: float = 2.5,
) -> AnomalyDetectionResult:
    """
    Detect statistical climate anomalies using Z-score or IQR fences.
    
    Args:
        df: Input DataFrame with date and climate columns.
        date_col: Timestamp column.
        value_col: Target climate measurement column.
        method: Detection algorithm ('z_score' or 'iqr').
        threshold: Sensitivity multiplier (e.g. 2.0-3.0 for z-score, 1.5 for IQR).
        
    Returns:
        AnomalyDetectionResult containing baseline metrics, anomalies list, and caveats.
    """
    method_normalized = method.lower().strip()
    if method_normalized not in ("z_score", "iqr"):
        raise ValueError(f"Unsupported anomaly detection method: '{method}'. Must be 'z_score' or 'iqr'.")

    limitations: List[str] = []

    if df is None or len(df) == 0 or date_col not in df.columns or value_col not in df.columns:
        return AnomalyDetectionResult(
            column_name=value_col,
            method=method_normalized,
            threshold_used=threshold,
            total_points=0,
            valid_points=0,
            anomaly_count=0,
            anomaly_percentage=0.0,
            anomalies=[],
            limitations=["Dataset is empty or missing required columns."],
        )

    # Clean working copy preserving row order
    work_df = pd.DataFrame()
    work_df["date_raw"] = df[date_col].astype(str)
    work_df["date"] = parse_dates_safe(df[date_col])
    work_df["value"] = pd.to_numeric(df[value_col], errors="coerce")

    total_rows = len(work_df)
    valid_mask = work_df["value"].notna()
    valid_df = work_df[valid_mask].copy()
    valid_count = len(valid_df)
    missing_count = total_rows - valid_count

    if missing_count > 0:
        limitations.append(
            f"{missing_count} missing or non-numeric observation(s) were excluded from baseline statistics."
        )

    if valid_count < 4:
        limitations.append(
            f"Sample size is very small (n={valid_count}). Anomaly thresholds have high statistical uncertainty."
        )

    if valid_count == 0:
        return AnomalyDetectionResult(
            column_name=value_col,
            method=method_normalized,
            threshold_used=threshold,
            total_points=total_rows,
            valid_points=0,
            anomaly_count=0,
            anomaly_percentage=0.0,
            anomalies=[],
            limitations=limitations + ["No numeric observations available to detect anomalies."],
        )

    vals = valid_df["value"].values
    points: List[AnomalyPoint] = []
    anomaly_count = 0

    baseline_mean: Optional[float] = None
    baseline_std: Optional[float] = None
    q1: Optional[float] = None
    q3: Optional[float] = None
    iqr_val: Optional[float] = None

    if method_normalized == "z_score":
        mean_val = float(np.mean(vals))
        std_val = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
        baseline_mean = round(mean_val, 3)
        baseline_std = round(std_val, 3)

        if np.isclose(std_val, 0.0):
            limitations.append(
                "Variance is zero (all observations are identical). No Z-score anomalies can be flagged."
            )
            lower_bound = mean_val
            upper_bound = mean_val
            for _, row in valid_df.iterrows():
                d_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else str(row["date_raw"])
                points.append(
                    AnomalyPoint(
                        date=d_str,
                        original_value=round(float(row["value"]), 3),
                        method="z_score",
                        score=0.0,
                        threshold_used=threshold,
                        lower_bound=round(lower_bound, 3),
                        upper_bound=round(upper_bound, 3),
                        is_anomaly=False,
                    )
                )
        else:
            lower_bound = mean_val - (threshold * std_val)
            upper_bound = mean_val + (threshold * std_val)

            for _, row in valid_df.iterrows():
                val = float(row["value"])
                z = (val - mean_val) / std_val
                is_anom = abs(z) > threshold
                if is_anom:
                    anomaly_count += 1

                d_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else str(row["date_raw"])
                points.append(
                    AnomalyPoint(
                        date=d_str,
                        original_value=round(val, 3),
                        method="z_score",
                        score=round(float(z), 3),
                        threshold_used=threshold,
                        lower_bound=round(lower_bound, 3),
                        upper_bound=round(upper_bound, 3),
                        is_anomaly=is_anom,
                    )
                )

    else:  # IQR Method
        q25 = float(np.percentile(vals, 25))
        q75 = float(np.percentile(vals, 75))
        iqr = q75 - q25
        q1 = round(q25, 3)
        q3 = round(q75, 3)
        iqr_val = round(iqr, 3)

        lower_bound = q25 - (threshold * iqr)
        upper_bound = q75 + (threshold * iqr)

        if np.isclose(iqr, 0.0):
            limitations.append(
                "Interquartile range (IQR) is zero. Most observations share the same value; "
                "IQR bounds collapse to the median."
            )

        for _, row in valid_df.iterrows():
            val = float(row["value"])
            is_anom = (val < lower_bound) or (val > upper_bound)
            if is_anom:
                anomaly_count += 1

            # Score expresses distance from bounds in units of IQR (or raw difference if IQR==0)
            if iqr > 0:
                dist = (val - upper_bound) / iqr if val > upper_bound else (lower_bound - val) / iqr if val < lower_bound else 0.0
            else:
                dist = abs(val - q25)

            d_str = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else str(row["date_raw"])
            points.append(
                AnomalyPoint(
                    date=d_str,
                    original_value=round(val, 3),
                    method="iqr",
                    score=round(float(dist), 3),
                    threshold_used=threshold,
                    lower_bound=round(lower_bound, 3),
                    upper_bound=round(upper_bound, 3),
                    is_anomaly=is_anom,
                )
            )

    anom_pct = round((anomaly_count / valid_count * 100.0), 2) if valid_count > 0 else 0.0

    return AnomalyDetectionResult(
        column_name=value_col,
        method=method_normalized,
        threshold_used=threshold,
        total_points=total_rows,
        valid_points=valid_count,
        anomaly_count=anomaly_count,
        anomaly_percentage=anom_pct,
        baseline_mean=baseline_mean,
        baseline_std=baseline_std,
        q1=q1,
        q3=q3,
        iqr=iqr_val,
        anomalies=points,
        limitations=limitations,
    )

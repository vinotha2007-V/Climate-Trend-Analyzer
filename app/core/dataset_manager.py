"""
Dataset Storage and Secure Access Manager.

Handles secure resolution of sample and user-uploaded datasets, strict path-traversal
prevention, file size validation, and dataset lifecycle management.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException, status
import pandas as pd

from app.core.quality_reporter import DataQualityReporter
from app.core.validator import ClimateDataValidator
from app.models.schemas import DatasetMetadata, QualityScoreBreakdown, ValidationResult

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOADS_DIR = (BASE_DIR / "data" / "uploads").resolve()
SAMPLE_FILE_PATH = (BASE_DIR / "data" / "sample" / "sample_climate_data.csv").resolve()

# 15 MB maximum payload size for CSV uploads
MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024

# Strict identifier regex (prevent directory traversal characters such as .. or / or \)
ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def resolve_dataset_path(dataset_id: str) -> Path:
    """
    Safely resolve dataset file path while guarding against path traversal attacks.
    """
    cleaned_id = dataset_id.strip()

    if cleaned_id.lower() == "sample":
        if not SAMPLE_FILE_PATH.exists() or not SAMPLE_FILE_PATH.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Curated sample dataset file not found on server.",
            )
        return SAMPLE_FILE_PATH

    # Validate identifier format
    if not ID_REGEX.match(cleaned_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dataset identifier format. Must be alphanumeric.",
        )

    # Ensure uploads directory exists
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    target_path = (UPLOADS_DIR / f"{cleaned_id}.csv").resolve()

    # Path traversal assertion: target must strictly reside within UPLOADS_DIR
    if target_path.parent != UPLOADS_DIR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: invalid file path traversal attempt.",
        )

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset with ID '{cleaned_id}' not found.",
        )

    return target_path


def load_dataset_or_404(dataset_id: str = "sample") -> Tuple[pd.DataFrame, ValidationResult]:
    """
    Resolve and validate dataset file; returns DataFrame and ValidationResult or raises HTTP error.
    """
    path = resolve_dataset_path(dataset_id)
    df, val = ClimateDataValidator.load_and_validate(path)

    if not val.is_valid or df is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"Dataset '{dataset_id}' contains fatal validation errors.",
                "fatal_errors": val.fatal_errors,
                "warnings": val.warnings,
            },
        )

    return df, val


def get_dataset_metadata(dataset_id: str = "sample") -> DatasetMetadata:
    """Extract metadata for an active or sample dataset."""
    df, val = load_dataset_or_404(dataset_id)
    report = DataQualityReporter.evaluate(df, val)

    is_sample = dataset_id.lower() == "sample"
    name = (
        "NOAA Global Surface Temperature Anomalies (1850-2024)"
        if is_sample
        else f"User Upload ({dataset_id})"
    )
    source = (
        "NOAA NCEI Climate at a Glance (CAG) - NOAAGlobalTemp v5.1"
        if is_sample
        else "User Uploaded CSV"
    )

    return DatasetMetadata(
        dataset_id=dataset_id,
        name=name,
        source=source,
        is_sample=is_sample,
        total_rows=val.total_rows,
        date_range_start=report.date_range_start,
        date_range_end=report.date_range_end,
        detected_columns=val.detected_columns,
        climate_columns=val.climate_columns,
        date_column=val.date_column,
    )


def save_uploaded_csv(
    filename: str,
    content: bytes,
) -> Tuple[str, ValidationResult, QualityScoreBreakdown]:
    """
    Validate, sanitize, and safely persist an uploaded CSV file.
    Ensures atomic creation, prevents overwrites, and cleans up partial files on failure.
    
    Args:
        filename: Original file name.
        content: Raw byte contents.
        
    Returns:
        Tuple of (dataset_id, ValidationResult, QualityScoreBreakdown)
    """
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"File size exceeds maximum allowed limit of "
                f"{MAX_UPLOAD_SIZE_BYTES / (1024 * 1024):.0f} MB."
            ),
        )

    if not filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only comma-separated (.csv) files are supported.",
        )

    # Validate contents using ClimateDataValidator before writing anything to disk
    df, val = ClimateDataValidator.load_and_validate(content)

    if not val.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "The uploaded CSV does not satisfy the required climate data schema.",
                "fatal_errors": val.fatal_errors,
                "warnings": val.warnings,
            },
        )

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate collision-free UUID
    while True:
        dataset_id = uuid.uuid4().hex
        destination = UPLOADS_DIR / f"{dataset_id}.csv"
        if not destination.exists():
            break

    # Write safely with automatic cleanup on failure
    try:
        with open(destination, "wb") as f:
            f.write(content)

        # Compute quality report
        report = DataQualityReporter.evaluate(df, val)
        return dataset_id, val, report.quality_score
    except Exception:
        # Guarantee no partial or corrupt file remains on disk
        destination.unlink(missing_ok=True)
        raise

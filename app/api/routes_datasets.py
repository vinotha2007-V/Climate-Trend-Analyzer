"""
Dataset API Routes.

Exposes endpoints for retrieving sample dataset metadata, preview observations,
evaluating sample data quality, and safely uploading new climate CSV datasets.
"""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.dataset_manager import (
    get_dataset_metadata,
    load_dataset_or_404,
    save_uploaded_csv,
)
from app.core.quality_reporter import DataQualityReporter
from app.models.schemas import (
    DataQualityReport,
    SampleDatasetResponse,
    UploadResponse,
)

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])


@router.get(
    "/sample",
    response_model=SampleDatasetResponse,
    summary="Retrieve curated sample dataset metadata and preview records",
)
def get_sample_dataset():
    """Returns metadata and initial preview records of the verified NOAA dataset."""
    df, val = load_dataset_or_404("sample")
    metadata = get_dataset_metadata("sample")

    # Clean preview records for JSON serialization (first 100 rows)
    preview_df = df.head(100).copy()
    # Replace NaN with None for valid JSON serialization
    preview_records = preview_df.where(pd.notna(preview_df), None).to_dict(orient="records")

    return SampleDatasetResponse(
        metadata=metadata,
        total_records=len(df),
        data_preview=preview_records,
    )


@router.get(
    "/sample/quality",
    response_model=DataQualityReport,
    summary="Get data-quality audit report for the sample dataset",
)
def get_sample_dataset_quality():
    """Returns complete 0–100 data quality score and audit metrics for the sample dataset."""
    df, val = load_dataset_or_404("sample")
    return DataQualityReporter.evaluate(df, val)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and validate a new climate CSV dataset",
)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Accept a user-provided climate CSV, enforce schema validation and size limits,
    and return a secure dataset identifier along with data health scores.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    content = bytearray()
    chunk_size = 1024 * 1024  # 1 MB chunk
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > 15 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File size exceeds maximum allowed limit of 15 MB.",
            )

    raw_bytes = bytes(content)
    dataset_id, val, score = save_uploaded_csv(filename=file.filename, content=raw_bytes)

    return UploadResponse(
        dataset_id=dataset_id,
        filename=file.filename,
        file_size_bytes=len(raw_bytes),
        validation=val,
        quality_score=score,
        message=f"Dataset uploaded successfully. Data quality grade: {score.grade} ({score.final_score}/100).",
    )

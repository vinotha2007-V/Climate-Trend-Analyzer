"""
Climate Data Validator.

Safely ingests CSV files, normalizes header schemas, validates dates and numeric
climate records, detects duplicate timestamps and missing values, and reports
actionable diagnostics without silently mutating or dropping records.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

from app.models.schemas import ValidationResult

# Canonical alias mapping for supported climate datasets
COLUMN_ALIASES: Dict[str, List[str]] = {
    "date": [
        "date", "dates", "datetime", "timestamp", "time", "year_month",
        "month_year", "observation_date", "record_date", "dt"
    ],
    "temperature": [
        "temperature", "temp", "tavg", "mean_temp", "tmean", "temp_c",
        "temperature_c", "temp_f", "temperature_f", "temperature_degc",
        "avg_temperature", "surface_temperature"
    ],
    "rainfall": [
        "rainfall", "precipitation", "prcp", "precip", "rain", "rain_mm",
        "rainfall_mm", "prcp_mm", "total_precipitation", "precipitation_mm"
    ],
    "temp_anomaly": [
        "temp_anomaly", "temperature_anomaly", "anomaly", "anomaly_c",
        "tavg_anomaly", "temperature_anomaly_c", "anomaly_degc",
        "departure_from_average", "departure"
    ],
    "tmin": [
        "tmin", "temp_min", "min_temp", "minimum_temperature", "temperature_min"
    ],
    "tmax": [
        "tmax", "temp_max", "max_temp", "maximum_temperature", "temperature_max"
    ],
}


def normalize_column_name(col: str) -> str:
    """Clean and standardize a single header name."""
    clean = str(col).strip().lower().replace(" ", "_").replace("-", "_").replace(".", "_")
    for canonical, aliases in COLUMN_ALIASES.items():
        if clean in aliases:
            return canonical
    return clean


def parse_dates_safe(series: pd.Series) -> pd.Series:
    """
    Robust datetime parsing supporting standard ISO formats, year-month strings,
    slashed dates, and 6-digit NOAA/HadCRUT YYYYMM integer/string codes.
    """
    if series.empty:
        return pd.to_datetime(series, errors="coerce")

    # Clean whitespace and nulls
    s = series.astype(str).str.strip()
    s = s.mask(s.isin(["nan", "None", "", "null", "<NA>", "NAT"]))
    non_null = s.dropna()

    if not non_null.empty and non_null.str.match(r"^\d{6}$").all():
        return pd.to_datetime(s, format="%Y%m", errors="coerce")
    return pd.to_datetime(s, format="mixed", errors="coerce")


def map_columns(columns: List[str]) -> Tuple[Dict[str, str], Optional[str], List[str]]:
    """
    Map raw column names to canonical names.
    Returns:
        (mapping_dict, recognized_date_col, recognized_climate_cols)
    """
    mapping: Dict[str, str] = {}
    recognized_date: Optional[str] = None
    recognized_climate: List[str] = []

    for col in columns:
        norm = normalize_column_name(col)
        mapping[col] = norm
        if norm == "date" and recognized_date is None:
            recognized_date = norm
        elif norm in ("temperature", "rainfall", "temp_anomaly", "tmin", "tmax"):
            if norm not in recognized_climate:
                recognized_climate.append(norm)

    return mapping, recognized_date, recognized_climate


class ClimateDataValidator:
    """Validates CSV climate records safely without dropping or imputing rows."""

    @staticmethod
    def load_and_validate(
        source: Union[str, bytes, Path, io.StringIO, io.BytesIO]
    ) -> Tuple[Optional[pd.DataFrame], ValidationResult]:
        """
        Ingest CSV data, normalize headers, and validate schema integrity.
        
        Args:
            source: File path, raw CSV text string, bytes, or file-like buffer.
            
        Returns:
            Tuple of (DataFrame or None, ValidationResult)
        """
        fatal_errors: List[str] = []
        warnings: List[str] = []

        # 1. Read CSV into DataFrame safely
        df: Optional[pd.DataFrame] = None
        try:
            if isinstance(source, bytes):
                # Try common encodings
                for enc in ("utf-8", "utf-8-sig", "latin-1"):
                    try:
                        df = pd.read_csv(io.BytesIO(source), encoding=enc, comment="#")
                        break
                    except (UnicodeDecodeError, pd.errors.ParserError):
                        continue
                if df is None:
                    fatal_errors.append("Failed to decode CSV bytes with supported encodings (UTF-8, Latin-1).")
            elif isinstance(source, (str, Path)):
                source_str = str(source)
                if source_str.strip() == "":
                    fatal_errors.append("The CSV data source is empty (0 bytes).")
                elif "\n" in source_str or "," in source_str:
                    # Raw CSV content passed directly
                    df = pd.read_csv(io.StringIO(source_str), comment="#")
                else:
                    path = Path(source)
                    if not path.exists():
                        fatal_errors.append(f"File not found: '{source}'")
                    elif path.stat().st_size == 0:
                        fatal_errors.append("The uploaded CSV file is empty (0 bytes).")
                    else:
                        df = pd.read_csv(path, comment="#")
            elif hasattr(source, "read"):
                df = pd.read_csv(source, comment="#")
            else:
                fatal_errors.append(f"Unsupported source type: {type(source).__name__}")
        except pd.errors.EmptyDataError:
            fatal_errors.append("The CSV file contains no data or headers (empty file).")
        except pd.errors.ParserError as e:
            fatal_errors.append(f"Malformed CSV syntax or unparseable lines: {str(e)}")
        except Exception as e:
            fatal_errors.append(f"Unexpected error reading CSV: {str(e)}")

        if fatal_errors or df is None:
            return None, ValidationResult(
                is_valid=False,
                fatal_errors=fatal_errors,
                warnings=warnings,
                total_rows=0,
                total_columns=0,
                detected_columns=[],
                normalized_columns={},
            )

        # 2. Check for empty DataFrame
        raw_columns = [str(c) for c in df.columns]
        total_rows = len(df)
        total_cols = len(raw_columns)

        if total_rows == 0:
            fatal_errors.append("The CSV file contains headers but contains 0 data rows.")
            return df, ValidationResult(
                is_valid=False,
                fatal_errors=fatal_errors,
                warnings=warnings,
                total_rows=0,
                total_columns=total_cols,
                detected_columns=raw_columns,
                normalized_columns={},
            )

        # 3. Normalize column headers
        col_mapping, date_col, climate_cols = map_columns(raw_columns)
        normalized_df = df.rename(columns=col_mapping).copy()

        # 4. Validate required schema columns
        if not date_col:
            fatal_errors.append(
                f"Missing required date column. Recognized aliases: {', '.join(COLUMN_ALIASES['date'])}. "
                f"Detected columns: {raw_columns}"
            )

        if not climate_cols:
            fatal_errors.append(
                "Missing at least one numeric climate measurement column "
                "(e.g., 'temperature', 'rainfall', 'temp_anomaly'). "
                f"Detected columns: {raw_columns}"
            )

        # If missing critical columns, abort early before field validation
        if fatal_errors:
            return normalized_df, ValidationResult(
                is_valid=False,
                fatal_errors=fatal_errors,
                warnings=warnings,
                total_rows=total_rows,
                total_columns=total_cols,
                detected_columns=raw_columns,
                normalized_columns=col_mapping,
                date_column=date_col,
                climate_columns=climate_cols,
            )

        # 5. Validate Date parsing
        date_series = normalized_df[date_col]
        coerced_dates = parse_dates_safe(date_series)
        missing_dates = int(date_series.isna().sum())
        invalid_dates = int((coerced_dates.isna() & date_series.notna()).sum())

        if missing_dates > 0:
            warnings.append(f"Found {missing_dates} row(s) with missing date timestamps.")
        if invalid_dates > 0:
            warnings.append(f"Found {invalid_dates} row(s) with unparseable date formats.")
        if coerced_dates.isna().all():
            fatal_errors.append(f"Date column '{date_col}' contains 0 valid parseable timestamps.")

        # Check duplicate dates
        duplicate_dates = int(coerced_dates.dropna().duplicated().sum())
        if duplicate_dates > 0:
            warnings.append(f"Found {duplicate_dates} duplicate date record(s).")

        # 6. Validate Climate Measurement Columns
        for col in climate_cols:
            series = normalized_df[col]
            missing_val_count = int(series.isna().sum())
            coerced_numeric = pd.to_numeric(series, errors="coerce")
            invalid_numeric_count = int((coerced_numeric.isna() & series.notna()).sum())

            if missing_val_count > 0:
                pct = (missing_val_count / total_rows) * 100
                warnings.append(f"Column '{col}' has {missing_val_count} missing values ({pct:.1f}%).")

            if invalid_numeric_count > 0:
                warnings.append(f"Column '{col}' has {invalid_numeric_count} non-numeric invalid value(s).")

            if coerced_numeric.isna().all():
                fatal_errors.append(f"Climate column '{col}' contains no valid numeric data points.")

        is_valid = len(fatal_errors) == 0

        return normalized_df, ValidationResult(
            is_valid=is_valid,
            fatal_errors=fatal_errors,
            warnings=warnings,
            total_rows=total_rows,
            total_columns=total_cols,
            detected_columns=raw_columns,
            normalized_columns=col_mapping,
            date_column=date_col,
            climate_columns=climate_cols,
        )

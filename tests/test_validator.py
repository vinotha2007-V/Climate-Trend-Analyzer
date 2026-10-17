"""
Tests for ClimateDataValidator.
"""
import io
import pytest
import pandas as pd
from app.core.validator import ClimateDataValidator, normalize_column_name


SAMPLE_VALID_CSV = """date,temperature,rainfall
2020-01-01,15.2,45.0
2020-02-01,16.1,38.2
2020-03-01,18.4,22.1
2020-04-01,21.0,15.0
"""

SAMPLE_ALIASES_CSV = """observation_date,tavg,prcp_mm,temp_anomaly
2021-01-01,12.5,50.2,0.45
2021-02-01,13.8,42.1,0.62
"""

SAMPLE_MISSING_DATE_COL_CSV = """location,temperature,humidity
CityA,22.5,60
CityB,24.1,65
"""

SAMPLE_MISSING_CLIMATE_COL_CSV = """date,city,country
2020-01-01,London,UK
2020-02-01,Paris,France
"""

SAMPLE_HEADER_ONLY_CSV = """date,temperature,rainfall
"""

SAMPLE_DIRTY_DATA_CSV = """date,temperature,rainfall
2020-01-01,15.2,45.0
2020-02-01,corrupted_value,38.2
invalid_date_str,18.4,22.1
2020-01-01,15.2,45.0
2020-05-01,,12.0
"""


def test_normalize_column_name():
    """Verify alias mapping and header normalization."""
    assert normalize_column_name("Date") == "date"
    assert normalize_column_name(" observation_date ") == "date"
    assert normalize_column_name("TAVG") == "temperature"
    assert normalize_column_name("temperature_c") == "temperature"
    assert normalize_column_name("precipitation") == "rainfall"
    assert normalize_column_name("prcp_mm") == "rainfall"
    assert normalize_column_name("temp_anomaly") == "temp_anomaly"
    assert normalize_column_name("Custom_Metric") == "custom_metric"


def test_valid_csv_ingestion():
    """Verify valid CSV is parsed, mapped, and passes validation."""
    df, result = ClimateDataValidator.load_and_validate(SAMPLE_VALID_CSV)
    assert result.is_valid is True
    assert len(result.fatal_errors) == 0
    assert result.total_rows == 4
    assert result.total_columns == 3
    assert result.date_column == "date"
    assert "temperature" in result.climate_columns
    assert "rainfall" in result.climate_columns
    assert df is not None
    assert len(df) == 4
    # Columns in returned DataFrame are normalized
    assert "date" in df.columns
    assert "temperature" in df.columns
    assert "rainfall" in df.columns


def test_column_alias_mapping():
    """Verify non-standard but recognized header aliases are matched."""
    df, result = ClimateDataValidator.load_and_validate(SAMPLE_ALIASES_CSV)
    assert result.is_valid is True
    assert result.date_column == "date"
    assert "temperature" in result.climate_columns
    assert "rainfall" in result.climate_columns
    assert "temp_anomaly" in result.climate_columns


def test_missing_date_column():
    """Verify fatal error is reported when no date column exists."""
    df, result = ClimateDataValidator.load_and_validate(SAMPLE_MISSING_DATE_COL_CSV)
    assert result.is_valid is False
    assert any("date" in err.lower() for err in result.fatal_errors)


def test_missing_climate_column():
    """Verify fatal error when no numeric climate columns are present."""
    df, result = ClimateDataValidator.load_and_validate(SAMPLE_MISSING_CLIMATE_COL_CSV)
    assert result.is_valid is False
    assert any("climate measurement" in err.lower() for err in result.fatal_errors)


def test_empty_string_input():
    """Verify empty CSV string returns invalid result without crashing."""
    df, result = ClimateDataValidator.load_and_validate("")
    assert result.is_valid is False
    assert any("empty" in err.lower() or "no data" in err.lower() for err in result.fatal_errors)


def test_header_only_csv():
    """Verify CSV with headers but zero data rows fails validation gracefully."""
    df, result = ClimateDataValidator.load_and_validate(SAMPLE_HEADER_ONLY_CSV)
    assert result.is_valid is False
    assert result.total_rows == 0
    assert any("0 data rows" in err for err in result.fatal_errors)


def test_dirty_data_warnings_and_no_silent_mutations():
    """
    Verify validator warns on invalid dates, non-numeric values, duplicates,
    and missing data without silently deleting or imputing records.
    """
    df, result = ClimateDataValidator.load_and_validate(SAMPLE_DIRTY_DATA_CSV)
    assert df is not None
    # Crucial rule: original 5 rows must NOT be deleted or dropped
    assert len(df) == 5

    # Warnings should capture dirty data aspects
    warning_text = " ".join(result.warnings)
    assert "unparseable date" in warning_text.lower()
    assert "non-numeric" in warning_text.lower()
    assert "duplicate date" in warning_text.lower()
    assert "missing values" in warning_text.lower()


def test_bytes_input_support():
    """Verify bytes object can be passed directly as source."""
    bytes_data = SAMPLE_VALID_CSV.encode("utf-8")
    df, result = ClimateDataValidator.load_and_validate(bytes_data)
    assert result.is_valid is True
    assert result.total_rows == 4


def test_mixed_case_and_spaced_headers():
    """Verify headers with spaces, capitals, and dashes normalize cleanly."""
    csv_data = """Observation Date, Mean-Temp , Total Precipitation
2020-01-01,14.5,12.0
2020-02-01,15.2,18.5
"""
    df, result = ClimateDataValidator.load_and_validate(csv_data)
    assert result.is_valid is True
    assert result.date_column == "date"
    assert "temperature" in result.climate_columns
    assert "rainfall" in result.climate_columns


def test_various_date_formats():
    """Verify ISO strings and year-month strings parse cleanly."""
    csv_data = """date,temperature
2021/01/15,10.2
2021-02-15,11.0
2021-03,12.5
"""
    df, result = ClimateDataValidator.load_and_validate(csv_data)
    assert result.is_valid is True
    assert len(result.warnings) == 0


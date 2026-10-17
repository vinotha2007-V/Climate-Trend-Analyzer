"""
Pydantic schemas and data contracts for data validation and quality reporting.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ColumnQuality(BaseModel):
    """Detailed quality metrics for a single column."""
    name: str = Field(..., description="Column name")
    normalized_name: str = Field(..., description="Standardized internal column name")
    inferred_type: str = Field(..., description="Inferred data type (e.g., date, float, integer, object)")
    total_records: int = Field(..., ge=0, description="Total record count in column")
    missing_count: int = Field(..., ge=0, description="Count of null/empty/NaN records")
    missing_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of missing records")
    invalid_count: int = Field(0, ge=0, description="Count of values that could not be parsed to target type")


class QualityScoreBreakdown(BaseModel):
    """Transparent deduction breakdown for data-quality scoring."""
    base_score: float = 100.0
    missing_data_penalty: float = Field(0.0, ge=0.0, description="Penalty for missing values")
    duplicate_date_penalty: float = Field(0.0, ge=0.0, description="Penalty for duplicate date entries")
    invalid_value_penalty: float = Field(0.0, ge=0.0, description="Penalty for unparseable dates or non-numeric values")
    empty_column_penalty: float = Field(0.0, ge=0.0, description="Penalty for entirely empty required columns")
    final_score: float = Field(..., ge=0.0, le=100.0, description="Final clamped score (0.0 - 100.0)")
    grade: str = Field(..., description="Qualitative rating: Excellent, Good, Fair, or Poor")
    methodology: str = Field(..., description="Explanation of calculation rules and applied weights")


class ValidationResult(BaseModel):
    """Outcome of CSV loading, schema normalization, and structural validation."""
    is_valid: bool = Field(..., description="True if dataset satisfies minimal required schema and has parseable data")
    fatal_errors: List[str] = Field(default_factory=list, description="Blocking errors preventing analysis")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking data health notices")
    total_rows: int = Field(0, ge=0, description="Total data rows parsed")
    total_columns: int = Field(0, ge=0, description="Total columns identified")
    detected_columns: List[str] = Field(default_factory=list, description="Original column headers in CSV")
    normalized_columns: Dict[str, str] = Field(default_factory=dict, description="Mapping of original -> standard names")
    date_column: Optional[str] = Field(None, description="Standardized name of recognized date column")
    climate_columns: List[str] = Field(default_factory=list, description="Recognized numeric climate columns")


class DataQualityReport(BaseModel):
    """Complete data-quality audit report."""
    validation: ValidationResult
    quality_score: QualityScoreBreakdown
    column_metrics: List[ColumnQuality] = Field(default_factory=list)
    duplicate_date_count: int = Field(0, ge=0, description="Count of non-unique timestamps/dates")
    date_range_start: Optional[str] = Field(None, description="Earliest valid date in dataset (ISO-8601 string)")
    date_range_end: Optional[str] = Field(None, description="Latest valid date in dataset (ISO-8601 string)")


# ==========================================
# Phase 3: Scientific Analysis & Anomaly Schemas
# ==========================================

class TrendPoint(BaseModel):
    """Aggregated or filtered time series observation point."""
    period: str = Field(..., description="Timestamp or period identifier (e.g., '2020', '2020-05')")
    mean: float = Field(..., description="Arithmetic mean of values in period")
    min: float = Field(..., description="Minimum observed value in period")
    max: float = Field(..., description="Maximum observed value in period")
    total: Optional[float] = Field(None, description="Sum of values (especially for rainfall / precipitation)")
    count: int = Field(..., ge=0, description="Number of valid observations in period")
    rolling_avg: Optional[float] = Field(None, description="Centered/backward rolling average value")


class LinearTrend(BaseModel):
    """Linear regression trend statistics over time."""
    slope_per_year: float = Field(..., description="Rate of change per year")
    slope_per_decade: float = Field(..., description="Rate of change per decade (10 * slope_per_year)")
    intercept: float = Field(..., description="Regression intercept")
    r_squared: float = Field(..., ge=0.0, le=1.0, description="Coefficient of determination (R²)")
    p_value: Optional[float] = Field(None, description="Two-sided p-value for a hypothesis test whose null hypothesis is slope=0")
    std_err: Optional[float] = Field(None, description="Standard error of the estimated gradient")
    unit_description: str = Field(..., description="Detailed description of physical units (e.g., '°C per decade')")
    is_statistically_significant: bool = Field(..., description="True if p_value < 0.05")


class TrendAnalysisResult(BaseModel):
    """Comprehensive trend analysis outcome."""
    column_name: str = Field(..., description="Analyzed climate measurement column")
    aggregation_frequency: str = Field(..., description="Aggregation cadence: 'annual', 'monthly', or 'raw'")
    time_period_start: Optional[str] = Field(None, description="Earliest date included in analysis")
    time_period_end: Optional[str] = Field(None, description="Latest date included in analysis")
    total_observations: int = Field(..., ge=0, description="Total rows in dataset range")
    valid_observations: int = Field(..., ge=0, description="Count of non-null numeric observations")
    missing_observations: int = Field(..., ge=0, description="Count of omitted null or invalid rows")
    missing_percentage: float = Field(..., ge=0.0, le=100.0, description="Missing observation percentage")
    rolling_window: int = Field(..., ge=1, description="Rolling window size in periods")
    linear_trend: Optional[LinearTrend] = Field(None, description="Estimated linear regression trend if estimable")
    data_points: List[TrendPoint] = Field(default_factory=list, description="Computed trend summary points")
    limitations: List[str] = Field(default_factory=list, description="Data and statistical caveats")
    scientific_disclaimer: str = Field(
        default="A statistical trend describes observed historical association and does not prove causal mechanisms.",
        description="Scientific non-causation disclaimer"
    )


class MonthlyClimatology(BaseModel):
    """Historical average pattern for a specific month across multi-year records."""
    month: int = Field(..., ge=1, le=12, description="Month index (1-12)")
    month_name: str = Field(..., description="Month name (e.g. 'January')")
    mean: float = Field(..., description="Historical average for this month across all years")
    min: float = Field(..., description="Lowest recorded monthly value")
    max: float = Field(..., description="Highest recorded monthly value")
    std: Optional[float] = Field(None, description="Sample standard deviation across years")
    observation_count: int = Field(..., ge=0, description="Number of yearly records contributing to month")


class SeasonalSummary(BaseModel):
    """Aggregated climatological pattern for standard meteorological seasons."""
    season: str = Field(..., description="Season name (e.g. 'DJF - Winter', 'MAM - Spring')")
    months: List[str] = Field(..., description="Included months")
    mean: float = Field(..., description="Mean seasonal value")
    min: float = Field(..., description="Minimum seasonal value")
    max: float = Field(..., description="Maximum seasonal value")


class SeasonalAnalysisResult(BaseModel):
    """Outcome of seasonal climatology analysis."""
    column_name: str = Field(..., description="Analyzed climate measurement")
    total_years: int = Field(..., ge=0, description="Number of distinct years present")
    is_seasonal_supported: bool = Field(..., description="True if frequency and coverage support seasonal patterns")
    reason_if_unsupported: Optional[str] = Field(None, description="Explanation if dataset coverage is insufficient")
    monthly_patterns: List[MonthlyClimatology] = Field(default_factory=list)
    seasonal_summaries: List[SeasonalSummary] = Field(default_factory=list)
    scientific_distinction_note: str = Field(
        default="Monthly averages show historical climatology cycles, distinct from mathematical seasonal time-series decomposition.",
        description="Distinction between empirical monthly averages and mathematical decomposition"
    )


class AnomalyPoint(BaseModel):
    """Individual anomaly detection evaluation point."""
    date: str = Field(..., description="Observation timestamp")
    original_value: float = Field(..., description="Observed climate metric value")
    method: str = Field(..., description="Detection algorithm: 'z_score' or 'iqr'")
    score: float = Field(..., description="Calculated metric (standardized z-score or distance from IQR fence)")
    threshold_used: float = Field(..., description="Threshold applied")
    lower_bound: Optional[float] = Field(None, description="Lower statistical fence")
    upper_bound: Optional[float] = Field(None, description="Upper statistical fence")
    is_anomaly: bool = Field(..., description="True if observation breaches detection threshold")


class AnomalyDetectionResult(BaseModel):
    """Collection of anomaly detection results and statistical baselines."""
    column_name: str = Field(..., description="Analyzed measurement column")
    method: str = Field(..., description="Applied algorithm: 'z_score' or 'iqr'")
    threshold_used: float = Field(..., description="Threshold multiplier used")
    total_points: int = Field(..., ge=0, description="Total points evaluated")
    valid_points: int = Field(..., ge=0, description="Count of numeric points tested")
    anomaly_count: int = Field(..., ge=0, description="Count of flagged statistical anomalies")
    anomaly_percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of anomalies")
    baseline_mean: Optional[float] = Field(None, description="Mean (for Z-score baseline)")
    baseline_std: Optional[float] = Field(None, description="Standard deviation (for Z-score baseline)")
    q1: Optional[float] = Field(None, description="25th percentile (for IQR baseline)")
    q3: Optional[float] = Field(None, description="75th percentile (for IQR baseline)")
    iqr: Optional[float] = Field(None, description="Interquartile range (for IQR baseline)")
    anomalies: List[AnomalyPoint] = Field(default_factory=list, description="All points with anomaly flags")
    limitations: List[str] = Field(default_factory=list, description="Caveats and baseline notices")
    scientific_caveat: str = Field(
        default="A statistical anomaly denotes an unusual mathematical deviation; it does not automatically indicate a climate disaster or sensor malfunction.",
        description="Scientific caveat regarding anomaly interpretation"
    )


# ==========================================
# Phase 5: REST API & Export Schemas
# ==========================================

class DatasetMetadata(BaseModel):
    """Metadata information for an active or sample dataset."""
    dataset_id: str = Field(..., description="Unique dataset identifier or 'sample'")
    name: str = Field(..., description="Human-readable dataset title")
    source: str = Field(..., description="Origin / provider attribution")
    is_sample: bool = Field(False, description="True if this is the verified public reference dataset")
    total_rows: int = Field(..., ge=0, description="Total observations in dataset")
    date_range_start: Optional[str] = Field(None, description="Earliest observation timestamp")
    date_range_end: Optional[str] = Field(None, description="Latest observation timestamp")
    detected_columns: List[str] = Field(default_factory=list, description="Raw column headers")
    climate_columns: List[str] = Field(default_factory=list, description="Identified numeric climate variables")
    date_column: Optional[str] = Field(None, description="Standardized date column header")


class SampleDatasetResponse(BaseModel):
    """API payload for the curated sample dataset."""
    metadata: DatasetMetadata
    total_records: int
    data_preview: List[Dict[str, Optional[float | str]]] = Field(
        default_factory=list,
        description="Initial preview records for UI inspection"
    )


class UploadResponse(BaseModel):
    """API payload upon uploading a user CSV dataset."""
    dataset_id: str = Field(..., description="Secure generated identifier for querying this dataset")
    filename: str = Field(..., description="Sanitized original filename")
    file_size_bytes: int = Field(..., ge=0, description="Size of uploaded CSV in bytes")
    validation: ValidationResult
    quality_score: QualityScoreBreakdown
    message: str = Field(..., description="User-facing status message")



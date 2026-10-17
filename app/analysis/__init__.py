"""Climate statistical analysis, trends, and anomaly detection package."""

from app.analysis.trends import calculate_trends
from app.analysis.seasonal import calculate_seasonal_patterns
from app.analysis.anomalies import detect_anomalies

__all__ = [
    "calculate_trends",
    "calculate_seasonal_patterns",
    "detect_anomalies",
]

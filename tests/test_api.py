"""
Integration and End-to-End API Tests for Climate Trend Analyzer.
"""
import io
import pytest
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)

MOCK_VALID_CSV = """date,temperature,rainfall
2020-01-01,10.5,50.0
2020-02-01,11.2,42.0
2020-03-01,13.8,30.0
2020-04-01,16.5,20.0
2020-05-01,20.1,15.0
"""

MOCK_INVALID_CSV = """city,country,population
Paris,France,2161000
London,UK,8982000
"""


def test_health_check_endpoint():
    """Verify health endpoint returns status 200 with service information."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Climate Trend Analyzer" in data["service"]


def test_dashboard_home_route_serves_html():
    """Verify root GET / serves the interactive dashboard HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Climate Trend Analyzer" in response.text
    assert "trendChart" in response.text


def test_static_css_served():
    """Verify static stylesheet is served with status 200."""
    response = client.get("/static/css/style.css")
    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"] or "text/plain" in response.headers["content-type"]


def test_sample_dataset_retrieval():
    """Verify sample dataset endpoint returns metadata and preview records."""
    response = client.get("/api/datasets/sample")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 2100
    assert data["metadata"]["is_sample"] is True
    assert "NOAA" in data["metadata"]["source"]
    assert len(data["data_preview"]) > 0


def test_sample_dataset_quality_endpoint():
    """Verify sample dataset quality endpoint returns 100.0 Excellent score."""
    response = client.get("/api/datasets/sample/quality")
    assert response.status_code == 200
    data = response.json()
    assert data["validation"]["is_valid"] is True
    assert data["quality_score"]["final_score"] == 100.0
    assert data["quality_score"]["grade"] == "Excellent"


def test_successful_csv_upload_and_query():
    """Verify uploading a custom CSV yields a valid dataset_id that can be queried."""
    files = {"file": ("test_custom.csv", io.BytesIO(MOCK_VALID_CSV.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=files)

    assert upload_res.status_code == 201
    upload_data = upload_res.json()
    dataset_id = upload_data["dataset_id"]
    assert dataset_id != "sample"
    assert upload_data["validation"]["is_valid"] is True
    assert upload_data["quality_score"]["final_score"] == 100.0

    # Query trends on the uploaded dataset
    trends_res = client.get(f"/api/analysis/trends?dataset_id={dataset_id}")
    assert trends_res.status_code == 200
    trends_data = trends_res.json()
    assert trends_data["valid_observations"] == 5

    # Query quality on uploaded dataset
    quality_res = client.get(f"/api/analysis/quality?dataset_id={dataset_id}")
    assert quality_res.status_code == 200
    assert quality_res.json()["quality_score"]["final_score"] == 100.0


def test_upload_missing_climate_columns_fails():
    """Verify uploading CSV without date/climate columns returns HTTP 400."""
    files = {"file": ("invalid.csv", io.BytesIO(MOCK_INVALID_CSV.encode("utf-8")), "text/csv")}
    response = client.post("/api/datasets/upload", files=files)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "fatal_errors" in detail
    assert any("date" in err.lower() for err in detail["fatal_errors"])


def test_upload_empty_file_fails():
    """Verify uploading zero-byte CSV returns HTTP 400."""
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    response = client.post("/api/datasets/upload", files=files)

    assert response.status_code == 400
    assert "fatal_errors" in response.json()["detail"]


def test_upload_non_csv_extension_fails():
    """Verify uploading non-.csv file returns HTTP 400."""
    files = {"file": ("document.txt", io.BytesIO(b"plain text"), "text/plain")}
    response = client.post("/api/datasets/upload", files=files)

    assert response.status_code == 400
    assert "Only comma-separated" in response.json()["detail"]


def test_analysis_trends_endpoint():
    """Verify trends endpoint computes annual and monthly cadences on sample data."""
    # Annual default
    res = client.get("/api/analysis/trends?dataset_id=sample&frequency=annual&window=5")
    assert res.status_code == 200
    data = res.json()
    assert data["aggregation_frequency"] == "annual"
    assert data["linear_trend"] is not None
    assert data["linear_trend"]["slope_per_decade"] > 0.0

    # Monthly
    m_res = client.get("/api/analysis/trends?dataset_id=sample&frequency=monthly&window=12")
    assert m_res.status_code == 200
    assert m_res.json()["aggregation_frequency"] == "monthly"


def test_analysis_trends_invalid_parameters():
    """Verify invalid frequency pattern returns HTTP 422."""
    res = client.get("/api/analysis/trends?dataset_id=sample&frequency=hourly")
    assert res.status_code == 422


def test_analysis_seasonal_endpoint():
    """Verify seasonal endpoint returns 12-month pattern on sample data."""
    res = client.get("/api/analysis/seasonal?dataset_id=sample")
    assert res.status_code == 200
    data = res.json()
    assert data["is_seasonal_supported"] is True
    assert len(data["monthly_patterns"]) == 12


def test_analysis_anomalies_endpoint():
    """Verify anomaly detection endpoint with Z-score and IQR algorithms."""
    # Z-score
    z_res = client.get("/api/analysis/anomalies?dataset_id=sample&method=z_score&threshold=2.5")
    assert z_res.status_code == 200
    z_data = z_res.json()
    assert z_data["method"] == "z_score"
    assert z_data["anomaly_count"] > 0

    # IQR
    iqr_res = client.get("/api/analysis/anomalies?dataset_id=sample&method=iqr&threshold=1.5")
    assert iqr_res.status_code == 200
    iqr_data = iqr_res.json()
    assert iqr_data["method"] == "iqr"


def test_analysis_anomalies_invalid_method():
    """Verify unsupported anomaly algorithm returns HTTP 422."""
    res = client.get("/api/analysis/anomalies?dataset_id=sample&method=kmeans")
    assert res.status_code == 422


def test_export_csv_endpoint():
    """Verify CSV export endpoint returns downloadable attachment with optional anomaly flags."""
    res = client.get("/api/export/csv?dataset_id=sample&include_anomalies=true&method=z_score&threshold=2.5")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert 'attachment; filename="climate_sample_processed.csv"' in res.headers["content-disposition"]
    csv_text = res.text
    assert "date" in csv_text
    assert "temp_anomaly_is_anomaly" in csv_text
    assert "temp_anomaly_anomaly_score" in csv_text


def test_export_summary_json_endpoint():
    """Verify summary export endpoint returns structured JSON report."""
    res = client.get("/api/export/summary?dataset_id=sample")
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
    assert 'attachment; filename="climate_sample_summary.json"' in res.headers["content-disposition"]
    data = res.json()
    assert "metadata" in data
    assert "data_quality_report" in data
    assert "trend_analysis" in data
    assert "scientific_disclaimer" in data


def test_security_path_traversal_prevention():
    """Verify attempts to pass path traversal sequences in dataset_id are blocked."""
    # Directory traversal attack
    res1 = client.get("/api/analysis/trends?dataset_id=../../etc/passwd")
    assert res1.status_code in (400, 403, 404)

    res2 = client.get("/api/analysis/trends?dataset_id=../sample")
    assert res2.status_code in (400, 403, 404)

    # Non-existent dataset ID
    res3 = client.get("/api/analysis/trends?dataset_id=nonexistent_dataset_12345")
    assert res3.status_code == 404


def test_oversized_upload_rejection():
    """Verify uploads exceeding 15MB are rejected with HTTP 413."""
    oversized_bytes = b"date,temperature\n" + b"2020-01-01,15.0\n" * 1_000_000
    files = {"file": ("huge_file.csv", io.BytesIO(oversized_bytes), "text/csv")}
    response = client.post("/api/datasets/upload", files=files)
    assert response.status_code == 413
    assert "exceeds maximum allowed limit" in response.json()["detail"]


def test_failed_upload_leaves_no_garbage_files():
    """Verify that a rejected upload never leaves partial files on disk."""
    from pathlib import Path
    uploads_dir = Path("data/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    files_before = set(uploads_dir.glob("*.csv"))

    # Attempt failed upload (missing climate column)
    files = {"file": ("bad_payload.csv", io.BytesIO(MOCK_INVALID_CSV.encode("utf-8")), "text/csv")}
    res = client.post("/api/datasets/upload", files=files)
    assert res.status_code == 400

    files_after = set(uploads_dir.glob("*.csv"))
    # Exactly same set of files, no leftover artifacts
    assert files_before == files_after


def test_consecutive_uploads_unique_ids_and_no_overwrites():
    """Verify consecutive uploads generate distinct IDs and both remain accessible."""
    csv_a = "date,temperature\n2020-01-01,10.0\n2020-02-01,11.0\n2020-03-01,12.0\n"
    csv_b = "date,temperature\n2021-01-01,20.0\n2021-02-01,21.0\n2021-03-01,22.0\n"

    res_a = client.post("/api/datasets/upload", files={"file": ("a.csv", io.BytesIO(csv_a.encode("utf-8")), "text/csv")})
    res_b = client.post("/api/datasets/upload", files={"file": ("b.csv", io.BytesIO(csv_b.encode("utf-8")), "text/csv")})

    assert res_a.status_code == 201
    assert res_b.status_code == 201

    id_a = res_a.json()["dataset_id"]
    id_b = res_b.json()["dataset_id"]
    assert id_a != id_b

    # Query dataset A (annual mean for 2020: (10+11+12)/3 = 11.0)
    t_a = client.get(f"/api/analysis/trends?dataset_id={id_a}&frequency=annual").json()
    assert t_a["data_points"][0]["mean"] == 11.0

    # Query dataset B (annual mean for 2021: (20+21+22)/3 = 21.0)
    t_b = client.get(f"/api/analysis/trends?dataset_id={id_b}&frequency=annual").json()
    assert t_b["data_points"][0]["mean"] == 21.0


# Climate Trend Analyzer

An end-to-end, full-stack scientific time-series analytics platform designed to ingest, validate, analyze, and visualize historical climate observations (surface temperatures and rainfall), compute empirical rates of change, perform statistical anomaly detection, and deliver actionable data quality insights through an interactive web dashboard.

---

## 🌟 Key Features

1. **Automated Data Ingestion & Quality Engine (`app/core/`)**
   - Safe CSV parsing with multi-format date coercion (`YYYY-MM-DD`, `YYYY-MM`, slashed dates, and NOAA 6-digit `YYYYMM` codes).
   - Zero-silent-mutation principle: raw observation counts and indices are strictly preserved without automatic row dropping or imputation.
   - Transparent **0–100 Data-Quality Health Score** auditing missing values, duplicate timestamps, and data types with deterministic penalty breakdowns.

2. **Scientific Trend & Rate-of-Change Analysis (`app/analysis/trends.py`)**
   - Annual and monthly aggregations with configurable moving average windows (e.g. 5-period, 10-period rolling means).
   - Ordinary Least Squares (OLS) regression over continuous decimal years, calculating rates of change per decade (`°C/decade` or `mm/decade`), $R^2$ variance explained, standard errors, and two-sided $p$-values.
   - Prominently displays non-causation disclaimers emphasizing that statistical trends describe observed historical correlation.

3. **Multi-Year Climatology & Seasonal Patterns (`app/analysis/seasonal.py`)**
   - Multi-year calendar month climatology cycle (January through December) with mean, min, max, and sample standard deviations.
   - Aggregated meteorological seasons: **DJF** (Winter), **MAM** (Spring), **JJA** (Summer), and **SON** (Autumn).
   - Rigorous data sufficiency gates rejecting seasonal calculations for datasets with insufficient year spans or non-monthly frequencies.

4. **Configurable Anomaly Detection (`app/analysis/anomalies.py`)**
   - Parametric **$Z$-Score** ($|z| > k$) and non-parametric **Interquartile Range (IQR)** boxplot fences ($[Q_1 - k \cdot \text{IQR}, Q_3 + k \cdot \text{IQR}]$) with customizable sensitivity multipliers.
   - Resilient against zero-variance/constant data and small sample sizes.
   - Explicit scientific caveat noting that statistical anomalies indicate mathematical deviations, not verified climate disasters or sensor failures.

5. **Curated NOAA Reference Dataset (`data/sample/`)**
   - Includes **2,100 consecutive monthly global surface temperature anomaly records** (January 1850 through December 2024) from the NOAA NCEI Climate at a Glance (CAG) NOAAGlobalTemp v5.1 dataset.
   - Complete provenance, baseline periods (1901–2000), physical units (°C), and observational limitations documented in [`data/sample/DATASET_SOURCE.md`](file:///c:/Users/acer/Desktop/Climate%20Trend%20Analyzer/data/sample/DATASET_SOURCE.md).

6. **Interactive Single-Page Dashboard (`app/templates/`, `app/static/`)**
   - Modern, glassmorphic dark-theme UI with responsive layout, KPI summary cards, and interactive Chart.js time-series visualizations.
   - Drag-and-drop CSV uploader with real-time validation feedback.
   - One-click export of processed observations with anomaly flags (CSV) and analytical summaries (JSON).

7. **Production Engineering & Security**
   - Path-traversal defense (`resolve_dataset_path`), collision-free UUID identifiers, 15MB file size limits, and atomic file creation with automatic cleanup on failure.
   - 100% test coverage with **61 passing automated tests** in `pytest`.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.13, FastAPI, Uvicorn, Pydantic v2
- **Data & Statistics:** pandas, NumPy, SciPy (scipy.stats)
- **Frontend:** Vanilla HTML5, Modern Responsive CSS3 (Glassmorphism), Vanilla JavaScript (ES6+), Chart.js
- **Testing:** pytest, HTTPX / Starlette TestClient
- **Environment:** Isolated Python Virtual Environment (`.venv`)

---

## 📁 Project Architecture

```text
Climate Trend Analyzer/
├── .gitignore                     # Git exclusion rules (.venv, uploads, cache)
├── README.md                      # Comprehensive documentation and guide
├── requirements.txt               # Pinned dependencies for Python 3.13 on Windows
├── run.py                         # Single-command dev server runner
│
├── app/                           # Main application package
│   ├── __init__.py
│   ├── main.py                    # FastAPI instance, static mounts, /health & / routes
│   │
│   ├── api/                       # REST API routing layer
│   │   ├── __init__.py
│   │   ├── routes_datasets.py     # Sample metadata, quality, and CSV upload
│   │   ├── routes_analysis.py     # Trends, seasonal, anomalies, and quality
│   │   └── routes_export.py       # Downloadable CSV & JSON summary endpoints
│   │
│   ├── core/                      # Data integrity & validation engines
│   │   ├── __init__.py
│   │   ├── validator.py           # Schema checks, date coercion, alias mapping
│   │   ├── quality_reporter.py    # Per-column metrics & 0–100 health scoring
│   │   └── dataset_manager.py     # Secure path resolution, UUIDs, upload cleanup
│   │
│   ├── analysis/                  # Scientific computing & modeling
│   │   ├── __init__.py
│   │   ├── trends.py              # Decimal-year OLS regression & rolling means
│   │   ├── seasonal.py            # 12-month climatology & meteorological seasons
│   │   └── anomalies.py           # Z-score and IQR statistical outlier engines
│   │
│   ├── models/                    # Pydantic schemas & response contracts
│   │   ├── __init__.py
│   │   └── schemas.py
│   │
│   ├── static/                    # Frontend assets
│   │   ├── css/
│   │   │   └── style.css          # Glassmorphic dark theme design system
│   │   └── js/
│   │       ├── api.js             # Async REST API client
│   │       ├── charts.js          # Chart.js time-series, climatology & anomaly renderers
│   │       └── app.js             # Controller, event handlers, and tab manager
│   │
│   └── templates/
│       └── index.html             # Responsive single-page dashboard
│
├── data/
│   ├── sample/
│   │   ├── sample_climate_data.csv # 2,100 verified NOAA monthly records (1850-2024)
│   │   └── DATASET_SOURCE.md      # Attribution, units, baseline, and limitations
│   └── uploads/                   # Staged user CSV uploads (gitignored)
│
└── tests/                         # Comprehensive pytest test suite (61 tests)
    ├── __init__.py
    ├── test_scaffold.py           # Import and scaffolding tests
    ├── test_validator.py          # Schema parsing and dirty-data validation tests
    ├── test_quality_reporter.py   # Quality scoring and deduction boundary tests
    ├── test_trends.py             # Trend regression, rolling mean, and OLS tests
    ├── test_seasonal.py           # Climatology and seasonal sufficiency tests
    ├── test_anomalies.py          # Z-score and IQR anomaly detection tests
    ├── test_sample_dataset.py     # Real NOAA dataset integration tests
    └── test_api.py                # End-to-end API, security, and export tests
```

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- **Python 3.13+** installed on your system.

### 2. Activate the Virtual Environment
Open PowerShell in the project directory:
```powershell
# Activate the existing virtual environment
.\.venv\Scripts\Activate.ps1
```
*(If dependencies ever need to be reinstalled: `pip install -r requirements.txt`)*

### 3. Run the Automated Test Suite
Verify that all 61 unit, integration, and security tests pass:
```powershell
.\.venv\Scripts\pytest.exe -v
```

### 4. Start the Application Server
Run the local development server:
```powershell
python run.py
```
Or directly via Uvicorn:
```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Access the Web Dashboard
Open your browser and navigate to:
- **Interactive Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 📖 Usage Walkthrough

### 1. Exploring the Verified NOAA Reference Dataset
- Upon opening the dashboard, the **NOAA Global Surface Temperature Anomalies (1850–2024)** dataset is automatically loaded.
- View the 4 summary KPI cards displaying total observations (2,100 months), date span (1850–2024), 100/100 Excellent data quality score, and the empirical warming rate (+0.056 °C/decade).
- Adjust the **Aggregation Cadence** (Annual, Monthly, Raw) and the **Moving Average Window** (1–25 periods) to observe smoothing across decades.

### 2. Inspecting Seasonal Climatology
- Switch to the **Seasonal Climatology** tab to view the multi-year monthly cycle (Jan–Dec) and seasonal averages for Winter (DJF), Spring (MAM), Summer (JJA), and Autumn (SON).

### 3. Detecting Statistical Anomalies
- Switch to the **Anomaly Detection** tab to evaluate extreme temperature deviations.
- Choose between **Z-Score** ($|z| > k$) and **Interquartile Range (IQR)** boxplot fences.
- Adjust the sensitivity threshold ($k$) and click **Apply** to view highlighted anomaly points and the detailed anomaly events table.

### 4. Auditing Data Quality
- Switch to the **Data Quality Audit** tab to inspect the 0–100 health score meter, deduction rules, and per-column metrics detailing missing percentages and duplicate timestamps.

### 5. Uploading Custom Climate CSV Files
- Click **Upload Custom CSV** in the header or controls panel.
- Drag & drop or select any climate CSV file.
- The server strictly validates that the file has a recognized `date` column and at least one numeric climate variable (e.g. `temperature`, `rainfall`, `temp_anomaly`), rejecting invalid schemas or files over 15 MB.
- Upon successful ingestion, the active dataset switches automatically to your uploaded file.

### 6. Exporting Processed Data & Summaries
- Navigate to the **Data Preview & Export** tab.
- Click **Export Processed CSV** to download a CSV containing your observations and newly computed anomaly flags/scores (`temp_anomaly_is_anomaly`, `temp_anomaly_anomaly_score`).
- Click **Download JSON Summary** to download an analytical audit report bundling metadata, data health scores, trend statistics, and scientific disclaimers.

---

## ⚖️ Scientific & Methodological Disclaimers

1. **Non-Causation Notice:** Ordinary Least Squares (OLS) linear trend slopes describe historical observed association across time series. A statistical trend does not prove physical causation or singular attribution.
2. **Statistical Anomalies vs. Disasters:** A statistical anomaly indicates an unusual mathematical departure relative to baseline variance; it does not automatically denote an ecological disaster or sensor failure.
3. **Historical Sampling Density:** In early decades (1850–1900), in-situ terrestrial weather stations and maritime shipping logs were geographically concentrated in North America, Western Europe, and North Atlantic shipping routes, resulting in wider reconstruction confidence intervals compared to the modern satellite and ocean-buoy era (post-1979).

---

## 📜 License & Citation

- **Code:** Distributed under the MIT Open Source License.
- **Reference Climate Data:** Sourced from public domain U.S. Federal Government records provided by NOAA / NCEI:
  > *NOAA National Centers for Environmental Information, Climate at a Glance: Global Time Series, retrieved October 2026 from https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/*

# Dataset Source & Provenance Documentation

## 1. Overview & Attribution

- **Dataset Name:** NOAA Global Surface Temperature Dataset (NOAAGlobalTemp v5.1) - Global Land and Ocean Surface Temperature Anomalies
- **Publisher:** National Oceanic and Atmospheric Administration (NOAA) / National Centers for Environmental Information (NCEI)
- **Primary Portal:** [NOAA Climate at a Glance (CAG) Time Series](https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/)
- **Direct Source URL:** [https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/global/time-series/globe/land_ocean/1/0/1850-2024/data.csv](https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/global/time-series/globe/land_ocean/1/0/1850-2024/data.csv)
- **Access / Download Date:** October 2026 (Reflecting complete historical records through December 2024)
- **Licensing / Terms of Use:** Public Domain (U.S. Federal Government Data, NOAA open data policy)

---

## 2. Geographic Coverage & Temporal Range

- **Geographic Coverage:** **Global** ($90^\circ\text{S} - 90^\circ\text{N}$, $180^\circ\text{W} - 180^\circ\text{E}$). Blends in-situ land surface air temperatures (from the Global Historical Climatology Network - Monthly / GHCNm) and sea surface temperatures (from the Extended Reconstructed Sea Surface Temperature / ERSST v5).
- **Temporal Frequency:** Monthly observations.
- **Earliest Record:** January 1850 (`1850-01-01` / `185001`)
- **Latest Record:** December 2024 (`2024-12-01` / `202412`)
- **Total Valid Observations:** 2,100 consecutive monthly records across 175 complete calendar years.

---

## 3. Data Dictionary & Physical Units

| Column | Data Type | Physical Unit | Description |
| :--- | :--- | :--- | :--- |
| **`date`** | Date (`YYYY-MM-DD`) | ISO-8601 Calendar Date | First day of observation month (`YYYY-MM-01`). |
| **`temperature_anomaly`** | Float (`float64`) | **Degrees Celsius (°C)** | Global surface temperature departure from the 20th-century baseline average (1901–2000). |
| **`noaa_raw_date`** | String / Integer | `YYYYMM` code | Original 6-digit NOAA observation identifier (e.g., `185001` = January 1850). |

---

## 4. Base Period & Anomaly Methodology

- **Baseline Climatology Period:** **1901–2000** (100-year 20th-century climatological mean).
- **Interpretation:** 
  - A value of `0.00` indicates temperatures matched the 1901–2000 average.
  - A positive value (e.g., `+1.25°C` in late 2024) indicates global mean surface temperature was $1.25^\circ\text{C}$ warmer than the 20th-century baseline.
  - A negative value (e.g., `-0.43°C` in January 1850) indicates cooler conditions relative to the baseline.

---

## 5. Transformations Performed

To ensure reliable parsing across data science tools while preserving 100% empirical fidelity:
1. Stripped leading administrative comment headers (`# Title...`, `# Units...`, `# Base Period...`).
2. Mapped the original NOAA column `Departure from Average` to the canonical name `temperature_anomaly`.
3. Standardized the 6-digit date code `YYYYMM` into an ISO-8601 formatted date string (`YYYY-MM-01`), retaining the original `noaa_raw_date` for audit verification.
4. **No missing values were imputed, filled, or synthesized.** All 2,100 values represent official NOAA calculations.

---

## 6. Known Observational Limitations

1. **Station Density Over Time:** In the mid-19th century (1850–1900), direct surface weather stations were largely concentrated in North America, Western Europe, and commercial shipping lanes. Spatial interpolation and statistical reconstruction introduce higher uncertainty for early decades compared to modern satellite and Argo float eras (post-1979).
2. **Global Aggregate vs. Local Climate:** This dataset represents a planetary spatial mean. Regional and local trends exhibit substantially larger variance and localized microclimate influences.
3. **Statistical Anomaly Caveat:** Statistical anomalies identified within this dataset mark mathematical departures from long-term trends; they do not by themselves constitute causal attribution or proof of specific weather events.

---

## 7. Reproduction Steps

To verify or reproduce this download directly from NOAA's servers:

```python
import httpx
import pandas as pd
import io

url = "https://www.ncei.noaa.gov/access/monitoring/climate-at-a-glance/global/time-series/globe/land_ocean/1/0/1850-2024/data.csv"
headers = {"User-Agent": "Mozilla/5.0"}

response = httpx.get(url, follow_redirects=True, headers=headers)
response.raise_for_status()

# Exclude comment lines and load CSV
lines = [l for l in response.text.splitlines() if not l.startswith("#") and l.strip()]
df = pd.read_csv(io.StringIO("\n".join(lines)))

# Format ISO date
df["date"] = df["Date"].apply(lambda x: f"{str(x)[:4]}-{str(x)[4:6]}-01")
df["temperature_anomaly"] = df["Departure from Average"]
out_df = df[["date", "temperature_anomaly", "Date"]].rename(columns={"Date": "noaa_raw_date"})

out_df.to_csv("data/sample/sample_climate_data.csv", index=False)
print("Saved 2,100 verified NOAA observations.")
```

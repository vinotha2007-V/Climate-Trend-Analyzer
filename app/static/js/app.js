/**
 * Climate Trend Analyzer - Application Controller
 * Handles user interactions, state management, and updates views.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Global App State
  const state = {
    activeDatasetId: "sample",
    activeColumn: null,
    availableColumns: [],
    frequency: "annual",
    window: 5,
    anomalyMethod: "z_score",
    anomalyThreshold: 2.5,
    datasets: {
      sample: { name: "NOAA Global Surface Temp (1850-2024)", total_rows: 2100 }
    }
  };

  // DOM Elements
  const elements = {
    // Top Bar
    activeDatasetBadge: document.getElementById("activeDatasetBadge"),
    alertBanner: document.getElementById("alertBanner"),
    alertMessage: document.getElementById("alertMessage"),
    alertCloseBtn: document.getElementById("alertCloseBtn"),

    // KPI Cards
    kpiObservations: document.getElementById("kpiObservations"),
    kpiDateSpan: document.getElementById("kpiDateSpan"),
    kpiQualityScore: document.getElementById("kpiQualityScore"),
    kpiQualityGrade: document.getElementById("kpiQualityGrade"),
    kpiTrendSlope: document.getElementById("kpiTrendSlope"),
    kpiTrendSignificance: document.getElementById("kpiTrendSignificance"),
    kpiAnomaliesCount: document.getElementById("kpiAnomaliesCount"),
    kpiAnomaliesPct: document.getElementById("kpiAnomaliesPct"),

    // Controls
    datasetSelect: document.getElementById("datasetSelect"),
    columnSelect: document.getElementById("columnSelect"),
    frequencySelect: document.getElementById("frequencySelect"),
    windowRange: document.getElementById("windowRange"),
    windowValue: document.getElementById("windowValue"),

    // Tabs
    tabButtons: document.querySelectorAll(".tab-btn"),
    tabContents: document.querySelectorAll(".tab-content"),

    // Trend Tab
    trendStatsBadge: document.getElementById("trendStatsBadge"),
    trendRateText: document.getElementById("trendRateText"),
    trendR2Text: document.getElementById("trendR2Text"),
    trendPValText: document.getElementById("trendPValText"),
    trendSigText: document.getElementById("trendSigText"),
    trendDisclaimer: document.getElementById("trendDisclaimer"),
    trendLoader: document.getElementById("trendChartLoading"),

    // Seasonal Tab
    seasonalUnsupportedWarning: document.getElementById("seasonalUnsupportedWarning"),
    seasonalUnsupportedReason: document.getElementById("seasonalUnsupportedReason"),
    seasonsGrid: document.getElementById("seasonsGrid"),
    seasonalLoader: document.getElementById("seasonalChartLoading"),

    // Anomaly Tab
    anomalyMethodSelect: document.getElementById("anomalyMethodSelect"),
    anomalyThresholdInput: document.getElementById("anomalyThresholdInput"),
    applyAnomalyBtn: document.getElementById("applyAnomalyBtn"),
    anomalyTotalFlagged: document.getElementById("anomalyTotalFlagged"),
    anomalyPercentFlagged: document.getElementById("anomalyPercentFlagged"),
    anomalyFencesText: document.getElementById("anomalyFencesText"),
    anomalyTableBody: document.getElementById("anomalyTableBody"),
    anomalyLoader: document.getElementById("anomalyChartLoading"),

    // Quality Tab
    qualityScoreBig: document.getElementById("qualityScoreBig"),
    qualityRatingTitle: document.getElementById("qualityRatingTitle"),
    qualityBadgeHeader: document.getElementById("qualityBadgeHeader"),
    penMissing: document.getElementById("penMissing"),
    penDuplicates: document.getElementById("penDuplicates"),
    penInvalid: document.getElementById("penInvalid"),
    penFatal: document.getElementById("penFatal"),
    qualityMethodologyNote: document.getElementById("qualityMethodologyNote"),
    qualityMetricsBody: document.getElementById("qualityMetricsBody"),

    // Export & Preview Tab
    exportIncludeAnomalies: document.getElementById("exportIncludeAnomalies"),
    exportCsvBtn: document.getElementById("exportCsvBtn"),
    exportJsonBtn: document.getElementById("exportJsonBtn"),
    previewTableHead: document.getElementById("previewTableHead"),
    previewTableBody: document.getElementById("previewTableBody"),

    // Upload Modal
    openUploadModalBtn: document.getElementById("openUploadModalBtn"),
    uploadModal: document.getElementById("uploadModal"),
    closeUploadModalBtn: document.getElementById("closeUploadModalBtn"),
    cancelUploadBtn: document.getElementById("cancelUploadBtn"),
    uploadForm: document.getElementById("uploadForm"),
    fileDropzone: document.getElementById("fileDropzone"),
    csvFileInput: document.getElementById("csvFileInput"),
    selectedFileInfo: document.getElementById("selectedFileInfo"),
    selectedFileName: document.getElementById("selectedFileName"),
    selectedFileSize: document.getElementById("selectedFileSize"),
    submitUploadBtn: document.getElementById("submitUploadBtn"),
    uploadStatusMsg: document.getElementById("uploadStatusMsg"),
  };

  // Utilities
  function showAlert(msg, type = "info") {
    elements.alertMessage.textContent = msg;
    elements.alertBanner.className = `alert-banner alert-${type}`;
    elements.alertBanner.classList.remove("hidden");
  }

  function hideAlert() {
    elements.alertBanner.classList.add("hidden");
  }

  // Tab Navigation Handling
  elements.tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("aria-controls");

      elements.tabButtons.forEach(b => {
        b.classList.remove("active");
        b.setAttribute("aria-selected", "false");
      });
      elements.tabContents.forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      document.getElementById(targetId)?.classList.add("active");
    });
  });

  // Controls Event Listeners
  elements.alertCloseBtn.addEventListener("click", hideAlert);

  elements.datasetSelect.addEventListener("change", async (e) => {
    state.activeDatasetId = e.target.value;
    await loadActiveDatasetMetadata();
    await refreshAllAnalytics();
  });

  elements.columnSelect.addEventListener("change", async (e) => {
    state.activeColumn = e.target.value;
    await refreshAllAnalytics();
  });

  elements.frequencySelect.addEventListener("change", async (e) => {
    state.frequency = e.target.value;
    await loadTrends();
  });

  elements.windowRange.addEventListener("input", (e) => {
    state.window = parseInt(e.target.value, 10);
    elements.windowValue.textContent = `${state.window} periods`;
  });

  let windowDebounceTimer;
  elements.windowRange.addEventListener("change", () => {
    clearTimeout(windowDebounceTimer);
    windowDebounceTimer = setTimeout(() => {
      loadTrends();
    }, 200);
  });

  elements.applyAnomalyBtn.addEventListener("click", () => {
    state.anomalyMethod = elements.anomalyMethodSelect.value;
    state.anomalyThreshold = parseFloat(elements.anomalyThresholdInput.value) || 2.5;
    loadAnomalies();
  });

  // Export Listeners
  elements.exportCsvBtn.addEventListener("click", () => {
    const url = ClimateApiClient.getExportCsvUrl(
      state.activeDatasetId,
      state.activeColumn,
      elements.exportIncludeAnomalies.checked,
      state.anomalyMethod,
      state.anomalyThreshold
    );
    window.location.href = url;
  });

  elements.exportJsonBtn.addEventListener("click", () => {
    const url = ClimateApiClient.getExportSummaryUrl(state.activeDatasetId, state.activeColumn);
    window.location.href = url;
  });

  // Upload Modal Management
  elements.openUploadModalBtn.addEventListener("click", () => {
    elements.uploadStatusMsg.classList.add("hidden");
    elements.uploadForm.reset();
    elements.selectedFileInfo.classList.add("hidden");
    elements.submitUploadBtn.disabled = true;
    elements.uploadModal.classList.remove("hidden");
  });

  const closeUploadModal = () => elements.uploadModal.classList.add("hidden");
  elements.closeUploadModalBtn.addEventListener("click", closeUploadModal);
  elements.cancelUploadBtn.addEventListener("click", closeUploadModal);

  elements.csvFileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) {
      elements.selectedFileName.textContent = file.name;
      elements.selectedFileSize.textContent = `(${(file.size / 1024).toFixed(1)} KB)`;
      elements.selectedFileInfo.classList.remove("hidden");
      elements.submitUploadBtn.disabled = false;
    }
  });

  // Drag & drop
  ["dragenter", "dragover"].forEach(evt => {
    elements.fileDropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      elements.fileDropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(evt => {
    elements.fileDropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      elements.fileDropzone.classList.remove("dragover");
    });
  });

  elements.fileDropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer?.files[0];
    if (file && file.name.endsWith(".csv")) {
      elements.csvFileInput.files = e.dataTransfer.files;
      elements.selectedFileName.textContent = file.name;
      elements.selectedFileSize.textContent = `(${(file.size / 1024).toFixed(1)} KB)`;
      elements.selectedFileInfo.classList.remove("hidden");
      elements.submitUploadBtn.disabled = false;
    }
  });

  elements.uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = elements.csvFileInput.files[0];
    if (!file) return;

    elements.submitUploadBtn.disabled = true;
    elements.uploadStatusMsg.className = "upload-status-box alert-info";
    elements.uploadStatusMsg.textContent = "Validating schema and uploading...";
    elements.uploadStatusMsg.classList.remove("hidden");

    try {
      const result = await ClimateApiClient.uploadDataset(file);

      // Register new dataset in state
      const newId = result.dataset_id;
      const displayName = `${result.filename} (${result.quality_score.grade})`;
      state.datasets[newId] = { name: displayName };

      // Add to dropdown
      const opt = document.createElement("option");
      opt.value = newId;
      opt.textContent = displayName;
      elements.datasetSelect.appendChild(opt);
      elements.datasetSelect.value = newId;
      state.activeDatasetId = newId;

      closeUploadModal();
      showAlert(`Uploaded '${result.filename}' successfully! Quality score: ${result.quality_score.final_score}/100.`, "success");

      await loadActiveDatasetMetadata();
      await refreshAllAnalytics();
    } catch (err) {
      elements.uploadStatusMsg.className = "upload-status-box alert-error";
      elements.uploadStatusMsg.textContent = err.message;
      elements.submitUploadBtn.disabled = false;
    }
  });

  // Core Data Loaders
  async function loadActiveDatasetMetadata() {
    try {
      let meta;
      if (state.activeDatasetId === "sample") {
        const sampleData = await ClimateApiClient.getSampleDataset();
        meta = sampleData.metadata;
        renderPreviewTable(sampleData.data_preview);
      } else {
        // Query trends to infer columns and row count
        const trendSample = await ClimateApiClient.getTrends(state.activeDatasetId);
        meta = {
          name: state.datasets[state.activeDatasetId]?.name || state.activeDatasetId,
          total_rows: trendSample.total_observations,
          date_range_start: trendSample.time_period_start,
          date_range_end: trendSample.time_period_end,
          climate_columns: [trendSample.column_name],
        };
      }

      elements.activeDatasetBadge.textContent = meta.name;
      elements.kpiObservations.textContent = meta.total_rows.toLocaleString();
      elements.kpiDateSpan.textContent = `${meta.date_range_start ? meta.date_range_start.slice(0, 4) : "Start"} – ${meta.date_range_end ? meta.date_range_end.slice(0, 4) : "End"}`;

      // Populate Column Select
      elements.columnSelect.innerHTML = "";
      state.availableColumns = meta.climate_columns || ["temp_anomaly"];
      state.availableColumns.forEach(col => {
        const opt = document.createElement("option");
        opt.value = col;
        opt.textContent = formatColumnLabel(col);
        elements.columnSelect.appendChild(opt);
      });

      if (!state.activeColumn || !state.availableColumns.includes(state.activeColumn)) {
        state.activeColumn = state.availableColumns[0];
      }
      elements.columnSelect.value = state.activeColumn;
    } catch (err) {
      showAlert(`Failed to load dataset metadata: ${err.message}`, "error");
    }
  }

  function formatColumnLabel(col) {
    const map = {
      temp_anomaly: "Temperature Anomaly (°C)",
      temperature: "Observed Temperature (°C)",
      rainfall: "Precipitation / Rainfall (mm)",
      tmin: "Minimum Temperature (°C)",
      tmax: "Maximum Temperature (°C)",
    };
    return map[col] || col.replace(/_/g, " ").toUpperCase();
  }

  async function loadTrends() {
    elements.trendLoader.classList.remove("hidden");
    try {
      const data = await ClimateApiClient.getTrends(
        state.activeDatasetId,
        state.activeColumn,
        state.frequency,
        state.window
      );

      ClimateCharts.renderTrendChart("trendChart", data);

      if (data.linear_trend) {
        const slopeDecade = data.linear_trend.slope_per_decade;
        const sign = slopeDecade > 0 ? "+" : "";
        elements.kpiTrendSlope.textContent = `${sign}${slopeDecade} °C`;
        elements.kpiTrendSignificance.textContent = data.linear_trend.is_statistically_significant
          ? "Statistically Significant (p < 0.05)"
          : "Not Significant (p ≥ 0.05)";

        elements.trendRateText.textContent = `${sign}${slopeDecade} ${data.linear_trend.unit_description}`;
        elements.trendR2Text.textContent = `${(data.linear_trend.r_squared * 100).toFixed(1)}% (R²=${data.linear_trend.r_squared})`;
        elements.trendPValText.textContent = data.linear_trend.p_value !== null ? String(data.linear_trend.p_value) : "N/A";
        elements.trendSigText.textContent = data.linear_trend.is_statistically_significant ? "Yes (p < 0.05)" : "No";
      } else {
        elements.kpiTrendSlope.textContent = "N/A";
        elements.kpiTrendSignificance.textContent = "Insufficient points";
        elements.trendRateText.textContent = "Trend not estimable";
        elements.trendR2Text.textContent = "N/A";
        elements.trendPValText.textContent = "N/A";
        elements.trendSigText.textContent = "N/A";
      }

      elements.trendDisclaimer.textContent = data.scientific_disclaimer;
    } catch (err) {
      showAlert(`Error calculating trend: ${err.message}`, "error");
    } finally {
      elements.trendLoader.classList.add("hidden");
    }
  }

  async function loadSeasonal() {
    elements.seasonalLoader.classList.remove("hidden");
    try {
      const data = await ClimateApiClient.getSeasonal(state.activeDatasetId, state.activeColumn);

      if (!data.is_seasonal_supported) {
        elements.seasonalUnsupportedReason.textContent = data.reason_if_unsupported || "Seasonal analysis not supported for this dataset.";
        elements.seasonalUnsupportedWarning.classList.remove("hidden");
        elements.seasonsGrid.innerHTML = "";
      } else {
        elements.seasonalUnsupportedWarning.classList.add("hidden");
        ClimateCharts.renderSeasonalChart("seasonalChart", data);

        // Render Seasons Cards
        elements.seasonsGrid.innerHTML = "";
        data.seasonal_summaries.forEach(s => {
          const card = document.createElement("div");
          card.className = "season-card";
          card.innerHTML = `
            <div class="season-title">${s.season}</div>
            <div class="season-months">${s.months.join(", ")}</div>
            <div class="season-mean">${s.mean > 0 ? "+" : ""}${s.mean} °C</div>
            <div class="subtext text-muted">Min: ${s.min}°C | Max: ${s.max}°C</div>
          `;
          elements.seasonsGrid.appendChild(card);
        });
      }
    } catch (err) {
      showAlert(`Error loading seasonal climatology: ${err.message}`, "error");
    } finally {
      elements.seasonalLoader.classList.add("hidden");
    }
  }

  async function loadAnomalies() {
    elements.anomalyLoader.classList.remove("hidden");
    try {
      const data = await ClimateApiClient.getAnomalies(
        state.activeDatasetId,
        state.activeColumn,
        state.anomalyMethod,
        state.anomalyThreshold
      );

      ClimateCharts.renderAnomalyChart("anomalyChart", data);

      elements.kpiAnomaliesCount.textContent = data.anomaly_count;
      elements.kpiAnomaliesPct.textContent = `${data.anomaly_percentage}% of records`;

      elements.anomalyTotalFlagged.textContent = data.anomaly_count;
      elements.anomalyPercentFlagged.textContent = `${data.anomaly_percentage}%`;

      if (data.method === "z_score") {
        elements.anomalyFencesText.textContent = `Baseline Mean: ${data.baseline_mean} | Std Dev: ±${data.baseline_std} | Threshold: |z| > ${data.threshold_used}`;
      } else {
        elements.anomalyFencesText.textContent = `Q1: ${data.q1} | Q3: ${data.q3} | IQR: ${data.iqr} | Multiplier: ${data.threshold_used}x`;
      }

      // Populate Table with flagged anomalies (up to 50 most extreme)
      const flagged = data.anomalies.filter(a => a.is_anomaly).sort((a, b) => Math.abs(b.score) - Math.abs(a.score));
      elements.anomalyTableBody.innerHTML = "";

      if (flagged.length === 0) {
        elements.anomalyTableBody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No observations breached the ${data.method.toUpperCase()} statistical threshold.</td></tr>`;
      } else {
        flagged.slice(0, 50).forEach(anom => {
          const tr = document.createElement("tr");
          const isHigh = anom.original_value > (anom.upper_bound ?? 0);
          const boundText = isHigh ? `> Upper (${anom.upper_bound})` : `< Lower (${anom.lower_bound})`;
          tr.innerHTML = `
            <td><strong>${anom.date}</strong></td>
            <td>${anom.original_value > 0 ? "+" : ""}${anom.original_value}</td>
            <td><span class="badge badge-danger">${anom.score}</span></td>
            <td><span class="subtext">${boundText}</span></td>
            <td><span class="badge badge-warning">${isHigh ? "High Extreme" : "Low Extreme"}</span></td>
          `;
          elements.anomalyTableBody.appendChild(tr);
        });
      }
    } catch (err) {
      showAlert(`Error loading anomalies: ${err.message}`, "error");
    } finally {
      elements.anomalyLoader.classList.add("hidden");
    }
  }

  async function loadQuality() {
    try {
      const data = await ClimateApiClient.getQuality(state.activeDatasetId);
      const score = data.quality_score;

      elements.kpiQualityScore.textContent = `${score.final_score} / 100`;
      elements.kpiQualityGrade.textContent = `Rating: ${score.grade}`;

      elements.qualityScoreBig.textContent = score.final_score;
      elements.qualityRatingTitle.textContent = score.grade;
      elements.qualityBadgeHeader.textContent = `Score: ${score.final_score} / 100 (${score.grade})`;

      // Rating Coloration
      const gradeColor = score.final_score >= 90 ? "#10b981" : score.final_score >= 75 ? "#06b6d4" : score.final_score >= 50 ? "#f59e0b" : "#f43f5e";
      elements.qualityRatingTitle.style.color = gradeColor;

      elements.penMissing.textContent = `-${score.missing_data_penalty} pts (max 35)`;
      elements.penDuplicates.textContent = `-${score.duplicate_date_penalty} pts (max 25)`;
      elements.penInvalid.textContent = `-${score.invalid_value_penalty} pts (max 25)`;
      elements.penFatal.textContent = `-${score.empty_column_penalty} pts (max 15)`;
      elements.qualityMethodologyNote.textContent = score.methodology;

      // Render Metrics Table
      elements.qualityMetricsBody.innerHTML = "";
      data.column_metrics.forEach(col => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${col.name}</strong></td>
          <td><span class="badge badge-neutral">${col.inferred_type}</span></td>
          <td>${col.total_records.toLocaleString()}</td>
          <td>${col.missing_count}</td>
          <td>${col.missing_percentage}%</td>
          <td>${col.invalid_count}</td>
        `;
        elements.qualityMetricsBody.appendChild(tr);
      });
    } catch (err) {
      showAlert(`Error loading data quality: ${err.message}`, "error");
    }
  }

  function renderPreviewTable(records) {
    if (!records || !records.length) {
      elements.previewTableHead.innerHTML = "";
      elements.previewTableBody.innerHTML = `<tr><td class="text-center text-muted">No observations to preview.</td></tr>`;
      return;
    }

    const headers = Object.keys(records[0]);
    elements.previewTableHead.innerHTML = `<tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr>`;

    elements.previewTableBody.innerHTML = "";
    records.slice(0, 50).forEach(row => {
      const tr = document.createElement("tr");
      tr.innerHTML = headers.map(h => `<td>${row[h] !== null ? row[h] : '<span class="text-muted">null</span>'}</td>`).join("");
      elements.previewTableBody.appendChild(tr);
    });
  }

  async function refreshAllAnalytics() {
    await Promise.allSettled([
      loadTrends(),
      loadSeasonal(),
      loadAnomalies(),
      loadQuality(),
    ]);
  }

  // Initial Boot
  async function init() {
    await loadActiveDatasetMetadata();
    await refreshAllAnalytics();
  }

  init();
});

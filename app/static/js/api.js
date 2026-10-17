/**
 * Climate Trend Analyzer - API Client Layer
 * Handles all backend communication with configured baseURL and structured error handling.
 */

const API_BASE = ""; // Relative URL ensures automatic port & domain matching

class ClimateApiClient {
  /**
   * Safe fetch wrapper with JSON parsing and HTTP error normalization.
   */
  static async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    try {
      const response = await fetch(url, options);

      if (!response.ok) {
        let errorData = null;
        try {
          errorData = await response.json();
        } catch (_) {
          errorData = { detail: await response.text() };
        }

        let message = `HTTP ${response.status}: Request failed`;
        if (errorData && errorData.detail) {
          if (typeof errorData.detail === "string") {
            message = errorData.detail;
          } else if (Array.isArray(errorData.detail)) {
            message = errorData.detail.map(d => d.msg || JSON.stringify(d)).join(", ");
          } else if (errorData.detail.message) {
            message = errorData.detail.message;
            if (errorData.detail.fatal_errors) {
              message += " (" + errorData.detail.fatal_errors.join("; ") + ")";
            }
          }
        }
        throw new Error(message);
      }

      return await response.json();
    } catch (err) {
      console.error(`API Error on [${endpoint}]:`, err);
      throw err;
    }
  }

  // Datasets Endpoints
  static async getSampleDataset() {
    return this.request("/api/datasets/sample");
  }

  static async getSampleQuality() {
    return this.request("/api/datasets/sample/quality");
  }

  static async uploadDataset(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE}/api/datasets/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let errBody;
      try {
        errBody = await response.json();
      } catch (_) {
        errBody = { detail: await response.text() };
      }
      let msg = "Upload failed";
      if (errBody && errBody.detail) {
        msg = typeof errBody.detail === "string" ? errBody.detail : errBody.detail.message || JSON.stringify(errBody.detail);
      }
      throw new Error(msg);
    }

    return await response.json();
  }

  // Analysis Endpoints
  static async getTrends(datasetId = "sample", column = null, frequency = "annual", window = 5) {
    const params = new URLSearchParams({
      dataset_id: datasetId,
      frequency: frequency,
      window: String(window),
    });
    if (column) params.append("column", column);
    return this.request(`/api/analysis/trends?${params.toString()}`);
  }

  static async getSeasonal(datasetId = "sample", column = null) {
    const params = new URLSearchParams({ dataset_id: datasetId });
    if (column) params.append("column", column);
    return this.request(`/api/analysis/seasonal?${params.toString()}`);
  }

  static async getAnomalies(datasetId = "sample", column = null, method = "z_score", threshold = 2.5) {
    const params = new URLSearchParams({
      dataset_id: datasetId,
      method: method,
      threshold: String(threshold),
    });
    if (column) params.append("column", column);
    return this.request(`/api/analysis/anomalies?${params.toString()}`);
  }

  static async getQuality(datasetId = "sample") {
    return this.request(`/api/analysis/quality?dataset_id=${encodeURIComponent(datasetId)}`);
  }

  // Export URLs
  static getExportCsvUrl(datasetId = "sample", column = null, includeAnomalies = false, method = "z_score", threshold = 2.5) {
    const params = new URLSearchParams({
      dataset_id: datasetId,
      include_anomalies: String(includeAnomalies),
      method: method,
      threshold: String(threshold),
    });
    if (column) params.append("column", column);
    return `${API_BASE}/api/export/csv?${params.toString()}`;
  }

  static getExportSummaryUrl(datasetId = "sample", column = null) {
    const params = new URLSearchParams({ dataset_id: datasetId });
    if (column) params.append("column", column);
    return `${API_BASE}/api/export/summary?${params.toString()}`;
  }
}

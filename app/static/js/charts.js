/**
 * Climate Trend Analyzer - Chart Rendering Manager
 * Manages Chart.js instances with accessible color palettes and tooltips.
 */

class ClimateCharts {
  static trendChartInstance = null;
  static seasonalChartInstance = null;
  static anomalyChartInstance = null;

  /**
   * Common Chart.js styling options for dark theme
   */
  static getBaseOptions(titleText = "", yAxisTitle = "") {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 600 },
      plugins: {
        legend: {
          position: "top",
          labels: {
            color: "#94a3b8",
            font: { family: "system-ui, sans-serif", size: 12, weight: 600 },
            usePointStyle: true,
            boxWidth: 8,
          },
        },
        tooltip: {
          backgroundColor: "rgba(13, 19, 34, 0.95)",
          titleColor: "#ffffff",
          bodyColor: "#e2e8f0",
          borderColor: "rgba(255, 255, 255, 0.1)",
          borderWidth: 1,
          padding: 10,
          boxPadding: 4,
          usePointStyle: true,
        },
      },
      scales: {
        x: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#64748b", maxRotation: 45, autoSkip: true, maxTicksLimit: 15 },
        },
        y: {
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: { color: "#64748b" },
          title: { display: !!yAxisTitle, text: yAxisTitle, color: "#94a3b8" },
        },
      },
    };
  }

  /**
   * Render or update the Trend & Moving Average Chart
   */
  static renderTrendChart(canvasId, trendData) {
    const ctx = document.getElementById(canvasId)?.getContext("2d");
    if (!ctx) return;

    if (this.trendChartInstance) {
      this.trendChartInstance.destroy();
    }

    const labels = trendData.data_points.map(p => p.period);
    const observedValues = trendData.data_points.map(p => p.mean);
    const rollingValues = trendData.data_points.map(p => p.rolling_avg);

    // Compute linear regression fit line points if available
    const datasets = [
      {
        label: "Observed Mean",
        data: observedValues,
        borderColor: "rgba(148, 163, 184, 0.5)",
        backgroundColor: "rgba(148, 163, 184, 0.15)",
        borderWidth: 1.5,
        pointRadius: labels.length > 100 ? 1 : 3,
        pointHoverRadius: 5,
        tension: 0.1,
        order: 3,
      },
      {
        label: `${trendData.rolling_window}-Period Rolling Avg`,
        data: rollingValues,
        borderColor: "#06b6d4",
        backgroundColor: "transparent",
        borderWidth: 2.5,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
        order: 2,
      },
    ];

    if (trendData.linear_trend && trendData.data_points.length >= 2) {
      const slopePerYear = trendData.linear_trend.slope_per_year;
      const intercept = trendData.linear_trend.intercept;
      const n = trendData.data_points.length;
      const trendLineData = [];

      for (let i = 0; i < n; i++) {
        // Years elapsed from index 0
        const yVal = intercept + (slopePerYear * i);
        trendLineData.push(Math.round(yVal * 1000) / 1000);
      }

      datasets.push({
        label: `Linear Trend (${trendData.linear_trend.slope_per_decade > 0 ? "+" : ""}${trendData.linear_trend.slope_per_decade} °C/decade)`,
        data: trendLineData,
        borderColor: "#f59e0b",
        borderDash: [6, 4],
        backgroundColor: "transparent",
        borderWidth: 2,
        pointRadius: 0,
        order: 1,
      });
    }

    const options = this.getBaseOptions("Climate Trends", trendData.linear_trend?.unit_description || "Value");

    this.trendChartInstance = new Chart(ctx, {
      type: "line",
      data: { labels, datasets },
      options: options,
    });
  }

  /**
   * Render or update the Monthly Climatology Chart
   */
  static renderSeasonalChart(canvasId, seasonalData) {
    const ctx = document.getElementById(canvasId)?.getContext("2d");
    if (!ctx) return;

    if (this.seasonalChartInstance) {
      this.seasonalChartInstance.destroy();
    }

    if (!seasonalData.is_seasonal_supported || !seasonalData.monthly_patterns.length) {
      return;
    }

    const labels = seasonalData.monthly_patterns.map(p => p.month_name.slice(0, 3));
    const means = seasonalData.monthly_patterns.map(p => p.mean);
    const mins = seasonalData.monthly_patterns.map(p => p.min);
    const maxs = seasonalData.monthly_patterns.map(p => p.max);

    // Seasonal color palette: Winter (cyan), Spring (emerald), Summer (amber), Autumn (orange)
    const backgroundColors = [
      "#38bdf8", "#38bdf8", // Jan, Feb (Winter)
      "#34d399", "#34d399", "#34d399", // Mar, Apr, May (Spring)
      "#f59e0b", "#f59e0b", "#f59e0b", // Jun, Jul, Aug (Summer)
      "#fb923c", "#fb923c", "#fb923c", // Sep, Oct, Nov (Autumn)
      "#38bdf8" // Dec (Winter)
    ];

    const options = this.getBaseOptions("Climatology by Month", "Historical Mean (°C)");
    options.plugins.tooltip.callbacks = {
      afterLabel: function(context) {
        const idx = context.dataIndex;
        return `Range: [${mins[idx]}°C to ${maxs[idx]}°C]\nStd Dev: ±${seasonalData.monthly_patterns[idx].std || 0}°C`;
      }
    };

    this.seasonalChartInstance = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Historical Monthly Climatology Mean",
          data: means,
          backgroundColor: backgroundColors,
          borderRadius: 4,
          borderWidth: 0,
        }],
      },
      options: options,
    });
  }

  /**
   * Render or update the Anomaly Detection Chart
   */
  static renderAnomalyChart(canvasId, anomalyData) {
    const ctx = document.getElementById(canvasId)?.getContext("2d");
    if (!ctx) return;

    if (this.anomalyChartInstance) {
      this.anomalyChartInstance.destroy();
    }

    const labels = anomalyData.anomalies.map(p => p.date);
    const allValues = anomalyData.anomalies.map(p => p.original_value);

    // Isolate anomalous points
    const anomalyPoints = anomalyData.anomalies.map(p => p.is_anomaly ? p.original_value : null);

    const datasets = [
      {
        type: "line",
        label: "Observed Climate Time Series",
        data: allValues,
        borderColor: "rgba(148, 163, 184, 0.4)",
        backgroundColor: "transparent",
        borderWidth: 1.2,
        pointRadius: 0,
        pointHoverRadius: 3,
        tension: 0.1,
        order: 3,
      },
      {
        type: "scatter",
        label: `Flagged Anomalies (${anomalyData.method.toUpperCase()} k=${anomalyData.threshold_used})`,
        data: anomalyPoints,
        borderColor: "#f43f5e",
        backgroundColor: "#f43f5e",
        pointRadius: 5,
        pointHoverRadius: 8,
        pointStyle: "circle",
        order: 1,
      },
    ];

    // Add statistical fences if bounds are available
    if (anomalyData.anomalies.length > 0 && anomalyData.anomalies[0].upper_bound !== null) {
      const up = anomalyData.anomalies[0].upper_bound;
      const low = anomalyData.anomalies[0].lower_bound;

      datasets.push({
        type: "line",
        label: "Upper Statistical Fence",
        data: Array(labels.length).fill(up),
        borderColor: "rgba(244, 63, 94, 0.4)",
        borderDash: [5, 5],
        borderWidth: 1.5,
        pointRadius: 0,
        order: 2,
      });

      datasets.push({
        type: "line",
        label: "Lower Statistical Fence",
        data: Array(labels.length).fill(low),
        borderColor: "rgba(6, 182, 212, 0.4)",
        borderDash: [5, 5],
        borderWidth: 1.5,
        pointRadius: 0,
        order: 2,
      });
    }

    const options = this.getBaseOptions("Anomaly Detection", "Value");
    options.plugins.tooltip.callbacks = {
      afterLabel: function(context) {
        const item = anomalyData.anomalies[context.dataIndex];
        if (item && item.is_anomaly) {
          return `⚠️ Flagged Anomaly!\nScore: ${item.score}\nMethod: ${item.method.toUpperCase()}`;
        }
        return "";
      }
    };

    this.anomalyChartInstance = new Chart(ctx, {
      data: { labels, datasets },
      options: options,
    });
  }
}

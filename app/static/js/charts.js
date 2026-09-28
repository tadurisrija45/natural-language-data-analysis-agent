/**
 * Chart rendering helper using Chart.js
 */
const ChartManager = {
  instances: {},

  renderChart(canvasId, chartConfig) {
    if (!chartConfig || !chartConfig.data) return null;
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    // Destroy existing instance on canvas if any
    if (this.instances[canvasId]) {
      this.instances[canvasId].destroy();
    }

    const ctx = canvas.getContext("2d");
    try {
      const chartInstance = new Chart(ctx, {
        type: chartConfig.type || "bar",
        data: chartConfig.data,
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: chartConfig.options?.indexAxis || "x",
          plugins: {
            legend: {
              display: ["pie", "doughnut"].includes(chartConfig.type),
              position: "bottom"
            },
            tooltip: {
              backgroundColor: "#0F172A",
              titleFont: { size: 13, weight: "bold" },
              bodyFont: { size: 12 },
              padding: 10,
              cornerRadius: 6
            }
          },
          scales: ["pie", "doughnut"].includes(chartConfig.type) ? {} : {
            x: {
              grid: { color: "#F1F5F9" },
              ticks: { color: "#64748B", font: { size: 11 } }
            },
            y: {
              grid: { color: "#F1F5F9" },
              ticks: { color: "#64748B", font: { size: 11 } }
            }
          }
        }
      });
      this.instances[canvasId] = chartInstance;
      return chartInstance;
    } catch (e) {
      console.error("Error creating chart:", e);
      return null;
    }
  }
};

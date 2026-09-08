const FOT_COLORS = {
  orange: "#f97316",
  orangeSoft: "rgba(249, 115, 22, 0.15)",
  zomato: "#e23744",
  swiggy: "#fc8019",
  slate: "#64748b",
  palette: ["#f97316", "#0ea5e9", "#8b5cf6", "#22c55e", "#ef4444", "#eab308", "#14b8a6", "#ec4899"],
};

// Chart.js paints to a <canvas>, so it doesn't pick up CSS/`dark:` changes on
// its own -- charts created here register themselves in FOT_CHARTS, and
// window.applyChartTheme() (called by theme.js on every toggle) restyles and
// redraws each one in place.
window.FOT_CHARTS = window.FOT_CHARTS || [];

function fotIsDark() {
  return document.documentElement.classList.contains("dark");
}

function fotThemeColors() {
  return fotIsDark()
    ? { text: "#94a3b8", grid: "#1e293b", cardBorder: "#1e293b", emptyText: "#64748b" }
    : { text: "#64748b", grid: "#f1f5f9", cardBorder: "#ffffff", emptyText: "#94a3b8" };
}

Chart.defaults.font.family = "ui-sans-serif, system-ui, -apple-system, sans-serif";
Chart.defaults.color = fotThemeColors().text;
Chart.defaults.plugins.legend.labels.usePointStyle = true;

function fotFormatCurrency(value, symbol) {
  symbol = symbol || "₹";
  return symbol + Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function fotEmptyCanvasMessage(ctx, message) {
  const canvas = ctx.canvas;
  ctx.save();
  ctx.textAlign = "center";
  ctx.fillStyle = fotThemeColors().emptyText;
  ctx.font = "13px ui-sans-serif, system-ui, sans-serif";
  ctx.fillText(message || "Not enough data yet", canvas.width / 2, canvas.height / 2);
  ctx.restore();
}

function fotRegisterChart(chart) {
  if (chart) window.FOT_CHARTS.push(chart);
  return chart;
}

window.applyChartTheme = function () {
  const colors = fotThemeColors();
  Chart.defaults.color = colors.text;
  window.FOT_CHARTS = window.FOT_CHARTS.filter((chart) => chart && !chart._fotDestroyed);
  window.FOT_CHARTS.forEach((chart) => {
    const opts = chart.options || {};
    if (opts.scales) {
      Object.values(opts.scales).forEach((scale) => {
        if (scale.grid) scale.grid.color = colors.grid;
        if (scale.ticks) scale.ticks.color = colors.text;
      });
    }
    if (opts.plugins && opts.plugins.legend && opts.plugins.legend.labels) {
      opts.plugins.legend.labels.color = colors.text;
    }
    if (chart.config.type === "doughnut" && chart.data.datasets[0]) {
      chart.data.datasets[0].borderColor = colors.cardBorder;
    }
    chart.update("none");
  });
};

// Wraps chart.destroy() so applyChartTheme() can skip charts a page has
// since torn down (e.g. the dashboard's period selector re-rendering the
// monthly chart) instead of erroring on a stale reference.
function fotDestroyChart(chart) {
  if (!chart) return;
  chart._fotDestroyed = true;
  chart.destroy();
}

function renderLineChart(canvasId, labels, data, { currency = "₹", label = "Spending" } = {}) {
  const el = document.getElementById(canvasId);
  if (!el) return null;
  const ctx = el.getContext("2d");
  if (!labels.length) {
    fotEmptyCanvasMessage(ctx, "No spending data yet");
    return null;
  }
  const colors = fotThemeColors();
  const gradient = ctx.createLinearGradient(0, 0, 0, el.height || 220);
  gradient.addColorStop(0, "rgba(249, 115, 22, 0.25)");
  gradient.addColorStop(1, "rgba(249, 115, 22, 0.02)");

  return fotRegisterChart(
    new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label,
            data,
            borderColor: FOT_COLORS.orange,
            backgroundColor: gradient,
            fill: true,
            tension: 0.35,
            pointRadius: 3,
            pointBackgroundColor: FOT_COLORS.orange,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) => fotFormatCurrency(item.raw, currency),
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { color: colors.text, callback: (v) => fotFormatCurrency(v, currency) },
            grid: { color: colors.grid },
          },
          x: { ticks: { color: colors.text }, grid: { display: false } },
        },
      },
    })
  );
}

function renderDoughnutChart(canvasId, labels, data, colors) {
  const el = document.getElementById(canvasId);
  if (!el) return null;
  const ctx = el.getContext("2d");
  if (!data.some((v) => v > 0)) {
    fotEmptyCanvasMessage(ctx, "Not enough data yet");
    return null;
  }
  const theme = fotThemeColors();
  return fotRegisterChart(
    new Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{ data, backgroundColor: colors || FOT_COLORS.palette, borderWidth: 2, borderColor: theme.cardBorder }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: { legend: { position: "bottom", labels: { color: theme.text } } },
      },
    })
  );
}

function renderHorizontalBarChart(canvasId, labels, data, { currency = "₹" } = {}) {
  const el = document.getElementById(canvasId);
  if (!el) return null;
  const ctx = el.getContext("2d");
  if (!labels.length) {
    fotEmptyCanvasMessage(ctx, "Not enough data yet");
    return null;
  }
  const colors = fotThemeColors();
  return fotRegisterChart(
    new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{ data, backgroundColor: FOT_COLORS.orange, borderRadius: 6, maxBarThickness: 20 }],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: (item) => fotFormatCurrency(item.raw, currency) } },
        },
        scales: {
          x: { beginAtZero: true, ticks: { color: colors.text }, grid: { color: colors.grid } },
          y: { ticks: { color: colors.text }, grid: { display: false } },
        },
      },
    })
  );
}

function renderBarChart(canvasId, labels, data, { color = FOT_COLORS.orange } = {}) {
  const el = document.getElementById(canvasId);
  if (!el) return null;
  const ctx = el.getContext("2d");
  if (!labels.length || !data.some((v) => v > 0)) {
    fotEmptyCanvasMessage(ctx, "Not enough data yet");
    return null;
  }
  const colors = fotThemeColors();
  return fotRegisterChart(
    new Chart(ctx, {
      type: "bar",
      data: { labels, datasets: [{ data, backgroundColor: color, borderRadius: 6, maxBarThickness: 36 }] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { color: colors.text }, grid: { color: colors.grid } },
          x: { ticks: { color: colors.text }, grid: { display: false } },
        },
      },
    })
  );
}

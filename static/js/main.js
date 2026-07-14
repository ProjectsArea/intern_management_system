document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  const toggle = document.getElementById("sidebarToggle");

  function closeSidebar() {
    sidebar?.classList.remove("show");
    overlay?.classList.remove("show");
  }

  function openSidebar() {
    sidebar?.classList.add("show");
    overlay?.classList.add("show");
  }

  toggle?.addEventListener("click", () => {
    if (sidebar?.classList.contains("show")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  overlay?.addEventListener("click", closeSidebar);

  document.querySelectorAll("[data-confirm]").forEach((el) => {
    el.addEventListener("click", (event) => {
      const message = el.getAttribute("data-confirm") || "Are you sure?";
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });
});

function createChart(canvasId, type, labels, data, colors) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof Chart === "undefined") {
    return;
  }
  const ctx = canvas.getContext("2d");
  const defaultColors = [
    "#1e5aaf",
    "#3b82f6",
    "#60a5fa",
    "#93c5fd",
    "#64748b",
    "#0ea5e9",
    "#2563eb",
  ];
  new Chart(ctx, {
    type,
    data: {
      labels,
      datasets: [
        {
          label: canvas.dataset.label || "Data",
          data,
          backgroundColor: colors || defaultColors,
          borderColor: type === "line" ? "#1e5aaf" : colors || defaultColors,
          borderWidth: type === "line" ? 2 : 1,
          fill: type === "line" ? false : true,
          tension: 0.35,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: type !== "bar" && type !== "line",
          position: "bottom",
        },
      },
      scales:
        type === "bar" || type === "line"
          ? {
              y: {
                beginAtZero: true,
                ticks: { precision: 0 },
              },
            }
          : {},
    },
  });
}

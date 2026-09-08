document.addEventListener("submit", (e) => {
  const form = e.target;
  if (form.matches("[data-confirm]")) {
    const message = form.getAttribute("data-confirm") || "Are you sure?";
    if (!window.confirm(message)) {
      e.preventDefault();
    }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-clear-filters]").forEach((btn) => {
    btn.addEventListener("click", () => {
      window.location.href = btn.getAttribute("data-clear-filters");
    });
  });
});

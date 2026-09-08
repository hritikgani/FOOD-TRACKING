(function () {
  function getStoredTheme() {
    try {
      return localStorage.getItem("theme");
    } catch (e) {
      return null;
    }
  }

  function setStoredTheme(theme) {
    try {
      localStorage.setItem("theme", theme);
    } catch (e) {
      /* private browsing / storage blocked -- theme still applies for this load */
    }
  }

  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function resolveIsDark(theme) {
    return theme === "dark" || (theme === "system" && systemPrefersDark());
  }

  function currentTheme() {
    return getStoredTheme() || document.documentElement.getAttribute("data-theme") || "system";
  }

  function applyTheme(theme) {
    document.documentElement.classList.toggle("dark", resolveIsDark(theme));
    document.documentElement.setAttribute("data-theme", theme);
    if (window.applyChartTheme) window.applyChartTheme();
  }

  function persistToServer(theme) {
    fetch("/settings/theme", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: "theme=" + encodeURIComponent(theme),
    }).catch(function () {
      /* best-effort -- localStorage already has it for this browser */
    });
  }

  function setTheme(theme) {
    setStoredTheme(theme);
    applyTheme(theme);
    persistToServer(theme);
  }

  function toggleTheme() {
    var isDark = resolveIsDark(currentTheme());
    setTheme(isDark ? "light" : "dark");
  }

  window.FOT_THEME = { setTheme: setTheme, toggleTheme: toggleTheme, currentTheme: currentTheme };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", toggleTheme);
    });

    // The Settings page's System/Light/Dark dropdown -- apply live so the
    // choice previews immediately instead of waiting for the form's POST
    // + redirect round trip.
    document.querySelectorAll("[data-theme-select]").forEach(function (select) {
      select.value = currentTheme();
      select.addEventListener("change", function () {
        setTheme(select.value);
      });
    });

    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", function () {
        if (currentTheme() === "system") applyTheme("system");
      });
    }
  });
})();

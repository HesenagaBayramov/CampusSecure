"use strict";

document.addEventListener("DOMContentLoaded", () => {
  // Bootstrap styling is paired with browser validation so forms remain usable without JavaScript.
  document.querySelectorAll(".needs-validation").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    });
  });

  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.passwordToggle);
      if (!input) return;
      const showing = input.type === "password";
      input.type = showing ? "text" : "password";
      button.setAttribute("aria-pressed", String(showing));
      button.setAttribute("aria-label", showing ? "Hide password" : "Show password");
      const symbol = button.querySelector("use");
      if (symbol) symbol.setAttribute("href", symbol.getAttribute("href").replace(/#eye(?:-off)?$/, showing ? "#eye-off" : "#eye"));
    });
  });

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const search = document.getElementById("requestSearch");
  const status = document.getElementById("statusFilter");
  if (search && status) {
    const rows = [...document.querySelectorAll("[data-request-row]")];
    const empty = document.getElementById("requestEmpty");
    const filter = () => {
      const term = search.value.trim().toLocaleLowerCase();
      let visible = 0;
      rows.forEach((row) => {
        const matches = row.dataset.search.includes(term) && (status.value === "all" || row.dataset.status === status.value);
        row.hidden = !matches;
        if (matches) visible += 1;
      });
      if (empty) empty.hidden = visible !== 0;
    };
    search.addEventListener("input", filter);
    status.addEventListener("change", filter);
  }
});

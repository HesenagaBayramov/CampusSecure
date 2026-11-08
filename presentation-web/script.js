"use strict";

(() => {
  const stage = document.getElementById("stage");
  const slides = [...document.querySelectorAll(".slide[data-slide]")];
  const previousButton = document.getElementById("previous-button");
  const nextButton = document.getElementById("next-button");
  const fullScreenButton = document.getElementById("fullscreen-button");
  const slideCount = document.getElementById("slide-count");
  const progress = document.getElementById("progress");
  const progressFill = document.getElementById("progress-fill");
  const footerSection = document.getElementById("footer-section");
  const overviewButtons = [...document.querySelectorAll("[data-go-to]")];
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  if (!stage || slides.length !== 7) return;

  let current = 0;
  let transitioning = false;
  let queuedIndex = null;
  let transitionTimer = null;
  let statsFrame = null;

  slides.forEach((slide, index) => {
    slide.tabIndex = -1;
    slide.setAttribute("aria-hidden", String(index !== 0));
    slide.inert = index !== 0;
  });
  document.body.classList.add("js-ready");

  function updateControls() {
    slideCount.innerHTML = `${String(current + 1).padStart(2, "0")} <span>/ 07</span>`;
    footerSection.textContent = slides[current].dataset.title.toUpperCase();
    progress.setAttribute("aria-valuenow", String(current + 1));
    progressFill.style.width = `${((current + 1) / slides.length) * 100}%`;
    previousButton.disabled = current === 0;
    nextButton.disabled = current === slides.length - 1;
    overviewButtons.forEach((button, index) => {
      if (index === current) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
    });
  }

  function animateResults() {
    if (statsFrame) cancelAnimationFrame(statsFrame);
    const counters = [...slides[6].querySelectorAll("[data-count]")];
    if (reducedMotion.matches) {
      counters.forEach((counter) => { counter.textContent = counter.dataset.count; });
      return;
    }
    const started = performance.now();
    const duration = 1050;
    const tick = (now) => {
      if (current !== 6) return;
      const portion = Math.min(1, (now - started) / duration);
      const eased = 1 - Math.pow(1 - portion, 3);
      counters.forEach((counter) => {
        const target = Number(counter.dataset.count);
        counter.textContent = String(Math.round(target * eased));
      });
      if (portion < 1) statsFrame = requestAnimationFrame(tick);
    };
    statsFrame = requestAnimationFrame(tick);
  }

  function goTo(requestedIndex, restoreFocus = false) {
    const target = Math.max(0, Math.min(slides.length - 1, requestedIndex));
    if (target === current && !transitioning) return;
    if (transitioning) {
      queuedIndex = target;
      return;
    }

    const previousIndex = current;
    const outgoing = slides[previousIndex];
    const incoming = slides[target];
    const direction = target > previousIndex ? "right" : "left";
    transitioning = true;
    current = target;

    incoming.classList.add(direction === "right" ? "enter-from-right" : "enter-from-left");
    incoming.classList.add("is-active");
    incoming.inert = false;
    incoming.setAttribute("aria-hidden", "false");
    outgoing.classList.add("is-exiting", direction === "right" ? "exit-left" : "exit-right");
    outgoing.classList.remove("is-active");
    outgoing.inert = true;
    outgoing.setAttribute("aria-hidden", "true");
    updateControls();
    if (target === 6) animateResults();

    const finish = () => {
      clearTimeout(transitionTimer);
      outgoing.classList.remove("is-exiting", "exit-left", "exit-right");
      incoming.classList.remove("enter-from-left", "enter-from-right");
      transitioning = false;
      if (restoreFocus && queuedIndex === null) incoming.focus({ preventScroll: true });
      const nextQueued = queuedIndex;
      queuedIndex = null;
      if (nextQueued !== null && nextQueued !== current) goTo(nextQueued, restoreFocus);
    };

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        incoming.classList.remove("enter-from-left", "enter-from-right");
        transitionTimer = setTimeout(finish, reducedMotion.matches ? 20 : 700);
      });
    });
  }

  function step(delta, restoreFocus = false) {
    goTo((queuedIndex ?? current) + delta, restoreFocus);
  }

  previousButton.addEventListener("click", () => step(-1));
  nextButton.addEventListener("click", () => step(1));
  overviewButtons.forEach((button) => {
    button.addEventListener("click", () => goTo(Number(button.dataset.goTo)));
  });

  function toggleFullScreen() {
    if (document.fullscreenElement) document.exitFullscreen();
    else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen();
  }

  fullScreenButton.addEventListener("click", toggleFullScreen);
  document.addEventListener("fullscreenchange", () => {
    const active = Boolean(document.fullscreenElement);
    fullScreenButton.setAttribute("aria-label", active ? "Exit full screen" : "Enter full screen");
    fullScreenButton.title = active ? "Exit full screen (F)" : "Toggle full screen (F)";
    fullScreenButton.querySelector("use").setAttribute("href", active ? "#i-compress" : "#i-expand");
  });

  document.addEventListener("keydown", (event) => {
    const focusedControl = event.target instanceof Element
      ? event.target.closest("button, input, textarea, select, [contenteditable='true']")
      : null;
    if (event.key === "f" || event.key === "F") {
      if (!focusedControl) {
        event.preventDefault();
        toggleFullScreen();
      }
      return;
    }
    if (event.key === "Home") {
      event.preventDefault();
      goTo(0, true);
    } else if (event.key === "End") {
      event.preventDefault();
      goTo(slides.length - 1, true);
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      step(1, true);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      step(-1, true);
    } else if ((event.key === " " || event.code === "Space") && !focusedControl) {
      event.preventDefault();
      step(1, true);
    }
  });

  let touchStart = null;
  stage.addEventListener("touchstart", (event) => {
    if (event.touches.length !== 1 || event.target.closest("button, input")) return;
    touchStart = { x: event.touches[0].clientX, y: event.touches[0].clientY };
  }, { passive: true });
  stage.addEventListener("touchend", (event) => {
    if (!touchStart || event.changedTouches.length !== 1) return;
    const deltaX = event.changedTouches[0].clientX - touchStart.x;
    const deltaY = event.changedTouches[0].clientY - touchStart.y;
    touchStart = null;
    if (Math.abs(deltaX) > 58 && Math.abs(deltaX) > Math.abs(deltaY) * 1.35) {
      step(deltaX < 0 ? 1 : -1);
    }
  }, { passive: true });
  stage.addEventListener("touchcancel", () => { touchStart = null; }, { passive: true });

  const scenarioDetails = [
    {
      kicker: "SELECTED / 01 · OBJECT AUTHORIZATION",
      text: "Secure Mode compares Alice's user ID with request 201's student_id. Bob's fictional record is denied with HTTP 403.",
      status: "VULNERABLE 200  ·  SECURE 403",
    },
    {
      kicker: "SELECTED / 02 · FUNCTION AUTHORIZATION",
      text: "Secure Mode requires the administrator role before an announcement is inserted. Alice receives HTTP 403 and no row is saved.",
      status: "VULNERABLE 201  ·  SECURE 403",
    },
    {
      kicker: "SELECTED / 03 · PROFILE FIELD AUTHORIZATION",
      text: "Secure Mode accepts only ordinary profile fields. Alice's role=admin submission is rejected before any database write.",
      status: "VULNERABLE 200  ·  SECURE 403",
    },
  ];

  document.querySelectorAll("[data-scenario]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.scenario);
      const detail = scenarioDetails[index];
      if (!detail) return;
      document.querySelectorAll("[data-scenario]").forEach((card) => {
        const selected = card === button;
        card.classList.toggle("is-selected", selected);
        card.setAttribute("aria-pressed", String(selected));
      });
      document.getElementById("scenario-detail-kicker").textContent = detail.kicker;
      document.getElementById("scenario-detail-text").textContent = detail.text;
      document.getElementById("scenario-detail-status").textContent = detail.status;
    });
  });

  const policyStates = {
    secure: {
      gates: ["Owner checked", "Admin required", "Role rejected"],
      codes: ["403", "403", "403"],
      labels: ["FORBIDDEN", "FORBIDDEN", "FORBIDDEN"],
      explanation: "Secure Mode: server-loaded identity, role, and an explicit profile field allowlist determine the outcome before data is returned or changed.",
    },
    vulnerable: {
      gates: ["Owner skipped", "Role skipped", "Role accepted"],
      codes: ["200", "201", "200"],
      labels: ["RECORD READ", "ROW CREATED", "ROLE SAVED"],
      explanation: "Vulnerable Mode: these three specific API checks are intentionally relaxed for the isolated synthetic laboratory. Authentication and CSRF still apply.",
    },
  };

  function setIllustrativeMode(mode) {
    const state = policyStates[mode];
    if (!state) return;
    stage.dataset.illustrativeMode = mode;
    document.querySelectorAll("[data-mode]").forEach((button) => {
      const selected = button.dataset.mode === mode;
      button.classList.toggle("is-active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    document.querySelectorAll("[data-policy]").forEach((row, index) => {
      row.querySelector(".policy-gate span").textContent = state.gates[index];
      const result = row.querySelector(".policy-result");
      result.classList.add("is-changing");
      result.classList.toggle("secure-result", mode === "secure");
      result.classList.toggle("vulnerable-result", mode === "vulnerable");
      result.innerHTML = `${state.codes[index]} <small>${state.labels[index]}</small>`;
      requestAnimationFrame(() => result.classList.remove("is-changing"));
    });
    document.getElementById("mode-explanation").textContent = state.explanation;
  }

  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.addEventListener("click", () => setIllustrativeMode(button.dataset.mode));
  });
  stage.dataset.illustrativeMode = "secure";

  const captureUrls = new Map();
  function showCapture(slot, source, status) {
    const image = slot.querySelector(".capture-image");
    image.onload = () => {
      slot.classList.add("has-capture");
      slot.querySelector(".slot-state").textContent = status;
      slot.querySelector(".remove-capture").hidden = false;
    };
    image.onerror = () => {
      slot.classList.remove("has-capture");
      slot.querySelector(".slot-state").textContent = "IMAGE COULD NOT BE LOADED";
    };
    image.src = source;
  }

  document.querySelectorAll("[data-slot]").forEach((slot) => {
    const key = slot.dataset.slot;
    const input = slot.querySelector(".capture-input");
    const image = slot.querySelector(".capture-image");
    slot.querySelector(".capture-button").addEventListener("click", () => input.click());
    input.addEventListener("change", () => {
      const file = input.files && input.files[0];
      if (!file) return;
      if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
        slot.querySelector(".slot-state").textContent = "CHOOSE PNG, JPG OR WEBP";
        input.value = "";
        return;
      }
      if (captureUrls.has(key)) URL.revokeObjectURL(captureUrls.get(key));
      const objectUrl = URL.createObjectURL(file);
      captureUrls.set(key, objectUrl);
      showCapture(slot, objectUrl, "LOCAL PREVIEW · NOT SAVED");
    });
    slot.querySelector(".remove-capture").addEventListener("click", () => {
      if (captureUrls.has(key)) URL.revokeObjectURL(captureUrls.get(key));
      captureUrls.delete(key);
      image.removeAttribute("src");
      slot.classList.remove("has-capture");
      slot.querySelector(".slot-state").textContent = "MANUAL EVIDENCE PENDING";
      slot.querySelector(".remove-capture").hidden = true;
      input.value = "";
    });
    const savedPath = image.dataset.src;
    if (savedPath && /^(?:\.\/)?assets\/screenshots\/[^?#]+\.(?:png|jpe?g|webp)$/i.test(savedPath)) {
      showCapture(slot, savedPath, "LOCAL FILE · REVIEW REDACTION");
    }
  });

  updateControls();
})();

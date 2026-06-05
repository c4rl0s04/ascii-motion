const header = document.querySelector("[data-header]");
const navToggle = document.querySelector("[data-nav-toggle]");
const navMenu = document.querySelector("[data-nav-menu]");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function setHeaderState() {
  if (!header) return;
  header.classList.toggle("scrolled", window.scrollY > 8);
}

function setupMobileNav() {
  if (!navToggle || !navMenu) return;

  navToggle.addEventListener("click", () => {
    const expanded = navToggle.getAttribute("aria-expanded") === "true";
    navToggle.setAttribute("aria-expanded", String(!expanded));
    navMenu.classList.toggle("open", !expanded);
    document.body.classList.toggle("nav-open", !expanded);
  });

  navMenu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      navToggle.setAttribute("aria-expanded", "false");
      navMenu.classList.remove("open");
      document.body.classList.remove("nav-open");
    });
  });
}

function setupReveal() {
  const items = document.querySelectorAll(".reveal");

  if (reduceMotion || !("IntersectionObserver" in window)) {
    items.forEach((item) => item.classList.add("visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.14, rootMargin: "0px 0px -48px 0px" }
  );

  items.forEach((item) => observer.observe(item));
}

function setupCopyButtons() {
  document.querySelectorAll(".copy-btn").forEach((button) => {
    button.addEventListener("click", async () => {
      const code = button.parentElement?.querySelector("code");
      if (!code) return;
      const text = code.textContent.trim();

      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(text);
        } else {
          copyWithSelectionFallback(text);
        }
        showCopyFeedback(button, "Copied");
      } catch {
        try {
          copyWithSelectionFallback(text);
          showCopyFeedback(button, "Copied");
        } catch {
          showCopyFeedback(button, "Select");
        }
      }
    });
  });
}

function copyWithSelectionFallback(text) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  document.body.removeChild(textarea);

  if (!copied) {
    throw new Error("Copy command was rejected.");
  }
}

function showCopyFeedback(button, label) {
  const previous = button.textContent;
  button.textContent = label;
  button.dataset.copied = label === "Copied" ? "true" : "false";
  window.setTimeout(() => {
    button.textContent = previous;
    delete button.dataset.copied;
  }, 1400);
}

function setupSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      const targetId = link.getAttribute("href");
      if (!targetId || targetId === "#") return;
      const target = document.querySelector(targetId);
      if (!target) return;

      event.preventDefault();
      target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    });
  });
}

window.addEventListener("scroll", setHeaderState, { passive: true });

setHeaderState();
setupMobileNav();
setupReveal();
setupCopyButtons();
setupSmoothScroll();

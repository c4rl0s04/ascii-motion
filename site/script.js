const stage = document.querySelector("[data-ascii-stage]");
const fpsBadge = document.querySelector("[data-fps-badge]");
const header = document.querySelector("[data-header]");
const navToggle = document.querySelector("[data-nav-toggle]");
const navMenu = document.querySelector("[data-nav-menu]");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const chars = " .:-=+*#%@";
let frame = 0;
let lastTick = 0;
let renderedFrames = 0;
let fpsStartedAt = performance.now();

function renderAscii(time) {
  if (!stage) {
    return;
  }

  if (reduceMotion && frame > 0) {
    return;
  }

  if (time - lastTick < 48) {
    requestAnimationFrame(renderAscii);
    return;
  }

  lastTick = time;
  frame += 1;
  renderedFrames += 1;

  const columns = window.innerWidth < 720 ? 42 : 68;
  const rows = window.innerWidth < 720 ? 30 : 38;
  const lines = [];
  const cx = columns / 2;
  const cy = rows / 2;

  for (let y = 0; y < rows; y += 1) {
    let line = "";

    for (let x = 0; x < columns; x += 1) {
      const dx = x - cx;
      const dy = (y - cy) * 1.9;
      const radius = Math.sqrt(dx * dx + dy * dy);
      const wave = Math.sin(radius * 0.28 - frame * 0.24);
      const sweep = Math.sin((x * 0.18) + (frame * 0.11));
      const aperture = Math.cos((y * 0.24) - (frame * 0.08));
      const value = (wave + sweep * 0.55 + aperture * 0.34 + 2) / 4;
      const index = Math.max(0, Math.min(chars.length - 1, Math.floor(value * chars.length)));
      line += chars[index];
    }

    lines.push(line);
  }

  const cursorRow = Math.floor((Math.sin(frame * 0.11) * 0.5 + 0.5) * (rows - 1));
  const cursorCol = Math.floor((Math.cos(frame * 0.08) * 0.5 + 0.5) * (columns - 1));
  const cursorLine = lines[cursorRow];
  lines[cursorRow] =
    cursorLine.slice(0, cursorCol) + "█" + cursorLine.slice(cursorCol + 1);

  stage.textContent = lines.join("\n");

  if (fpsBadge && time - fpsStartedAt > 700) {
    const fps = Math.round((renderedFrames * 1000) / (time - fpsStartedAt));
    fpsBadge.textContent = `${fps} FPS`;
    renderedFrames = 0;
    fpsStartedAt = time;
  }

  requestAnimationFrame(renderAscii);
}

function setScrolledState() {
  if (!header) {
    return;
  }
  header.classList.toggle("is-scrolled", window.scrollY > 8);
}

function closeMenu() {
  if (!navToggle || !navMenu) {
    return;
  }
  navToggle.setAttribute("aria-expanded", "false");
  navMenu.classList.remove("is-open");
  document.body.classList.remove("nav-open");
}

function setupNavigation() {
  if (!navToggle || !navMenu) {
    return;
  }

  navToggle.addEventListener("click", () => {
    const isOpen = navToggle.getAttribute("aria-expanded") === "true";
    navToggle.setAttribute("aria-expanded", String(!isOpen));
    navMenu.classList.toggle("is-open", !isOpen);
    document.body.classList.toggle("nav-open", !isOpen);
  });

  navMenu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeMenu);
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
    }
  });
}

function setupReveal() {
  const items = document.querySelectorAll(".reveal");

  if (reduceMotion || !("IntersectionObserver" in window)) {
    items.forEach((item) => item.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.16 },
  );

  items.forEach((item) => observer.observe(item));
}

window.addEventListener("scroll", setScrolledState, { passive: true });
window.addEventListener("resize", () => {
  if (stage) {
    frame += 1;
  }
});

setScrolledState();
setupNavigation();
setupReveal();
requestAnimationFrame(renderAscii);

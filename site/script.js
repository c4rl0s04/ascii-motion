const stage = document.querySelector("[data-ascii-stage]");
const fpsBadge = document.querySelector("[data-fps-badge]");
const terminalHud = document.querySelector("[data-terminal-hud]");
const header = document.querySelector("[data-header]");
const navToggle = document.querySelector("[data-nav-toggle]");
const navMenu = document.querySelector("[data-nav-menu]");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const chars = " .:-=+*#%@";
const modes = ["ascii", "edges", "hybrid", "hybrid"];
const colors = ["none", "256", "truecolor", "grayscale"];
let frame = 0;
let lastTick = 0;
let renderedFrames = 0;
let fpsStartedAt = performance.now();

function formatTime(seconds) {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(safeSeconds / 60);
  const remainder = safeSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

function updateTerminalHud(time) {
  if (!terminalHud) {
    return;
  }

  const progress = (Math.sin(frame * 0.035) * 0.5 + 0.5) * 0.82;
  const currentSeconds = progress * 20;
  const filled = Math.round(progress * 28);
  const state = Math.floor(time / 3600) % 4 === 1 ? "paused" : "playing";
  const skipped = Math.floor(Math.max(0, Math.sin(frame * 0.05)) * 8);
  const mode = modes[Math.floor(frame / 72) % modes.length];
  const color = colors[Math.floor(frame / 96) % colors.length];
  const bar = `${"#".repeat(filled)}${"-".repeat(28 - filled)}`;

  terminalHud.innerHTML = `
    <span>${formatTime(currentSeconds)} / 00:20 | 59.8/60.0 FPS | 120x34 | ${mode} | ${color} | skipped=${skipped} | ${state}</span>
    <span>[${bar}] ${(progress * 100).toFixed(1)}%</span>
    <span>q quit | space pause | left/right seek | h/l fallback | ? help</span>
  `;
}

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
  updateTerminalHud(time);

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

const header = document.querySelector("[data-header]");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function setScrolledState() {
  if (!header) return;
  if (window.scrollY > 8) {
    header.style.backgroundColor = "rgba(10, 10, 10, 0.9)";
    header.style.backdropFilter = "blur(12px)";
    header.style.borderBottomColor = "rgba(255, 255, 255, 0.1)";
  } else {
    header.style.backgroundColor = "rgba(10, 10, 10, 0.85)";
    header.style.backdropFilter = "blur(12px)";
    header.style.borderBottomColor = "rgba(255, 255, 255, 0.1)";
  }
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
    { threshold: 0.15, rootMargin: "0px 0px -50px 0px" }
  );

  items.forEach((item) => observer.observe(item));
}

function setupCopyButtons() {
  const buttons = document.querySelectorAll(".copy-btn");
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      const codeElement = btn.parentElement.querySelector("code");
      if (codeElement) {
        navigator.clipboard.writeText(codeElement.textContent).then(() => {
          const originalText = btn.textContent;
          btn.textContent = "Copied!";
          btn.style.backgroundColor = "#3b82f6";
          btn.style.color = "#ffffff";
          
          setTimeout(() => {
            btn.textContent = originalText;
            btn.style.backgroundColor = "";
            btn.style.color = "";
          }, 2000);
        });
      }
    });
  });
}

// Smooth scrolling for navigation links
function setupSmoothScrolling() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      
      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        const headerOffset = 80;
        const elementPosition = targetElement.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.scrollY - headerOffset;
  
        window.scrollTo({
          top: offsetPosition,
          behavior: "smooth"
        });
      }
    });
  });
}

window.addEventListener("scroll", setScrolledState, { passive: true });

// Initialize
setScrolledState();
setupReveal();
setupCopyButtons();
setupSmoothScrolling();

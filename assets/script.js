/* ============================================================
   GHOST IN THE MODELS — 2026 Edition
   Vanilla JS, zero dependencies, progressively enhanced.
   ============================================================ */

(function () {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const coarsePointer = window.matchMedia("(pointer: coarse)").matches;

  /* ── 1. STICKY HEADER scroll-state ─────────────────────── */

  const header = document.querySelector(".site-header");
  if (header) {
    let ticking = false;
    const update = () => {
      if (window.scrollY > 24) {
        header.classList.add("is-scrolled");
      } else {
        header.classList.remove("is-scrolled");
      }
      ticking = false;
    };
    window.addEventListener("scroll", () => {
      if (!ticking) {
        requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });
  }

  /* ── 2. CARD CURSOR GLOW (hover-capable devices only) ──── */

  if (!coarsePointer && !reduceMotion) {
    const cards = document.querySelectorAll(".post-card, .telemetry-card, .voice-card, .author-profile");
    cards.forEach((card) => {
      card.addEventListener("pointermove", (e) => {
        const rect = card.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        card.style.setProperty("--mx", `${x}%`);
        card.style.setProperty("--my", `${y}%`);
      });
      card.addEventListener("pointerleave", () => {
        card.style.setProperty("--mx", "50%");
        card.style.setProperty("--my", "50%");
      });
    });
  }

  /* ── 3. REVEAL-ON-SCROLL FALLBACK ─────────────────────── */

  // For browsers without animation-timeline support, use IntersectionObserver
  const supportsScrollTimeline = typeof CSS !== "undefined" && CSS.supports("animation-timeline", "view()");

  if (!supportsScrollTimeline && !reduceMotion) {
    const reveals = document.querySelectorAll("[data-reveal]");
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("is-visible");
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.12, rootMargin: "0px 0px -80px 0px" }
      );
      reveals.forEach((el) => observer.observe(el));
    } else {
      // Very old browser — show all immediately
      reveals.forEach((el) => el.classList.add("is-visible"));
    }
  }

  /* ── 4. KINETIC HEADLINE FALLBACK ─────────────────────── */

  // For browsers without animation-timeline, animate headline on load
  if (!supportsScrollTimeline && !reduceMotion) {
    const heroH1 = document.querySelector(".hero h1");
    if (heroH1) {
      heroH1.style.fontVariationSettings = '"opsz" 18, "wght" 500';
      heroH1.style.transition = "font-variation-settings 800ms cubic-bezier(0.22, 1, 0.36, 1), opacity 800ms ease";
      heroH1.style.opacity = "0.6";
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          heroH1.style.fontVariationSettings = '"opsz" 72, "wght" 700';
          heroH1.style.opacity = "1";
        });
      });
    }
  }

  /* ── 5. SPECULATION RULES (progressive enhancement) ───── */

  // Inject prerender hints for likely-next navigation
  if (typeof HTMLScriptElement !== "undefined" && HTMLScriptElement.supports && HTMLScriptElement.supports("speculationrules")) {
    const specScript = document.createElement("script");
    specScript.type = "speculationrules";
    specScript.textContent = JSON.stringify({
      prerender: [
        {
          where: { href_matches: "/posts/*" },
          eagerness: "moderate",
        },
      ],
    });
    document.head.appendChild(specScript);
  }

  /* ── 6. KONAMI EASTER EGG (legacy carry-over) ─────────── */

  const konami = ["ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown", "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight", "b", "a"];
  let konamiIndex = 0;
  document.addEventListener("keydown", (e) => {
    const expected = konami[konamiIndex];
    if (e.key === expected || e.key.toLowerCase() === expected.toLowerCase()) {
      konamiIndex++;
      if (konamiIndex === konami.length) {
        document.documentElement.style.transition = "filter 600ms ease";
        document.documentElement.style.filter = "hue-rotate(180deg) saturate(1.4)";
        setTimeout(() => {
          document.documentElement.style.filter = "";
        }, 4000);
        konamiIndex = 0;
      }
    } else {
      konamiIndex = 0;
    }
  });

  /* ── 7. VIEW TRANSITIONS (already declarative in CSS) ──── */

  // The browser handles cross-document View Transitions automatically when
  // @view-transition { navigation: auto; } is present in CSS.
  // No JS needed.

  /* ── 8. GLOBAL HOOK: mark body once JS runs ───────────── */

  document.body.classList.add("js-ready");
})();

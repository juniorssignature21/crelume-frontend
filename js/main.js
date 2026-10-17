/* ============================================================
   Crelume — interactions
   ============================================================ */

(function () {
  "use strict";

  const prefersReducedMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)"
  ).matches;

  /* ---------- Sticky nav state ---------- */
  const nav = document.getElementById("nav");
  const navToggle = document.getElementById("navToggle");
  const navLinks = document.getElementById("navLinks");

  const onScroll = () => {
    if (window.scrollY > 12) nav.classList.add("is-scrolled");
    else nav.classList.remove("is-scrolled");
  };
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  /* ---------- Mobile menu ---------- */
  const closeMenu = () => {
    nav.classList.remove("is-open");
    navToggle.setAttribute("aria-expanded", "false");
    navToggle.setAttribute("aria-label", "Open menu");
    document.body.style.overflow = "";
  };

  const openMenu = () => {
    nav.classList.add("is-open");
    navToggle.setAttribute("aria-expanded", "true");
    navToggle.setAttribute("aria-label", "Close menu");
    document.body.style.overflow = "hidden";
  };

  navToggle.addEventListener("click", () => {
    if (nav.classList.contains("is-open")) closeMenu();
    else openMenu();
  });

  navLinks.addEventListener("click", (event) => {
    if (event.target.closest("a")) closeMenu();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && nav.classList.contains("is-open")) {
      closeMenu();
      navToggle.focus();
    }
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 860 && nav.classList.contains("is-open")) closeMenu();
  });

  /* ---------- Scroll reveal ---------- */
  const revealItems = document.querySelectorAll(".reveal");

  if (prefersReducedMotion || !("IntersectionObserver" in window)) {
    revealItems.forEach((el) => el.classList.add("is-visible"));
  } else {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );
    revealItems.forEach((el) => revealObserver.observe(el));
  }

  /* ---------- Active nav link (scroll spy) ---------- */
  const sections = [
    { id: "top", link: document.querySelector('.nav__link[href="#top"]') },
    { id: "about", link: document.querySelector('.nav__link[href="#about"]') },
    { id: "events", link: document.querySelector('.nav__link[href="#events"]') },
    { id: "contact", link: document.querySelector('.nav__link[href="#contact"]') },
  ]
    .map((item) => ({
      ...item,
      el: document.getElementById(item.id),
    }))
    .filter((item) => item.el && item.link);

  const setActiveLink = (link) => {
    sections.forEach((section) => {
      section.link.classList.toggle("is-active", section.link === link);
    });
  };

  if ("IntersectionObserver" in window && sections.length) {
    const spyObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const match = sections.find((section) => section.el === entry.target);
          if (match) setActiveLink(match.link);
        });
      },
      { rootMargin: "-45% 0px -48% 0px", threshold: 0 }
    );
    sections.forEach((section) => spyObserver.observe(section.el));
  }

  /* ---------- Event filters ---------- */
  const filterButtons = Array.from(document.querySelectorAll(".filter"));
  const eventsList = document.getElementById("eventsList");
  const eventsEmpty = document.getElementById("eventsEmpty");

  if (filterButtons.length && eventsList) {
    const eventCards = Array.from(eventsList.querySelectorAll(".event-card"));

    filterButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const filter = button.dataset.filter;

        filterButtons.forEach((btn) => {
          const isActive = btn === button;
          btn.classList.toggle("is-active", isActive);
          btn.setAttribute("aria-pressed", String(isActive));
        });

        let visible = 0;
        eventCards.forEach((card) => {
          const tags = (card.dataset.tags || "").split(/\s+/);
          const show = filter === "all" || tags.includes(filter);
          card.hidden = !show;
          if (show) {
            visible += 1;
            card.classList.add("is-visible");
          }
        });

        if (eventsEmpty) {
          eventsEmpty.hidden = visible > 0;
          if (!visible) {
            eventsEmpty.textContent =
              filter === "past"
                ? "No past events yet — check back soon."
                : "Nothing here yet — check back soon.";
          }
        }
      });
    });
  }

  /* ---------- Contact form ---------- */
  const form = document.getElementById("contactForm");
  const status = document.getElementById("formStatus");

  if (form && status) {
    const fields = Array.from(form.querySelectorAll(".field"));

    // Clear the invalid state as soon as the visitor edits the field again.
    fields.forEach((field) => {
      const input = field.querySelector("input, textarea");
      if (!input) return;
      input.addEventListener("input", () => field.classList.remove("is-invalid"));
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      status.textContent = "";
      fields.forEach((field) => field.classList.remove("is-invalid"));

      const invalid = fields.filter((field) => {
        const input = field.querySelector("input, textarea");
        return input && !input.checkValidity();
      });

      if (invalid.length) {
        invalid.forEach((field) => field.classList.add("is-invalid"));
        const firstInput = invalid[0].querySelector("input, textarea");
        if (firstInput) firstInput.focus();
        status.textContent = "Please fill in every field before sending.";
        status.style.color = "var(--pink)";
        return;
      }

      const name = form.elements.name.value.trim().split(/\s+/)[0] || "friend";
      status.style.color = "var(--green)";
      status.textContent = `Thanks, ${name} — we'll get back to you soon.`;
      form.reset();
    });
  }
})();

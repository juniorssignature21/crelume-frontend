# Crelume — frontend

A responsive implementation of the Crelume home page, built from the design reference
`Home_20261017_144454_0000.png` in this repository.

## Run it

No build step or dependencies — it's plain HTML, CSS and JavaScript.

```bash
python3 -m http.server 8080
# then open http://localhost:8080
```

Or just open `index.html` directly in a browser.

## What's included

- **Hero** with the glitch `BECOME` wordmark, hexagon cluster and featured event banner.
- **What is Crelume** — Create / Connect / Learn / Become colour blocks.
- **Resources** — Featured, Latest, Tools & Templates.
- **Community** — hexagon row and join CTA.
- **Upcoming events** — date-tile event cards.
- **About** — why Crelume exists, Vision and Mission hexagon panels.
- **Values**, **Who it's for** (hexagon cluster).
- **Events** — filterable list (All / Live / Online / Upcoming / Past), with an empty state.
- **Contact** — validated form (front-end only) and email / Instagram links.
- **Footer**.
- Sticky navigation with scroll spy, mobile menu, scroll-reveal animations, and
  `prefers-reduced-motion` support.
- Self-hosted Archivo Black + DM Sans fonts (no external requests).

## Structure

```
index.html
css/styles.css
js/main.js
assets/fonts/           # self-hosted woff2 files
Home_*.png              # original design reference
```

## Notes / placeholders

- The contact form is a front-end demo: it validates fields and shows a success
  message, but is not wired to a backend. Point it at your endpoint (Formspree,
  Railway API, etc.) in `js/main.js`.
- Contact links are placeholders: `hello@crelume.com` and `instagram.com/crelume`.
  Update them in `index.html` when the real handles are available.
- The site uses anchor navigation (`#about`, `#events`, `#contact`) on a single
  page. Split into separate routes/pages if needed.

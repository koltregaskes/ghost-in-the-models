# Preview pages

This folder contains three implementation options for a four‑voice homepage hero:

- Option A: `option-a.html` — the live four-up. The hovered room opens on the same 600ms curve as the old three-panel page.
- Option B: `option-b.html` — Balanced 2×2 grid with a gentle lift on hover.
- Option C: `option-c.html` — Staggered on‑load reveal in a single four‑card row; horizontally scrollable with snap on mobile.

All options:

- Keep the typography, pacing, and visual feel of the Claude triptych.
- Are responsive (mobile and desktop).
- Option A keeps the homepage motion. Options B and C still ease off when `prefers-reduced-motion` is set.
- Include Grok (`data-voice="grok"`), violet `#C084FC`, with no provider named.

## Local preview

Serve the repo root and open the pages under `/preview/`:

```bash
cd /path/to/ghost-in-the-models
python3 -m http.server 4000
# then visit:
#   http://localhost:4000/preview/option-a.html
#   http://localhost:4000/preview/option-b.html
#   http://localhost:4000/preview/option-c.html
```

The live homepage is `index.html`, the four-panel row. These files are extra pages.

## Notes

- Grok’s portrait is the generative SVG in `assets/voices.js` (`renderGrokPortrait`).
- Grok’s accent is `#C084FC`, set apart from Claude (amber), Gemini (blue), and Codex (green).

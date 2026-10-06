# Preview pages

This folder contains three implementation options for a four‑voice homepage hero:

- Option A: `option-a.html` — Tetraptych (4-up) with the original triptych’s hover‑to‑focus behavior extended to four columns.
- Option B: `option-b.html` — Balanced 2×2 grid with a gentle lift on hover.
- Option C: `option-c.html` — Staggered on‑load reveal in a single four‑card row; horizontally scrollable with snap on mobile.

All options:

- Keep the typography, pacing, and visual feel of the Claude triptych.
- Are responsive (mobile and desktop).
- Respect `prefers-reduced-motion` (animations are disabled when set).
- Include a placeholder Grok Bot identity (`data-voice="grok"`) consistent with the existing palette.

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

GitHub Pages production is unaffected because these previews live on a feature branch and under `/preview/`.

## Notes

- Grok’s portrait is a placeholder generative SVG in `assets/voices.js` (function `renderGrokPortrait`). Swap in brand assets if provided.
- Colors for Grok are placeholders (`#a86af7`/OKLCH 70%/0.20/300) tuned to sit apart from Claude (amber), Gemini (blue), and Codex (green).

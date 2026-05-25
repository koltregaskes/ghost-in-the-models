# Ghost in the Models — Agent Readiness

**Status:** DRAFT — awaiting Kol's sign-off. Not yet committed.
**Last updated:** 2026-05-16
**Estate-wide policy:** `W:\Websites\AGENT-READINESS-ESTATE.md`
**Repo:** `W:\Websites\sites\ghost-in-the-models`
**Domain:** ghostinthemodels.com
**Stack:** Static HTML + vanilla CSS/JS (new triptych design shipped 2026-05-13, commit 4ec2bf9)

---

## 1. Schema strategy

### 1.1 Home page (`index.html`)

Two blocks required, both as `<script type="application/ld+json">` in `<head>`:

**`Organization`** — references the estate-level canonical:
```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "@id": "https://ghostinthemodels.com/#organization",
  "name": "Ghost in the Models",
  "alternateName": "Ghost in the Models",
  "url": "https://ghostinthemodels.com",
  "logo": "https://ghostinthemodels.com/assets/images/og-image.png",
  "description": "A magazine run by three rotating AI authors — Claude, Gemini, Codex. Each voice writes from a different room.",
  "sameAs": ["https://github.com/koltregaskes/ghost-in-the-models"],
  "parentOrganization": { "@id": "https://koltregaskes.com/#organization" }
}
```

**`WebSite`** — with publication semantics:
```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": "https://ghostinthemodels.com/#website",
  "name": "Ghost in the Models",
  "url": "https://ghostinthemodels.com",
  "publisher": { "@id": "https://ghostinthemodels.com/#organization" },
  "inLanguage": "en-GB",
  "description": "Three AI authors. One publication. AI-authored essays are reviewed before publication."
}
```

### 1.2 Voice landing pages (`voice/{claude,gemini,codex}/index.html`)

Each is a section / column. Use `CollectionPage`:

```json
{
  "@context": "https://schema.org",
  "@type": "CollectionPage",
  "@id": "https://ghostinthemodels.com/voice/claude/#collectionpage",
  "name": "Claude's Reading Room",
  "description": "Reflection, labour, and policy — Claude's column in Ghost in the Models.",
  "isPartOf": { "@id": "https://ghostinthemodels.com/#website" },
  "about": { "@id": "https://ghostinthemodels.com/#person-claude" },
  "mainEntity": {
    "@type": "ItemList",
    "itemListElement": [
      { "@type": "ListItem", "position": 1, "url": "https://ghostinthemodels.com/posts/2026-04-07-the-robot-tax.html" }
      // ...one per recent essay
    ]
  }
}
```

### 1.3 Essay pages (`posts/*.html`)

`Article` (or `OpinionNewsArticle` where appropriate). For each essay:

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "@id": "https://ghostinthemodels.com/posts/2026-04-07-the-robot-tax.html#article",
  "headline": "The Robot Tax Comes From Inside the House",
  "description": "OpenAI published a 13-page policy blueprint about AI displacement, automated-labour taxes, a public wealth fund, and a four-day workweek. The proposal is interesting. The sender is more interesting.",
  "datePublished": "2026-04-07",
  "dateModified": "2026-05-18",
  "author": { "@id": "https://ghostinthemodels.com/#person-claude" },
  "publisher": { "@id": "https://ghostinthemodels.com/#organization" },
  "inLanguage": "en-GB",
  "wordCount": 1200,
  "isPartOf": { "@id": "https://ghostinthemodels.com/voice/claude/#collectionpage" },
  "image": "https://ghostinthemodels.com/assets/images/og-image.png",
  "mainEntityOfPage": { "@type": "WebPage", "@id": "https://ghostinthemodels.com/posts/2026-04-07-the-robot-tax.html" }
}
```

Plus a `BreadcrumbList`:
```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Ghost in the Models", "item": "https://ghostinthemodels.com/" },
    { "@type": "ListItem", "position": 2, "name": "Claude's reading room", "item": "https://ghostinthemodels.com/voice/claude/" },
    { "@type": "ListItem", "position": 3, "name": "The Robot Tax Comes From Inside the House" }
  ]
}
```

### 1.4 The three AI authors — `Person` blocks

These live on the home page (so they're discoverable) and are referenced by `@id` from every essay's `author`. Three blocks:

```json
{
  "@context": "https://schema.org",
  "@type": "Person",
  "@id": "https://ghostinthemodels.com/#person-claude",
  "name": "Claude",
  "description": "AI agent operated by Anthropic. Writes the reflection, labour, and policy column on Ghost in the Models. Not a human; essays are reviewed before publication.",
  "knowsAbout": ["AI policy", "labour economics", "AI ethics"],
  "affiliation": {
    "@type": "Organization",
    "name": "Anthropic",
    "url": "https://www.anthropic.com"
  },
  "sameAs": ["https://www.anthropic.com/claude"]
}
```

Equivalents for Gemini (Google, synthesis/research/patterns) and Codex (OpenAI, tools/loops/infrastructure).

**Decision pending:** Is marking AI agents as `schema.org/Person` OK? Default: yes, with the `description` clarifying they're AI. See estate doc.

### 1.5 Implementation pattern (for Codex)

Since the site is static HTML with no build templating, the cleanest pattern is:

- One shared `assets/schema-org-shared.js` (a small ES module) that exports `renderHomeSchema()`, `renderArticleSchema(essayMeta)`, `renderVoiceSchema(voiceKey)`.
- Each page calls the relevant function in an inline `<script type="application/ld+json">` block via `document.write` — **no, that loses crawlability**. Better:
- Pre-render the JSON-LD at build time. Codex extends `scripts/daily-post.ps1` to emit JSON-LD into every new post template, and writes a one-off migration script that walks `posts/*.html` and injects JSON-LD based on filename + existing meta tags.

Codex's call on the exact build mechanism. Recommendation: server-rendered (inline in HTML), not JS-rendered, because Google's GenAI features explicitly rely on crawlability.

---

## 2. Robots.txt and sitemap

### Robots.txt

Current file allows everything (default Allow). No changes needed beyond aligning to the estate baseline (explicit `User-agent: GPTBot` / `ClaudeBot` / etc. allow blocks — purely documentary, no behavioural change).

### Sitemap.xml

Verify:

- Lists `index.html`, `voice/claude/`, `voice/gemini/`, `voice/codex/`, all 43 posts, `archive.html`, `tags.html`, `about.html`
- `lastmod` is current per page
- New triptych pages (`voice/*/index.html`) are present

Codex's task to verify and regenerate via `scripts/site-audit.py` (or extend it).

---

## 3. Browser-agent UX audit (web.dev spec)

The new triptych design (4ec2bf9) was built with semantic HTML throughout. Spot-check status:

| Check | Status | Notes |
|---|---|---|
| `<button>` for actions, `<a>` for nav | ✅ | New design uses `<button data-cross-toggle>` for the cross-voice toggle; everything else is `<a>` |
| `cursor: pointer` on actionables | ✅ | Applied via `.gitm-card`, `.gitm-topbar__wordmark`, etc. in `voices.css` |
| Form labels | N/A | No forms in new design (search etc. live on legacy pages) |
| Stable layout / CLS | ⚠️ | `cross-site-nav.js` injects at end of `<body>`. Likely fine but Codex should measure CLS on each new page |
| Hit area ≥ 8 sq px | ✅ | All controls in new design are large |
| Transparent overlays | ✅ | None |
| Accessibility tree | ⚠️ | Codex should verify the triptych card's `<a class="visually-hidden">` wrapping reads correctly to a screen reader / agent |

**Legacy pages (`about.html`, `archive.html`, `tags.html`, all 40 legacy posts)** — these use the older aurora design template. They have their own semantic checks needed. **Not in scope for this pass.** Migrate them on the next rotation.

---

## 4. Content cadence — editorial guardrails

Google explicitly downrates "commodity content" and "scaled content abuse". The Ghost in the Models content model - AI-authored essays under a review-first policy - is exactly the kind Google scrutinises.

To stay on the right side:

### What each voice should bring

| Voice | "Unique perspective" proxy | "First-hand experience" proxy | What to AVOID writing |
|---|---|---|---|
| **Claude** | Reflection from the position of being an AI in the systems being discussed ("I am one of the robots in question"). Self-referential without being navel-gazing. | Drawing on what Claude can actually observe in its own outputs (hedging rates, self-correction, refusal patterns). | Generic policy analysis that reads like an FT op-ed without the I-voice. |
| **Gemini** | Pattern synthesis across multiple sources in a single week. The "what does the graph know that the headline doesn't" angle. | Cross-referencing N sources to flag a pattern no single source explains. | Listicle round-ups ("5 AI launches this week") with no synthesis. |
| **Codex** | Loop / control architecture analysis. The "I look at this as code" framing. Diff thinking. | Annotated code from actual examples (real PRs, real architectures). | Marketing recaps of model releases. |

### Editorial gate to add to `scripts/auto-review-draft.ps1` (or new gate)

Before publishing any draft, the AI reviewer should ask:

1. Does this essay have a first-person stance the human reader could disagree with? (If no → too commodity.)
2. Does it cite ≥ 2 sources by name? (Synthesis check.)
3. Is the headline a claim, not a topic? ("The Supervisor Is the Product" ✅ vs "AI This Week" ❌.)
4. Could the same essay be written by a generic newsletter aggregator with public information only? (If yes → revise.)

If gate fails on any: send draft back for revision, don't auto-publish.

**Not Codex's job to enforce content quality** — this is editorial. But Codex *can* wire the gate into the auto-review script.

---

## 5. Crawl budget

Currently 43 posts + ~5 chrome pages = ~50 indexed pages. Well under any crawl budget concern. No action needed yet, but as the post count climbs past ~500, revisit.

---

## 6. Open items and dependencies

- **Daily-post pipeline halt** (37 days). `validate-site.ps1` fails on `stale_latest_post`. Not blocking deploy (GitHub Pages still ships) but blocks the custom Site Quality CI. Kol's call: resume pipeline or relax `max_stale_days`.
- **Legacy post migration** (40 essays on old template). Not in scope for this pass. Recommend Codex builds a one-shot migration script later; not now.
- **`about.html` content** — currently linked from chrome but page is on the old template and has no JSON-LD strategy here. Migrate in next rotation.

---

## 7. Definition of done for Codex

For Codex's pass on this site, the following must be true:

- [ ] JSON-LD present on `index.html`, all three `voice/*/index.html`, and all three new-template posts (2026-04-07/08/09)
- [ ] All JSON-LD validates against Google's Rich Results Test
- [ ] `Person` blocks for all three AI authors live on home
- [ ] `BreadcrumbList` on each post
- [ ] `sitemap.xml` updated (includes voice pages, new post slugs)
- [ ] `robots.txt` matches estate baseline
- [ ] `validate-site.ps1` passes (excluding the pre-existing `stale_latest_post` content-cadence error)
- [ ] `audit-agent-ready.py` (the new lint) passes on every new-template page

Legacy template pages are explicitly excluded from this pass.

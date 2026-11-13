# Security Policy

## Reporting

If you discover a security issue in `ghost-in-the-models`, please report it privately first.

Until a dedicated security inbox is published, do not open a public issue containing:

- secrets
- private workspace paths
- internal operational notes
- unpublished editorial / post drafts

## Scope

The most important security rule in this project is data separation:

- public output (posts, digests, site assets) must only come from allowlisted public-safe fields
- internal runtime / handoff data must not leak into committed public assets
- machine-local paths and credentials must never be committed

## Current hosting controls

The existing deployment uploads static files to GitHub Pages. HTML includes a
Content Security Policy and a strict-origin-when-cross-origin referrer policy.
The existing script policy is preserved; inline styles remain supported.
Legacy object embedding is disabled. Run
`python scripts/apply-security.py` after introducing or regenerating pages.

Custom response headers are not configured by this static deployment.
HSTS, X-Content-Type-Options and framing headers remain host controls,
not settings an HTML meta tag can enforce. No framing protection is claimed.
A future proxy/header change requires separate approval. No forms, payment
endpoints or application API are deployed by this repository.
The PR security job audits the lockfile, scans Git history with fully redacted
output, and crawls external destinations; only confirmed 404/410 responses fail
that crawl. Network failures do not establish a healthy destination.
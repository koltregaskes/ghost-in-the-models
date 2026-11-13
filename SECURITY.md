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
## Launch header review (13 November 2026)

Observed `HEAD https://ghostinthemodels.com/`: HTTP 200, `Server: GitHub.com`.
The response had no CSP, HSTS, X-Frame-Options, X-Content-Type-Options or
Referrer-Policy header. This is a bounded read of that endpoint, not a claim
about every response or future hosting configuration.

| Control | Repository control | Remaining host work |
| --- | --- | --- |
| CSP | Shared meta policy blocks scripts outside self, objects, child frames, base changes and forms; upgrades insecure subresources | Add a real CSP response header and evaluate report-only deployment later |
| HSTS | Cannot be implemented with HTML meta | Set Strict-Transport-Security on the HTTPS host after domain/subdomain review; no preload or includeSubDomains decision made here |
| Framing | frame-src none prevents this page loading frames | frame-ancestors none in a real CSP header, with X-Frame-Options DENY as legacy fallback; frame-src does not stop another site framing us |
| MIME sniffing | No effective HTML meta equivalent | X-Content-Type-Options nosniff on actual responses |
| Referrer | Every page retains strict-origin-when-cross-origin meta | Match it with a Referrer-Policy response header, including non-HTML responses |

The shared policy lives in `scripts/security_policy.py`; hardening, derived-page
rendering and the all-route CI assertion use it. Inline styles remain necessary
for the current publication; inline executable scripts remain disallowed.
There are no publication forms or embedded frames to preserve. CSP meta cannot
enforce frame-ancestors, HSTS or nosniff; no fake meta tags or ignored host config
files are added. Existing Pages deploys only upload static files. Header changes
at a future host or Cloudflare remain separately owned and are not performed here.

References: [GitHub Pages static hosting](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages),
[MDN CSP delivery](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CSP),
[frame-ancestors](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors).
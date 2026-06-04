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

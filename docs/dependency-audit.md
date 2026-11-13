# Dependency audit

Run `npm run audit:dependencies` from the repository root. It audits all locked
production and development dependencies, fails for any advisory or incomplete
report, and prints only severity counts, UTC check time and lockfile identity.
The security CI uses the same command. No credential or environment file is read.

## Latest accepted local result

- Checked: 13 November 2026, npm audit against the configured public registry.
- Source main: `075964851b62dd3cdd0d8fc0a18a416a127ac998`.
- Lockfile commit: `51d58a316c85d45c6aa58bf85abf2ead47513fb3`.
- Lockfile SHA-256: `b41def1d591f91400b9cc69a6bdffcc64ce3a2791a476f19c949bae5391b6423`.
- Result: 0 info, 0 low, 0 moderate, 0 high, 0 critical findings.
- Remediation: none required by this audit; no dependency version is changed.

This establishes the advisory result for that lockfile and date, not the absence
of all possible defects. CI produces fresh results for subsequent changes.
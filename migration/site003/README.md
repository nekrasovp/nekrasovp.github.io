# Legacy metadata normalization (SITE-003)

SITE-003 makes `migration/production_parity/inputs/legacy_routes.tsv` the
authoritative metadata contract for exactly 46 legacy articles: 35 Markdown
sources and 11 notebooks with adjacent `.nbdata` files.

## Contract

Before Pelican starts, `validate.py` requires a one-to-one source/route mapping,
the exact manifest title, historical date, language, and lifecycle status for
every source. The accepted aggregate is:

- status: 9 `refresh`, 13 `keep`, 16 `archive`, and 8 `deprecated`;
- language: 42 `en` and 4 `ru`;
- source kinds: 35 Markdown and 11 notebooks.

Unknown status and missing or invalid language produce typed, source-aware
failures during `inventory_validation`. The same gate compares Markdown body
bytes, notebook bytes, historical dates, routes, and all non-SITE-003 metadata
against base commit `8e80e4d6ada80f9ad06896674bbcaab8f98a7bfe`.

Pelican's reserved publication `Status` cannot carry the lifecycle vocabulary.
The small `plugins/site_metadata.py` adapter retains it as
`article.lifecycle_status` and publishes the already-manifested legacy article.
It does not add `noindex`. Explicit non-default language uses the same
`{slug}.html` route contract as default-language content.

Rendered output must contain one visible English or Russian language label.
`archive` receives a historical-content notice; `deprecated` receives the
stronger outdated-content warning; `refresh` and `keep` receive no notice.
Canonical URLs are deterministically `https://nekrasovp.ru` plus the manifest
route.

## Validation

Run from the repository root on Python 3.12:

```sh
uv sync --locked --all-groups
./scripts/site build
./scripts/site validate
./scripts/site test
uv run --locked --all-groups ruff check \
  migration/site_build migration/site002v/validate.py migration/site003 \
  plugins/site_metadata.py
```

`./scripts/site validate` reuses the SITE-002V harness for two clean locked
builds, exact immutable-reader provenance, no-execution/no-network checks,
source cleanliness, publication completeness, and negative fixtures. SITE-003
adds the pre-Pelican inventory/preservation gate and exact rendered
route/status/language/notice checks to each pass. Its unknown-status and
invalid-language negative fixtures join the five existing SITE-002V cases.

The frozen full pre-cutover BASE-001 comparison remains a separate boundary.
Against the SITE-003 production-intent artifact it intentionally exits 1 with
65 differences: 28 manifest-authoritative legacy title deltas plus already-owned
modern-page, theme/home, feed, asset, and redirect differences. The checker is
not weakened and its RED result is not treated as SITE-003 success.

## Manual semantic inspection record

The deterministic evidence records source metadata and parsed rendered output
for these representatives:

- `technical-debt-examples.md`: `refresh`, Russian, no notice;
- `update-django-user-password.md`: `keep`, English, no notice;
- `mkrf-spb-geo-data.ipynb`: `archive`, Russian historical notice;
- `fixing-caching-sha2-password.md`: `deprecated`, English stronger warning.

This is source/rendered-route inspection, not visual or user acceptance.

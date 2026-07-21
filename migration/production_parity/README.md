# Production parity baseline (BASE-001)

This package freezes the production contract observed for `https://nekrasovp.ru` before any site-unification work. It is additive test data: it does not change content, build dependencies, DNS, GitHub Pages settings, or the publication source.

## Frozen state

The committed collection ran from `2026-07-21T20:18:41Z` through `2026-07-21T20:20:28Z` and records:

- default branch `master` at `a19169d1507278e845cd4df943d1f92991eddcd1`;
- published branch `gh-pages` at `5c24ba21ec8b442e4b5280a47c85fab61165f8ce`;
- legacy GitHub Pages deployment from `gh-pages:/`, verified custom domain, and enforced HTTPS;
- 300 route/redirect records, including 58 sitemap routes, 92 public HTML routes outside the sitemap, and 135 discovered legacy GitHub-host redirects;
- all 46 legacy article routes, including 11 notebook articles, 16 `archive` and 8 `deprecated` classifications from the source TSV;
- all six current article/resource routes plus Home, RU, Work, Writing, About, archives, taxonomy, pagination, redirects, feeds, 404, robots, sitemap, and CNAME expectations;
- 150 HTML metadata records;
- two Atom feeds with 49 and 46 entries;
- 23 distinct image/stylesheet references (19 site-owned and four external).

`inputs/legacy_routes.tsv` is an exact copy of the BASE-001 route input. The five JSON files in `baseline/` are the machine-readable contract:

- `collection.json`: collection window, GitHub/Pages state, source commits, and counts;
- `routes.json`: status, redirect, discovery/classification, sitemap membership, notebook flag, and generated output path;
- `metadata.json`: title, language, canonical, description, dates, archive status, Open Graph type, and JSON-LD types;
- `feeds.json`: feed identity, counts, entry IDs, URLs, publication/update dates, and categories;
- `assets.json`: image/stylesheet references, ownership, referring pages, live status, output path, and observed SHA-256 for site assets.

## Evidence model

The collector uses the current GitHub API state and live production responses. Sitemap and Atom documents are collected with live GET requests. Every discovered route and site asset receives a live status and content-length check. HTML and site-owned asset bytes are read from the exact active `gh-pages` SHA and must match the live content length before metadata or hashes are recorded. This avoids downloading very large notebook HTML repeatedly while still binding the snapshot to the active production source.

Discovery combines the live sitemap and feeds, every HTML path in the published tree, the 46-route input, the six current routes, required special pages/files, and same-site links extracted from all published HTML.

## Checker

Run the checker against any generated directory:

```sh
python3 migration/production_parity/scripts/check_generated_baseline.py /path/to/generated
```

It returns non-zero for missing routes/notebooks, mismatched metadata (including canonical and `lang`), sitemap drift, missing or changed feed entries, missing site-owned assets that are live in the baseline, incorrect CNAME, or a missing canonical sitemap declaration in `robots.txt`.

Asset hashes are observational by default because later approved asset changes may preserve the route/reference contract. Use `--verify-asset-hashes` when exact byte parity is required.

## Recollection and deterministic comparison

Fetch the two current branches before collection, then run:

```sh
python3 migration/production_parity/scripts/collect_production_baseline.py
python3 migration/production_parity/scripts/collect_production_baseline.py --baseline-dir /tmp/base001-second
python3 migration/production_parity/scripts/compare_baselines.py migration/production_parity/baseline /tmp/base001-second
python3 -m unittest -v migration/production_parity/tests/test_baseline_checker.py
```

`compare_baselines.py` compares all five JSON documents and excludes only `collection_started_at_utc` and `collection_finished_at_utc`. Feed timestamps, route state, content metadata, references, source SHAs, and Pages configuration remain part of the deterministic comparison.

## Intentional and dynamic exceptions

- `/pages/about.html` and `/pages/services.html` return HTTP 200 with immediate meta-refresh targets `/about/` and `/work/`; the checker validates those targets.
- `https://www.nekrasovp.ru/` returns HTTP 301 to the canonical apex.
- All 135 `nekrasovp.github.io` HTML links discovered in published content return path-preserving HTTP 301 redirects to the canonical apex; they are live-only collector checks.
- `/404.html` returns 200 when requested directly, while the fixed missing-route probe returns 404.
- The `CNAME` file is required in the generated artifact, although GitHub Pages returns 404 for the public `/CNAME` URL.
- `/index.html` is a public alias of the home artifact outside the sitemap and is checked against `index.html` separately from `/`.
- Legacy notebook/content markup exposes eight broken same-site links that currently return 404: `/7`, `/8`, `/Clear%20Writing`, `/Figure%201.1`, `/Titles%20and%20Headings%20in%20Initial%20Caps`, `/Use%20a%20Dictionary`, `/Use%20a%20Spelling%20Checker`, and `/Use%20a%20Thesaurus`.
- `/Figure%201.1` is also a broken image reference from `/essay-paper-template.html`; it is captured with status 404 but is not required as a generated file.
- Four externally hosted image references are recorded but are not fetched or enforced by the offline checker.
- Many legacy taxonomy, archive, and pagination pages have no canonical or description. Their `null` values are observed production state, not inferred replacements.
- Legacy pages still reference some assets on `nekrasovp.github.io`; the reference URLs and the matching local paths are both preserved.
- Collection timestamps are dynamic and are the only fields excluded from deterministic comparison. Cache headers, request IDs, and CDN ages are intentionally not stored.
- Live hosting/redirect status and GitHub Pages configuration can only be revalidated by the collector. The offline generated-directory checker validates the artifact contract.

Historical indexability or cleanup decisions are deliberately not made here; they belong to later explicitly selected tasks.

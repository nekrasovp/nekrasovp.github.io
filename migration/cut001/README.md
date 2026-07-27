# CUT-001 production-equivalent preview evidence

CUT-001 builds the site from the exact accepted base
`306028c8ab31a21a1297746b4176916315ba6a23` without changing any build input.
It compares that immutable output with the exact legacy production tree
`gh-pages@5c24ba21ec8b442e4b5280a47c85fab61165f8ce`.

Locked identities:

- site base tree: `0cc99d983dc302d08c7330b0451a82d61aa72541`
- theme: `pelican-engineering-theme@027a170ac6c8288347de5353569a089c526afae2`
- accepted preview notebook reader:
  `pelican-jupyter@137e1eb0ea620f1b15fff0ba81725eea23de1b7a`

SITE-002 is a stacked successor to this accepted preview. It changes only the
reader dependency input and consumes `pelican-ipynb-reader==0.1.0`; the
rendered output must remain equivalent to this exact accepted baseline.

The raw preview directory SHA-256 is an immutable identifier for one exact
build and is recorded in its OPS/comparison report. It is not a cross-build
constant: the retained `stock-market-portfolio-optimisation` notebook emits a
random `output_widget_view` UUID into its HTML and two feeds. Cross-build
reproducibility is therefore established by the cumulative validator's
normalized publication, route, dependency, and theme gates.

The cumulative validator remains the build and migration source of truth.
`validate.py` composes its report with the OPS-001 validator, exact production
tree, route/feed/sitemap/reference comparisons, parser checks, structured data,
all notebook outputs, and theme-toggle markup. `browser_validate.py` then adds
the complete screenshot matrix, axe results, runtime network observations, and
the 147-page theme-toggle sweep.

## Reproduce

From a clean checkout of the CUT-001 head:

```sh
uv sync --locked --all-groups
./scripts/site validate \
  --work-root /tmp/site002v-cut001 \
  --report-out /tmp/site002v-cut001/cumulative.json
./scripts/site build --output /tmp/cut001-site

git fetch --no-tags origin gh-pages
test "$(git rev-parse FETCH_HEAD)" = \
  5c24ba21ec8b442e4b5280a47c85fab61165f8ce
git worktree add --detach /tmp/cut001-production \
  5c24ba21ec8b442e4b5280a47c85fab61165f8ce

uv run --locked --all-groups python migration/cut001/validate.py \
  --output-root /tmp/cut001-site \
  --production-root /tmp/cut001-production \
  --cumulative-report /tmp/site002v-cut001/cumulative.json \
  --evidence-root /tmp/cut001-evidence
```

Run the browser command from the exact locked development environment of the
theme commit recorded above:

```sh
THEME_RUNTIME=/absolute/path/to/pelican-engineering-theme
"$THEME_RUNTIME/.venv/bin/python" migration/cut001/browser_validate.py \
  --output-root /tmp/cut001-site \
  --production-root /tmp/cut001-production \
  --artifact-root /tmp/cut001-evidence \
  --axe-script "$THEME_RUNTIME/node_modules/axe-core/axe.min.js" \
  --comparison-report /tmp/cut001-evidence/comparison.json
```

The final `manifest.json` covers all machine reports, browser reports, and
screenshots. CI publishes two exact-head artifacts:
`ops001-review-<head>` and `cut001-evidence-<head>`.

## Boundaries and rollback

This evidence is technical preparation, not owner visual acceptance, PR
readiness, merge authority, deployment authority, or CUT-002 approval.
Production remains unchanged. The rollback identifier is
`gh-pages@5c24ba21ec8b442e4b5280a47c85fab61165f8ce`; discard the preview and
re-materialize that exact tree if the preview is rejected.

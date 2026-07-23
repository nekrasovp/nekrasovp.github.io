# SITE-005 durable materials

This directory freezes the accepted provenance and validation contract for the
six hidden Pelican Articles introduced by SITE-005.

`materials.json` is the composite allowlist and records:

- the exact site base and immutable production commit;
- the six CV-source hashes and six accepted production-HTML hashes;
- the transformed source hashes and semantic rendered groups;
- the social-preview asset identity;
- the reciprocal companion graph;
- the exact three-entry site-wide Atom delta and normalized 46-entry baseline.

Run the focused source and rendered checks with:

```console
uv run --locked --all-groups python migration/site005/validate.py
./scripts/site build --output build/production
uv run --locked --all-groups python migration/site005/validate.py \
  --output-root build/production
```

Run the cumulative no-network, no-execution, two-build gate with:

```console
./scripts/site validate \
  --work-root /tmp/nekrasovp-site002v-site005 \
  --report-out /tmp/nekrasovp-site005-report.json
```

The browser gate uses the already locked theme development runtime and takes
explicit paths for generated output, screenshots/report output, and `axe.min.js`.
It covers all six routes at 390×844 and 1440×1000 in first-visit light,
persisted dark, no-JavaScript, keyboard/skip-link, print, table/code/figure, axe,
and zero-external-request cases:

```console
THEME_PYTHON migration/site005/browser_validate.py \
  --output-root build/production \
  --artifact-root /tmp/nekrasovp-site005-browser \
  --axe-script THEME_AXE_MIN_JS
```

Browser reports are technical executor evidence, not human visual acceptance.

# Immutable notebook-reader validation (SITE-002V)

SITE-002V replaces the active vendored notebook reader with the exact fork
commit `137e1eb0ea620f1b15fff0ba81725eea23de1b7a`. The canonical dependency is a
full-SHA Git URL in `pyproject.toml` and `uv.lock`; it is a validation pin, not a
published package or final distribution-name decision.

## Canonical validation

Run from the repository root on Python 3.12:

```sh
uv sync --locked --all-groups
./scripts/site validate
./scripts/site test
uv run --locked --all-groups ruff check \
  migration/site_build migration/site002v/validate.py migration/site003 \
  plugins/site_metadata.py
```

`validate` creates a separate locked environment under a temporary work root,
proves the installed reader and PEP 610 provenance from that environment, then
runs two clean production-intent Pelican builds. It requires exactly 35
Markdown and 11 notebook articles, all 11 notebook routes in `notebooks.tsv`,
the classic `cell`/`input_area` class contract, representative committed output
modes, and one top-level `html`/`body` document per published page.

The 11 historical notebooks do not contain a committed error output. The
separate `fixtures/representative-outputs.ipynb` positive fixture is outside
`content/` and therefore does not change the 46/11 corpus; it carries committed
error and rich-HTML outputs and gates `output_error`, `output_html`, `cell`, and
`input_area` tokens plus the absence of nested documents.

The build subprocess is instrumented to fail on kernel starts, calls to
`NotebookClient.execute`, or IPv4/IPv6 connection attempts. The validator also
compares every content-source hash and the Git status before and after both
builds.

Seven negative cases use isolated fixture copies under the temporary work root;
they never edit `content/`:

- missing expected source;
- missing expected route;
- missing adjacent `.nbdata`;
- missing required `Title` metadata;
- malformed notebook JSON.
- unknown SITE-003 lifecycle status;
- invalid SITE-003 language.

Every case must exit non-zero with its source path, reader stage, stable error
category, and cause type.

## SITE-003 metadata resolution

SITE-003 resolves the accepted PLUGIN-003 metadata observations while reusing
this validator:

- route-inventory versus reader notebook title mismatches: 8 to 0;
- absent reader language: 11 to 0;
- rendered language versus target mismatches: 1 to 0.

The frozen BASE-001 metadata file is not edited. The validator derives a
temporary manifest-authoritative title overlay and requires exactly 28 legacy
page-title updates, including the 8 notebook corrections, before running the
existing publication gate.

The remaining accepted accessibility observations are unchanged:

- nbconvert emits 57 generated fallback image alts across nine sources;
- two authored image alts are empty.

The independent publication gate counts all 57 fallback alts in generated HTML.
Pelican's console log may deduplicate identical nbconvert records; its emitted
ledger is gated separately for deterministic counts and rejects every warning
type outside the two accepted alt categories.

Accessibility remediation and human original-zoom review belong to later
theme/accessibility work. No warning outside this exact ledger is accepted.

The former vendored reader is preserved only under
`migration/site002v/archive/legacy-ipynb-reader/`; it is outside active
`PLUGIN_PATHS` and must not be restored on validation failure.

## Pre-cutover parity boundary

The BASE-001 checker implementation and its six negative/positive unit tests
remain green. Running the complete frozen production checker against this
source-branch artifact still reports its known pre-cutover production/theme/feed
differences. SITE-002V and SITE-003 do not weaken that checker or treat the
source branch as deployable; later convergence tasks own those differences.

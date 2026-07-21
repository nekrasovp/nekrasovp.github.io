# SITE-001 validation record

Date: 2026-07-21

Repository: `nekrasovp/nekrasovp.github.io`

Base: `master` at `9cb14db010579f174e0c1897ba95183a2ea16c68`

Production impact: none; no deploy, Pages, DNS, content, or theme mutation

## Supported environment and lock

Selected production interpreter: CPython 3.12, constrained to
`>=3.12,<3.13`. Validation used Python 3.12.13 and uv 0.11.28.

Direct locked runtime versions:

| Package | Version |
| --- | --- |
| beautifulsoup4 | 4.15.0 |
| feedgenerator | 2.2.1 |
| IPython | 9.15.0 |
| Jinja2 | 3.1.6 |
| Markdown | 3.10.2 |
| nbconvert | 7.17.1 |
| Pelican | 4.12.0 |
| Pillow | 12.3.0 |
| Pygments | 2.19.2 |
| six | 1.17.0 |
| Traitlets | 5.15.1 |

Development group: ghp-import 2.1.0, Invoke 3.0.3.

Test group: pytest 9.1.1.

Complete transitive resolution: 70 packages in `uv.lock`.

Clean-environment proof:

```text
UV_PROJECT_ENVIRONMENT=/tmp/site001-clean-env.EFw5wY/venv uv sync --locked --all-groups
Using CPython 3.12.13
Resolved 70 packages
Installed 65 packages
pelican=4.12.0 markdown=3.10.2 nbconvert=7.17.1 pillow=12.3.0
exit 0
```

`uv lock --check` also returned 0. The temporary path is evidence only and is
not referenced by the repository or commands.

## Markdown smoke reproducibility

Two independent clean output directories were built with warnings fatal:

```sh
uv run --locked python migration/site_build/scripts/build.py \
  build markdown-smoke --output .tmp/site001-smoke-a
uv run --locked python migration/site_build/scripts/build.py \
  build markdown-smoke --output .tmp/site001-smoke-b
uv run --locked python migration/site_build/scripts/compare_route_sets.py \
  .tmp/site001-smoke-a .tmp/site001-smoke-b
```

Each build processed 35 Markdown articles and two pages with exit 0 and no
warning/error. Route comparison result:

```text
route sets match: count=103 sha256=2c9e0e5c706eabe99f0789ddeddba1caacc9ce70913f4b78f0ec4685be83b2dc
```

## Failure propagation

A temporary copy of the real theme received an invalid Jinja tag. The verifier
then invoked the repository wrapper:

```sh
uv run --locked python migration/site_build/scripts/verify_template_failure.py
```

Result:

```text
template failure propagated: child_exit=1 verifier_exit=0
```

The unmodified full production configuration was also invoked through the
wrapper:

```sh
uv run --locked python migration/site_build/scripts/build.py \
  build production --output .tmp/site001-production
```

It returned 1 at the archived reader's
`jinja2.exceptions.TemplateNotFound: basic`. A diagnostic direct Pelican run
before enabling fatal errors logged conversion errors for all 11 notebooks but
returned 0. The wrapper therefore sets `--fatal errors` for full builds and
`--fatal warnings` for the Markdown smoke; an incomplete full build cannot be
mistaken for green.

## BASE-001 completeness boundary

The BASE-001 checker was run against the green Markdown-only output:

```sh
python3 migration/production_parity/scripts/check_generated_baseline.py \
  .tmp/site001-smoke-a
```

It returned 1. BASE-001 records 11 notebook routes, the checkout contains 11
`.ipynb` sources, and the checker emitted exactly 11 `missing notebook article`
errors. This is the required visible boundary: SITE-001's smoke mode proves the
modern Markdown environment, but it is not a production-completeness pass.
PLUGIN-002 owns reader modernization and SITE-002 owns integration of the
PLUGIN-005 public release.

## Local serve and tests

```text
wrapper serve markdown-smoke --output .tmp/site001-serve --port 8765
GET / -> HTTP 200
```

```text
uv run --locked --group test pytest -q
5 passed
```

## Plugin inventory and deviations

The retained/replacement decisions and dependency rationale are recorded in
`BUILDING.md`. No vendored plugin was deleted or edited. `ipynb.markup` is
retained only to reproduce the full-build failure and remains selected for
future replacement by the PLUGIN-005 release.

Deviations from the initial assumption: none for Python (3.12 passed). The
important discovered behavior is Pelican's zero exit after logged reader errors
without `--fatal`; the wrapper closes that false-green path. No old Python,
nbconvert 5, notebook execution, content change, production publish, or
completeness bypass was introduced.

Follow-ups: PLUGIN-001 through PLUGIN-005, then SITE-002. No follow-up was
started by this task.

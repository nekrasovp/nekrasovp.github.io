# Reproducible Pelican build

SITE-001 defines the build environment without changing site content, the theme,
GitHub Pages settings, or the production source. It intentionally does not fix
the archived notebook reader.

## Supported environment

Production builds use CPython 3.12 (`.python-version`,
`requires-python = ">=3.12,<3.13"`). Pelican 4.12 supports Python 3.11 and newer
and explicitly classifies Python 3.12 as supported; nbconvert 7.17.1 supports
Python 3.9 and newer. CPython 3.12 was selected because a clean lock, exact sync,
Markdown build, plugin load, and failure-path tests all pass on 3.12.13. No
compatibility pin to an obsolete Python or nbconvert release is used.

The dependency authorities are `pyproject.toml` and `uv.lock`. Runtime packages
are in `[project.dependencies]`; legacy publishing/developer helpers are in the
`dev` group; test tooling is in the `test` group. Every direct dependency is
exactly pinned and the lock fixes the complete transitive graph. The previous
unpinned `requirements.txt` has been removed.

Runtime dependencies include Pelican, Markdown, feedgenerator, Pillow, and the
temporary notebook-reader imports (IPython, nbconvert, Jinja2, Pygments,
Traitlets, Beautiful Soup, and six). `networkx` and `pydot` were removed from the
site-build environment: they occur only in notebook content/output and notebook
code is never executed during publication. `ghp-import` and Invoke remain in the
`dev` group for compatibility with legacy local helpers; pytest is isolated in
the `test` group.

Official compatibility references:

- <https://docs.getpelican.com/en/stable/install.html>
- <https://pypi.org/project/pelican/>
- <https://pypi.org/project/nbconvert/>
- <https://docs.astral.sh/uv/concepts/projects/sync/>

## Install and verify the lock

Install uv separately, then run:

```sh
uv sync --locked --all-groups
uv lock --check
```

`--locked` refuses to update a stale lock. `--all-groups` is the explicit
developer/test environment; ordinary build commands use runtime dependencies
only because uv default groups are empty.

## Build commands

The wrapper always receives an explicit output directory, asks Pelican to clean
it before building, and returns non-zero for Pelican errors. Relative output is
resolved from the checkout and must be under `.tmp/` or `output/`. An absolute
temporary directory may be passed explicitly. Broad or source paths are
rejected. Absolute output outside the checkout must be below a system
temporary-directory root; the temporary roots themselves are rejected.

Clean Markdown-only smoke build (the green SITE-001 diagnostic path):

```sh
uv run --locked python migration/site_build/scripts/build.py \
  build markdown-smoke --output .tmp/markdown-smoke
```

Local serve of that diagnostic build:

```sh
uv run --locked python migration/site_build/scripts/build.py \
  serve markdown-smoke --output .tmp/serve --port 8000
```

Full production build (expected to be red until PLUGIN-002 and SITE-002):

```sh
uv run --locked python migration/site_build/scripts/build.py \
  build production --output .tmp/production
```

The production command has no publish/deploy side effect. With the current
archived reader it exits non-zero at nbconvert's missing `basic` template. Do
not invoke Pelican directly for the full build: Pelican otherwise logs notebook
conversion errors but can exit zero after omitting those articles.

Equivalent convenience targets are `make smoke`, `make serve`, and
`make publish`. Despite its historical name, `make publish` only runs the
production build and does not push or deploy anything.

## Plugin inventory

| Plugin | SITE-001 decision | Rationale and follow-up |
| --- | --- | --- |
| `i18n_subsites` | Retained vendored | Loaded in the 35-article Markdown smoke build. Replacing it would change multilingual behavior and is not required for build reproducibility. Its direct `six` dependency is pinned. |
| `related_posts` | Retained vendored | Loaded in the smoke build and has no dependency beyond Pelican/Python. Replacement is deferred to a task that can compare rendered behavior. |
| `tag_cloud` | Retained vendored | Loaded in the smoke build; current theme consumes its context. Replacement is deferred to a behavior-preserving task. |
| `ipynb.markup` | Temporarily retained for diagnostics; selected target is replacement | Excluded only from `markdown-smoke`. The full production configuration still loads it and fails honestly against current nbconvert. PLUGIN-001 through PLUGIN-005 own the public successor; SITE-002 owns pinning that release and removing the archived reader. |

No vendored plugin is deleted or modified by SITE-001.

## SITE-001 validation

```sh
uv run --locked --group test pytest -q
uv run --locked python migration/site_build/scripts/build.py \
  build markdown-smoke --output .tmp/smoke-a
uv run --locked python migration/site_build/scripts/build.py \
  build markdown-smoke --output .tmp/smoke-b
uv run --locked python migration/site_build/scripts/compare_route_sets.py \
  .tmp/smoke-a .tmp/smoke-b
uv run --locked python migration/site_build/scripts/verify_template_failure.py
python3 migration/production_parity/scripts/check_generated_baseline.py \
  .tmp/smoke-a
```

The final BASE-001 command must remain red: the diagnostic output deliberately
omits all 11 notebook articles. This is not a production completeness bypass.
The exact SITE-001 run record is in
`migration/site_build/evidence/SITE-001-validation.md`.

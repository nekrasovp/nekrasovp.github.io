# Reproducible Pelican build (SITE-001)

SITE-001 establishes a reproducible modern build environment without changing
site content, the theme, public URLs, production hosting, or publication state.
The old unbounded `requirements.txt` has been replaced by `pyproject.toml` and
the committed `uv.lock`.

## Runtime baseline and locked versions

Python 3.12 is the production baseline. It is a maintained modern runtime, it
is available to `uv` without a compatibility exception, and it resolves and
runs the current Markdown site plus all SITE-001 tests. `requires-python` is
intentionally bounded to `>=3.12,<3.13`; changing the production runtime is a
separate reviewed decision, not an implicit resolver upgrade.

The lock generated on Python 3.12.13 contains these direct runtime tools and
compatibility dependencies:

| Dependency | Locked version | Why it is explicit |
| --- | ---: | --- |
| Pelican | 4.12.0 | Static-site generator |
| Markdown | 3.10.2 | Markdown reader used by all 35 current Markdown articles |
| nbconvert | 7.17.1 | Modern notebook conversion baseline; exposes the legacy reader blocker |
| Pillow | 12.3.0 | Pelican image-processing runtime |
| feedgenerator | 2.2.1 | Atom feed generation used by `publishconf.py` |
| beautifulsoup4 | 4.15.0 | Imported by the vendored notebook reader |
| IPython | 9.15.0 | Imported by the vendored notebook reader |
| six | 1.17.0 | Imported by the vendored site plugins |

The separate `dev` group locks Ruff 0.15.22. The separate `test` group locks
pytest 8.4.2. Transitive dependencies are fully recorded in `uv.lock`.

## Canonical commands

Run all commands from the repository root:

```sh
uv sync --locked --all-groups
./scripts/site markdown
./scripts/site build
./scripts/site serve --port 8000
./scripts/site test
uv run --locked --all-groups ruff check migration/site_build
```

`./scripts/site markdown` is the clean Markdown-only smoke build. It always
uses `build/markdown`, deletes that explicit directory before generation, and
treats every Pelican warning as fatal.

`./scripts/site build` is the full production-settings build. It always uses
`build/production` and passes `--fatal errors`; Pelican must not return a false
green after logging a reader error and silently omitting notebook routes.

`./scripts/site serve` serves the Markdown-only configuration from the explicit
`build/local` directory with autoreload. The notebook reader remains blocked,
so the local working server deliberately uses the same green Markdown scope as
the smoke build.

All build commands pass both input and output paths explicitly. Neither the
wrapper nor `pelicanconf.py` uses the former implicit absolute `/output` path.
Optional `--output` and `--config` values exist for isolated acceptance tests;
the wrapper rejects `/` and the repository root as unsafe outputs and preserves
the child command's non-zero status.

## Plugin inventory

| Plugin | SITE-001 disposition | Evidence and boundary |
| --- | --- | --- |
| `i18n_subsites` | Retained; not replaced or removed | Loaded from the existing vendored `plugins/` tree in both clean Markdown builds. The theme still contains translation templates and catalogs. |
| `related_posts` | Retained; not replaced or removed | Loaded in both clean Markdown builds; the current theme still renders `includes/related-posts.html`. |
| `tag_cloud` | Retained; not replaced or removed | Loaded in both clean Markdown builds; the current sidebar still renders the tag cloud. |
| `ipynb.markup` | Temporarily retained in production; not replaced or removed | Production still declares `MARKUP = ('md', 'ipynb')` and the vendored reader. It is excluded only from the Markdown smoke/serve configuration so its known incompatibility cannot hide Markdown build health. Its successor belongs to `PLUGIN-001`; immutable site integration belongs to `SITE-002`. |

No plugin migration is performed by SITE-001.

## Notebook blocker and BASE-001 completeness

The repository contains 11 `.ipynb` articles and 11 adjacent `.nbdata` files.
With the locked modern environment, the vendored reader reaches
`plugins/ipynb/core.py`, asks nbconvert 7.17.1 for the removed legacy Jinja
template `basic`, and raises `jinja2.exceptions.TemplateNotFound: basic`.

This failure is expected and must remain visible. Without `--fatal errors`,
Pelican 4.12.0 logs the error for all 11 notebooks, emits only the 35 Markdown
articles, and incorrectly exits zero. The wrapper converts that dangerous
behavior into an immediate native Pelican non-zero result; it does not pin
nbconvert 5, downgrade Python, skip production notebooks, or change their
routes. The BASE-001 notebook inputs and production configuration remain
present, so an incomplete production artifact cannot be accepted as green.

Fixing or replacing the reader is explicitly outside SITE-001. That work starts
with `PLUGIN-001`, followed later by the separately reviewed `SITE-002`
integration. The production parity checker is not run against the intentionally
incomplete output.

## SITE-001 validation record

Validated on 2026-07-21 from `origin/master` commit
`9cb14db010579f174e0c1897ba95183a2ea16c68`:

| Command / gate | Result |
| --- | --- |
| `uv sync --locked --all-groups` | Exit 0; Python 3.12.13; 69 packages resolved from the committed lock |
| first `./scripts/site markdown` | Exit 0; 35 articles, 2 pages, 101 HTML routes |
| second clean `./scripts/site markdown` | Exit 0; same 101-route set |
| sorted route-set SHA-256, both runs | `abed01049c982834ee4d1f26812e4b0f5ff304fae093bffd9ce3a3d1e7f0e0db` |
| deterministic warning fixture with `--fatal warnings` | Exit 1; `SITE-001 deterministic warning fixture` |
| missing-theme fixture | Exit 1; `ValueError: Could not find the theme` |
| `./scripts/site build` | Expected exit 1; vendored reader / nbconvert traceback ends in `TemplateNotFound: basic` |
| `./scripts/site test` | Exit 0; 7 passed |
| `uv run --locked --all-groups ruff check migration/site_build` | Exit 0 |
| `./scripts/site serve --port 8765`, then HTTP GET `/` | HTTP 200; stopped manually after verification |

The acceptance fixtures are under `migration/site_build/tests/fixtures/`. They
exist only to prove warning and template-error propagation and are never used by
normal or production configuration.

SITE-001 does not invoke `upload.sh`, `pre-push`, `ghp-import`, or any Pages,
DNS, `gh-pages`, publish, or merge operation. Content, theme files,
`publishconf.py`, public URLs, and live production remain unchanged.

# Immutable theme integration (SITE-006)

The active Pelican theme is the final immutable Git source for SITE-006:
`pelican-engineering-theme` 0.1.0 installed from the exact merged Git commit
`027a170ac6c8288347de5353569a089c526afae2`. The full VCS requirement is locked
in `uv.lock`; public package release remains deferred.

`pelicanconf.py` obtains `THEME` only from the distribution's public
`get_theme_path()` API. Site-owned templates live under `templates/`, extend
the installed `!theme/...` namespace, and retain the documented 18-public-block
override boundary. The inactive vendored `theme/` directory was deleted only
after the pre-delete cumulative test, Ruff, production-build, and two-build
validation gates were GREEN.

The shared `./scripts/site validate` gate creates an external locked
environment, records PEP 610 `direct_url.json`, distribution version,
`site-packages` paths, lock source and commit, then compares normalized route,
metadata, asset, runtime-reference, and theme-identity evidence across two
clean full-corpus builds. SITE-003 continues to require all 46 legacy routes,
35 Markdown sources, 11 notebooks, lifecycle counts `9/13/16/8`, language
counts `42 en / 4 ru`, notices, labels, canonicals, and no-execution behavior.

The SITE-003 rendered validator now follows the immutable theme's approved em-dash
title separator and public semantic notice/article classes. It no longer
depends on the legacy `.article-language`, `.content-notice`, or
`article[data-content-status]` presentation selectors.

## Exact theme update procedure

Exercise and review future updates in an isolated clone and branch:

1. replace only the exact full theme commit in the `pyproject.toml` VCS
   requirement;
2. run
   `uv lock --upgrade-package pelican-engineering-theme`;
3. require the diff to contain only that requirement and the corresponding
   theme source and metadata in `uv.lock`;
4. run locked installation and the complete cumulative validation gates before
   proposing the update.

Floating branches or tags, local paths, copied package trees, and unverified
archives remain forbidden.

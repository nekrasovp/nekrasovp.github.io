# Immutable theme candidate integration (SITE-006V)

The active Pelican theme is the unpublished `pelican-engineering-theme` 0.1.0
candidate installed from the exact merged Git commit
`027a170ac6c8288347de5353569a089c526afae2`. The full VCS requirement is locked
in `uv.lock`; this is validation evidence, not a public release claim.

`pelicanconf.py` obtains `THEME` only from the distribution's public
`get_theme_path()` API. Site-owned templates live under `templates/`, extend
the installed `!theme/...` namespace, and are restricted to the documented 18
public blocks. The historical vendored `theme/` directory remains in the tree
for rollback but is neither configured nor copied into generated output.

The shared `./scripts/site validate` gate creates an external locked
environment, records PEP 610 `direct_url.json`, distribution version,
`site-packages` paths, lock source and commit, then compares normalized route,
metadata, asset, runtime-reference, and theme-identity evidence across two
clean full-corpus builds. SITE-003 continues to require all 46 legacy routes,
35 Markdown sources, 11 notebooks, lifecycle counts `9/13/16/8`, language
counts `42 en / 4 ru`, notices, labels, canonicals, and no-execution behavior.

The SITE-003 rendered validator now follows the candidate's approved em-dash
title separator and public semantic notice/article classes. It no longer
depends on the legacy `.article-language`, `.content-notice`, or
`article[data-content-status]` presentation selectors.

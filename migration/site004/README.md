# SITE-004 durable entry pages

This directory freezes the source-owner and rendered semantic contract for the
eight outputs introduced by SITE-004:

- `/`;
- `/ru/`;
- `/work/`;
- `/writing/`;
- `/about/`;
- `/404.html`;
- `/pages/about.html`;
- `/pages/services.html`.

`pages.json` binds those outputs to `master@2f91ab0...`, the unchanged
production copy/metadata source `gh-pages@5c24ba2...`, and the immutable
validation-only theme candidate `027a170...`. The production HTML hashes are
evidence inputs, not byte-parity requirements. The validator instead gates the
source owner, Page metadata, normalized approved copy, headings, links,
canonical/hreflang, social metadata, Person JSON-LD, 404 exclusions, and exact
redirect intent.

Run the focused source and rendered checks from the repository root:

```console
uv run --locked --all-groups python migration/site004/validate.py
./scripts/site build --output build/production
uv run --locked --all-groups python migration/site004/validate.py \
  --output-root build/production
```

The rendered link gate resolves SITE-004 links against the complete generated
artifact and requires all six SITE-005 routes plus both legacy technical-debt
articles. It does not turn the eight older BASE-001 broken-link observations
owned by historical article content into SITE-004 edits.

Browser evidence is technical executor evidence, not human visual acceptance.

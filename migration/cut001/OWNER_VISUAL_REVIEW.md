# CUT-001 owner visual review guide

This guide is the separate human visual-acceptance gate. The automated package
proves deterministic captures, layout contracts, accessibility scans, route and
content parity, and theme behavior. It does not make the owner's aesthetic or
product decision.

Use the `cut001-evidence-<exact-head>` artifact. For every canonical case below,
compare the three screenshots at both `1440x1000` desktop and `390x844` mobile:
legacy production reference, preview light, and preview dark.

| Case | Route | Language / page type |
| --- | --- | --- |
| `home_en` | `/` | English home |
| `home_ru` | `/ru/` | Russian home |
| `work` | `/work/` | English work |
| `about` | `/about/` | English about |
| `writing` | `/writing/` | English writing/archive |
| `modern_essay` | `/ai-native-sdlc-engineering-accountability.html` | modern English essay |
| `legacy_markdown_en` | `/python-gil.html` | legacy English Markdown |
| `legacy_markdown_ru` | `/technical-debt-examples.html` | legacy Russian Markdown |
| `notebook_en` | `/number-sequences.html` | English notebook |
| `notebook_ru` | `/mkrf-spb-geo-data.html` | Russian notebook and archived case |
| `archive_en` | `/arbitrage.html` | archived English content |
| `deprecated_en` | `/fixing-caching-sha2-password.html` | deprecated English content |
| `not_found_en` | `/404.html` | static 404 |

Two required matrix entries are canonical-equivalent rather than fabricated
duplicate captures:

- `archive_deprecated_ru` references `notebook_ru`; the Russian notebook is also
  the Russian archived-notebook case.
- `404_ru_acceptable` references `not_found_en`; the retained static 404 is the
  language-neutral acceptable Russian case.

Review:

1. hierarchy, typography, spacing, navigation, code/notebook overflow, images,
   archive/deprecation callouts, focus visibility, and light/dark contrast;
2. English and Russian labels and reading order;
3. desktop and mobile layout for every row;
4. the theme toggle and persistence on representative normal, notebook, and 404
   pages;
5. every difference from legacy production as an intentional preview change,
   not an accidental omission.

The agent-managed browser spot check used the immutable artifact with a
read-only local-origin rewrite solely so canonical absolute assets resolved from
the artifact. It confirmed:

- English home: expected heading; exactly one visible toggle; light to dark;
- Russian home: `lang=ru`, expected heading, visible persisted dark toggle;
- English notebook: expected title, one notebook region, 23 rendered images,
  visible persisted dark toggle;
- 404: expected heading, homepage/writing recovery links, visible toggle;
- current live production home: expected legacy semantic content for comparison.

The automated exact-origin harness, not that local rewrite, is authoritative for
network isolation, 78 screenshots, 52 axe scans, and the 147-page toggle sweep.

Record exactly one owner decision:

- **Accept CUT-001 visual evidence** — visual gate passes; this does not make the
  PR ready or authorize merge/deployment.
- **Accept with named differences** — list every accepted difference by
  case, viewport, and theme.
- **Request rework** — list each rejected case, viewport, theme, and expected
  correction.

After visual acceptance, `ready`, `merge`, outreach, and CUT-002 remain separate
owner-authorized gates. None is implied by this review.

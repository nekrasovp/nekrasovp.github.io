# BASE-001 validation evidence

Production remained unchanged throughout this task. Validation used a clean clone, branch `agent/base001-production-parity`, and a detached worktree of published commit `5c24ba21ec8b442e4b5280a47c85fab61165f8ce`.

## Live and repository state

- GitHub default branch: `master` at `a19169d1507278e845cd4df943d1f92991eddcd1`.
- GitHub Pages source: `gh-pages:/` at `5c24ba21ec8b442e4b5280a47c85fab61165f8ce`.
- Pages state: `built`, legacy build type, custom domain `nekrasovp.ru`, verified domain, HTTPS enforced.
- Committed collection window: `2026-07-21T20:18:41Z` to `2026-07-21T20:20:28Z`.

## Commands and results

```text
python3 migration/production_parity/scripts/collect_production_baseline.py --workers 24
BASE-001 collection complete: 300 route records, 58 sitemap routes, 46 legacy routes, 2 feeds, 23 asset references

python3 migration/production_parity/scripts/check_generated_baseline.py /Users/admin/Documents/Codex/2026-07-21/nekrasovp-base001/work/gh-pages-snapshot
BASE-001 parity check passed

python3 -m unittest -v migration/production_parity/tests/test_baseline_checker.py
Ran 6 tests
OK

python3 migration/production_parity/scripts/collect_production_baseline.py --workers 24 --baseline-dir /Users/admin/Documents/Codex/2026-07-21/nekrasovp-base001/work/base001-determinism-alias-4y8GEc
BASE-001 collection complete: 300 route records, 58 sitemap routes, 46 legacy routes, 2 feeds, 23 asset references

python3 migration/production_parity/scripts/compare_baselines.py migration/production_parity/baseline /Users/admin/Documents/Codex/2026-07-21/nekrasovp-base001/work/base001-determinism-alias-4y8GEc
BASE-001 collections are deterministic after excluding collection timestamps
```

The second independent collection ran from `2026-07-21T20:21:22Z` through `2026-07-21T20:24:45Z`. All non-timestamp JSON values matched.

## Required negative cases

The unittest suite constructs a complete generated fixture, runs the checker CLI, mutates one requirement at a time, and asserts exit code 1 for:

- missing non-notebook route;
- missing notebook article;
- missing Atom feed entry;
- wrong canonical URL;
- missing HTML `lang` attribute.

The unmodified fixture returns exit code 0. The same checker also passed against the real detached `gh-pages` artifact.

## Deviations and follow-ups

- The plan's branch assumptions were current; no branch/source adaptation was required.
- Production exposes the intentional meta-refresh redirects and legacy broken references documented in `README.md`; the baseline records them instead of repairing content.
- No production content, theme/build dependency, DNS, Pages setting, or publication source changed.
- No later SITE, THEME, or PLUGIN task was started.
- Cleanup, indexability, content repair, and build modernization remain follow-ups for their own explicitly selected tasks.

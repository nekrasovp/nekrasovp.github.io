# SITE-001 implementation

This directory contains the bounded SITE-001 build infrastructure:

- `markdown_smokeconf.py`: production-shaped Markdown-only diagnostic config;
- `scripts/build.py`: explicit-output, clean, failure-propagating wrapper;
- `scripts/compare_route_sets.py`: two-build route-set comparator;
- `scripts/verify_template_failure.py`: real Jinja failure-path verifier;
- `tests/`: wrapper and comparison tests;
- `evidence/`: exact validation record.

User-facing setup, commands, dependency rationale, and the plugin inventory are
documented in the repository-root `BUILDING.md`.

# Released notebook reader integration (SITE-002)

SITE-002 replaces the accepted validation-only Git dependency with the public,
immutable `pelican-ipynb-reader==0.1.0` release while preserving every SITE-002V
functional, no-execution, route, metadata, warning, and fragment contract.

## Branch and review boundary

The implementation branch is created from exact accepted CUT-001 preview head
`95c3f02ad6fc3589798ba73dc19e39045941235e`. Its draft pull request targets
`agent/cut-001-production-preview`, the unchanged head branch of PR #67.
Therefore the review diff contains only SITE-002 changes, while PR #67 remains
open, draft, unmerged, and byte-for-byte unchanged. The OPS-001 workflow runs
for every pull request, including this stacked base.

## Immutable release identity

- distribution: `pelican-ipynb-reader==0.1.0`
- canonical import: `pelican.plugins.ipynb_reader`
- provenance repository: <https://github.com/nekrasovp/pelican-jupyter>
- release: <https://github.com/nekrasovp/pelican-jupyter/releases/tag/v0.1.0>
- release source: `01b298d1a6b714755d7d9170538e4e7994038b8b`
- wheel SHA-256:
  `ec5212c0f5c414743032c3b2880904af898e726e5cb5ab314345634c8bb68153`
- sdist SHA-256:
  `c456eb564973d7241eb5ea01aed19662f20fc18c7bef0380d81a5d1b8fc87fa4`
- public index: <https://pypi.org/project/pelican-ipynb-reader/0.1.0/>
- replaced validation pin:
  `pelican-jupyter@137e1eb0ea620f1b15fff0ba81725eea23de1b7a`

`uv.lock` is the supported integrity mechanism. It must resolve the registry
release and record exactly the wheel and sdist hashes above. VCS, local path,
candidate artifact, and source-tree import fallbacks are rejected.

## Equivalence gate

Run the complete cumulative validator twice-built from a clean external
environment. Compare its normalized publication SHA-256, routes, metadata,
fragment modes, warning ledger, and output fingerprints with the accepted
SITE-002V/CUT-001 report and artifact. Distribution identity fields are the
only expected evidence difference; any rendered difference requires a new
owner visual decision.

The inactive archived vendored reader may be removed only after the released
artifact has passed this parity gate. No notebook execution, content change,
deployment, Pages/DNS mutation, or PR #67 state change is part of SITE-002.

The machine-readable release, branch, RED/GREEN, and output-difference record
is in `migration/site002/evidence.json`.

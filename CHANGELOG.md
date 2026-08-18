# Changelog

All notable changes to PatchSignal are documented here.

## [Unreleased]

### Added

- Test suite covering previously unproven behavior: CLI error paths and exit-code contract, policy loading boundaries (missing, malformed and invalid-table configs), risk-rule thresholds including the three-export `PUBLIC_API_SURFACE` boundary, and Git adapter defensive branches.

### Fixed

- `CI_CONFIG_CHANGED` now fires only for paths inside `.github/workflows/` instead of any file ending in `.yml` or `.yaml`, removing false positives for unrelated YAML documents.

## [0.3.0] - 2026-08-18

### Added

- 16 regression and boundary tests covering CLI failures, TOML validation, risk-rule thresholds, Git defensive branches, and empty repositories.
- Corrected `CI_CONFIG_CHANGED` so ordinary YAML documentation files do not force a full run.
- Raised effective project coverage to 96.91% on the expanded suite.

### Fixed

- Synchronized package metadata with the current release line after the merged maintainer PR.

## [0.2.1] - 2026-08-17

### Added

- Bandit static security scanning in the development toolchain and CI.
- Mypy static type checking as a required CI gate.

### Fixed

- Corrected the typed visitor contract for asynchronous Python functions.
- Documented the bounded Git subprocess exception used by the local adapter.

## [0.2.0] - 2026-08-17

### Added

- Optional `.patchsignal.toml` policies for full-run paths, mandatory tests, and ignored generated/vendor paths.
- Multi-file impact evaluation instead of using only the first changed path.
- Explicit `targeted` versus `full` test execution recommendations.
- Mandatory tests are promoted to score 100 in reports even when they were already discovered by impact analysis.
- Docker ignore rules and expanded policy documentation.

### Fixed

- Transitive impact selection now considers every changed file in a diff.

## [0.1.0] - 2026-08-16

### Added

- Local-first Git working-tree and range analysis.
- Syntax-only Python AST and TypeScript/JavaScript declaration indexing.
- Explainable impact items, candidate tests, deterministic risk signals, and graph counters.
- Markdown, JSON, and SARIF 2.1.0 renderers.
- Typed CLI exit codes suitable for CI gates.
- Documentation, contribution policy, security policy, fixtures, and automated quality checks.

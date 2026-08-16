# PatchSignal

> **Explainable change-impact analysis for safer code review and CI.**

[![CI](https://github.com/Alqudimi/PatchSignal/actions/workflows/ci.yml/badge.svg)](https://github.com/Alqudimi/PatchSignal/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

PatchSignal is a local-first Python CLI that explains what a Git change may affect. It connects a diff to symbols, imports, candidate tests, and deterministic risk signals, then emits Markdown, JSON, or SARIF for humans and CI systems.

## Why it exists

A changed line rarely matters only where it appears. Reviewers still need to discover affected symbols, likely tests, public API exposure, workflow changes, and security-sensitive paths by hand. Static analyzers find classes of defects, while PatchSignal answers a different question: **what evidence should we inspect or run because of this patch?**

PatchSignal is deliberately deterministic and offline-friendly. It does not upload source code, require an LLM, or claim that its graph is complete. Every result carries a reason and a bounded confidence score so a maintainer can challenge the recommendation.

## What it does

| Capability | Current behavior |
|---|---|
| Change discovery | Reads working-tree changes or a `base...head` Git range without shell interpolation. |
| Symbol indexing | Extracts Python symbols with `ast` and common TypeScript/JavaScript declarations. |
| Dependency evidence | Records imports and uses filename/module relationships for candidate impact. |
| Test selection | Finds nearby test/spec files and explains why they are candidates. |
| Risk gates | Flags workflow changes, security-sensitive paths, dependency/config changes, and public API surface changes. |
| Reports | Markdown for review, JSON for automation, and SARIF 2.1.0 for code-scanning consumers. |
| Extensibility | Parser and renderer boundaries are isolated so more languages and evidence providers can be added. |

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
patchsignal --repo .
```

Analyze a pull-request range:

```bash
patchsignal --repo . --base origin/main --head HEAD --format markdown
patchsignal --repo . --base origin/main --head HEAD --format sarif --output patchsignal.sarif
```

Use it as a CI gate:

```bash
patchsignal --base origin/main --head HEAD --fail-on high --format json > patchsignal.json
```

The command returns `0` when the configured threshold is not reached, `1` when it is reached, and `2` for an invalid repository or invocation.

## Architecture

```text
Git adapter → change set → language parsers → evidence graph
                                      ↓
                         impact + test candidates + risk rules
                                      ↓
                         Markdown / JSON / SARIF renderers
```

The core pipeline does not execute repository code. Parsers are syntax-only, adapters validate boundaries, and renderers consume typed domain models. See [`docs/architecture.md`](docs/architecture.md) for the decisions and trade-offs.

## Design principles

PatchSignal favors **explainability over false precision**, **local execution over source upload**, and **additive interfaces over breaking abstractions**. The graph is an evidence model, not a proof of semantic reachability. Consumers should use it to prioritize review and testing, not to skip required validation without judgment.

## Development

```bash
python -m pytest
ruff check .
python -m compileall -q src
```

The fixture-driven tests cover parser behavior, risk signals, rendering contracts, and exit-code monotonicity. Benchmarks and contribution expectations are documented in [`docs/development.md`](docs/development.md).

## Security

PatchSignal treats repository content as untrusted input. It never evaluates parsed code, invokes a shell for Git arguments, follows imports over the network, or embeds secrets in reports. Please report security issues privately according to [`SECURITY.md`](SECURITY.md).

## Roadmap

The next compatible extensions are a real path-aware dependency resolver, optional historical co-change evidence, language plugins for Go and Rust, and a GitHub Action wrapper. These are intentionally not required for the deterministic MVP.

## Contributing and license

Contributions are welcome. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), the architecture document, and an issue describing the evidence you intend to add. PatchSignal is released under the [MIT License](LICENSE).

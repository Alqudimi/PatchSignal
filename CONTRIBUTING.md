# Contributing to PatchSignal

Thank you for helping make change-impact analysis more useful and more trustworthy. Before opening a pull request, read [`docs/architecture.md`](docs/architecture.md) and make the smallest change that proves the intended behavior.

## Development loop

Create a virtual environment, install the development extras, run the unit suite, run Ruff, and inspect the generated Markdown and SARIF reports against the fixtures. New evidence rules must include a positive case, a non-match case, and an explanation that a reviewer can understand.

## Pull requests

Use a concise Conventional Commit-style title such as `feat: add Go symbol indexer` or `fix: handle renamed diff entries`. Describe the user-visible contract, security implications, test evidence, and any compatibility impact. Avoid bundling formatting-only changes with behavior changes.

## Scope and safety

PatchSignal must remain local-first and must not execute target repository code during analysis. New integrations must validate external data at the boundary, avoid shell interpolation, and document their privacy behavior. If a change intentionally weakens a signal, explain why in the pull request.

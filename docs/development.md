# Development Guide

PatchSignal targets Python 3.11 or newer and has no runtime dependency outside the standard library. The development extra installs Pytest, coverage, and Ruff. Use an isolated virtual environment and install the package in editable mode.

The smallest verification loop is `python -m pytest`, followed by `ruff check .` and `python -m compileall -q src`. For a report against a real branch, run `patchsignal --base origin/main --head HEAD --format markdown`. The JSON and SARIF forms are intended for scripts and CI annotations. Repository policies may be placed in `.patchsignal.toml`; `full_run_paths` forces a full-suite recommendation, `unskippable_tests` preserves critical tests in every candidate set, and `ignored_paths` excludes generated or vendored paths from indexing.

A change to a parser should add fixtures for valid syntax, malformed syntax, and a non-related file. A change to policy evaluation must test both matching and non-matching patterns, including the case where an already-related test is promoted to mandatory priority.
A new risk rule should document its false-positive boundary and test the rule threshold. Performance work must include a before/after measurement on a fixture repository; no speed claim should be made from intuition.

The MVP intentionally keeps the package dependency-free. A future plugin interface may introduce optional dependencies behind extras, but the default install must remain usable offline.

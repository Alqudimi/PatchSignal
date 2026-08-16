"""Command-line interface for PatchSignal."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from patchsignal.adapters.git import GitError, changed_files, changed_files_from_worktree
from patchsignal.analysis.engine import analyze
from patchsignal.output.renderers import render_json, render_markdown, render_sarif


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="patchsignal", description="Explainable change-impact analysis for Git repositories."
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository root (default: current directory).")
    parser.add_argument("--base", default=None, help="Git base revision; omit to inspect working-tree changes.")
    parser.add_argument("--head", default="HEAD", help="Git head revision when --base is supplied.")
    parser.add_argument("--format", choices=("markdown", "json", "sarif"), default="markdown")
    parser.add_argument("--output", type=Path, help="Write the report to a file instead of stdout.")
    parser.add_argument(
        "--fail-on",
        choices=("never", "medium", "high", "critical"),
        default="never",
        help="Exit non-zero at or above this risk level.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo.resolve()
    try:
        if args.base:
            files = changed_files(repo, args.base, args.head)
            base, head = args.base, args.head
        else:
            files = changed_files_from_worktree(repo)
            base = head = "working-tree"
        result = analyze(repo, [item.path for item in files], base, head)
        result.changed_files = files
        rendered = {"markdown": render_markdown, "json": render_json, "sarif": render_sarif}[args.format](result)
    except (GitError, OSError, ValueError) as exc:
        print(f"PatchSignal error: {exc}", file=sys.stderr)
        return 2
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return _risk_exit_code(result.max_risk.value, args.fail_on)


def _risk_exit_code(actual: str, threshold: str) -> int:
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3, "never": 99}
    return 1 if order[actual] >= order[threshold] else 0


if __name__ == "__main__":
    raise SystemExit(main())

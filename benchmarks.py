"""Tiny standard-library benchmark for local regression tracking."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from patchsignal.analysis.engine import analyze


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("--iterations", type=int, default=10)
    args = parser.parse_args()
    changed = [path.relative_to(args.repo).as_posix() for path in args.repo.rglob("*.py")][:3]
    start = time.perf_counter()
    for _ in range(args.iterations):
        analyze(args.repo, changed)
    elapsed = time.perf_counter() - start
    print(f"iterations={args.iterations} total_seconds={elapsed:.6f} avg_ms={elapsed / args.iterations * 1000:.3f}")


if __name__ == "__main__":
    main()

"""Git adapter. Commands are passed as argv lists and never through a shell."""

from __future__ import annotations

import subprocess  # nosec B404 - Git is invoked with a fixed executable and argv list.
from pathlib import Path

from patchsignal.models import ChangedFile


class GitError(RuntimeError):
    """Raised when the target path is not a usable Git repository."""


def _run(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(  # nosec - fixed Git executable, argv list, shell=False, and timeout.
            ["git", "-c", "color.ui=false", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitError(f"git command failed: {args[0]}") from exc
    return completed.stdout


def changed_files(repo: Path, base: str, head: str) -> list[ChangedFile]:
    output = _run(repo, "diff", "--numstat", "--diff-filter=ACMR", f"{base}...{head}")
    files: list[ChangedFile] = []
    for line in output.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        additions, deletions, path = parts
        files.append(
            ChangedFile(
                path=path,
                status="modified",
                additions=int(additions) if additions.isdigit() else 0,
                deletions=int(deletions) if deletions.isdigit() else 0,
            )
        )
    return files


def changed_files_from_worktree(repo: Path) -> list[ChangedFile]:
    output = _run(repo, "status", "--short")
    return [
        ChangedFile(path=line[3:], status=line[:2].strip() or "modified")
        for line in output.splitlines()
        if len(line) > 3
    ]

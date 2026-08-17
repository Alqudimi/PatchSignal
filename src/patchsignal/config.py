"""Validated, optional TOML configuration for repository-specific policies."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AnalysisConfig:
    full_run_paths: tuple[str, ...] = ()
    unskippable_tests: tuple[str, ...] = ()
    ignored_paths: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: Path | None) -> AnalysisConfig:
        if path is None:
            return cls()
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise ValueError(f"invalid PatchSignal config: {path}") from exc
        section = raw.get("patchsignal", raw)
        if not isinstance(section, dict):
            raise ValueError("PatchSignal config must contain a table")
        return cls(
            full_run_paths=_strings(section.get("full_run_paths", []), "full_run_paths"),
            unskippable_tests=_strings(section.get("unskippable_tests", []), "unskippable_tests"),
            ignored_paths=_strings(section.get("ignored_paths", []), "ignored_paths"),
        )


def _strings(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{name} must be a non-empty string array")
    return tuple(value)

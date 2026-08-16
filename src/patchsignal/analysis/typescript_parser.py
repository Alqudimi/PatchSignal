"""Dependency-light TypeScript parser for common module and declaration forms."""

from __future__ import annotations

import re
from pathlib import Path

from patchsignal.models import Relation, Symbol

_IMPORT = re.compile(r"(?:import|export)\s+(?:[^'\"]+?\s+from\s+)?['\"]([^'\"]+)['\"]")
_DECL = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(function|class|interface|type|const)\s+([A-Za-z_$][\w$]*)", re.MULTILINE
)


def parse_typescript_file(path: Path, root: Path) -> tuple[list[Symbol], list[Relation]]:
    source = path.read_text(encoding="utf-8")
    relative = path.relative_to(root).as_posix()
    symbols = [
        Symbol(
            name,
            relative,
            kind,
            source.count("\n", 0, match.start()) + 1,
            exported="export" in source[max(0, match.start() - 12) : match.start()],
        )
        for match in _DECL.finditer(source)
        for kind, name in [match.groups()]
    ]
    relations = [Relation(relative, target, "imports", relative) for target in _IMPORT.findall(source)]
    return symbols, relations

"""Deterministic change-impact analysis pipeline."""

from __future__ import annotations

from pathlib import Path

from patchsignal.analysis.python_parser import parse_python_file
from patchsignal.analysis.typescript_parser import parse_typescript_file
from patchsignal.models import AnalysisResult, ImpactItem, Relation, RiskLevel, RiskSignal, Symbol

_SUPPORTED = {".py", ".ts", ".tsx", ".js", ".jsx"}
_TEST_MARKERS = ("test", "spec")


def _parse_repository(root: Path) -> tuple[list[Symbol], list[Relation]]:
    symbols: list[Symbol] = []
    relations: list[Relation] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix not in _SUPPORTED:
            continue
        try:
            parsed = parse_python_file(path, root) if path.suffix == ".py" else parse_typescript_file(path, root)
        except (OSError, SyntaxError, UnicodeError):
            continue
        symbols.extend(parsed[0])
        relations.extend(parsed[1])
    return symbols, relations


def _module_stem(path: str) -> str:
    return Path(path).stem.lower().replace("index", "")


def _is_related(changed: str, candidate: str, relations: list[Relation]) -> bool:
    changed_stem = _module_stem(changed)
    candidate_stem = _module_stem(candidate)
    if changed_stem and changed_stem in candidate_stem or candidate_stem and candidate_stem in changed_stem:
        return True
    return any(
        relation.source == candidate and _module_stem(changed) in relation.target.lower() for relation in relations
    )


def analyze(
    root: Path, changed_paths: list[str], base: str = "working-tree", head: str = "working-tree"
) -> AnalysisResult:
    symbols, relations = _parse_repository(root)
    changed = set(changed_paths)
    impacted = [
        ImpactItem(
            symbol.path, f"symbol {symbol.qualified_name} is defined in a changed file", 90, (symbol.qualified_name,)
        )
        for symbol in symbols
        if symbol.path in changed
    ]
    candidate_paths = sorted(
        {
            symbol.path
            for symbol in symbols
            if symbol.path not in changed and _is_related(next(iter(changed), ""), symbol.path, relations)
        }
    )
    tests = sorted(
        {
            path
            for path in (root.rglob("*") if root.exists() else [])
            if path.is_file() and any(marker in path.name.lower() for marker in _TEST_MARKERS)
        }
    )
    candidate_tests = [
        ImpactItem(
            path.relative_to(root).as_posix(), "test filename is related to an impacted module", 80, (path.name,)
        )
        for path in tests
        if any(_is_related(changed_path, path.relative_to(root).as_posix(), relations) for changed_path in changed)
    ]
    signals = _risk_signals(root, changed_paths, symbols)
    return AnalysisResult(
        base=base,
        head=head,
        changed_files=[],
        impacted_symbols=impacted
        + [ImpactItem(path, "imports or naming indicate transitive impact", 60) for path in candidate_paths],
        candidate_tests=candidate_tests,
        risk_signals=signals,
        graph_nodes=len({symbol.path for symbol in symbols}),
        graph_edges=len(relations),
    )


def _risk_signals(root: Path, changed_paths: list[str], symbols: list[Symbol]) -> list[RiskSignal]:
    signals: list[RiskSignal] = []
    paths = tuple(sorted(changed_paths))
    if any(path.endswith((".yml", ".yaml", ".github/workflows")) or ".github/workflows/" in path for path in paths):
        signals.append(
            RiskSignal(
                "CI_CONFIG_CHANGED",
                "CI or workflow configuration changed; run the full validation suite.",
                RiskLevel.HIGH,
                paths,
            )
        )
    if any("auth" in path.lower() or "security" in path.lower() for path in paths):
        signals.append(
            RiskSignal(
                "SECURITY_SURFACE",
                "Security-sensitive path changed; require focused security review.",
                RiskLevel.HIGH,
                paths,
            )
        )
    if any(path.endswith((".toml", ".lock", ".json")) for path in paths):
        signals.append(
            RiskSignal("DEPENDENCY_OR_CONFIG", "Dependency or configuration metadata changed.", RiskLevel.MEDIUM, paths)
        )
    if sum(1 for symbol in symbols if symbol.path in paths and symbol.exported) >= 3:
        signals.append(
            RiskSignal(
                "PUBLIC_API_SURFACE",
                "Multiple exported symbols changed; review compatibility impact.",
                RiskLevel.MEDIUM,
                paths,
            )
        )
    if not signals:
        signals.append(
            RiskSignal(
                "LOCAL_CODE_CHANGE",
                "No elevated rule matched; inspect the impacted symbols and candidate tests.",
                RiskLevel.LOW,
                paths,
            )
        )
    return signals

"""Deterministic change-impact analysis pipeline."""

from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path

from patchsignal.analysis.python_parser import parse_python_file
from patchsignal.analysis.typescript_parser import parse_typescript_file
from patchsignal.config import AnalysisConfig
from patchsignal.models import AnalysisResult, ImpactItem, Relation, RiskLevel, RiskSignal, Symbol

_SUPPORTED = {".py", ".ts", ".tsx", ".js", ".jsx"}
_TEST_MARKERS = ("test", "spec")


def _parse_repository(root: Path, config: AnalysisConfig) -> tuple[list[Symbol], list[Relation]]:
    symbols: list[Symbol] = []
    relations: list[Relation] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix() if path.is_absolute() else path.as_posix()
        if not path.is_file() or ".git" in path.parts or path.suffix not in _SUPPORTED:
            continue
        if any(fnmatch(relative, pattern) for pattern in config.ignored_paths):
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
        relation.source == candidate and changed_stem and changed_stem in relation.target.lower()
        for relation in relations
    )


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(path, pattern) or pattern in path for pattern in patterns)


def analyze(
    root: Path,
    changed_paths: list[str],
    base: str = "working-tree",
    head: str = "working-tree",
    config: AnalysisConfig | None = None,
) -> AnalysisResult:
    policy = config or AnalysisConfig()
    symbols, relations = _parse_repository(root, policy)
    changed = {path for path in changed_paths if not _matches_any(path, policy.ignored_paths)}
    impacted = [
        ImpactItem(
            symbol.path,
            f"symbol {symbol.qualified_name} is defined in a changed file",
            90,
            (symbol.qualified_name,),
        )
        for symbol in symbols
        if symbol.path in changed
    ]
    candidate_paths = sorted(
        {
            symbol.path
            for symbol in symbols
            if symbol.path not in changed
            and any(_is_related(changed_path, symbol.path, relations) for changed_path in changed)
        }
    )
    tests = sorted(
        {
            path
            for path in (root.rglob("*") if root.exists() else [])
            if path.is_file() and any(marker in path.name.lower() for marker in _TEST_MARKERS)
        }
    )
    mandatory = sorted(
        {
            path.relative_to(root).as_posix()
            for path in tests
            if _matches_any(path.relative_to(root).as_posix(), policy.unskippable_tests)
        }
    )
    candidate_tests = [
        ImpactItem(
            path.relative_to(root).as_posix(),
            "test filename is related to an impacted module",
            80,
            (path.name,),
        )
        for path in tests
        if any(_is_related(changed_path, path.relative_to(root).as_posix(), relations) for changed_path in changed)
    ]
    mandatory_paths = set(mandatory)
    candidate_tests = [
        ImpactItem(item.path, "configured as unskippable by repository policy", 100, ("policy",))
        if item.path in mandatory_paths
        else item
        for item in candidate_tests
    ]
    candidate_tests.extend(
        ImpactItem(path, "configured as unskippable by repository policy", 100, ("policy",))
        for path in mandatory
        if path not in {item.path for item in candidate_tests}
    )
    full_run = not changed or any(_matches_any(path, policy.full_run_paths) for path in changed)
    signals = _risk_signals(changed_paths, symbols)
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
        recommended_mode="full" if full_run else "targeted",
        unskippable_tests=mandatory,
    )


def _risk_signals(changed_paths: list[str], symbols: list[Symbol]) -> list[RiskSignal]:
    signals: list[RiskSignal] = []
    paths = tuple(sorted(changed_paths))
    if any(".github/workflows/" in path or path.split("/")[-1] in (".github", "workflows") for path in paths):
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

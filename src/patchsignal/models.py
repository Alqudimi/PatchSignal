"""Stable public data contracts for PatchSignal."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status: str
    additions: int = 0
    deletions: int = 0


@dataclass(frozen=True)
class Symbol:
    qualified_name: str
    path: str
    kind: str
    line: int
    exported: bool = False


@dataclass(frozen=True)
class Relation:
    source: str
    target: str
    relation: str
    path: str


@dataclass(frozen=True)
class ImpactItem:
    path: str
    reason: str
    score: int
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class RiskSignal:
    code: str
    message: str
    level: RiskLevel
    paths: tuple[str, ...] = ()


@dataclass
class AnalysisResult:
    base: str
    head: str
    changed_files: list[ChangedFile] = field(default_factory=list)
    impacted_symbols: list[ImpactItem] = field(default_factory=list)
    candidate_tests: list[ImpactItem] = field(default_factory=list)
    risk_signals: list[RiskSignal] = field(default_factory=list)
    graph_nodes: int = 0
    graph_edges: int = 0

    @property
    def max_risk(self) -> RiskLevel:
        order = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2, RiskLevel.CRITICAL: 3}
        signals = self.risk_signals or [RiskSignal("NO_SIGNAL", "No risk rule matched", RiskLevel.LOW)]
        return max(signals, key=lambda signal: order[signal.level]).level

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

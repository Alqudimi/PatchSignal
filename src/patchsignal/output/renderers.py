"""Human and machine-readable renderers."""

from __future__ import annotations

import json
from typing import Any

from patchsignal.models import AnalysisResult


def render_json(result: AnalysisResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True, default=str) + "\n"


def render_markdown(result: AnalysisResult) -> str:
    lines = [
        "# PatchSignal analysis",
        "",
        f"**Range:** `{result.base}` → `{result.head}`  ",
        f"**Maximum risk:** `{result.max_risk.value}`  ",
        f"**Recommended test mode:** `{result.recommended_mode}`  ",
        f"**Graph:** {result.graph_nodes} nodes, {result.graph_edges} edges",
        "",
        "## Risk signals",
        "",
        "| Level | Code | Message | Paths |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {s.level.value} | `{s.code}` | {s.message} | {', '.join(s.paths) or '—'} |" for s in result.risk_signals
    )
    lines.extend(
        ["", "## Impacted files and symbols", "", "| Score | Path | Reason | Evidence |", "|---:|---|---|---|"]
    )
    lines.extend(
        f"| {item.score} | `{item.path}` | {item.reason} | {', '.join(item.evidence) or '—'} |"
        for item in result.impacted_symbols
    )
    lines.extend(["", "## Candidate tests", "", "| Score | Test | Reason |", "|---:|---|---|"])
    lines.extend(f"| {item.score} | `{item.path}` | {item.reason} |" for item in result.candidate_tests)
    if not result.candidate_tests:
        lines.append("| — | — | No matching tests were discovered. |")
    return "\n".join(lines) + "\n"


def render_sarif(result: AnalysisResult) -> str:
    rules: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for signal in result.risk_signals:
        rules.append({"id": signal.code, "shortDescription": {"text": signal.message}})
        results.append(
            {
                "ruleId": signal.code,
                "level": "error" if signal.level.value in {"high", "critical"} else "warning",
                "message": {"text": signal.message},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": path}}} for path in signal.paths[:10]],
            }
        )
    payload = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{"tool": {"driver": {"name": "PatchSignal", "version": "0.1.0", "rules": rules}}, "results": results}],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"

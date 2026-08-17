import json
import subprocess
from pathlib import Path

import pytest

from patchsignal.adapters.git import GitError, changed_files, changed_files_from_worktree
from patchsignal.analysis.engine import analyze
from patchsignal.analysis.python_parser import parse_python_file
from patchsignal.analysis.typescript_parser import parse_typescript_file
from patchsignal.cli import _risk_exit_code, main
from patchsignal.config import AnalysisConfig
from patchsignal.models import RiskLevel
from patchsignal.output.renderers import render_json, render_markdown, render_sarif


def test_python_symbols_and_import_impact(tmp_path: Path) -> None:
    (tmp_path / "service.py").write_text("import domain\n\ndef serve():\n    return domain.value()\n", encoding="utf-8")
    (tmp_path / "domain.py").write_text("def value():\n    return 42\n", encoding="utf-8")
    (tmp_path / "test_domain.py").write_text("def test_value():\n    assert True\n", encoding="utf-8")

    result = analyze(tmp_path, ["domain.py"])

    assert any(item.path == "domain.py" for item in result.impacted_symbols)
    assert result.graph_nodes >= 2
    assert result.max_risk is RiskLevel.LOW


def test_security_and_dependency_signals(tmp_path: Path) -> None:
    (tmp_path / "auth_service.py").write_text("def login():\n    return True\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    result = analyze(tmp_path, ["auth_service.py", "pyproject.toml"])
    codes = {signal.code for signal in result.risk_signals}

    assert "SECURITY_SURFACE" in codes
    assert "DEPENDENCY_OR_CONFIG" in codes
    assert result.max_risk is RiskLevel.HIGH


def test_renderers_are_machine_readable(tmp_path: Path) -> None:
    result = analyze(tmp_path, [])
    payload = json.loads(render_json(result))
    sarif = json.loads(render_sarif(result))
    markdown = render_markdown(result)
    assert "risk_signals" in payload
    assert sarif["version"] == "2.1.0"
    assert "## Candidate tests" in markdown


def test_fail_threshold_is_monotonic() -> None:
    assert _risk_exit_code("high", "medium") == 1
    assert _risk_exit_code("medium", "high") == 0
    assert _risk_exit_code("critical", "never") == 0


def test_python_parser_handles_classes_and_async_functions(tmp_path: Path) -> None:
    path = tmp_path / "module.py"
    path.write_text(
        "import os\nclass Service:\n    async def run(self):\n        return os.getcwd()\n", encoding="utf-8"
    )
    symbols, relations = parse_python_file(path, tmp_path)
    assert {symbol.kind for symbol in symbols} == {"class", "function"}
    assert relations[0].target == "os"


def test_typescript_parser_extracts_declarations_and_imports(tmp_path: Path) -> None:
    path = tmp_path / "module.ts"
    path.write_text(
        "import { x } from './dep';\nexport interface Config {}\nexport const value = x;\n",
        encoding="utf-8",
    )
    symbols, relations = parse_typescript_file(path, tmp_path)
    assert {symbol.qualified_name for symbol in symbols} == {"Config", "value"}
    assert relations[0].target == "./dep"


def test_git_adapter_reads_worktree_and_range(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "module.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "module.py").write_text("value = 2\n", encoding="utf-8")
    worktree = changed_files_from_worktree(tmp_path)
    assert worktree[0].path == "module.py"
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "change"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    ranged = changed_files(tmp_path, "HEAD~1", "HEAD")
    assert ranged[0].path == "module.py"


def test_git_adapter_reports_invalid_repo(tmp_path: Path) -> None:
    with pytest.raises(GitError):
        changed_files(tmp_path, "main", "HEAD")


def test_policy_config_controls_full_run_and_mandatory_tests(tmp_path: Path) -> None:
    (tmp_path / "service.py").write_text("def serve():\n    return True\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_service.py").write_text("def test_service():\n    assert True\n", encoding="utf-8")
    config = AnalysisConfig(full_run_paths=("service.py",), unskippable_tests=("tests/test_service.py",))

    result = analyze(tmp_path, ["service.py"], config=config)

    assert result.recommended_mode == "full"
    assert result.unskippable_tests == ["tests/test_service.py"]
    assert result.candidate_tests[0].score == 100


def test_invalid_policy_config_is_rejected(tmp_path: Path) -> None:
    config_path = tmp_path / "bad.toml"
    config_path.write_text('full_run_paths = "not-an-array"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        AnalysisConfig.load(config_path)


def test_cli_writes_json_report_and_returns_success(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "module.py").write_text("value = 1\n", encoding="utf-8")
    output = tmp_path / "report.json"
    assert main(["--repo", str(tmp_path), "--format", "json", "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["base"] == "working-tree"

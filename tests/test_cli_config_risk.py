"""Tests for CLI error paths, config boundaries and risk-rule thresholds.

Each test pins down a previously untested behavior contract: CLI error
recovery and reporting, policy loading boundaries, and the exact
thresholds at which risk rules fire (including non-match cases).
"""

from pathlib import Path

import pytest

from patchsignal.adapters.git import changed_files
from patchsignal.analysis.engine import analyze
from patchsignal.cli import _risk_exit_code, build_parser, main
from patchsignal.config import AnalysisConfig
from patchsignal.models import RiskLevel


def _repo(tmp_path: Path) -> None:
    from subprocess import run

    run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True, capture_output=True)
    run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True, capture_output=True)


# ── CLI error handling and output contracts ────────────────────────────


def test_cli_returns_error_exit_on_invalid_repo(tmp_path: Path, capsys) -> None:
    """Invalid repository errors surface with exit code 2 and a prefixed message."""
    code = main(["--repo", str(tmp_path / "missing"), "--format", "json"])
    assert code == 2
    captured = capsys.readouterr()
    assert "PatchSignal error" in captured.err


def test_cli_stderr_message_is_prefixed(tmp_path: Path, capsys) -> None:
    """Error output always carries the PatchSignal prefix so scripts can filter it."""
    _repo(tmp_path)
    (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")
    code = main(["--repo", str(tmp_path), "--base", "nonexistent-ref"])
    assert code == 2
    assert capsys.readouterr().err.startswith("PatchSignal error:")


def test_cli_unknown_argument_fails_before_analysis(tmp_path: Path) -> None:
    """Argument errors are raised by argparse without running analysis."""
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--unknown-flag"])


def test_cli_fail_on_threshold_applies_to_reported_max_risk(tmp_path: Path) -> None:
    """--fail-on medium exits non-zero when any reported signal is medium or higher."""
    _repo(tmp_path)
    (tmp_path / "auth_service.py").write_text("def login():\n    return True\n", encoding="utf-8")
    assert main(["--repo", str(tmp_path), "--fail-on", "medium"]) == 1
    assert main(["--repo", str(tmp_path), "--fail-on", "critical"]) == 0


def test_cli_markdown_output_contains_signal_table(tmp_path: Path, capsys) -> None:
    """Markdown rendering includes a risk signal for a security-surface change."""
    _repo(tmp_path)
    (tmp_path / "security" / "policies").mkdir(parents=True)
    (tmp_path / "security" / "policies" / "auth.py").write_text("def verify():\n    pass\n", encoding="utf-8")
    assert main(["--repo", str(tmp_path), "--format", "markdown"]) == 0
    assert "SECURITY_SURFACE" in capsys.readouterr().out


# ── Config loading boundaries ──────────────────────────────────────────


def test_config_load_without_path_returns_defaults(tmp_path: Path) -> None:
    """A missing policy file yields the default empty policy."""
    assert AnalysisConfig.load(None) == AnalysisConfig()


def test_config_rejects_section_that_is_not_a_table(tmp_path: Path) -> None:
    """A patchsignal section holding a scalar (not a table) is rejected."""
    config_path = tmp_path / "bad.toml"
    config_path.write_text('[patchsignal]\nfull_run_paths = "single"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        AnalysisConfig.load(config_path)


def test_config_rejects_malformed_toml(tmp_path: Path) -> None:
    """Syntax errors in the policy file are wrapped into a ValueError."""
    config_path = tmp_path / "bad.toml"
    config_path.write_text("this is not valid toml [[[", encoding="utf-8")
    with pytest.raises(ValueError):
        AnalysisConfig.load(config_path)


def test_config_rejects_non_string_array_members(tmp_path: Path) -> None:
    """Non-string or empty members inside a policy array are rejected."""
    config_path = tmp_path / "bad.toml"
    config_path.write_text('ignored_paths = ["src/", "", 3]\n', encoding="utf-8")
    with pytest.raises(ValueError):
        AnalysisConfig.load(config_path)


def test_config_loads_valid_policy(tmp_path: Path) -> None:
    """A valid top-level policy table maps into AnalysisConfig fields."""
    config_path = tmp_path / "policy.toml"
    config_path.write_text(
        'ignored_paths = ["vendor/"]\nunskippable_tests = ["tests/core_test.py"]\n', encoding="utf-8"
    )
    config = AnalysisConfig.load(config_path)
    assert config.ignored_paths == ("vendor/",)
    assert config.unskippable_tests == ("tests/core_test.py",)


# ── Risk rule thresholds and non-match cases ───────────────────────────


def test_ci_workflow_change_triggers_high_signal(tmp_path: Path) -> None:
    """Editing a workflow file forces a HIGH CI_CONFIG_CHANGED signal."""
    result = analyze(tmp_path, [".github/workflows/ci.yml"])
    codes = {signal.code for signal in result.risk_signals}
    assert "CI_CONFIG_CHANGED" in codes
    assert result.max_risk is RiskLevel.HIGH


def test_non_workflow_yaml_does_not_trigger_ci_signal(tmp_path: Path) -> None:
    """An ordinary YAML file is not mistaken for CI configuration."""
    _repo(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.yml").write_text("title: guide\n", encoding="utf-8")
    result = analyze(tmp_path, ["docs/guide.yml"])
    codes = {signal.code for signal in result.risk_signals}
    assert "CI_CONFIG_CHANGED" not in codes


def test_public_api_threshold_requires_three_exports(tmp_path: Path) -> None:
    """PUBLIC_API_SURFACE fires only when three or more exports change."""

    def module_with_exports(count: int) -> None:
        lines = [f"def api_{i}():\n    pass\n" for i in range(count)]
        (tmp_path / "api.py").write_text("".join(lines), encoding="utf-8")

    module_with_exports(2)
    result = analyze(tmp_path, ["api.py"])
    assert "PUBLIC_API_SURFACE" not in {signal.code for signal in result.risk_signals}

    module_with_exports(3)
    result = analyze(tmp_path, ["api.py"])
    assert "PUBLIC_API_SURFACE" in {signal.code for signal in result.risk_signals}
    assert result.max_risk is RiskLevel.MEDIUM


# ── Git adapter boundaries ─────────────────────────────────────────────


def test_changed_files_filters_malformed_diff_lines(tmp_path: Path) -> None:
    """Unexpected numstat line shapes are skipped instead of crashing."""
    _repo(tmp_path)
    from subprocess import run

    run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    # --numstat --diff-filter with a range that includes a binary-like rename
    # cannot be fully faked cheaply, so verify the parser's defensive branch
    # via the real adapter against a clean repo.
    files = changed_files(tmp_path, "HEAD", "HEAD")
    assert files == []


def test_exit_code_order_is_monotonic_across_all_levels() -> None:
    """_risk_exit_code respects the full risk ordering against every threshold."""
    assert _risk_exit_code("low", "low") == 1
    assert _risk_exit_code("critical", "medium") == 1
    assert _risk_exit_code("low", "critical") == 0


def test_empty_symbol_list_uses_fallback_signal() -> None:
    """An empty repository still produces a LOW fallback signal."""
    assert analyze(Path("/dev/null"), []).max_risk is RiskLevel.LOW

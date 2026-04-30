# Copyright (c) Microsoft. All rights reserved.

"""End-to-end tests for the amplifier-reality-check CLI.

Invokes the CLI as a real subprocess via ``uv run`` so tests exercise the
installed entry point exactly as a user would. Run ``uv sync`` once before
running these tests.

Errors are raw Pydantic dicts of shape
``{"type": str, "loc": list[str | int], "msg": str, "input": Any}``. YAML
parse / IO / discovery failures use synthesized dicts with distinct
``type`` codes (``yaml_parse_error``, ``io_error``, ``no_files_found``).
"""

import json
from pathlib import Path

from helpers import run_cli, run_cli_json

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _has_error(errors: list[dict], type_: str, loc: list | None = None) -> bool:
    """Return True if ``errors`` contains an entry matching type and loc."""
    for e in errors:
        if e.get("type") != type_:
            continue
        if loc is not None and list(e.get("loc", [])) != loc:
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def test_version():
    result = run_cli("--version")
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


def test_help_lists_commands():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "validate-acceptance-tests" in result.stdout
    assert "schema" in result.stdout


def test_validate_help():
    result = run_cli("validate-acceptance-tests", "--help")
    assert result.returncode == 0
    assert "PATH" in result.stdout


def test_validate_requires_path():
    result = run_cli("validate-acceptance-tests")
    assert result.returncode != 0


def test_validate_nonexistent_path():
    """Click's exists=True rejects missing paths before our code runs."""
    result = run_cli(
        "validate-acceptance-tests", "/nonexistent/path/does/not/exist.yaml"
    )
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# schema command
# ---------------------------------------------------------------------------


def test_schema_command_emits_json_schema():
    """``schema`` prints a JSON Schema document for the acceptance-tests suite."""
    data, _ = run_cli_json("schema")
    assert "properties" in data
    for key in (
        "summary",
        "software_type",
        "entry_points",
        "tests",
        "assumptions",
        "metadata",
    ):
        assert key in data["properties"]
    # Required keys are listed
    assert "summary" in data.get("required", [])
    # The Test, EntryPoint, Step models register as $defs
    assert "$defs" in data
    assert {"Test", "EntryPoint", "Step"} <= set(data["$defs"].keys())


# ---------------------------------------------------------------------------
# Valid YAML files (exit 0, valid=True)
# ---------------------------------------------------------------------------


def test_valid_minimal():
    data, _ = run_cli_json(
        "validate-acceptance-tests", str(FIXTURES / "valid-minimal.yaml")
    )
    assert data["valid"] is True
    assert data["file_count"] == 1
    assert data["files"][0]["valid"] is True
    assert data["files"][0]["errors"] == []


def test_valid_comprehensive():
    data, _ = run_cli_json(
        "validate-acceptance-tests", str(FIXTURES / "valid-comprehensive.yaml")
    )
    assert data["valid"] is True
    assert data["files"][0]["errors"] == []


def test_valid_other_test_type():
    """The catch-all ``other`` test type is accepted."""
    data, _ = run_cli_json(
        "validate-acceptance-tests", str(FIXTURES / "valid-other-test-type.yaml")
    )
    assert data["valid"] is True


def test_valid_with_metadata():
    """The open-ended top-level ``metadata`` field accepts arbitrary content."""
    data, _ = run_cli_json(
        "validate-acceptance-tests", str(FIXTURES / "valid-with-metadata.yaml")
    )
    assert data["valid"] is True


# ---------------------------------------------------------------------------
# Invalid YAML files (exit 1, valid=False, with structured errors)
# ---------------------------------------------------------------------------


def _validate_invalid(fixture_name: str) -> dict:
    """Run validate on a fixture expected to fail, return parsed JSON."""
    result = run_cli("validate-acceptance-tests", str(FIXTURES / fixture_name))
    assert result.returncode == 1, (
        f"Expected exit 1 for {fixture_name}, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    data = json.loads(result.stdout)
    assert data["valid"] is False
    return data


def test_invalid_missing_summary():
    data = _validate_invalid("invalid-missing-summary.yaml")
    errors = data["files"][0]["errors"]
    assert _has_error(errors, "missing", ["summary"])


def test_invalid_bad_software_type():
    data = _validate_invalid("invalid-bad-software-type.yaml")
    errors = data["files"][0]["errors"]
    assert _has_error(errors, "literal_error", ["software_type"])


def test_invalid_old_generic_test_type():
    """Regression: ``generic`` was renamed to ``other``; using ``generic`` fails."""
    data = _validate_invalid("invalid-old-generic-type.yaml")
    errors = data["files"][0]["errors"]
    assert _has_error(errors, "literal_error", ["tests", 0, "type"])


def test_invalid_empty_steps():
    """Empty ``steps`` list violates ``min_length=1`` (Pydantic ``too_short``)."""
    data = _validate_invalid("invalid-empty-steps.yaml")
    errors = data["files"][0]["errors"]
    assert _has_error(errors, "too_short", ["tests", 0, "steps"])


def test_invalid_bad_step_shape():
    data = _validate_invalid("invalid-bad-step-shape.yaml")
    errors = data["files"][0]["errors"]
    assert _has_error(errors, "missing", ["tests", 0, "steps", 0, "expect"])


def test_invalid_bad_entry_point_type():
    data = _validate_invalid("invalid-bad-entry-point.yaml")
    errors = data["files"][0]["errors"]
    assert _has_error(errors, "literal_error", ["entry_points", 0, "type"])


def test_invalid_unknown_top_level_key():
    """``extra='forbid'`` rejects unknown top-level keys; metadata is the escape hatch."""
    data = _validate_invalid("invalid-unknown-key.yaml")
    errors = data["files"][0]["errors"]
    assert _has_error(errors, "extra_forbidden", ["unknown_key"])


# ---------------------------------------------------------------------------
# Directory mode
# ---------------------------------------------------------------------------


def test_valid_directory_recursive():
    """Directory mode globs ``**/*.yaml`` recursively across nested folders."""
    data, _ = run_cli_json(
        "validate-acceptance-tests", str(FIXTURES / "valid-directory")
    )
    assert data["valid"] is True
    assert data["file_count"] == 2
    paths = [f["path"] for f in data["files"]]
    assert any("login.yaml" in p for p in paths)
    assert any("endpoints.yaml" in p for p in paths)


def test_mixed_directory_overall_invalid():
    """One invalid file in a directory fails the overall report."""
    result = run_cli("validate-acceptance-tests", str(FIXTURES / "mixed-directory"))
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["valid"] is False
    assert data["file_count"] == 2
    valid = [f for f in data["files"] if f["valid"]]
    invalid = [f for f in data["files"] if not f["valid"]]
    assert len(valid) == 1
    assert len(invalid) == 1


# ---------------------------------------------------------------------------
# Edge cases (synthesized via tmp_path so no committed empty dirs / bad YAML)
# ---------------------------------------------------------------------------


def test_empty_directory(tmp_path):
    result = run_cli("validate-acceptance-tests", str(tmp_path))
    assert result.returncode == 1
    data = json.loads(result.stdout)
    errors = data["files"][0]["errors"]
    assert _has_error(errors, "no_files_found")


def test_non_yaml_file(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("not yaml")
    result = run_cli("validate-acceptance-tests", str(f))
    assert result.returncode == 1
    data = json.loads(result.stdout)
    errors = data["files"][0]["errors"]
    assert _has_error(errors, "no_files_found")


def test_malformed_yaml(tmp_path):
    f = tmp_path / "broken.yaml"
    f.write_text("summary: [unclosed list\n")
    result = run_cli("validate-acceptance-tests", str(f))
    assert result.returncode == 1
    data = json.loads(result.stdout)
    errors = data["files"][0]["errors"]
    assert _has_error(errors, "yaml_parse_error")


def test_yaml_root_is_not_mapping(tmp_path):
    """Pydantic emits a ``model_type`` (or similar) error when root isn't a dict."""
    f = tmp_path / "list-root.yaml"
    f.write_text("- not a mapping\n- just a list\n")
    result = run_cli("validate-acceptance-tests", str(f))
    assert result.returncode == 1
    data = json.loads(result.stdout)
    errors = data["files"][0]["errors"]
    # We accept any non-empty error structure here; exact type code can vary
    # across Pydantic minor versions.
    assert errors


def test_yml_extension_is_discovered(tmp_path):
    """``.yml`` files are discovered alongside ``.yaml``."""
    f = tmp_path / "tests.yml"
    f.write_text(
        "summary: minimal\n"
        "software_type: library\n"
        "entry_points: []\n"
        "tests: []\n"
        "assumptions: []\n"
    )
    data, _ = run_cli_json("validate-acceptance-tests", str(f))
    assert data["valid"] is True

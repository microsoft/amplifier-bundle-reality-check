# Copyright (c) Microsoft. All rights reserved.

"""End-to-end tests for the validate-report CLI subcommand.

The raw report (model output) carries only ``id``, ``status``, ``evidence``,
and optional ``screenshots``. ``validate-report`` merges in test descriptions,
source files, and validator types from the acceptance tests, then writes an
expanded report with passed/failures/missing buckets and summary statistics.

Per-entry tolerances: bad-id, bad-status, missing-field, duplicate-id, and
unknown-id raw entries are dropped silently and counted in
``dropped_raw_entries``. Top-level structural problems (YAML parse error,
missing/wrong-type ``results`` key) ARE fatal.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from helpers import run_cli, run_cli_json

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPORTS = FIXTURES / "reports"
ACCEPTANCE = REPORTS / "acceptance-3-tests.yaml"


def _ids(items: list[dict]) -> list[str]:
    return [i["id"] for i in items]


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def test_validate_report_help():
    result = run_cli("validate-report", "--help")
    assert result.returncode == 0
    assert "REPORT_PATH" in result.stdout
    assert "--acceptance-tests" in result.stdout
    assert "--output" in result.stdout


def test_validate_report_in_main_help():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "validate-report" in result.stdout


def test_schema_type_choice():
    """``schema --type report`` returns the raw report schema."""
    data, _ = run_cli_json("schema", "--type", "report")
    # RawReport has a single 'results' property
    assert "properties" in data
    assert "results" in data["properties"]
    # And the per-entry shape is in $defs
    assert "$defs" in data
    assert "RawResultEntry" in data["$defs"]
    entry_props = data["$defs"]["RawResultEntry"]["properties"]
    for key in ("id", "status", "evidence", "screenshots"):
        assert key in entry_props


def test_schema_default_is_acceptance_tests():
    """``schema`` (no flag) still returns the acceptance-tests schema."""
    data, _ = run_cli_json("schema")
    assert "tests" in data["properties"]
    assert "summary" in data["properties"]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_all_pass_writes_expanded_report(tmp_path):
    out = tmp_path / "expanded.yaml"
    data, _ = run_cli_json(
        "validate-report",
        str(REPORTS / "raw-all-pass.yaml"),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(out),
    )
    assert data["valid"] is True
    assert data["raw_errors"] == []
    assert data["acceptance_errors"] == []
    assert data["output_path"] == str(out)

    expanded = data["expanded_report"]
    assert expanded["statistics"]["total"] == 3
    assert expanded["statistics"]["passed"] == 3
    assert expanded["statistics"]["failed"] == 0
    assert expanded["statistics"]["missing"] == 0
    assert expanded["statistics"]["pass_rate"] == "3/3"
    assert _ids(expanded["passed"]) == ["aaaaaaaa", "bbbbbbbb", "cccccccc"]
    assert expanded["failures"] == []
    assert expanded["missing"] == []
    assert expanded["dropped_raw_entries"] == 0

    # File on disk matches stdout content.
    assert out.exists()
    written = yaml.safe_load(out.read_text())
    assert written["statistics"]["pass_rate"] == "3/3"
    assert len(written["passed"]) == 3


def test_mixed_pass_fail_missing(tmp_path):
    out = tmp_path / "expanded.yaml"
    data, _ = run_cli_json(
        "validate-report",
        str(REPORTS / "raw-mixed.yaml"),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(out),
    )
    assert data["valid"] is True
    expanded = data["expanded_report"]
    assert expanded["statistics"]["total"] == 3
    assert expanded["statistics"]["passed"] == 1
    assert expanded["statistics"]["failed"] == 1
    assert expanded["statistics"]["missing"] == 1
    assert expanded["statistics"]["pass_rate"] == "1/3"
    assert _ids(expanded["passed"]) == ["aaaaaaaa"]
    assert _ids(expanded["failures"]) == ["bbbbbbbb"]
    assert _ids(expanded["missing"]) == ["cccccccc"]
    # Reason populated only for missing entries.
    assert expanded["missing"][0]["reason"] is not None
    assert expanded["passed"][0]["reason"] is None


def test_merged_fields_come_from_acceptance_tests(tmp_path):
    """test description, source_file, and validator are merged in by id lookup."""
    data, _ = run_cli_json(
        "validate-report",
        str(REPORTS / "raw-all-pass.yaml"),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    expanded = data["expanded_report"]
    by_id = {r["id"]: r for r in expanded["passed"]}

    aaaa = by_id["aaaaaaaa"]
    assert aaaa["test"] == "User can log in"
    assert aaaa["validator"] == "browser"
    assert aaaa["source_file"] == "acceptance-3-tests.yaml"

    cccc = by_id["cccccccc"]
    assert cccc["test"] == "API health endpoint responds"
    assert cccc["validator"] == "other"


def test_screenshots_carried_through(tmp_path):
    data, _ = run_cli_json(
        "validate-report",
        str(REPORTS / "raw-mixed.yaml"),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    expanded = data["expanded_report"]
    bbbb = next(r for r in expanded["failures"] if r["id"] == "bbbbbbbb")
    assert bbbb["screenshots"] == ["02-dashboard.png", "03-error.png"]


def test_assumptions_carried_forward(tmp_path):
    """Assumptions on the acceptance-tests suite end up on the expanded report."""
    accept = tmp_path / "with-assumptions.yaml"
    accept.write_text(
        "summary: with assumptions\n"
        "software_type: web_app\n"
        "entry_points: []\n"
        "tests:\n"
        '  - id: "11111111"\n'
        "    description: Only test\n"
        "    type: browser\n"
        "    steps:\n"
        "      - action: open\n"
        "        expect: ok\n"
        "assumptions:\n"
        "  - Assumes the dev server is on port 8080\n"
        "  - Assumes the demo user exists\n"
    )
    raw = tmp_path / "raw.yaml"
    raw.write_text(
        'results:\n  - id: "11111111"\n    status: pass\n    evidence: it loaded\n'
    )
    data, _ = run_cli_json(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(accept),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    expanded = data["expanded_report"]
    assert expanded["assumptions"] == [
        "Assumes the dev server is on port 8080",
        "Assumes the demo user exists",
    ]


# ---------------------------------------------------------------------------
# Tolerant per-entry handling
# ---------------------------------------------------------------------------


def test_bad_entries_are_dropped_silently(tmp_path):
    """Bad-id, bad-status, missing-field, and unknown-id entries are dropped."""
    out = tmp_path / "out.yaml"
    data, _ = run_cli_json(
        "validate-report",
        str(REPORTS / "raw-with-bad-ids.yaml"),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(out),
    )
    # Validation still SUCCEEDS -- bad entries are just dropped.
    assert data["valid"] is True
    expanded = data["expanded_report"]

    # Only aaaaaaaa survived: 1 pass.
    assert expanded["statistics"]["passed"] == 1
    assert _ids(expanded["passed"]) == ["aaaaaaaa"]

    # bbbbbbbb (bad status) and cccccccc (missing field) had bad raw entries
    # so they're treated as if not reported -> missing.
    assert expanded["statistics"]["missing"] == 2
    assert _ids(expanded["missing"]) == ["bbbbbbbb", "cccccccc"]

    # Four entries dropped:
    #   - "NOT-HEX"   bad id format
    #   - "ff00ff00"  unknown id
    #   - "bbbbbbbb"  bad status
    #   - "cccccccc"  missing evidence
    assert expanded["dropped_raw_entries"] == 4


def test_duplicate_raw_id_first_wins(tmp_path):
    raw = tmp_path / "raw.yaml"
    raw.write_text(
        "results:\n"
        "  - id: aaaaaaaa\n"
        "    status: pass\n"
        "    evidence: first wins\n"
        "  - id: aaaaaaaa\n"
        "    status: fail\n"
        "    evidence: this one is dropped\n"
    )
    data, _ = run_cli_json(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    expanded = data["expanded_report"]
    assert expanded["statistics"]["passed"] == 1
    assert expanded["passed"][0]["evidence"] == "first wins"
    assert expanded["dropped_raw_entries"] == 1


def test_unknown_id_dropped_does_not_appear_in_buckets(tmp_path):
    raw = tmp_path / "raw.yaml"
    raw.write_text(
        "results:\n  - id: ff00ff00\n    status: pass\n    evidence: orphan\n"
    )
    data, _ = run_cli_json(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    expanded = data["expanded_report"]
    # ff00ff00 gone; all 3 acceptance tests in missing.
    assert expanded["passed"] == []
    assert expanded["failures"] == []
    assert expanded["statistics"]["missing"] == 3
    assert expanded["dropped_raw_entries"] == 1
    # Definitely not in any bucket
    all_ids: set[str] = set()
    for bucket in ("passed", "failures", "missing"):
        all_ids.update(_ids(expanded[bucket]))
    assert "ff00ff00" not in all_ids


def test_empty_results_list_produces_all_missing(tmp_path):
    data, _ = run_cli_json(
        "validate-report",
        str(REPORTS / "raw-empty-results.yaml"),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    expanded = data["expanded_report"]
    assert expanded["statistics"]["passed"] == 0
    assert expanded["statistics"]["failed"] == 0
    assert expanded["statistics"]["missing"] == 3
    assert expanded["dropped_raw_entries"] == 0


# ---------------------------------------------------------------------------
# Structural failures (exit 1)
# ---------------------------------------------------------------------------


def _validate_invalid(raw_fixture: str, *extra_args: str) -> dict:
    result = run_cli(
        "validate-report",
        str(REPORTS / raw_fixture),
        "--acceptance-tests",
        str(ACCEPTANCE),
        *extra_args,
    )
    assert result.returncode == 1, (
        f"Expected exit 1 for {raw_fixture}, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return json.loads(result.stdout)


def test_missing_results_key_fails(tmp_path):
    data = _validate_invalid(
        "raw-no-results-key.yaml", "--output", str(tmp_path / "out.yaml")
    )
    assert data["valid"] is False
    types = [e["type"] for e in data["raw_errors"]]
    assert "missing" in types
    # Expanded report not produced -> output not written.
    assert data["expanded_report"] is None
    assert not (tmp_path / "out.yaml").exists()


def test_extra_toplevel_key_fails(tmp_path):
    data = _validate_invalid(
        "raw-extra-toplevel-key.yaml", "--output", str(tmp_path / "out.yaml")
    )
    assert data["valid"] is False
    types = [e["type"] for e in data["raw_errors"]]
    assert "extra_forbidden" in types


def test_malformed_yaml_fails(tmp_path):
    data = _validate_invalid(
        "raw-malformed-yaml.yaml", "--output", str(tmp_path / "out.yaml")
    )
    assert data["valid"] is False
    types = [e["type"] for e in data["raw_errors"]]
    assert "yaml_parse_error" in types


def test_results_not_a_list_fails(tmp_path):
    raw = tmp_path / "raw.yaml"
    raw.write_text("results:\n  not: a list\n")
    result = run_cli(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    types = [e["type"] for e in data["raw_errors"]]
    assert "list_type" in types


def test_root_not_mapping_fails(tmp_path):
    raw = tmp_path / "raw.yaml"
    raw.write_text("- just\n- a list\n")
    result = run_cli(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    types = [e["type"] for e in data["raw_errors"]]
    assert "model_type" in types


def test_invalid_acceptance_tests_fails(tmp_path):
    """If acceptance tests don't validate, the whole thing is invalid."""
    bad_accept = tmp_path / "bad.yaml"
    # Missing required 'summary' -> won't validate.
    bad_accept.write_text(
        "software_type: web_app\nentry_points: []\ntests: []\nassumptions: []\n"
    )
    result = run_cli(
        "validate-report",
        str(REPORTS / "raw-all-pass.yaml"),
        "--acceptance-tests",
        str(bad_accept),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["valid"] is False
    assert data["acceptance_errors"]
    assert data["expanded_report"] is None


# ---------------------------------------------------------------------------
# Acceptance-tests directory mode
# ---------------------------------------------------------------------------


def test_directory_acceptance_tests_works(tmp_path):
    """When acceptance tests come from a directory, source_file is relative
    to the directory root and tests are merged from all files."""
    accept_dir = tmp_path / "accept"
    (accept_dir / "auth").mkdir(parents=True)
    (accept_dir / "api").mkdir()
    (accept_dir / "auth" / "login.yaml").write_text(
        "summary: login\n"
        "software_type: web_app\n"
        "entry_points: []\n"
        "tests:\n"
        '  - id: "11111111"\n'
        "    description: Login works\n"
        "    type: browser\n"
        "    steps:\n"
        "      - action: log in\n"
        "        expect: dashboard\n"
        "assumptions: []\n"
    )
    (accept_dir / "api" / "endpoints.yaml").write_text(
        "summary: endpoints\n"
        "software_type: api_service\n"
        "entry_points: []\n"
        "tests:\n"
        '  - id: "22222222"\n'
        "    description: Health endpoint OK\n"
        "    type: other\n"
        "    steps:\n"
        "      - action: hit /health\n"
        '        expect: "200"\n'
        "assumptions: []\n"
    )
    raw = tmp_path / "raw.yaml"
    raw.write_text(
        "results:\n"
        '  - id: "11111111"\n'
        "    status: pass\n"
        "    evidence: login worked\n"
        '  - id: "22222222"\n'
        "    status: fail\n"
        "    evidence: 500 error\n"
    )
    data, _ = run_cli_json(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(accept_dir),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    expanded = data["expanded_report"]
    by_id = {
        r["id"]: r
        for bucket in ("passed", "failures", "missing")
        for r in expanded[bucket]
    }
    # source_file is relative to the directory root.
    assert by_id["11111111"]["source_file"] == "auth/login.yaml"
    assert by_id["22222222"]["source_file"] == "api/endpoints.yaml"
    assert expanded["statistics"]["pass_rate"] == "1/2"


# ---------------------------------------------------------------------------
# Default --output path
# ---------------------------------------------------------------------------


def test_default_output_path(tmp_path):
    """Without --output, expanded report lands next to REPORT_PATH."""
    raw = tmp_path / "raw.yaml"
    raw.write_text("results:\n  - id: aaaaaaaa\n    status: pass\n    evidence: ok\n")
    data, _ = run_cli_json(
        "validate-report", str(raw), "--acceptance-tests", str(ACCEPTANCE)
    )
    default_path = tmp_path / "report.expanded.yaml"
    assert data["output_path"] == str(default_path)
    assert default_path.exists()


# ---------------------------------------------------------------------------
# Stderr signals
# ---------------------------------------------------------------------------


def test_stderr_reports_dropped_entries(tmp_path):
    result = run_cli(
        "validate-report",
        str(REPORTS / "raw-with-bad-ids.yaml"),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    assert result.returncode == 0
    assert "Dropped 4 raw entries" in result.stderr


def test_stderr_reports_output_written(tmp_path):
    result = run_cli(
        "validate-report",
        str(REPORTS / "raw-all-pass.yaml"),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    assert result.returncode == 0
    assert "Wrote expanded report" in result.stderr


# ---------------------------------------------------------------------------
# HTML emission (--html-output, --screenshots-dir, --dtu-details-file)
# ---------------------------------------------------------------------------


def test_html_written_to_default_path(tmp_path):
    """Without --html-output, an HTML file lands next to REPORT_PATH."""
    raw = tmp_path / "raw.yaml"
    raw.write_text("results:\n  - id: aaaaaaaa\n    status: pass\n    evidence: ok\n")
    data, _ = run_cli_json(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    default_html = tmp_path / "report.html"
    assert data["html_output_path"] == str(default_html)
    assert default_html.exists()
    text = default_html.read_text()
    assert text.lstrip().startswith("<!DOCTYPE html>")
    assert "Reality Check Report" in text


def test_html_written_to_explicit_path(tmp_path):
    raw = tmp_path / "raw.yaml"
    raw.write_text("results:\n  - id: aaaaaaaa\n    status: pass\n    evidence: ok\n")
    custom = tmp_path / "nested" / "report.html"
    data, _ = run_cli_json(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
        "--html-output",
        str(custom),
    )
    assert data["html_output_path"] == str(custom)
    assert custom.exists()
    # Parent directory was created.
    assert custom.parent.is_dir()


def test_stderr_reports_html_written(tmp_path):
    result = run_cli(
        "validate-report",
        str(REPORTS / "raw-all-pass.yaml"),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    assert result.returncode == 0
    assert "Wrote HTML report" in result.stderr


def test_html_skipped_on_structural_error(tmp_path):
    """When validation fails, no HTML is written and no path is reported."""
    raw = tmp_path / "raw.yaml"
    raw.write_text("not_a_mapping_just_a_string\n")
    result = run_cli(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["html_output_path"] is None
    assert not (tmp_path / "report.html").exists()


def test_dtu_details_file_surfaces_in_html(tmp_path):
    """--dtu-details-file contents appear in the rendered HTML footer."""
    raw = tmp_path / "raw.yaml"
    raw.write_text("results:\n  - id: aaaaaaaa\n    status: pass\n    evidence: ok\n")
    dtu = tmp_path / "dtu.txt"
    dtu.write_text("DTU URL: http://localhost:8410/chat/\nID: dtu-abc123\n")
    html_out = tmp_path / "report.html"
    run_cli_json(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
        "--html-output",
        str(html_out),
        "--dtu-details-file",
        str(dtu),
    )
    text = html_out.read_text()
    assert "Environment Access" in text
    assert "http://localhost:8410/chat/" in text
    assert "dtu-abc123" in text


def test_screenshots_dir_resolves_relative_paths(tmp_path):
    """--screenshots-dir lets the CLI resolve relative screenshot paths."""
    # Tiny 1x1 PNG (matches the unit test fixture).
    import base64

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNg"
        "YAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
    )
    shots = tmp_path / "screenshots"
    shots.mkdir()
    (shots / "01-login.png").write_bytes(png_bytes)

    raw = tmp_path / "raw.yaml"
    raw.write_text(
        "results:\n"
        "  - id: aaaaaaaa\n"
        "    status: pass\n"
        "    evidence: ok\n"
        "    screenshots:\n"
        "      - 01-login.png\n"
    )
    html_out = tmp_path / "report.html"
    run_cli_json(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
        "--html-output",
        str(html_out),
        "--screenshots-dir",
        str(shots),
    )
    text = html_out.read_text()
    assert "data:image/png;base64," in text


def test_screenshots_dir_default_is_report_parent(tmp_path):
    """Without --screenshots-dir, paths resolve relative to REPORT_PATH's parent."""
    import base64

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNg"
        "YAAAAAMAAWgmWQ0AAAAASUVORK5CYII="
    )
    (tmp_path / "01-login.png").write_bytes(png_bytes)

    raw = tmp_path / "raw.yaml"
    raw.write_text(
        "results:\n"
        "  - id: aaaaaaaa\n"
        "    status: pass\n"
        "    evidence: ok\n"
        "    screenshots:\n"
        "      - 01-login.png\n"
    )
    html_out = tmp_path / "report.html"
    run_cli_json(
        "validate-report",
        str(raw),
        "--acceptance-tests",
        str(ACCEPTANCE),
        "--output",
        str(tmp_path / "out.yaml"),
        "--html-output",
        str(html_out),
    )
    text = html_out.read_text()
    assert "data:image/png;base64," in text

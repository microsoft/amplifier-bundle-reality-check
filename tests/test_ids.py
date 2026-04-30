# Copyright (c) Microsoft. All rights reserved.

"""Tests for the auto-assigned ``id`` field on each acceptance Test.

IDs are 8-char lowercase hex strings, globally unique across the path
being validated, written into the source YAML in place by
``validate-acceptance-tests``. The CLI is idempotent: tests that already
have an ``id`` are left untouched.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import yaml

from helpers import run_cli, run_cli_json

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ID_PATTERN = re.compile(r"^[0-9a-f]{8}$")


def _yaml_no_ids(tmp: Path) -> Path:
    f = tmp / "tests.yaml"
    f.write_text(
        "summary: simple\n"
        "software_type: web_app\n"
        "entry_points: []\n"
        "tests:\n"
        "  - description: First test\n"
        "    type: browser\n"
        "    steps:\n"
        "      - action: open page\n"
        "        expect: page renders\n"
        "  - description: Second test\n"
        "    type: other\n"
        "    steps:\n"
        "      - action: hit endpoint\n"
        "        expect: 200 OK\n"
        "assumptions: []\n"
    )
    return f


# ---------------------------------------------------------------------------
# Injection on first run
# ---------------------------------------------------------------------------


def test_assigns_ids_on_first_run(tmp_path):
    """Validation injects 8-char hex IDs when missing and reports the count."""
    f = _yaml_no_ids(tmp_path)
    data, result = run_cli_json("validate-acceptance-tests", str(f))
    assert data["valid"] is True
    assert data["ids_added"] == 2
    # File was reported as modified
    modified = [Path(p) for p in data["modified_files"]]
    assert f in modified
    # Stderr surfaces the human-readable note
    assert "Added 2 test ID(s)" in result.stderr


def test_injected_ids_are_valid_hex(tmp_path):
    """Each injected ID matches ^[0-9a-f]{8}$ and is unique within the file."""
    f = _yaml_no_ids(tmp_path)
    run_cli_json("validate-acceptance-tests", str(f))
    parsed = yaml.safe_load(f.read_text())
    ids = [t["id"] for t in parsed["tests"]]
    assert len(ids) == 2
    assert len(set(ids)) == 2  # unique
    for tid in ids:
        assert ID_PATTERN.match(tid), f"bad id format: {tid!r}"


def test_id_inserted_as_first_field(tmp_path):
    """Injected ID lands at the top of each test mapping for readability."""
    f = _yaml_no_ids(tmp_path)
    run_cli_json("validate-acceptance-tests", str(f))
    parsed = yaml.safe_load(f.read_text())
    for t in parsed["tests"]:
        # Python 3.7+ dicts preserve insertion order, and PyYAML respects it
        # on round-trip via the C loader. The first key of each test must
        # be 'id'.
        assert next(iter(t)) == "id", (
            f"expected first key of test to be 'id', got keys: {list(t)!r}"
        )


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_second_run_is_idempotent(tmp_path):
    """Re-running validation on a file that already has IDs adds zero."""
    f = _yaml_no_ids(tmp_path)
    run_cli_json("validate-acceptance-tests", str(f))
    first_text = f.read_text()
    first_ids = [t["id"] for t in yaml.safe_load(first_text)["tests"]]

    data, _ = run_cli_json("validate-acceptance-tests", str(f))
    assert data["ids_added"] == 0
    assert data["modified_files"] == []
    second_text = f.read_text()
    # Bytes-equal: no rewrite happened on the second pass
    assert first_text == second_text
    second_ids = [t["id"] for t in yaml.safe_load(second_text)["tests"]]
    assert first_ids == second_ids


def test_partial_idempotency(tmp_path):
    """Tests with existing IDs are preserved; only missing ones get filled."""
    f = tmp_path / "partial.yaml"
    f.write_text(
        "summary: partial\n"
        "software_type: web_app\n"
        "entry_points: []\n"
        "tests:\n"
        "  - id: aaaaaaaa\n"
        "    description: Pre-existing\n"
        "    type: browser\n"
        "    steps:\n"
        "      - action: open\n"
        "        expect: renders\n"
        "  - description: New test\n"
        "    type: browser\n"
        "    steps:\n"
        "      - action: click\n"
        "        expect: navigates\n"
        "assumptions: []\n"
    )
    data, _ = run_cli_json("validate-acceptance-tests", str(f))
    assert data["valid"] is True
    assert data["ids_added"] == 1
    parsed = yaml.safe_load(f.read_text())
    ids = [t["id"] for t in parsed["tests"]]
    assert ids[0] == "aaaaaaaa"  # preserved verbatim
    assert ID_PATTERN.match(ids[1]) and ids[1] != "aaaaaaaa"


# ---------------------------------------------------------------------------
# Format and uniqueness validation (failures)
# ---------------------------------------------------------------------------


def test_malformed_id_is_rejected(tmp_path):
    """An existing ``id`` that doesn't match ^[0-9a-f]{8}$ fails validation."""
    f = tmp_path / "bad-id.yaml"
    f.write_text(
        "summary: bad\n"
        "software_type: web_app\n"
        "entry_points: []\n"
        "tests:\n"
        "  - id: NOT-HEX\n"
        "    description: Has malformed id\n"
        "    type: browser\n"
        "    steps:\n"
        "      - action: open\n"
        "        expect: renders\n"
        "assumptions: []\n"
    )
    result = run_cli("validate-acceptance-tests", str(f))
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["valid"] is False
    errors = data["files"][0]["errors"]
    # Pydantic surfaces a string_pattern_mismatch on the test's id field.
    assert any(
        e.get("type") == "string_pattern_mismatch"
        and list(e.get("loc", [])) == ["tests", 0, "id"]
        for e in errors
    )


def test_duplicate_ids_across_files_rejected(tmp_path):
    """Cross-file duplicate IDs are flagged as ``duplicate_id`` errors."""
    a = tmp_path / "a.yaml"
    b = tmp_path / "b.yaml"
    body = (
        "summary: dup\n"
        "software_type: web_app\n"
        "entry_points: []\n"
        "tests:\n"
        "  - id: deadbeef\n"
        "    description: Same id in two files\n"
        "    type: browser\n"
        "    steps:\n"
        "      - action: x\n"
        "        expect: y\n"
        "assumptions: []\n"
    )
    a.write_text(body)
    b.write_text(body)

    result = run_cli("validate-acceptance-tests", str(tmp_path))
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["valid"] is False
    # Both files should carry a duplicate_id error referencing 'deadbeef'.
    dup_files = [
        f
        for f in data["files"]
        if any(e.get("type") == "duplicate_id" for e in f["errors"])
    ]
    assert len(dup_files) == 2
    for fr in dup_files:
        dup = next(e for e in fr["errors"] if e.get("type") == "duplicate_id")
        assert "deadbeef" in dup["msg"]


def test_unique_ids_across_directory_pass(tmp_path):
    """Directory mode keeps assignments unique across files."""
    for i in range(3):
        sub = tmp_path / f"feature_{i}"
        sub.mkdir()
        f = sub / "tests.yaml"
        f.write_text(
            f"summary: feature {i}\n"
            f"software_type: web_app\n"
            f"entry_points: []\n"
            f"tests:\n"
            f"  - description: T{i}-a\n"
            f"    type: browser\n"
            f"    steps:\n"
            f"      - action: open\n"
            f"        expect: renders\n"
            f"  - description: T{i}-b\n"
            f"    type: browser\n"
            f"    steps:\n"
            f"      - action: click\n"
            f"        expect: navigates\n"
            f"assumptions: []\n"
        )
    data, _ = run_cli_json("validate-acceptance-tests", str(tmp_path))
    assert data["valid"] is True
    assert data["ids_added"] == 6
    all_ids: list[str] = []
    for fr in data["files"]:
        parsed = yaml.safe_load(Path(fr["path"]).read_text())
        all_ids.extend(t["id"] for t in parsed["tests"])
    assert len(all_ids) == len(set(all_ids))  # globally unique


# ---------------------------------------------------------------------------
# YAML preservation (comments, key order)
# ---------------------------------------------------------------------------


def test_comments_preserved_after_id_injection(tmp_path):
    """ruamel round-trip mode keeps user comments intact."""
    f = tmp_path / "with-comments.yaml"
    f.write_text(
        "# This is a top-level comment\n"
        "summary: with comments\n"
        "software_type: web_app\n"
        "entry_points: []\n"
        "tests:\n"
        "  # Comment before first test\n"
        "  - description: First\n"
        "    type: browser\n"
        "    steps:\n"
        "      - action: open\n"
        "        expect: renders\n"
        "assumptions: []\n"
    )
    run_cli_json("validate-acceptance-tests", str(f))
    text = f.read_text()
    assert "# This is a top-level comment" in text
    assert "# Comment before first test" in text


# ---------------------------------------------------------------------------
# Empty test list -- no IDs to assign
# ---------------------------------------------------------------------------


def test_empty_tests_list_no_ids_added(tmp_path):
    """A suite with zero tests adds zero IDs and remains valid."""
    f = tmp_path / "empty.yaml"
    f.write_text(
        "summary: empty\n"
        "software_type: library\n"
        "entry_points: []\n"
        "tests: []\n"
        "assumptions: []\n"
    )
    data, _ = run_cli_json("validate-acceptance-tests", str(f))
    assert data["valid"] is True
    assert data["ids_added"] == 0
    assert data["modified_files"] == []


# ---------------------------------------------------------------------------
# Pre-existing fixtures already have IDs (committed). Sanity-check.
# ---------------------------------------------------------------------------


def test_committed_fixtures_have_ids(tmp_path):
    """Copy committed fixtures to tmp, verify all tests have valid IDs."""
    src = FIXTURES / "valid-comprehensive.yaml"
    dst = tmp_path / "copy.yaml"
    shutil.copy(src, dst)
    data, _ = run_cli_json("validate-acceptance-tests", str(dst))
    assert data["valid"] is True
    # Already had IDs: no new IDs assigned.
    assert data["ids_added"] == 0
    parsed = yaml.safe_load(dst.read_text())
    for t in parsed["tests"]:
        assert ID_PATTERN.match(t["id"]), f"bad id: {t['id']!r}"

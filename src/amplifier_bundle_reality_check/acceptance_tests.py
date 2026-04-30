# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Acceptance test schema, discovery, and validation.

The Pydantic models below ARE the schema. Source of truth lives in code.

The intent-analyzer agent's ``output_path`` is polymorphic: it may be a
single ``.yaml`` file or a directory containing one or more YAML files
(optionally nested). Each file is independently valid against the schema.

``Test.type == "other"`` is the catch-all for tests that don't fit the
``browser`` or ``cli`` validator types -- forward-compatible for new test
types that may be added later.

Each ``Test`` has an ``id``: an 8-char lowercase hex string that uniquely
identifies it across the entire acceptance-tests path. IDs are auto-assigned
by ``validate_path`` for any test missing one and written back to the source
YAML in place. Once assigned, IDs are stable across re-runs of the
convergence loop -- the validator is idempotent: only fills missing, never
replaces existing.
"""

from __future__ import annotations

import io
import secrets
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, computed_field
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# ---------------------------------------------------------------------------
# Schema models
# ---------------------------------------------------------------------------

NonEmptyStr = Annotated[str, Field(min_length=1)]
TestId = Annotated[str, Field(pattern=r"^[0-9a-f]{8}$")]


class _Strict(BaseModel):
    """Base for schema models: forbid unknown keys, no type coercion."""

    model_config = ConfigDict(extra="forbid", strict=True)


class Step(_Strict):
    action: NonEmptyStr
    expect: NonEmptyStr


class EntryPoint(_Strict):
    type: Literal["url", "command", "import"]
    value: NonEmptyStr
    label: NonEmptyStr


class Test(_Strict):
    id: TestId
    description: NonEmptyStr
    type: Literal["browser", "cli", "other"]
    steps: list[Step] = Field(min_length=1)


class AcceptanceTestsSuite(_Strict):
    summary: NonEmptyStr
    software_type: Literal["web_app", "cli_tool", "api_service", "library"]
    entry_points: list[EntryPoint]
    tests: list[Test]
    assumptions: list[NonEmptyStr]
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class FileResult(BaseModel):
    """Result of validating a single YAML file."""

    path: Path
    valid: bool
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Aggregate result across one or more YAML files."""

    root: Path
    files: list[FileResult] = Field(default_factory=list)
    ids_added: int = 0
    modified_files: list[Path] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valid(self) -> bool:
        return bool(self.files) and all(f.valid for f in self.files)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def file_count(self) -> int:
        return len(self.files)


# ---------------------------------------------------------------------------
# Discovery + validation
# ---------------------------------------------------------------------------


def discover_yaml_files(path: Path) -> list[Path]:
    """Resolve an acceptance-tests path into a list of YAML files.

    - File path: returns ``[path]`` if it has a ``.yaml`` or ``.yml`` suffix.
    - Directory path: returns ``**/*.yaml`` and ``**/*.yml`` recursively, sorted.
    """
    if path.is_file():
        if path.suffix in {".yaml", ".yml"}:
            return [path]
        return []
    if path.is_dir():
        files = sorted({*path.rglob("*.yaml"), *path.rglob("*.yml")})
        return list(files)
    return []


# ---------------------------------------------------------------------------
# ID assignment (in-place YAML mutation, comment-preserving)
# ---------------------------------------------------------------------------


def _new_test_id(taken: set[str]) -> str:
    """Generate an 8-char lowercase hex ID not already in ``taken``.

    Collision probability at suite scale (low hundreds of tests) is
    negligible (~1e-6 per assignment) but we still loop defensively so
    a forced collision in tests has a deterministic exit.
    """
    while True:
        candidate = secrets.token_hex(4)
        if candidate not in taken:
            return candidate


def _ruamel_yaml() -> YAML:
    """Round-trip YAML loader that preserves comments and key order."""
    y = YAML(typ="rt")
    y.preserve_quotes = True
    # Match the existing fixtures' style: 2-space indentation, no awkward
    # sequence dash hanging.
    y.indent(mapping=2, sequence=4, offset=2)
    y.width = 4096  # don't auto-wrap long strings
    return y


def _fill_missing_ids(files: list[Path]) -> tuple[list[Path], int]:
    """Inject ``id`` into any test that lacks one, in place across files.

    - Idempotent: tests that already have a valid-looking ``id`` are left
      alone (we don't validate the format here -- pydantic will).
    - Globally unique: tracks IDs across all files in this batch and
      regenerates on the rare collision.
    - Resilient: skips files whose top-level structure doesn't expose
      a ``tests`` list (those will fail pydantic validation anyway).
    - Comment-preserving: uses ruamel.yaml round-trip mode.

    Returns ``(modified_files, ids_added)``.
    """
    taken: set[str] = set()
    modified: list[Path] = []
    ids_added = 0

    yaml_rt = _ruamel_yaml()

    # First pass: collect already-assigned IDs so new ones don't collide.
    parsed: dict[Path, Any] = {}
    for f in files:
        try:
            with open(f, encoding="utf-8") as fp:
                data = yaml_rt.load(fp)
        except Exception:
            # Malformed YAML / IO error -- leave for pydantic stage.
            continue
        parsed[f] = data
        if not isinstance(data, dict):
            continue
        tests = data.get("tests")
        if not isinstance(tests, list):
            continue
        for t in tests:
            if not isinstance(t, dict):
                continue
            existing = t.get("id")
            if isinstance(existing, str) and existing:
                taken.add(existing)

    # Second pass: assign IDs and write back files that changed.
    for f, data in parsed.items():
        if not isinstance(data, dict):
            continue
        tests = data.get("tests")
        if not isinstance(tests, list):
            continue
        file_changed = False
        for t in tests:
            # Round-trip mode loads mappings as CommentedMap (a dict
            # subclass with .insert(pos, key, value)). Plain dicts are
            # not expected here, but we guard for clarity.
            if not isinstance(t, CommentedMap):
                continue
            existing = t.get("id")
            if isinstance(existing, str) and existing:
                continue
            new_id = _new_test_id(taken)
            taken.add(new_id)
            # Insert ``id`` as the first key for readability.
            t.insert(0, "id", new_id)
            file_changed = True
            ids_added += 1
        if file_changed:
            buf = io.StringIO()
            yaml_rt.dump(data, buf)
            f.write_text(buf.getvalue(), encoding="utf-8")
            modified.append(f)

    return modified, ids_added


def _check_unique_ids(files: list[FileResult]) -> None:
    """Append ``duplicate_id`` errors to FileResults that share an ID.

    Mutates ``files`` in place: any FileResult that contributed a
    duplicate gets a synthetic error and ``valid`` flipped to False.
    Only inspects files that already passed pydantic validation
    (i.e. ``valid is True``); files with structural errors are skipped
    here -- their existing errors are sufficient signal.
    """
    seen: dict[str, list[Path]] = {}
    file_tests: dict[Path, list[str]] = {}

    for fr in files:
        if not fr.valid:
            continue
        try:
            with open(fr.path, encoding="utf-8") as fp:
                data = yaml.safe_load(fp)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        tests = data.get("tests")
        if not isinstance(tests, list):
            continue
        ids: list[str] = []
        for t in tests:
            if isinstance(t, dict):
                tid = t.get("id")
                if isinstance(tid, str):
                    ids.append(tid)
                    seen.setdefault(tid, []).append(fr.path)
        file_tests[fr.path] = ids

    duplicates = {tid: paths for tid, paths in seen.items() if len(paths) > 1}
    if not duplicates:
        return

    by_path: dict[Path, FileResult] = {fr.path: fr for fr in files}
    for tid, paths in duplicates.items():
        unique_paths = sorted(set(paths))
        msg = (
            f"id '{tid}' appears in multiple files: "
            f"{', '.join(str(p) for p in unique_paths)}"
        )
        for p in unique_paths:
            fr = by_path.get(p)
            if fr is None:
                continue
            fr.errors.append(
                {
                    "type": "duplicate_id",
                    "loc": ["tests"],
                    "msg": msg,
                    "input": tid,
                }
            )
            fr.valid = False


# ---------------------------------------------------------------------------
# Per-file validation
# ---------------------------------------------------------------------------


def validate_file(path: Path) -> FileResult:
    """Validate a single acceptance-tests YAML file against the schema.

    On schema violation, ``errors`` contains raw Pydantic error dicts
    (``type``, ``loc``, ``msg``, ``input``) -- agents and humans can both
    consume these. YAML parse and IO errors use synthesized dicts with
    distinct ``type`` codes (``yaml_parse_error``, ``io_error``).
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        return FileResult(
            path=path,
            valid=False,
            errors=[{"type": "yaml_parse_error", "loc": [], "msg": str(exc)}],
        )
    except OSError as exc:
        return FileResult(
            path=path,
            valid=False,
            errors=[{"type": "io_error", "loc": [], "msg": str(exc)}],
        )

    try:
        AcceptanceTestsSuite.model_validate(data)
    except ValidationError as exc:
        return FileResult(
            path=path,
            valid=False,
            errors=list(exc.errors(include_url=False)),
        )

    return FileResult(path=path, valid=True, errors=[])


def validate_path(path: Path) -> ValidationReport:
    """Validate an acceptance-tests path (file or directory).

    Side effects: any ``Test`` lacking an ``id`` is assigned a fresh
    8-char lowercase hex ID and the source YAML is rewritten in place.
    The resulting ``ValidationReport`` reports ``ids_added`` and
    ``modified_files`` so callers can surface the change.
    """
    files = discover_yaml_files(path)
    if not files:
        return ValidationReport(
            root=path,
            files=[
                FileResult(
                    path=path,
                    valid=False,
                    errors=[
                        {
                            "type": "no_files_found",
                            "loc": [],
                            "msg": "no .yaml or .yml files found at path",
                        }
                    ],
                )
            ],
        )

    # 1. Fill missing IDs in place (mutates files on disk).
    modified, ids_added = _fill_missing_ids(files)

    # 2. Schema validation per file.
    file_results = [validate_file(f) for f in files]

    # 3. Cross-file uniqueness check (only inspects files that passed
    #    schema validation).
    _check_unique_ids(file_results)

    return ValidationReport(
        root=path,
        files=file_results,
        ids_added=ids_added,
        modified_files=modified,
    )
